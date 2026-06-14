"""Bridge discovery findings to ingest pipeline."""

from livelead.domain.discovery.finding import DiscoveryFinding
from livelead.domain.events.normalize import MockFinding


def to_ingest_finding(f: DiscoveryFinding) -> MockFinding:
    return MockFinding(
        title=f.title,
        source_url=f.source_url,
        description=f.description,
        organizer=f.organizer,
        region=f.region,
    )
