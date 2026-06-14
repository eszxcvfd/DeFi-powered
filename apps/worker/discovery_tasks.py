import dramatiq

from livelead.application.discovery.service import run_discovery_job as _run
from livelead.infrastructure.queue.broker import configure_broker
from livelead.runtime.settings import parse_settings

configure_broker(parse_settings())


@dramatiq.actor(queue_name="default", max_retries=0)
def run_discovery_job(job_id: str) -> None:
    _run(job_id)
