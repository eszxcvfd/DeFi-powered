"""Lead CSV import/export domain types (US-050).

Pure value objects, enums, CSV parser, field mapping
normalizer, and spreadsheet-formula escape helper. The
domain layer does not import any framework, ORM, or
session details so the same code paths can be reused by
the REST handlers, the worker entrypoint (if added in a
later story), and the unit tests.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LeadImportStatus(StrEnum):
    """Closed import-job lifecycle vocabulary (US-050)."""

    PREVIEWED = "previewed"
    APPLIED = "applied"
    FAILED = "failed"


class LeadImportClassification(StrEnum):
    """Closed per-row classification vocabulary (US-050).

    The preview stage assigns one of `READY`, `DUPLICATE`,
    or `INVALID` to every row. The apply stage flips
    `READY` rows to `IMPORTED` once a lead is created and
    marks the rest as `SKIPPED` for auditability.
    """

    READY = "ready"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    IMPORTED = "imported"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Bounded field vocabulary
# ---------------------------------------------------------------------------


# The bounded field set the CSV import surface accepts. The
# set is closed so the field mapper cannot silently
# introduce new columns into the lead domain.
LEAD_IMPORT_FIELDS: tuple[str, ...] = (
    "display_name",
    "company",
    "title",
    "public_url",
    "discovery_source",
    "event_id",
    "campaign_id",
    "interests",
    "pain_points",
    "owner",
    "status",
    "lawful_basis_note",
    "follow_up_date",
    "notes",
    "email",
    "external_id",
    "manual_entry_note",
)

LEAD_IMPORT_REQUIRED_FIELDS: tuple[str, ...] = ("display_name",)

SUPPORTED_LEAD_IMPORT_FIELDS: frozenset[str] = frozenset(LEAD_IMPORT_FIELDS)

# Maximum file size the preview endpoint will accept. 1 MiB
# is generous for a hand-curated list while still bounding
# parser memory under the FastAPI worker.
LEAD_IMPORT_MAX_BYTES = 1 * 1024 * 1024

# Hard cap on the number of data rows the preview will
# process in a single job. Anything beyond this is
# rejected up-front so the bounded slice does not become
# an unbounded ingestion path.
LEAD_IMPORT_MAX_ROWS = 5_000

# Maximum number of import rows returned in a single
# paginated response. Larger pages require explicit
# pagination through `?offset=`.
LEAD_IMPORT_ROW_PAGE_SIZE = 100

# Spreadsheet formula prefixes that must be escaped on
# export so opening the CSV in a spreadsheet does not
# silently execute them.
_FORMULA_PREFIX_CHARS: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LeadImportError(ValueError):
    """Base error for the bounded CSV import surface."""


class LeadImportFileInvalid(LeadImportError):
    """Raised when the CSV cannot be parsed or has the wrong shape."""


class LeadImportFileTooLarge(LeadImportError):
    """Raised when the uploaded file exceeds the size limit."""


class LeadImportMappingInvalid(LeadImportError):
    """Raised when the field mapping references an unknown lead field
    or does not include a required field such as `display_name`."""


class LeadImportProvenanceMissing(LeadImportError):
    """Raised when the preview request omits the required provenance note."""


class LeadImportJobNotFound(LeadImportError):
    """Raised when the requested import job does not exist."""


class LeadImportJobNotReady(LeadImportError):
    """Raised when the import job is not in `previewed` state."""


class LeadImportForbidden(LeadImportError):
    """Raised when the requester cannot run an import or export."""


class LeadExportForbidden(LeadImportError):
    """Raised when the requester cannot run a lead CSV export."""


# ---------------------------------------------------------------------------
# Field mapping helpers
# ---------------------------------------------------------------------------


def normalize_field_name(raw: str) -> str:
    """Lowercase, strip, and collapse separators from a CSV header
    or a user-typed field name so the bounded field set can be
    matched without surprising the user.
    """

    if raw is None:
        return ""
    text = str(raw).strip().lower()
    text = re.sub(r"[\s\-/]+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text


def normalize_mapping(mapping: dict[str, str]) -> dict[str, str]:
    """Normalize a header->field mapping payload.

    Empty entries are dropped. Unknown fields raise
    `LeadImportMappingInvalid` so the bounded surface cannot
    silently pass arbitrary keys into the lead domain.
    """

    if not isinstance(mapping, dict):
        raise LeadImportMappingInvalid("mapping must be an object")

    out: dict[str, str] = {}
    for raw_header, raw_field in mapping.items():
        header = (raw_header or "").strip()
        if not header:
            continue
        field_name = normalize_field_name(str(raw_field or ""))
        if not field_name:
            continue
        if field_name not in SUPPORTED_LEAD_IMPORT_FIELDS:
            raise LeadImportMappingInvalid(f"unknown lead field: {field_name}")
        out[header] = field_name

    if "display_name" not in out.values():
        raise LeadImportMappingInvalid("display_name mapping is required")
    return out


def resolve_mapping(headers: list[str], raw_mapping: dict[str, str] | None) -> dict[str, str]:
    """Resolve a normalized header->field mapping from the raw payload.

    If `raw_mapping` is `None` or empty, the function attempts
    to auto-map each header to a known field by normalizing the
    header name and comparing it against the bounded field
    vocabulary. Headers that still do not match a known field
    are dropped with no error so the preview can show the
    user which columns were ignored.
    """

    headers = [h for h in headers if h is not None]
    if not headers:
        raise LeadImportFileInvalid("csv must include a header row")

    if raw_mapping:
        return normalize_mapping(raw_mapping)

    out: dict[str, str] = {}
    for header in headers:
        candidate = normalize_field_name(header)
        if candidate in SUPPORTED_LEAD_IMPORT_FIELDS:
            out[header] = candidate
    if "display_name" not in out.values():
        # Auto-mapping without display_name is ambiguous; force
        # the user to map the file explicitly.
        raise LeadImportMappingInvalid(
            "could not infer display_name; provide an explicit mapping"
        )
    return out


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------


def _detect_delimiter(sample: str) -> str:
    """Detect a CSV delimiter from a sample of the file.

    Prefers `,` followed by `;` and `\t` based on the first
    line that contains a quote-agnostic candidate. The
    detector never falls back to a multi-character
    delimiter so the bounded slice keeps the parser
    contract narrow.
    """

    if not sample:
        return ","
    first_line = sample.splitlines()[0] if sample else ""
    counts = {",": first_line.count(","), ";": first_line.count(";"), "\t": first_line.count("\t")}
    best = max(counts, key=lambda k: counts[k])
    if counts[best] <= 0:
        return ","
    return best


def parse_csv_payload(payload: bytes) -> tuple[str, list[dict[str, str]], list[str]]:
    """Parse an uploaded CSV payload.

    Returns the detected delimiter, the rows as
    `header -> cell` dictionaries, and the original header
    list in the order they appear in the file. Empty
    trailing rows are dropped.
    """

    if payload is None:
        raise LeadImportFileInvalid("empty upload")
    if len(payload) > LEAD_IMPORT_MAX_BYTES:
        raise LeadImportFileTooLarge(
            f"file exceeds {LEAD_IMPORT_MAX_BYTES} bytes"
        )
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise LeadImportFileInvalid("file must be UTF-8 encoded") from exc
    if not text.strip():
        raise LeadImportFileInvalid("file is empty")

    delimiter = _detect_delimiter(text[:4096])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        raw_headers = next(reader)
    except StopIteration as exc:
        raise LeadImportFileInvalid("csv is missing a header row") from exc

    headers = [h.strip() for h in raw_headers]
    if not any(headers):
        raise LeadImportFileInvalid("csv header row is empty")

    rows: list[dict[str, str]] = []
    for index, raw in enumerate(reader, start=1):
        # Drop rows that are entirely empty.
        if not any((cell or "").strip() for cell in raw):
            continue
        # Pad / trim to the header length so partial rows do
        # not raise csv errors mid-parse.
        if len(raw) < len(headers):
            raw = list(raw) + [""] * (len(headers) - len(raw))
        elif len(raw) > len(headers):
            raw = list(raw[: len(headers)])
        rows.append({headers[i]: (raw[i] or "").strip() for i in range(len(headers))})
        if len(rows) >= LEAD_IMPORT_MAX_ROWS:
            raise LeadImportFileTooLarge(
                f"csv exceeds {LEAD_IMPORT_MAX_ROWS} data rows"
            )

    if not rows:
        raise LeadImportFileInvalid("csv has no data rows")

    return delimiter, rows, headers


def hash_payload(payload: bytes) -> str:
    """Stable SHA-256 hash used for audit evidence and idempotency."""

    return hashlib.sha256(payload or b"").hexdigest()


# ---------------------------------------------------------------------------
# Row classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NormalizedImportRow:
    """Result of normalizing one CSV row through the field mapping.

    The normalized payload is the bounded set of lead fields
    the preview will hand to the lead domain. `raw_cells`
    preserves the original cell text so the audit entry can
    reference it without leaking the whole CSV body.
    """

    row_number: int
    normalized: dict[str, str]
    raw_cells: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClassifiedImportRow:
    """One row after duplicate and validation classification."""

    row_number: int
    normalized: dict[str, str]
    classification: LeadImportClassification
    duplicate_lead_id: UUID | None = None
    duplicate_reason: str = ""
    error_codes: tuple[str, ...] = ()


def normalize_row(row_number: int, raw_row: dict[str, str], mapping: dict[str, str]) -> NormalizedImportRow:
    """Map one raw CSV row through the field mapping.

    Empty cells are dropped. The `raw_cells` snapshot is
    kept in stable field order so the audit trail can
    refer to the original columns without re-parsing the
    file.
    """

    normalized: dict[str, str] = {}
    raw_cells: dict[str, str] = {}
    for header, field_name in mapping.items():
        cell = (raw_row.get(header) or "").strip()
        if not cell:
            continue
        normalized[field_name] = cell
        raw_cells[header] = cell
    return NormalizedImportRow(
        row_number=row_number,
        normalized=normalized,
        raw_cells=raw_cells,
    )


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


def _validate_date(cell: str) -> str | None:
    """Return a stable error code or `None` for a valid date."""

    from datetime import date

    try:
        date.fromisoformat(cell)
    except ValueError:
        return "follow_up_date_invalid"
    return None


def _validate_status(cell: str) -> str | None:
    from livelead.domain.leads.models import LeadStage

    try:
        LeadStage(cell)
    except ValueError:
        return "status_invalid"
    return None


def _validate_url(cell: str) -> str | None:
    from urllib.parse import urlparse

    candidate = cell.strip()
    if not candidate:
        return None
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return "public_url_invalid"
    return None


_FIELD_VALIDATORS: dict[str, callable] = {
    "follow_up_date": _validate_date,
    "status": _validate_status,
    "public_url": _validate_url,
}


def validate_normalized_row(
    row: NormalizedImportRow,
    *,
    has_provenance_note: bool,
) -> tuple[str, ...]:
    """Return the set of error codes for one normalized row.

    A row needs `display_name` and at least one of
    `company`, `public_url`, or a job-level provenance
    note. The provenance note is supplied at the job
    level so the user can document a single batch origin
    and still have individual rows pass the import gate.
    """

    errors: list[str] = []
    for required in LEAD_IMPORT_REQUIRED_FIELDS:
        if not (row.normalized.get(required) or "").strip():
            errors.append(f"{required}_missing")

    if not has_provenance_note:
        if not (row.normalized.get("company") or "").strip() and not (
            row.normalized.get("public_url") or ""
        ).strip():
            errors.append("provenance_or_identifier_missing")

    for field_name, cell in row.normalized.items():
        validator = _FIELD_VALIDATORS.get(field_name)
        if validator is None:
            continue
        err = validator(cell)
        if err:
            errors.append(err)
    return tuple(errors)


# ---------------------------------------------------------------------------
# Spreadsheet-formula escape (US-050 export safety)
# ---------------------------------------------------------------------------


def escape_formula_cell(value: str | None) -> str:
    """Escape a cell value so a spreadsheet will not treat it as a formula.

    The escape is a single leading apostrophe when the cell
    starts with one of the dangerous prefixes. Spreadsheets
    treat the apostrophe as a marker and the user sees the
    original character. Empty values and non-string values
    pass through unchanged.
    """

    text = "" if value is None else str(value)
    if not text:
        return text
    if text[0] in _FORMULA_PREFIX_CHARS:
        return "'" + text
    return text


# ---------------------------------------------------------------------------
# Persisted value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LeadImportJob:
    id: UUID
    organization_id: UUID
    created_by_user_id: str
    actor_role: str
    filename: str
    file_sha256: str
    delimiter: str
    mapping: dict[str, str]
    provenance_note: str
    campaign_id: UUID | None
    status: LeadImportStatus
    total_rows: int
    ready_rows: int
    duplicate_rows: int
    invalid_rows: int
    created_rows: int
    skipped_rows: int
    error_message: str
    created_at: str
    applied_at: str | None


@dataclass(frozen=True, slots=True)
class LeadImportRow:
    id: UUID
    import_job_id: UUID
    organization_id: UUID
    row_number: int
    normalized: dict[str, str]
    classification: LeadImportClassification
    duplicate_lead_id: UUID | None
    duplicate_reason: str
    error_codes: tuple[str, ...]
    created_lead_id: UUID | None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Export value object
# ---------------------------------------------------------------------------


LEAD_EXPORT_FIELDS: tuple[str, ...] = (
    "id",
    "display_name",
    "company",
    "title",
    "public_url",
    "owner",
    "stage",
    "discovery_source",
    "campaign_id",
    "event_id",
    "interests",
    "pain_points",
    "lawful_basis_note",
    "follow_up_date",
    "notes",
    "manual_entry_note",
    "email_hash",
    "external_id",
    "origin_kind",
    "created_by",
    "created_at",
    "updated_at",
)


def build_export_csv(rows: list[dict[str, str | None]], *, delimiter: str = ",") -> bytes:
    """Serialize the export rows to a CSV byte string with formula escaping.

    Each cell is run through `escape_formula_cell` so a
    spreadsheet does not interpret a value as a formula. The
    header row is the bounded set of export fields, in the
    same order as `LEAD_EXPORT_FIELDS`.
    """

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    writer.writerow(LEAD_EXPORT_FIELDS)
    for row in rows:
        writer.writerow([escape_formula_cell(row.get(field, "")) for field in LEAD_EXPORT_FIELDS])
    return buf.getvalue().encode("utf-8")


__all__ = [
    "LEAD_EXPORT_FIELDS",
    "LEAD_IMPORT_FIELDS",
    "LEAD_IMPORT_MAX_BYTES",
    "LEAD_IMPORT_MAX_ROWS",
    "LEAD_IMPORT_REQUIRED_FIELDS",
    "LEAD_IMPORT_ROW_PAGE_SIZE",
    "ClassifiedImportRow",
    "LeadExportForbidden",
    "LeadImportClassification",
    "LeadImportError",
    "LeadImportFileInvalid",
    "LeadImportFileTooLarge",
    "LeadImportForbidden",
    "LeadImportJob",
    "LeadImportJobNotFound",
    "LeadImportJobNotReady",
    "LeadImportMappingInvalid",
    "LeadImportProvenanceMissing",
    "LeadImportRow",
    "LeadImportStatus",
    "NormalizedImportRow",
    "SUPPORTED_LEAD_IMPORT_FIELDS",
    "build_export_csv",
    "escape_formula_cell",
    "hash_payload",
    "normalize_field_name",
    "normalize_mapping",
    "normalize_row",
    "parse_csv_payload",
    "resolve_mapping",
    "validate_normalized_row",
]
