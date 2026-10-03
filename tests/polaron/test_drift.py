"""Synthetic drift injection: each drift moves the KPIs it should, with known ground truth."""

import json
from pathlib import Path

import numpy as np
import pytest

from hackbench.polaron.drift import DRIFTS, apply_drift, build_suite
from hackbench.polaron.kpis import compute_kpis
from hackbench.polaron.task import PolaronTask
from hackbench.profile import load_profile
from tests.polaron.conftest import PX_NM, Truth, make_image


def _k(img: np.ndarray) -> dict[str, float]:
    return compute_kpis(img, PX_NM)


def test_drift_catalogue_separates_material_from_imaging() -> None:
    kinds = {name: d.kind for name, d in DRIFTS.items()}
    assert kinds == {
        "pores": "material",
        "coarsen": "material",
        "contrast": "imaging",
        "blur": "imaging",
    }


def test_added_pores_raise_porosity_by_about_the_requested_amount() -> None:
    img, _ = make_image(0.10, 0.05, seed=11)
    drifted = apply_drift(img, "pores", 0.08, seed=0)
    gain = _k(drifted)["porosity_pct"] - _k(img)["porosity_pct"]
    assert gain == pytest.approx(8.0, abs=2.0)


def test_coarsening_grows_pores() -> None:
    img, _ = make_image(0.12, 0.05, seed=12)
    assert _k(apply_drift(img, "coarsen", 1.4))["pore_diameter_um"] > _k(img)["pore_diameter_um"]


def test_blur_lowers_edge_density() -> None:
    img, _ = make_image(0.12, 0.05, seed=13)
    assert _k(apply_drift(img, "blur", 2.0))["edge_density"] < _k(img)["edge_density"]


def test_contrast_changes_intensity_spread_not_porosity() -> None:
    img, _ = make_image(0.12, 0.05, seed=14)
    before, after = _k(img), _k(apply_drift(img, "contrast", 0.8))
    assert after["intensity_std"] < before["intensity_std"]
    assert after["porosity_pct"] == pytest.approx(before["porosity_pct"], abs=1.0)


def test_build_suite_writes_halves_and_truth(
    tmp_path: Path, dataset: dict[str, list[Truth]]
) -> None:
    out = tmp_path / "suite"
    truth = build_suite(
        source_dir=tmp_path,
        baseline="Batch_1",
        channel="BSE",
        out_dir=out,
        levels={"pores": (0.08,), "contrast": (0.8,)},
        seed=0,
    )
    assert set(truth) == {"S_base", "S_none", "S_pores_0.08", "S_contrast_0.8"}
    assert truth["S_none"]["expected"] == ["accept"]
    assert truth["S_pores_0.08"]["expected"] == ["reject"]
    assert truth["S_contrast_0.8"]["expected"] == ["accept"]
    assert json.loads((out / "truth.json").read_text()) == truth
    assert len(list((out / "S_base").glob("*_BSE.tif"))) == 5


def test_suite_runs_through_the_pipeline_and_scores(
    tmp_path: Path, dataset: dict[str, list[Truth]]
) -> None:
    out = tmp_path / "suite"
    build_suite(
        source_dir=tmp_path,
        baseline="Batch_1",
        channel="BSE",
        out_dir=out,
        levels={"pores": (0.15,)},
        seed=0,
    )
    params = {**load_profile("polaron").domain, "baseline_batch": "S_base"}
    task = PolaronTask(out, params)
    results = task.run(journal_path=tmp_path / "suite.jsonl")
    assert results["S_pores_0.15"]["verdict"] == "reject"
    assert task.score("S_pores_0.15", {"verdict": "reject"}) == {"correct": 1.0}
    assert task.score("S_pores_0.15", {"verdict": "accept"}) == {"correct": 0.0}
    assert task.ground_truth("S_none") == {"kind": "none", "magnitude": 0.0, "expected": ["accept"]}
