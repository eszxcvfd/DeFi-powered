from livelead.domain.discovery.lifecycle import aggregate_job_status, can_cancel, is_terminal
from livelead.domain.discovery.models import DiscoveryJobStatus, SourceRunStatus
from livelead.infrastructure.connectors.mock import mock_profile_for_domain, run_mock_source


def test_aggregate_succeeded():
    s = aggregate_job_status([SourceRunStatus.SUCCEEDED], cancelled=False)
    assert s == DiscoveryJobStatus.SUCCEEDED


def test_aggregate_partial():
    s = aggregate_job_status(
        [SourceRunStatus.SUCCEEDED, SourceRunStatus.FAILED],
        cancelled=False,
    )
    assert s == DiscoveryJobStatus.PARTIAL


def test_can_cancel_running():
    assert can_cancel(DiscoveryJobStatus.RUNNING)


def test_terminal():
    assert is_terminal(DiscoveryJobStatus.SUCCEEDED)


def test_mock_success_domain():
    assert mock_profile_for_domain("events.example.com") == "success"
    r = run_mock_source("ok.example.com", cancel_check=lambda: False)
    assert r.status == SourceRunStatus.SUCCEEDED


def test_mock_fail_domain():
    r = run_mock_source("fail.example.com", cancel_check=lambda: False)
    assert r.status == SourceRunStatus.FAILED
