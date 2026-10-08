"""Scratch dir for suite images and agent workspaces: never a fixed, shared /tmp path."""

import stat
from pathlib import Path

from hackbench.polaron.__main__ import _scratch_dir


def test_default_is_a_private_temp_dir_removed_afterwards() -> None:
    with _scratch_dir(None) as a, _scratch_dir(None) as b:
        assert a != b  # unpredictable, unique per run
        assert a.is_dir()
        assert stat.S_IMODE(a.stat().st_mode) == 0o700  # owner-only
    assert not a.exists()


def test_an_explicit_dir_is_used_as_is_and_kept(tmp_path: Path) -> None:
    with _scratch_dir(tmp_path) as d:
        assert d == tmp_path
    assert tmp_path.is_dir()
