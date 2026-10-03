"""Synthetic Polaron-like micrographs with known ground truth (no real data in tests or CI)."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import tifffile

PX_NM = 25.0
PX_PER_INCH = 25.4e6 / PX_NM  # 25 nm per pixel, as in the real files


@dataclass(frozen=True)
class Truth:
    porosity_pct: float
    bright_pct: float
    pore_radius_px: int


def make_image(
    porosity_target: float, bright_target: float, seed: int, shape: tuple[int, int] = (300, 500)
) -> tuple[np.ndarray, Truth]:
    """Mid-grey solid with dark pore discs and bright additive discs, plus mild noise."""
    rng = np.random.default_rng(seed)
    h, w = shape
    img = np.full(shape, 0.5)
    yy, xx = np.mgrid[0:h, 0:w]
    radius = 6
    dark = np.zeros(shape, bool)
    bright = np.zeros(shape, bool)
    for target, mask in ((porosity_target, dark), (bright_target, bright)):
        while mask.mean() < target:
            cy, cx = rng.integers(radius, h - radius), rng.integers(radius, w - radius)
            disc = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2
            if not (disc & (dark | bright)).any():
                mask |= disc
    img[dark] = 0.08
    img[bright] = 0.92
    img += rng.normal(0, 0.02, shape)
    truth = Truth(100 * dark.mean(), 100 * bright.mean(), radius)
    return np.clip(img, 0, 1), truth


def write_tiff(path: Path, img: np.ndarray, edge_strip: bool = True) -> None:
    grey = (img * 255).astype(np.uint8)
    rgb = np.stack([grey, grey, grey], axis=-1)
    if edge_strip:  # the real files carry a coloured 2-px strip on the right edge
        rgb[:, -2:, 0] = 0
        rgb[:, -2:, 1] = 255
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(
        path, rgb, compression="lzw", resolution=(PX_PER_INCH, PX_PER_INCH), resolutionunit="INCH"
    )


@pytest.fixture
def dataset(tmp_path: Path) -> dict[str, list[Truth]]:
    """Batch_1 = baseline, Batch_2 = same process, Batch_3 = much more porous."""
    plan = {"Batch_1": 0.10, "Batch_2": 0.10, "Batch_3": 0.25}
    truths: dict[str, list[Truth]] = {}
    for b_idx, (batch, porosity) in enumerate(plan.items()):
        truths[batch] = []
        for i in range(5):
            img, truth = make_image(porosity, 0.05, seed=100 * b_idx + i)
            fov = f"img_{batch[-1]}{i:03d}"
            write_tiff(tmp_path / batch / f"{fov}_BSE.tif", img)
            # Reason: the real channel mix differs by batch; mirror that shortcut here.
            other = "SE" if (batch == "Batch_2" and i == 0) else "ETD"
            write_tiff(tmp_path / batch / f"{fov}_{other}.tif", img)
            truths[batch].append(truth)
    return truths
