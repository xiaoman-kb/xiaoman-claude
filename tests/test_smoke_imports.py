from pathlib import Path

from xiaoman_agent import config
from xiaoman_agent.io_tools import safe_path


def test_config_exports_exist():
    assert config.WORKDIR is not None
    assert config.REPO_ROOT is not None


def test_safe_path_resolves_inside_base(tmp_path: Path):
    p = safe_path("a.txt", base_dir=tmp_path)
    assert p == tmp_path / "a.txt"
