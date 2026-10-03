"""Item 9a: material KPIs decide, imaging KPIs only flag; k is calibrated on train only."""

from pathlib import Path

from hackbench.polaron.task import PolaronTask, calibrate_k
from hackbench.profile import load_profile
from tests.polaron.conftest import Truth

MATERIAL = {
    "porosity_pct": 10.0,
    "bright_phase_pct": 5.0,
    "pore_density_per_um2": 4.0,
    "pore_diameter_um": 0.1,
}


def _rows(n: int, **overrides: float) -> list[dict[str, float]]:
    """n FOVs with small natural spread; overrides shift a KPI for the whole batch."""
    rows = []
    for i in range(n):
        wobble = 1 + 0.02 * ((i % 3) - 1)
        row = {k: v * wobble for k, v in MATERIAL.items()}
        row |= {"edge_density": 0.04 * wobble, "intensity_std": 0.09 * wobble}
        row |= {k: v * wobble for k, v in overrides.items()}
        rows.append(row)
    return rows


def _task(tmp_path: Path) -> PolaronTask:
    return PolaronTask(tmp_path, load_profile("polaron").domain)


def test_imaging_only_shift_is_accepted_with_an_acquisition_flag(tmp_path: Path) -> None:
    per_batch = {"Batch_1": _rows(6), "B": _rows(6, edge_density=0.02, intensity_std=0.05)}
    out = _task(tmp_path).compare(per_batch, "B")
    assert out["verdict"] == "accept"
    assert set(out["acquisition_flags"]) == {"edge_density", "intensity_std"}


def test_material_shift_still_drives_a_reject(tmp_path: Path) -> None:
    per_batch = {"Batch_1": _rows(6), "B": _rows(6, porosity_pct=25.0)}
    out = _task(tmp_path).compare(per_batch, "B")
    assert out["verdict"] == "reject"
    assert out["driving"] == ["porosity_pct"]
    assert out["acquisition_flags"] == []


def test_calibrate_k_picks_the_most_accurate_tolerance_on_training_data(tmp_path: Path) -> None:
    per_batch = {
        "S_base": _rows(6),
        "S_none": _rows(6, porosity_pct=10.1),  # wobble well within 2 x baseline SD: accept
        "S_big": _rows(6, porosity_pct=16.0),  # large shift: must be rejected
    }
    truth = {"S_none": {"expected": ["accept"]}, "S_big": {"expected": ["reject"]}}
    best_k, table = calibrate_k(_task(tmp_path), per_batch, "S_base", truth, grid=(0.1, 2.0, 50.0))
    assert best_k == 2.0  # 0.1 flags the wobble; 50 misses the real shift
    assert table[2.0] == 1.0
    assert table[0.1] < 1.0
    assert table[50.0] < 1.0


def test_synthetic_end_to_end_contrast_drift_is_no_longer_rejected(
    tmp_path: Path, dataset: dict[str, list[Truth]]
) -> None:
    from hackbench.polaron.drift import build_suite

    out = tmp_path / "suite"
    build_suite(tmp_path, "Batch_1", "BSE", out, levels={"contrast": (0.7,)}, seed=0)
    params = {**load_profile("polaron").domain, "baseline_batch": "S_base", "crop_px": 0}
    results = PolaronTask(out, params).run(journal_path=tmp_path / "j.jsonl")
    assert results["S_contrast_0.7"]["verdict"] != "reject"
