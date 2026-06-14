import os

from livelead.runtime.env_bootstrap import load_repo_dotenv, repo_root


def test_load_repo_dotenv_sets_livelead_vars(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=false\n", encoding="utf-8")
    monkeypatch.delenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", raising=False)
    monkeypatch.setattr("livelead.runtime.env_bootstrap.repo_root", lambda: tmp_path)
    load_repo_dotenv()
    assert os.environ.get("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS") == "false"


def test_repo_root_points_at_project():
    root = repo_root()
    assert (root / "src" / "livelead").is_dir()
    assert (root / "apps" / "api").is_dir()
