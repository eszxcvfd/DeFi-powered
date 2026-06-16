import pytest
from apps.api.main import create_app
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _browser_automation_stub(monkeypatch):
    monkeypatch.setenv("LIVELEAD_BROWSER_AUTOMATION_MODE", "stub")
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "true")
    monkeypatch.setenv("LIVELEAD_DISCOVERY_COPILOT_PROVIDER", "deterministic")
    monkeypatch.delenv("LIVELEAD_GOOGLE_AI_STUDIO_API_KEY", raising=False)
    from livelead.infrastructure.browser.factory import reset_runtime_cache_for_tests

    reset_runtime_cache_for_tests()
    yield
    reset_runtime_cache_for_tests()


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db = tmp_path / "test.sqlite3"
    monkeypatch.setenv("LIVELEAD_SQLITE_PATH", str(db))
    monkeypatch.setenv("LIVELEAD_REDIS_URL", "redis://127.0.0.1:6379/0")
    app = create_app()
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.app = app  # type: ignore[attr-defined]
            yield ac
