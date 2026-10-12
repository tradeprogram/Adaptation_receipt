import math

import numpy as np

from app.server import metrics
from app.server.envelope import metric, ok, degraded


def test_recovery_ratio_basic():
    assert math.isclose(metrics.recovery_ratio([0.2, 0.2, 0.2], [0.5, 0.5, 0.5]), 0.4)


def test_recovery_ratio_missing_control_is_none():
    assert metrics.recovery_ratio([0.2, 0.3], []) is None
    assert metrics.recovery_ratio([], [0.5]) is None


def test_robust_z_requires_two_baseline_points():
    assert metrics.robust_z(0.3, [0.5]) is None
    assert metrics.robust_z(None, [0.5, 0.6]) is None
    z = metrics.robust_z(0.0, [0.5, 0.6, 0.55, 0.52, 0.58])
    assert z is not None and z < -3


def test_robust_z_zero_spread_is_none_not_zero():
    assert metrics.robust_z(0.5, [0.5, 0.5, 0.5]) is None


def test_did_effect_reports_missing_group():
    r = metrics.did_effect([1, 2], [2, 3], [], [1, 1])
    assert r["effect"] is None and "ctrl_pre" in r["reason"]
    r2 = metrics.did_effect([1, 1, 1], [3, 3, 3], [1, 1, 1], [2, 2, 2])
    assert math.isclose(r2["effect"], 1.0)


def test_bootstrap_ci_small_sample_none_and_contains_true_diff():
    assert metrics.bootstrap_ci([1, 2, 3], [1, 2, 3]) is None
    rng = np.random.default_rng(0)
    a = rng.normal(1.0, 0.1, 500); b = rng.normal(0.0, 0.1, 500)
    lo, hi = metrics.bootstrap_ci(a, b)
    assert lo < 1.0 < hi and lo > 0.8


def test_mde_decreases_with_pixels():
    base = np.random.default_rng(1).normal(0.5, 0.05, 200)
    assert metrics.mde(base, 100) > metrics.mde(base, 10000)
    assert metrics.mde(base, 1) is None


def test_summarize_empty():
    s = metrics.summarize([])
    assert s["n"] == 0 and s["median"] is None


def test_metric_badge_and_measured_flag():
    m = metric(None, "MODEL", "ha")
    assert m["measured"] is False and m["value"] is None
    assert ok({"a": 1})["status"] == "ok"
    assert degraded({}, ["key"])["status"] == "degraded"
