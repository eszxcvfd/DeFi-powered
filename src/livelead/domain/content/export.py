"""Export approved content without internal review metadata."""

from livelead.domain.content.models import GeneratedContentDraft


def export_markdown(draft: GeneratedContentDraft) -> str:
    settings = draft.settings
    lines = [
        f"# Approved content — variant {draft.variant_index + 1}",
        "",
        f"- Platform: {settings.platform.value}",
        f"- Type: {settings.content_type.value}",
        f"- Language: {settings.language}",
        f"- Tone: {settings.tone}",
        "",
        draft.body_text.strip(),
        "",
    ]
    return "\n".join(lines)


def export_csv(draft: GeneratedContentDraft) -> str:
    settings = draft.settings
    body = draft.body_text.replace('"', '""').replace("\r\n", "\n").replace("\n", "\\n")
    return (
        "variant_index,platform,content_type,language,tone,body_text\n"
        f'{draft.variant_index},"{settings.platform.value}","{settings.content_type.value}",'
        f'"{settings.language}","{settings.tone}","{body}"\n'
    )
