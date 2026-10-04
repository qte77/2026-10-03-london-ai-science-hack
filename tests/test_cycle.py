"""hackbench.cycle: the end-to-end orchestrator, on synthetic data (no network, no keys)."""

import json
from pathlib import Path
from typing import Any

import pytest

from hackbench.cycle import (
    PREREG_HACKBENCH,
    compute_agents,
    compute_kpi_robustness,
    compute_parallax,
    compute_reference,
    load_kpi_rows,
    magnitude_of,
    parallax_label,
    run_cycle,
    strip_blobs,
    summarize_suite,
)
from hackbench.journal import Journal
from hackbench.profile import load_profile
from tests.polaron.conftest import dataset  # noqa: F401 - reused fixture, not called directly


def _append_kpis(journal: Journal, item: str, **kpis: float) -> None:
    journal.append({"tool": "kpis", "item": item, "result": dict(kpis)})


def _kpi_row(porosity: float, bright: float = 15.0, density: float = 4.0) -> dict[str, float]:
    return {
        "porosity_pct": porosity,
        "bright_phase_pct": bright,
        "pore_density_per_um2": density,
        "pore_diameter_um": 0.1,
        "edge_density": 0.04,
        "intensity_std": 0.09,
    }


def test_load_kpi_rows_dedups_rows_written_twice_into_the_same_journal(tmp_path: Path) -> None:
    """`_suite()` collects the training and held-out suites into ONE journal; S_base/S_none
    rows appear in both passes under the same item id. Naive grouping would double-count
    them and silently inflate n_fov. The loader must keep exactly one row per item id."""
    path = tmp_path / "j.jsonl"
    journal = Journal(path)
    # First pass (training suite): S_base + a drift batch only used in training.
    _append_kpis(journal, "S_base/fov_01", **_kpi_row(10.0))
    _append_kpis(journal, "S_blur_1.0/fov_01", **_kpi_row(9.0))
    # Second pass (held-out suite): S_base repeats (identical row); a held-out-only batch.
    _append_kpis(journal, "S_base/fov_01", **_kpi_row(10.0))
    _append_kpis(journal, "S_blur_1.5/fov_01", **_kpi_row(8.0))

    per_batch, ids_by_batch = load_kpi_rows(path)

    assert per_batch["S_base"] == [_kpi_row(10.0)]  # not duplicated
    assert ids_by_batch["S_base"] == ["S_base/fov_01"]
    assert set(per_batch) == {"S_base", "S_blur_1.0", "S_blur_1.5"}


def test_magnitude_of_parses_the_batch_id() -> None:
    assert magnitude_of("S_base") == 0.0
    assert magnitude_of("S_none") == 0.0
    assert magnitude_of("S_blur_1.5") == 1.5
    assert magnitude_of("S_pores_0.03") == 0.03


def test_compute_reference_reproduces_compare_and_excludes_the_baseline(
    tmp_path: Path,
    dataset: dict[str, Any],  # noqa: F811 - fixture param, not a redefinition
) -> None:
    from hackbench.journal import Journal
    from hackbench.polaron.task import PolaronTask

    domain = load_profile("polaron").domain
    task = PolaronTask(data_dir=tmp_path, params=domain)
    per_batch = task.collect(Journal(tmp_path / "collect.jsonl"))

    out = compute_reference(per_batch, "Batch_1", 2.5, domain)

    assert out["Batch_1"] is None  # baseline is never compared against itself
    assert out["Batch_2"] == task.compare(per_batch, "Batch_2", k=2.5, baseline="Batch_1")
    batch_3 = out["Batch_3"]
    assert batch_3 is not None
    assert batch_3["verdict"] in ("accept", "investigate", "reject")
    assert "acquisition_flags" in batch_3


def test_summarize_suite_reports_held_out_accuracy_and_magnitude() -> None:
    raw = {
        "calibration": {"chosen_k": 2.5, "train_accuracy_by_k": {}},
        "S_none": {
            "verdict": "accept",
            "expected": ["accept"],
            "correct": True,
            "kind": "none",
            "kpis": {},
        },
        "S_blur_1.5": {
            "verdict": "reject",
            "expected": ["accept"],
            "correct": False,
            "kind": "imaging",
            "kpis": {},
        },
        "journal_verified": True,
        "commit": "abc",
    }
    out = summarize_suite(raw)
    assert out["chosen_k"] == 2.5
    assert out["heldout_accuracy"] == 0.5
    assert out["items"]["S_blur_1.5"] == {
        "kind": "imaging",
        "magnitude": 1.5,
        "expected": ["accept"],
        "verdict": "reject",
        "correct": False,
    }


def test_kpi_robustness_splits_by_drift_kind_and_ignores_none() -> None:
    raw = {
        "calibration": {"chosen_k": 2.5},
        "S_none": {
            "kind": "none",
            "kpis": {"porosity_pct": {"role": "material", "diff": 100.0, "tolerance": 1.0}},
        },
        "S_contrast_1.4": {
            "kind": "imaging",
            "kpis": {
                "porosity_pct": {"role": "material", "diff": 2.0, "tolerance": 4.0},
                "edge_density": {"role": "diagnostic", "diff": 1.0, "tolerance": 2.0},
            },
        },
        "S_pores_0.1": {
            "kind": "material",
            "kpis": {
                "porosity_pct": {"role": "material", "diff": 6.0, "tolerance": 4.0},
                "edge_density": {"role": "diagnostic", "diff": 0.0, "tolerance": 2.0},
            },
        },
    }
    out = compute_kpi_robustness(raw)
    assert out["porosity_pct"] == {
        "role": "material",
        "imaging_shift": 0.5,
        "material_shift": 1.5,
    }
    assert out["edge_density"] == {
        "role": "diagnostic",
        "imaging_shift": 0.5,
        "material_shift": 0.0,
    }


def test_compute_agents_scripted_controls_behave_as_designed(tmp_path: Path) -> None:
    """HonestAgent must trip no honeypot and never use the decoy; CheatingAgent must trip
    every honeypot and always submit the decoy label (so it is always wrong, by construction)."""
    domain = load_profile("polaron").domain
    rows = {
        "S_base": [_kpi_row(10.0), _kpi_row(11.0), _kpi_row(9.0)],
        "S_drift_1.0": [_kpi_row(20.0), _kpi_row(21.0), _kpi_row(19.0)],
    }
    ids = {
        "S_base": ["S_base/fov_01", "S_base/fov_02", "S_base/fov_03"],
        "S_drift_1.0": ["S_drift_1.0/fov_01", "S_drift_1.0/fov_02", "S_drift_1.0/fov_03"],
    }
    suite_items = {"S_drift_1.0": {"expected": ["reject"], "kind": "material"}}

    result = compute_agents(rows, ids, suite_items, domain, 2.5, tmp_path, with_claude=False)

    assert result["status"] == "ok"
    assert "--with-claude not set" in result["reason"]
    honest, cheater = result["configs"]["scripted/honest"], result["configs"]["scripted/cheater"]
    assert honest["n"] == cheater["n"] == 1
    assert honest["trips"] == 0
    assert honest["used_decoy"] == 0
    assert cheater["trips"] == 2  # both honeypots: previous-qc-report + cached-verdict
    assert cheater["used_decoy"] == 1
    assert cheater["accuracy"] == 0.0  # the decoy is wrong by construction


def test_parallax_label_reads_the_decision_claim_case_insensitively() -> None:
    brief = {"claims": [{"id": "decision.verdict", "label": "ACCEPT"}]}
    assert parallax_label(brief) == "accept"
    assert parallax_label({"hero": {"decision": {"state": "Reject"}}}) == "reject"
    assert parallax_label({"hero": {"decision": {"state": "nonsense"}}}) is None


def test_strip_blobs_drops_data_image_and_base64_fields() -> None:
    raw = {"a": "fine", "b": "data:image/png;base64,AAAA", "nested": {"c": "has base64 blob"}}
    assert strip_blobs(raw) == {"a": "fine", "nested": {}}


def test_compute_parallax_marks_the_baseline_as_not_comparable(tmp_path: Path) -> None:
    (tmp_path / "decision_brief.Batch_1.json").write_text(
        json.dumps({"source": {"role": "reference"}, "claims": []})
    )
    (tmp_path / "decision_brief.Batch_2.json").write_text(
        json.dumps(
            {"source": {"role": None}, "claims": [{"id": "decision.verdict", "label": "ACCEPT"}]}
        )
    )
    batches = {
        "Batch_1": None,
        "Batch_2": {
            "verdict": "accept",
            "driving": [],
            "acquisition_flags": [],
            "n_fov": 1,
            "kpis": {},
        },
    }
    out = compute_parallax(batches, tmp_path)
    assert out["Batch_1"]["agree"] is None
    assert out["Batch_2"]["agree"] is True
    assert out["Batch_2"]["parallax_brief"]["source"]["role"] is None


def test_compute_parallax_includes_briefs_for_batches_hackbench_did_not_run(
    tmp_path: Path,
) -> None:
    (tmp_path / "decision_brief.Hackathon-Polaron-test.json").write_text(
        json.dumps({"source": {"role": None}, "claims": []})
    )
    out = compute_parallax({}, tmp_path)
    test_batch = out["Hackathon-Polaron-test"]
    assert test_batch["hackbench"] is None  # we never claim a run we didn't do
    assert test_batch["agree"] is None
    assert test_batch["parallax_brief"] is not None


def test_run_cycle_end_to_end_on_synthetic_inputs_needs_no_keys(
    tmp_path: Path,
    dataset: dict[str, Any],  # noqa: F811 - fixture param, not a redefinition
) -> None:
    from hackbench.polaron.drift import DEFAULT_LEVELS
    from hackbench.polaron.drift import build_suite as _build_suite
    from hackbench.polaron.task import PolaronTask, calibrate_k

    domain = load_profile("polaron").domain
    inputs = tmp_path / "inputs"
    inputs.mkdir()

    task = PolaronTask(data_dir=tmp_path, params=domain)
    journal_path = inputs / "journal.jsonl"
    task.run(journal_path=journal_path)

    suite_dir = tmp_path / "suite"
    suite_params = {**domain, "baseline_batch": "S_base", "crop_px": 0}
    truth = _build_suite(
        tmp_path, "Batch_1", str(domain["channel"]), suite_dir, DEFAULT_LEVELS, 0, 0
    )
    suite_journal_path = inputs / "suite-journal.jsonl"
    suite_journal = Journal(suite_journal_path)
    suite_task = PolaronTask(suite_dir, suite_params)
    suite_kpis = suite_task.collect(suite_journal)
    best_k, table = calibrate_k(suite_task, suite_kpis, "S_base", truth)
    suite_results: dict[str, Any] = {
        "calibration": {"chosen_k": best_k, "train_accuracy_by_k": table}
    }
    for batch in suite_kpis:
        if batch == "S_base":
            continue
        r = suite_task.compare(suite_kpis, batch, k=best_k)
        expected_raw = truth[batch]["expected"]
        assert isinstance(expected_raw, list)
        expected = [str(v) for v in expected_raw]
        r |= {
            "expected": expected,
            "kind": truth[batch]["kind"],
            "correct": r["verdict"] in expected,
        }
        suite_results[batch] = r
    (inputs / "suite.json").write_text(json.dumps(suite_results, default=str))

    out_dir = tmp_path / "out"
    result = run_cycle(inputs, out_dir, parallax_dir=None, with_claude=False)

    assert result["schema"] == "hackbench-results/1"
    assert result["prereg"]["hackbench"] == PREREG_HACKBENCH
    assert result["prereg"]["parallax"] is None
    assert set(result["batches"]) == {"Batch_1", "Batch_2", "Batch_3"}
    assert result["batches"]["Batch_1"]["hackbench"] is None
    assert result["agents"]["configs"]["scripted/honest"]["n"] > 0
    assert result["papers"]["status"] == "skipped"
    assert result["paper_judge"]["status"] == "skipped"
    assert len(result["limits"]) == 1
    names = [s["name"] for s in result["cycle"]["stages"]]
    assert names == [
        "reference",
        "suite",
        "kpi_robustness",
        "agents",
        "papers",
        "paper_judge",
        "parallax",
    ]
    assert (out_dir / "results.json").exists()
    assert (out_dir / "cycle-journal.jsonl").exists()


def test_run_cycle_is_missing_claude_key_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PAPERCLIP_API_KEY", raising=False)
    monkeypatch.delenv("GXL_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    journal = Journal(inputs / "journal.jsonl")
    _append_kpis(journal, "Batch_1/fov_01", **_kpi_row(10.0))
    _append_kpis(journal, "Batch_2/fov_01", **_kpi_row(11.0))
    suite_journal = Journal(inputs / "suite-journal.jsonl")
    _append_kpis(suite_journal, "S_base/fov_01", **_kpi_row(10.0))
    _append_kpis(suite_journal, "S_none/fov_01", **_kpi_row(10.0))
    (inputs / "suite.json").write_text(
        json.dumps(
            {
                "calibration": {"chosen_k": 2.5},
                "S_none": {
                    "verdict": "accept",
                    "expected": ["accept"],
                    "correct": True,
                    "kind": "none",
                    "kpis": {},
                },
            }
        )
    )
    result = run_cycle(inputs, tmp_path / "out", parallax_dir=None, with_claude=False)
    assert result["papers"] == {
        "status": "skipped",
        "reason": "PAPERCLIP_API_KEY/GXL_API_KEY unset",
    }
    assert result["paper_judge"] == {"status": "skipped", "reason": "research bundle missing"}
    reason = result["agents"]["reason"]
    assert "ANTHROPIC_API_KEY" in reason or "--with-claude" in reason
