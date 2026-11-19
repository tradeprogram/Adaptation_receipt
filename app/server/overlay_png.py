"""지도 오버레이 PNG 생성 — 연속값(지표면온도)·분류값(침수 범위) 공용.

색은 원격탐사 관행을 따른다: 온도는 순차형 열 색상표(inferno), 전후 차이는 RdBu 발산형(청 냉각, 적 가열), 침수는 청색.
NaN은 완전 투명.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

WARM = [(0, 0, 4), (66, 10, 104), (147, 38, 103), (221, 81, 58), (252, 165, 10), (252, 255, 164)]               # inferno, 낮음에서 높음
NDVI_STOPS = [(165, 0, 38), (244, 109, 67), (254, 224, 139), (217, 239, 139), (102, 189, 99), (0, 104, 55)]              # RdYlGn, NDVI 관행
DIVERGE = [(33, 102, 172), (103, 169, 207), (247, 247, 247), (239, 138, 98), (178, 24, 43)]                       # RdBu_r, 음에서 양


def _ramp(vals: np.ndarray, stops: list[tuple[int, int, int]]) -> np.ndarray:
    """0~1 값을 색 정지점 사이에서 선형 보간해 (h, w, 3) uint8로."""
    v = np.clip(np.nan_to_num(vals, nan=0.0), 0, 1)
    n = len(stops) - 1
    pos = v * n
    i = np.clip(np.floor(pos).astype(int), 0, n - 1)
    f = (pos - i)[..., None]
    st = np.array(stops, dtype=float)
    rgb = st[i] * (1 - f) + st[i + 1] * f
    return rgb.astype("uint8")


def scalar_png(arr: np.ndarray, path: Path, vmin: float, vmax: float, stops: list[tuple[int, int, int]] = WARM, alpha: int = 215) -> None:
    from PIL import Image
    span = (vmax - vmin) or 1.0
    rgb = _ramp((arr - vmin) / span, stops)
    a = np.where(np.isfinite(arr), alpha, 0).astype("uint8")
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(path)


def _grow(m: np.ndarray, r: int) -> np.ndarray:
    d = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return d


def class_png(cls: np.ndarray, path: Path, palette: dict[int, tuple[int, int, int, int]], dilate: tuple[int, ...] = (), radius: int = 2, halo: bool = True) -> None:
    """분류값을 색으로. dilate에 든 클래스는 흩어진 화소가 지도에서 표식처럼 읽히도록 radius만큼 넓히고 흰 테두리를 두른다(통계에는 쓰지 않는다)."""
    from PIL import Image
    h, w = cls.shape
    img = np.zeros((h, w, 4), dtype="uint8")
    fixed = np.isin(cls, [x for x in palette if x not in dilate]) if dilate else np.zeros_like(cls, bool)
    if dilate and halo:
        anyd = np.zeros_like(cls, bool)
        for k in dilate: anyd |= cls == k
        ring = _grow(anyd, radius + 1) & ~fixed
        img[ring] = (255, 255, 255, 215)
    for k, c in palette.items():
        m = cls == k
        if k in dilate:
            m = _grow(m, radius) & ~fixed
        img[m] = c
    Image.fromarray(img, "RGBA").save(path)


FLOOD_PALETTE = {1: (21, 78, 160, 245), 2: (130, 130, 130, 140)}                                    # 1 침수(변화) · 2 상시 수역
CHANGE_PALETTE = {1: (21, 78, 160, 240), 2: (190, 24, 40, 245), 3: (90, 40, 130, 245), 4: (130, 130, 130, 120)}   # 1 전만 · 2 후만 · 3 둘 다 · 4 상시 수역
