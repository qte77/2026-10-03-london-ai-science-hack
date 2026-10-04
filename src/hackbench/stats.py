"""Domain-agnostic statistics: bootstrap CI of a mean difference, and the three-way verdict."""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

LABELS = ("accept", "investigate", "reject")


def bootstrap_diff_ci(
    base: ArrayLike, batch: ArrayLike, n: int = 2000, seed: int = 0, level: float = 0.95
) -> tuple[float, float, float]:
    """Difference of means (batch - base) with a percentile bootstrap CI over items."""
    a, b = np.asarray(base, float), np.asarray(batch, float)
    rng = np.random.default_rng(seed)
    resampled = rng.choice(b, (n, b.size), replace=True).mean(1) - rng.choice(
        a, (n, a.size), replace=True
    ).mean(1)
    tail = (1 - level) / 2 * 100
    lo, hi = np.percentile(resampled, [tail, 100 - tail])
    return float(b.mean() - a.mean()), float(lo), float(hi)


@dataclass(frozen=True)
class Verdict:
    label: str  # "accept" | "investigate" | "reject"
    driving: tuple[str, ...]  # KPIs whose CI is not wholly inside tolerance


def verdict(cis: Mapping[str, tuple[float, float]], tolerance: Mapping[str, float]) -> Verdict:
    """Accept if every CI is inside ±tolerance; reject if any is wholly outside; else
    investigate. The KPIs not wholly inside are returned as the drivers."""
    outside = [k for k, (lo, hi) in cis.items() if lo > tolerance[k] or hi < -tolerance[k]]
    straddling = [
        k
        for k, (lo, hi) in cis.items()
        if k not in outside and (lo < -tolerance[k] or hi > tolerance[k])
    ]
    if outside:
        return Verdict("reject", tuple(outside))
    if straddling:
        return Verdict("investigate", tuple(straddling))
    return Verdict("accept", ())
