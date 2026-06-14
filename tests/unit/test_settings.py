from pathlib import Path

from livelead.runtime.settings import AppSettings, parse_settings


def test_default_sqlite_path_under_data():
    s = AppSettings()
    assert s.sqlite_path == Path("data/livelead.sqlite3")


def test_database_url_uses_aiosqlite(monkeypatch, tmp_path):
    p = tmp_path / "custom.sqlite3"
    monkeypatch.setenv("LIVELEAD_SQLITE_PATH", str(p))
    s = parse_settings()
    assert "sqlite+aiosqlite:///" in s.database_url
    assert str(p.resolve()) in s.database_url