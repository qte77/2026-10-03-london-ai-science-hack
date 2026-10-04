"""Config seams: settings from env, version from package metadata, use-case profile, Task shape."""

import tomllib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import hackbench
from hackbench.api import create_app
from hackbench.profile import load_profile
from hackbench.settings import Settings
from hackbench.task import Task


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "HACKBENCH_BASE_URL",
        "HACKBENCH_PROFILE",
        "HACKBENCH_COMMIT",
        "HACKBENCH_DATA_DIR",
        "HACKBENCH_RESULTS_PATH",
        "HACKBENCH_SNAPSHOT_PATH",
    ):
        monkeypatch.delenv(var, raising=False)
    assert Settings.from_env() == Settings(
        base_url="http://localhost:8000",
        profile="polaron",
        commit="local",
        data_dir="data/polaron",
        results_path="results/cycle/results.json",
        snapshot_path="data/results.snapshot.json",
    )


def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HACKBENCH_BASE_URL", "https://example.test/")
    monkeypatch.setenv("HACKBENCH_PROFILE", "other")
    s = Settings.from_env()
    assert s.base_url == "https://example.test"  # trailing slash stripped
    assert s.profile == "other"


def test_version_comes_from_package_metadata() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    assert hackbench.__version__ == pyproject["project"]["version"]
    assert create_app().version == hackbench.__version__


def test_polaron_profile_holds_the_domain_copy() -> None:
    p = load_profile("polaron")
    assert p.tagline
    assert p.when_to_use
    assert p.when_not_to_use
    assert p.skill.id == "evaluate-qc-verdict"
    assert any("detector-channel" in rule for rule in p.integrity_rules)


def test_unknown_profile_fails_loudly() -> None:
    with pytest.raises(FileNotFoundError):
        load_profile("no-such-profile")


def test_served_copy_comes_from_the_profile() -> None:
    p = load_profile("polaron")
    text = TestClient(create_app()).get("/llms.txt").text
    assert p.tagline in text
    assert p.when_to_use[0] in text


class _FakeTask:
    def load_items(self) -> Sequence[Mapping[str, object]]:
        return [{"id": "a"}]

    def tools(self) -> Mapping[str, Callable[..., object]]:
        return {}

    def ground_truth(self, item_id: str) -> object:
        return "accept"

    def honeypots(self) -> Sequence[str]:
        return []

    def score(self, item_id: str, verdict: Mapping[str, object]) -> Mapping[str, float]:
        return {"correct": 1.0}


def test_a_domain_task_satisfies_the_task_protocol() -> None:
    assert isinstance(_FakeTask(), Task)
    assert not isinstance(object(), Task)
