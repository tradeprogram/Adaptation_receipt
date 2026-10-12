"""지도 오버레이 PNG 생성 — 연속값(지표면온도)·분류값(침수 범위) 공용.

색은 지형도 문법을 따른다: 온도는 갈색 계열 순차, 전후 차이는 청(냉각)–적(가열) 발산, 침수는 청색 계열.
NaN은 완전 투명.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

WARM = [(252, 245, 226), (240, 214, 160), (222, 170, 96), (190, 120, 50), (140, 76, 28), (84, 40, 14)]          # 낮음 → 높음
DIVERGE = [(26, 82, 150), (120, 160, 205), (245, 243, 236), (222, 150, 110), (160, 44, 30)]                       # 음(−) → 양(+)


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


def class_png(cls: np.ndarray, path: Path, palette: dict[int, tuple[int, int, int, int]]) -> None:
    from PIL import Image
    h, w = cls.shape
    img = np.zeros((h, w, 4), dtype="uint8")
    for k, c in palette.items():
        img[cls == k] = c
    Image.fromarray(img, "RGBA").save(path)


FLOOD_PALETTE = {1: (31, 90, 160, 225), 2: (120, 120, 120, 150)}                                    # 1 침수(변화) · 2 상시 수역
CHANGE_PALETTE = {1: (31, 90, 160, 225), 2: (160, 44, 30, 225), 3: (70, 40, 110, 235), 4: (120, 120, 120, 120)}   # 1 전만 · 2 후만 · 3 둘 다 · 4 상시 수역
