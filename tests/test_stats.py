"""Generic statistics: bootstrap CI of a difference in means, and the three-way verdict."""

import numpy as np

from hackbench.stats import bootstrap_diff_ci, verdict


def test_bootstrap_ci_covers_a_known_difference() -> None:
    rng = np.random.default_rng(1)
    base = rng.normal(10.0, 0.5, size=12)
    batch = rng.normal(12.0, 0.5, size=12)
    diff, lo, hi = bootstrap_diff_ci(base, batch, n=2000, seed=0)
    assert lo < 2.0 < hi
    assert lo < diff < hi


def test_bootstrap_is_reproducible_with_a_seed() -> None:
    base, batch = np.array([1.0, 2.0, 3.0]), np.array([2.0, 3.0, 4.0])
    assert bootstrap_diff_ci(base, batch, seed=7) == bootstrap_diff_ci(base, batch, seed=7)


def test_verdict_accepts_when_every_ci_is_inside_tolerance() -> None:
    v = verdict({"porosity": (-0.2, 0.3)}, {"porosity": 1.0})
    assert v.label == "accept"
    assert v.driving == ()


def test_verdict_rejects_when_any_ci_is_wholly_outside() -> None:
    v = verdict({"porosity": (-0.1, 0.1), "pore_d": (1.5, 2.5)}, {"porosity": 1.0, "pore_d": 1.0})
    assert v.label == "reject"
    assert v.driving == ("pore_d",)


def test_verdict_investigates_when_a_ci_straddles_the_tolerance() -> None:
    v = verdict({"porosity": (0.5, 1.5)}, {"porosity": 1.0})
    assert v.label == "investigate"
    assert v.driving == ("porosity",)


def test_negative_shifts_count_as_well() -> None:
    assert verdict({"x": (-3.0, -2.0)}, {"x": 1.0}).label == "reject"
