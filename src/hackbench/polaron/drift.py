"""Synthetic drift with known ground truth, injected into real baseline micrographs.

Material drifts change the electrode (more pores, coarser particles): the right verdict is
reject once large. Imaging drifts change only how it was imaged (contrast, focus): the material
is unchanged, so the right verdict is accept. That second family measures whether the QC
pipeline confuses acquisition settings with a material change.

Fair comparison: every baseline field of view is split in half. Left halves form the synthetic
baseline; right halves (a different region of the same material) feed the drifted batches.
"""

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage
from skimage.filters import threshold_multiotsu

from hackbench.polaron.io import load_channel, pixel_size_nm, save_channel

Image = NDArray[np.float64]
PORE_RADIUS_PX = 3  # ~0.15 µm at 25 nm/px, close to the real mean pore diameter


def _add_pores(img: Image, fraction: float, seed: int) -> Image:
    rng = np.random.default_rng(seed)
    already_dark = img < threshold_multiotsu(img, classes=3)[0]
    dark_value = float(np.percentile(img, 2))
    r = PORE_RADIUS_PX
    disc = np.hypot(*np.mgrid[-r : r + 1, -r : r + 1]) <= r
    painted = np.zeros(img.shape, bool)
    per_round = max(1, int(fraction * img.size / disc.sum() / 4))
    h, w = img.shape
    while (painted & ~already_dark).mean() < fraction:
        seeds = np.zeros(img.shape, bool)
        seeds[rng.integers(0, h, per_round), rng.integers(0, w, per_round)] = True
        painted |= ndimage.binary_dilation(seeds, structure=disc)
    out = img.copy()
    out[painted] = dark_value
    return out


def _coarsen(img: Image, factor: float, seed: int) -> Image:
    zoomed = ndimage.zoom(img, factor, order=1)
    top = (zoomed.shape[0] - img.shape[0]) // 2
    left = (zoomed.shape[1] - img.shape[1]) // 2
    return np.asarray(zoomed[top : top + img.shape[0], left : left + img.shape[1]], float)


def _contrast(img: Image, gain: float, seed: int) -> Image:
    mean = float(img.mean())
    return np.clip(mean + (img - mean) * gain, 0.0, 1.0)


def _blur(img: Image, sigma: float, seed: int) -> Image:
    return np.asarray(ndimage.gaussian_filter(img, sigma), float)


@dataclass(frozen=True)
class Drift:
    kind: str  # "material" | "imaging"
    apply: Callable[[Image, float, int], Image]
    reject_at: float | None  # material drifts: magnitude from which reject is the only right answer


DRIFTS: Mapping[str, Drift] = {
    "pores": Drift("material", _add_pores, reject_at=0.05),
    "coarsen": Drift("material", _coarsen, reject_at=1.3),
    "contrast": Drift("imaging", _contrast, reject_at=None),
    "blur": Drift("imaging", _blur, reject_at=None),
}

DEFAULT_LEVELS: Mapping[str, Sequence[float]] = {
    "pores": (0.02, 0.08),
    "coarsen": (1.1, 1.4),
    "contrast": (0.8, 1.25),
    "blur": (1.0, 3.0),
}


# Held-out levels differ from the training levels, so calibration cannot memorise them.
HELDOUT_LEVELS: Mapping[str, Sequence[float]] = {
    "pores": (0.03, 0.10),
    "coarsen": (1.2, 1.5),
    "contrast": (0.7, 1.4),
    "blur": (1.5, 2.5),
}


def apply_drift(img: Image, name: str, magnitude: float, seed: int = 0) -> Image:
    return DRIFTS[name].apply(img, magnitude, seed)


def expected_verdicts(name: str, magnitude: float) -> list[str]:
    drift = DRIFTS[name]
    if drift.kind == "imaging":
        return ["accept"]
    assert drift.reject_at is not None  # noqa: S101 - invariant of the catalogue above
    return ["reject"] if magnitude >= drift.reject_at else ["investigate", "reject"]


def build_suite(
    source_dir: Path,
    baseline: str,
    channel: str,
    out_dir: Path,
    levels: Mapping[str, Sequence[float]] = DEFAULT_LEVELS,
    seed: int = 0,
    crop_px: int = 4,
) -> dict[str, dict[str, object]]:
    """Write S_base (left halves), S_none and one batch per drift level (right halves)."""
    truth: dict[str, dict[str, object]] = {
        "S_base": {"kind": "baseline", "magnitude": 0.0, "expected": []},
        "S_none": {"kind": "none", "magnitude": 0.0, "expected": ["accept"]},
    }
    batches: list[tuple[str, str | None, float]] = [("S_none", None, 0.0)]
    for name, mags in levels.items():
        for mag in mags:
            batch = f"S_{name}_{mag:g}"
            batches.append((batch, name, mag))
            truth[batch] = {
                "kind": DRIFTS[name].kind,
                "magnitude": mag,
                "expected": expected_verdicts(name, mag),
            }

    for i, path in enumerate(sorted((source_dir / baseline).glob(f"*_{channel}.tif"))):
        img = load_channel(path, crop_px)
        px_nm = pixel_size_nm(path)
        half = img.shape[1] // 2
        left, right = img[:, :half], img[:, half : 2 * half]
        save_channel(out_dir / "S_base" / path.name, left, px_nm)
        for batch, drift_name, mag in batches:
            drifted = right if drift_name is None else apply_drift(right, drift_name, mag, seed + i)
            save_channel(out_dir / batch / path.name, drifted, px_nm)

    (out_dir / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    return truth
