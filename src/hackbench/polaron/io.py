"""Read Polaron SEM TIFFs: one greyscale channel, edge-cropped, plus the physical pixel size."""

from pathlib import Path

import numpy as np
import tifffile
from numpy.typing import NDArray

INCH_NM = 25.4e6
CM_NM = 1e7


def pixel_size_nm(path: Path) -> float:
    """Pixel size from XResolution (pixels per unit). The original SEM metadata is stripped."""
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        if not isinstance(page, tifffile.TiffPage):
            raise ValueError(f"{path}: first page has no TIFF tags")
        tags = page.tags
        num, den = tags["XResolution"].value
        unit = tags["ResolutionUnit"].value if "ResolutionUnit" in tags else 2
    per_unit_nm = CM_NM if int(unit) == 3 else INCH_NM
    return float(per_unit_nm / (num / den))


def save_channel(path: Path, img: NDArray[np.float64], px_nm: float) -> None:
    """Write a [0, 1] greyscale image as an 8-bit LZW TIFF that keeps the pixel size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    px_per_inch = INCH_NM / px_nm
    tifffile.imwrite(
        path,
        (np.clip(img, 0.0, 1.0) * 255).astype(np.uint8),
        compression="lzw",
        resolution=(px_per_inch, px_per_inch),
        resolutionunit="INCH",
    )


def load_channel(path: Path, crop_px: int) -> NDArray[np.float64]:
    """First colour channel as floats in [0, 1], with `crop_px` removed from every edge.

    Reason: the files are greyscale stored as RGB; a 2-px coloured strip on the right edge
    of some files would otherwise leak into KPIs (and could act as a batch shortcut).
    """
    arr = tifffile.imread(path)
    grey = arr[..., 0] if arr.ndim == 3 else arr
    if crop_px:
        grey = grey[crop_px:-crop_px, crop_px:-crop_px]
    return grey.astype(np.float64) / 255.0
