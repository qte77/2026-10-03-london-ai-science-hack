"""Interpretable microstructure KPIs from one greyscale SEM field of view.

Three-class multi-Otsu splits the image into dark (pores / binder gaps), mid (active
material) and bright (conductive additive / secondary phase).
"""

import numpy as np
from numpy.typing import NDArray
from skimage.filters import sobel, threshold_multiotsu
from skimage.measure import label

MIN_PORE_PX = 4  # ignore single-pixel noise


def compute_kpis(img: NDArray[np.float64], px_nm: float) -> dict[str, float]:
    t_low, t_high = threshold_multiotsu(img, classes=3)
    dark = img < t_low
    bright = img > t_high

    labels = label(dark, connectivity=2)
    areas_px = np.bincount(labels.ravel())[1:]
    areas_px = areas_px[areas_px >= MIN_PORE_PX]
    px_um = px_nm / 1000.0
    diam_um = 2.0 * np.sqrt(areas_px / np.pi) * px_um if areas_px.size else np.zeros(0)
    field_um2 = img.size * px_um**2

    return {
        "porosity_pct": float(100.0 * dark.mean()),
        "bright_phase_pct": float(100.0 * bright.mean()),
        "pore_density_per_um2": float(areas_px.size / field_um2),
        "pore_diameter_um": float(diam_um.mean()) if diam_um.size else 0.0,
        "edge_density": float(sobel(img).mean()),
        "intensity_std": float(img.std()),
    }
