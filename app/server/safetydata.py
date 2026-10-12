"""행안부 재난안전데이터 공유플랫폼 — 무더위쉼터(DSSP-IF-10942), 복구계획공공시설(ID 확정 전).

실측(2026-10-12): 키는 등록 IP에서만 동작. 응답 {header{resultCode "00"}, totalCount, body[{RSTR_NM, RN_DTL_ADRES, LO, LA, USE_PSBL_NMPR, FCLTY_SCLAS, ARCD, YEAR, ...}]}
전수(6만 건)는 1000건씩 받아 cache/shelters_heat.json에 두고 bbox로 거른다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from . import config
from .fsutil import save_json_atomic

UA = {"User-Agent": config.USER_AGENT}
SHELTER_ID = "DSSP-IF-10942"
CACHE = config.CACHE_DIR / "shelters_heat.json"
SLIM = config.DATA_DIR / "shelters_heat_slim.json"   # 배포본 동봉(필드 9개로 줄인 전수)


def fetch_all(service_id: str, key: str, rows_per_page: int = 1000, max_pages: int = 200) -> list[dict] | None:
    out: list[dict] = []; page = 1; total = None
    while page <= max_pages:
        try:
            r = requests.get(f"https://www.safetydata.go.kr/V2/api/{service_id}", params={"serviceKey": key, "returnType": "json", "pageNo": page, "numOfRows": rows_per_page}, headers=UA, timeout=90)
            js = r.json()
        except (requests.RequestException, ValueError):
            time.sleep(2); continue
        if (js.get("header") or {}).get("resultCode") != "00":
            return None if not out else out          # 등록 IP 오류·접근거부는 '못 가져옴'
        body = js.get("body") or []; out.extend(body); total = js.get("totalCount")
        if not body or (total is not None and len(out) >= total):
            break
        page += 1; time.sleep(0.3)
    return out


def shelters(refresh: bool = False) -> list[dict] | None:
    """캐시된 무더위쉼터 전수. 없으면 키로 내려받는다. 키·IP 문제면 None."""
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    key = config.KEYS["SAFETYDATA_KEY_SHELTER"]
    rows = fetch_all(SHELTER_ID, key) if (key and not config.READ_ONLY) else None
    if rows:
        save_json_atomic(CACHE, rows)
        return rows
    if SLIM.exists():
        return json.loads(SLIM.read_text(encoding="utf-8"))
    return None


def shelters_in_bbox(bbox: list[float]) -> dict | None:
    rows = shelters()
    if rows is None:
        return None
    hit = []
    for s in rows:
        try:
            lo, la = float(s.get("LO")), float(s.get("LA"))
        except (TypeError, ValueError):
            continue
        if bbox[0] <= lo <= bbox[2] and bbox[1] <= la <= bbox[3]:
            hit.append({"name": s.get("RSTR_NM"), "addr": s.get("RN_DTL_ADRES") or s.get("DTL_ADRES"), "lon": lo, "lat": la, "capacity": s.get("USE_PSBL_NMPR"), "kind": s.get("FCLTY_SCLAS"), "year": s.get("YEAR")})
    return {"total": len(rows), "in_bbox": len(hit), "capacity_sum": sum(int(h["capacity"] or 0) for h in hit), "items": hit[:200]}
