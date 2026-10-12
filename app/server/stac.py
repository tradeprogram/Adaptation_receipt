"""Planetary Computer STAC 접근: 검색, SAS 토큰(재시도·캐시), 창 읽기, 장면 캐시(원자적 저장).

실측(2026-10-06): /search 200, 장면 전체 ID는 검색 결과로만 확보 가능, SAS 토큰 엔드포인트는 간헐 504.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

from . import config
from .fsutil import save_json_atomic as _save_json_atomic

_session = requests.Session()
_session.headers.update({"User-Agent": config.USER_AGENT})
if config.KEYS["PC_SDK_SUBSCRIPTION_KEY"]:
    _session.headers.update({"Ocp-Apim-Subscription-Key": config.KEYS["PC_SDK_SUBSCRIPTION_KEY"]})

_token_cache: dict[str, tuple[str, float]] = {}

GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2")


def search_items(collection: str, bbox: list[float], datetime: str, query: dict | None = None, limit: int = 50) -> list[dict]:
    body = {"collections": [collection], "bbox": bbox, "datetime": datetime, "limit": limit}
    if query:
        body["query"] = query
    last = None
    for attempt in range(4):
        try:
            r = _session.post(f"{config.STAC_URL}/search", json=body, timeout=config.HTTP_TIMEOUT)
            if r.status_code == 200:
                return r.json().get("features", [])
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = type(e).__name__
        time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"STAC search failed: {last}")


def sas_token(collection: str) -> str:
    """SAS 토큰. 50분 캐시, 6회 재시도(백오프). 504/비JSON 응답은 재시도 사유."""
    now = time.time()
    if collection in _token_cache and _token_cache[collection][1] > now:
        return _token_cache[collection][0]
    last = None
    for attempt in range(6):
        try:
            r = _session.get(f"{config.SAS_URL}/{collection}", timeout=config.HTTP_TIMEOUT)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                tok = r.json()["token"]
                _token_cache[collection] = (tok, now + 50 * 60)
                return tok
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = type(e).__name__
        time.sleep(3 + 5 * attempt)
    raise RuntimeError(f"SAS token unavailable for {collection}: {last}")


def utm_epsg_for(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def grid_for(bbox: list[float], res_m: float, epsg: int) -> tuple[float, float, float, float, int, int]:
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    x0, y0 = tr.transform(bbox[0], bbox[1]); x1, y1 = tr.transform(bbox[2], bbox[3])
    w = max(1, int((x1 - x0) / res_m)); h = max(1, int((y1 - y0) / res_m))
    return x0, y0, x1, y1, w, h


def read_window(href: str, x0: float, y0: float, x1: float, y1: float, w: int, h: int, nearest: bool, epsg: int) -> np.ndarray | None:
    """COG에서 지정 격자로 창을 읽는다. CRS가 다르면 None(모자이크 단계에서 건너뛴다)."""
    with rasterio.Env(**GDAL_ENV):
        with rasterio.open(href) as ds:
            if ds.crs is None or ds.crs.to_epsg() != epsg:
                return None
            win = from_bounds(x0, y0, x1, y1, ds.transform)
            rs = Resampling.nearest if nearest else Resampling.average
            return ds.read(1, window=win, out_shape=(h, w), resampling=rs, boundless=True, fill_value=0).astype("float32")


def scene_cache_path(key: str) -> Path:
    return config.SCENES_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest()[:20] + ".npz")


def save_npz_atomic(path: Path, **arrays) -> None:
    """같은 디렉터리의 임시 파일에 쓰고 fsync 후 교체한다. 실패 시 임시 파일을 지운다."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            np.savez_compressed(f, **arrays)
            f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


save_json_atomic = _save_json_atomic  # 하위 호환: 가벼운 fsutil로 이동


def load_bands(collection: str, items: list[dict], bands: list[str], bbox: list[float], res_m: float, epsg: int,
               nearest_bands: tuple[str, ...] = ("SCL", "QA_PIXEL"), cache_key: str = "") -> dict[str, np.ndarray]:
    """같은 패스의 여러 타일을 모자이크해 밴드별 배열을 돌려준다. 캐시가 있으면 읽지 않는다."""
    key = cache_key or ("|".join(sorted(i["id"] for i in items)) + f"|{bands}|{bbox}|{res_m}")
    cpath = scene_cache_path(key)
    if cpath.exists():
        with np.load(cpath) as z:
            return {b: z[b] for b in bands}
    x0, y0, x1, y1, w, h = grid_for(bbox, res_m, epsg)
    tok = sas_token(collection)
    out: dict[str, np.ndarray] = {}
    for b in bands:
        merged = None
        for it in items:
            if b not in it["assets"]:
                continue
            arr = read_window(it["assets"][b]["href"] + "?" + tok, x0, y0, x1, y1, w, h, b in nearest_bands, epsg)
            if arr is None:
                continue
            merged = arr if merged is None else np.where(merged == 0, arr, merged)
        if merged is None:
            raise RuntimeError(f"band {b} unreadable for {[i['id'] for i in items]}")
        out[b] = merged
    save_npz_atomic(cpath, **out)
    return out
