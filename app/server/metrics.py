"""파생 지표. 표본이 부족하면 None을 돌려주고, 0으로 메우지 않는다.

- robust_z: 계절 정합 기준선(median/MAD) 대비 표준화 편차
- did_effect: 이중차분 (처리 후-전) - (대조 후-전)
- bootstrap_ci: 중앙값 차이의 부트스트랩 신뢰구간(시드 고정)
- mde: 검출 가능 최소효과(화소 수·MAD 기반, 근사)
- recovery_ratio: 피해지/대조지 지표 비
"""
from __future__ import annotations

import math

import numpy as np

MAD_TO_SD = 1.4826


def _finite(a) -> np.ndarray:
    arr = np.asarray(a, dtype="float64").ravel()
    return arr[np.isfinite(arr)]


def robust_z(value: float | None, baseline) -> float | None:
    """value가 기준선 분포(median/MAD)에서 몇 σ 떨어졌는가. 기준선 2개 미만이면 None."""
    if value is None or not math.isfinite(value):
        return None
    b = _finite(baseline)
    if b.size < 2:
        return None
    med = float(np.median(b))
    mad = float(np.median(np.abs(b - med))) * MAD_TO_SD
    if mad == 0.0:
        return None  # 퍼짐이 0이면 z가 정의되지 않는다(0으로 두면 모든 값이 '정상'이 된다)
    return (value - med) / mad


def did_effect(treat_pre, treat_post, ctrl_pre, ctrl_post) -> dict:
    """이중차분. 각 집단은 화소값 배열. 어느 한 쪽이라도 비어 있으면 effect=None과 사유."""
    groups = {"treat_pre": _finite(treat_pre), "treat_post": _finite(treat_post),
              "ctrl_pre": _finite(ctrl_pre), "ctrl_post": _finite(ctrl_post)}
    empty = [k for k, v in groups.items() if v.size == 0]
    if empty:
        return {"effect": None, "reason": f"관측이 없는 집단: {', '.join(empty)}", "n": {k: int(v.size) for k, v in groups.items()}}
    med = {k: float(np.median(v)) for k, v in groups.items()}
    eff = (med["treat_post"] - med["treat_pre"]) - (med["ctrl_post"] - med["ctrl_pre"])
    return {"effect": float(eff), "medians": med, "n": {k: int(v.size) for k, v in groups.items()}, "reason": ""}


def bootstrap_ci(a, b, stat="median_diff", n_boot: int = 500, seed: int = 42, alpha: float = 0.05) -> tuple[float, float] | None:
    """median(a)-median(b)의 부트스트랩 CI. 표본이 각 10개 미만이면 None."""
    a = _finite(a); b = _finite(b)
    if a.size < 10 or b.size < 10:
        return None
    rng = np.random.default_rng(seed)
    # 화소가 수만 개면 1만 개로 표본화해 비용을 고정한다(결과는 중앙값이라 안정적)
    if a.size > 10000: a = rng.choice(a, 10000, replace=False)
    if b.size > 10000: b = rng.choice(b, 10000, replace=False)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        diffs[i] = np.median(rng.choice(a, a.size)) - np.median(rng.choice(b, b.size))
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def mde(baseline, n_pixels: int, z_alpha: float = 1.96, z_power: float = 0.84) -> float | None:
    """검출 가능 최소효과(지표 단위). 기준선 MAD로 σ를 근사, 독립 표본 가정(공간 자기상관 때문에 낙관적임을 카드에 명시)."""
    b = _finite(baseline)
    if b.size < 2 or n_pixels < 2:
        return None
    sd = float(np.median(np.abs(b - np.median(b)))) * MAD_TO_SD
    if sd == 0.0:
        return None
    return (z_alpha + z_power) * sd * math.sqrt(2.0 / n_pixels)


def recovery_ratio(treated, control) -> float | None:
    """피해지 중앙값 / 대조지 중앙값. 대조지 중앙값이 0 이하이거나 표본이 없으면 None."""
    t = _finite(treated); c = _finite(control)
    if t.size == 0 or c.size == 0:
        return None
    cm = float(np.median(c))
    if cm <= 0:
        return None
    return float(np.median(t)) / cm


def summarize(a) -> dict:
    """n·중앙값·평균·사분위·최댓값을 함께 보고한다(평균만 보고하지 않는다)."""
    x = _finite(a)
    if x.size == 0:
        return {"n": 0, "median": None, "mean": None, "q25": None, "q75": None, "max": None}
    q25, q75 = np.percentile(x, [25, 75])
    return {"n": int(x.size), "median": float(np.median(x)), "mean": float(np.mean(x)),
            "q25": float(q25), "q75": float(q75), "max": float(np.max(x))}


def robust_sd(baseline) -> float | None:
    """기준선의 MAD 기반 σ 근사(검정력 곡선용)."""
    b = _finite(baseline)
    if b.size < 2:
        return None
    sd = float(np.median(np.abs(b - np.median(b)))) * MAD_TO_SD
    return sd or None
