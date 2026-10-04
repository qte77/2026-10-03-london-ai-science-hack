"""`/v1/results` and `/results.md`: live volume (via `reload`) -> snapshot -> 503."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hackbench.api import create_app

SAMPLE: dict[str, Any] = {
    "schema": "hackbench-results/1",
    "commit": "abc123",
    "generated_at": "2026-10-04T00:00:00Z",
    "batches": {
        "Batch_1": {"parallax_brief": None, "hackbench": None, "agree": None},
        "Batch_2": {
            "parallax_brief": {"claims": [{"id": "decision.verdict", "label": "ACCEPT"}]},
            "hackbench": {
                "verdict": "accept",
                "driving": [],
                "acquisition_flags": [],
                "n_fov": 7,
                "kpis": {},
            },
            "agree": True,
        },
    },
    "suite": {"chosen_k": 2.5, "heldout_accuracy": 0.5, "items": {}},
    "kpi_robustness": {
        "porosity_pct": {"role": "material", "imaging_shift": 0.1, "material_shift": 0.9}
    },
    "agents": {"status": "ok", "configs": {}},
    "papers": {"status": "skipped", "reason": "unset"},
    "cycle": {
        "started": "t0",
        "finished": "t1",
        "stages": [{"name": "reference", "status": "ok", "seconds": 0.1}],
        "journal_sha": "deadbeef",
    },
}


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_falls_back_to_the_snapshot_when_no_live_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HACKBENCH_RESULTS_PATH", str(tmp_path / "missing.json"))
    snapshot = tmp_path / "snap.json"
    _write(snapshot, SAMPLE)
    monkeypatch.setenv("HACKBENCH_SNAPSHOT_PATH", str(snapshot))

    r = TestClient(create_app()).get("/v1/results")

    assert r.status_code == 200
    assert r.json()["commit"] == "abc123"
    assert r.headers["x-results-source"] == "snapshot"


def test_prefers_the_live_file_over_the_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live = tmp_path / "live.json"
    _write(live, {**SAMPLE, "commit": "live-sha"})
    monkeypatch.setenv("HACKBENCH_RESULTS_PATH", str(live))
    monkeypatch.setenv("HACKBENCH_SNAPSHOT_PATH", str(tmp_path / "missing.json"))

    r = TestClient(create_app()).get("/v1/results")

    assert r.json()["commit"] == "live-sha"
    assert r.headers["x-results-source"] == "live"


def test_calls_reload_before_checking_the_live_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live = tmp_path / "live.json"
    monkeypatch.setenv("HACKBENCH_RESULTS_PATH", str(live))
    monkeypatch.setenv("HACKBENCH_SNAPSHOT_PATH", str(tmp_path / "missing.json"))
    calls = []

    def reload_fn() -> None:
        calls.append(1)
        _write(live, SAMPLE)  # simulate the volume appearing after a reload

    r = TestClient(create_app(reload=reload_fn)).get("/v1/results")

    assert calls == [1]
    assert r.status_code == 200


def test_a_broken_reload_still_falls_back_to_the_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HACKBENCH_RESULTS_PATH", str(tmp_path / "missing.json"))
    snapshot = tmp_path / "snap.json"
    _write(snapshot, SAMPLE)
    monkeypatch.setenv("HACKBENCH_SNAPSHOT_PATH", str(snapshot))

    def broken() -> None:
        raise RuntimeError("volume not mounted")

    r = TestClient(create_app(reload=broken)).get("/v1/results")
    assert r.status_code == 200


def test_503_with_nothing_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HACKBENCH_RESULTS_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("HACKBENCH_SNAPSHOT_PATH", str(tmp_path / "also-missing.json"))

    r = TestClient(create_app()).get("/v1/results")

    assert r.status_code == 503


def test_results_md_renders_batches_suite_robustness_and_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HACKBENCH_RESULTS_PATH", str(tmp_path / "missing.json"))
    snapshot = tmp_path / "snap.json"
    _write(snapshot, SAMPLE)
    monkeypatch.setenv("HACKBENCH_SNAPSHOT_PATH", str(snapshot))

    r = TestClient(create_app()).get("/results.md")

    assert r.headers["content-type"].startswith("text/markdown")
    assert "Batch_2" in r.text
    assert "hackbench=`accept`" in r.text
    assert "parallax=`accept`" in r.text
    assert "agree=`True`" in r.text
    assert "0.5" in r.text  # heldout accuracy
    assert "porosity_pct" in r.text
    assert "reference: ok" in r.text  # cycle stage


def test_results_md_is_503_with_nothing_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HACKBENCH_RESULTS_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("HACKBENCH_SNAPSHOT_PATH", str(tmp_path / "also-missing.json"))

    r = TestClient(create_app()).get("/results.md")

    assert r.status_code == 503
    assert r.headers["content-type"].startswith("text/markdown")


def test_ui_is_mounted_only_when_dist_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ui" / "dist").mkdir(parents=True)
    (tmp_path / "ui" / "dist" / "index.html").write_text("<h1>ui</h1>")

    r = TestClient(create_app()).get("/results/")

    assert r.status_code == 200
    assert "<h1>ui</h1>" in r.text


def test_no_ui_mount_without_dist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # no ui/dist here
    r = TestClient(create_app()).get("/results/")
    assert r.status_code == 404
