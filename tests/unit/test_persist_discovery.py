from uuid import uuid4

from livelead.application.events.persist_discovery import persist_events_from_discovery_job
from livelead.domain.discovery.finding import DiscoveryFinding


def test_persist_skips_synthetic_fallback_when_no_findings(tmp_path, monkeypatch):
    db = tmp_path / "t.sqlite3"
    monkeypatch.setenv("LIVELEAD_SQLITE_PATH", str(db))
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "false")

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from livelead.infrastructure.db.models import Base, EventRow

    org = str(uuid4())
    camp = str(uuid4())
    sid = str(uuid4())
    job_id = str(uuid4())

    url = f"sqlite:///{db}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.close()

    created = persist_events_from_discovery_job(
        job_id=job_id,
        organization_id=org,
        campaign_id=camp,
        sources_progress={sid: {"status": "succeeded", "items_found": 5}},
        source_id_to_domain={sid: "coindesk.com"},
        source_findings={},
    )
    assert created == 0

    session = sessionmaker(bind=engine)()
    rows = session.execute(select(EventRow)).scalars().all()
    session.close()
    assert len(rows) == 0


def test_persist_ingests_real_findings(tmp_path, monkeypatch):
    db = tmp_path / "t2.sqlite3"
    monkeypatch.setenv("LIVELEAD_SQLITE_PATH", str(db))

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from livelead.infrastructure.db.models import Base, EventRow

    org = str(uuid4())
    camp = str(uuid4())
    sid = str(uuid4())
    job_id = str(uuid4())

    url = f"sqlite:///{db}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)

    finding = DiscoveryFinding(
        title="Real Crypto Summit 2026",
        source_url="https://coindesk.com/events/real-1",
        description="From RSS feed",
        region="US",
    )
    created = persist_events_from_discovery_job(
        job_id=job_id,
        organization_id=org,
        campaign_id=camp,
        sources_progress={sid: {"status": "succeeded", "items_found": 1}},
        source_id_to_domain={sid: "coindesk.com"},
        source_findings={sid: [finding]},
    )
    assert created == 1

    session = sessionmaker(bind=engine)()
    rows = session.execute(select(EventRow)).scalars().all()
    session.close()
    assert len(rows) == 1
    assert "Real Crypto Summit" in rows[0].canonical_title
