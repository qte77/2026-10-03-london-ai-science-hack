"""Polaron image loading and KPI extraction, checked against synthetic ground truth."""

from pathlib import Path

import numpy as np
import pytest

from hackbench.polaron.io import load_channel, pixel_size_nm
from hackbench.polaron.kpis import compute_kpis
from tests.polaron.conftest import PX_NM, make_image, write_tiff


def test_pixel_size_is_read_from_the_tiff(tmp_path: Path) -> None:
    img, _ = make_image(0.1, 0.05, seed=0)
    write_tiff(tmp_path / "a.tif", img)
    assert pixel_size_nm(tmp_path / "a.tif") == pytest.approx(PX_NM, abs=0.01)


def test_loader_takes_one_channel_and_crops_the_edge_strip(tmp_path: Path) -> None:
    img, _ = make_image(0.1, 0.05, seed=0)
    write_tiff(tmp_path / "a.tif", img, edge_strip=True)
    grey = load_channel(tmp_path / "a.tif", crop_px=4)
    assert grey.shape == (img.shape[0] - 8, img.shape[1] - 8)
    assert grey.dtype == np.float64
    assert 0.0 <= grey.min() <= grey.max() <= 1.0


def test_kpis_recover_known_porosity_and_bright_phase() -> None:
    img, truth = make_image(0.12, 0.05, seed=3)
    k = compute_kpis(img, px_nm=PX_NM)
    assert k["porosity_pct"] == pytest.approx(truth.porosity_pct, abs=1.0)
    assert k["bright_phase_pct"] == pytest.approx(truth.bright_pct, abs=1.0)


def test_kpis_recover_pore_size_in_microns() -> None:
    img, truth = make_image(0.12, 0.05, seed=4)
    k = compute_kpis(img, px_nm=PX_NM)
    expected_um = 2 * truth.pore_radius_px * PX_NM / 1000
    assert k["pore_diameter_um"] == pytest.approx(expected_um, rel=0.15)
    assert k["pore_density_per_um2"] > 0


def test_more_porous_material_scores_higher_porosity() -> None:
    low, _ = make_image(0.08, 0.05, seed=5)
    high, _ = make_image(0.25, 0.05, seed=5)
    assert compute_kpis(high, PX_NM)["porosity_pct"] > compute_kpis(low, PX_NM)["porosity_pct"]
