"""브이월드(V-World) 클라이언트 — 주소 지오코딩과 건물 footprint(WFS lt_c_spbd).

실측(2026-10-12): WFS는 KEY + DOMAIN(localhost) 파라미터로 200/GeoJSON, MAXFEATURES 상한 안에서만 반환하므로 bbox를 좁게 잡는다.
속성: buld_nm(단지명), buld_nm_dc(동명), bd_mgt_sn(25자리 건물관리번호: 시군구5+법정동5+대지구분1+본번4+부번4+일련6), gro_flo_co(지상층수).
"""
from __future__ import annotations

import requests

from . import config

UA = {"User-Agent": config.USER_AGENT}


def geocode(address: str, kind: str = "road") -> tuple[float, float] | None:
    key = config.KEYS["VWORLD_API_KEY"]
    if not key:
        return None
    r = requests.get("https://api.vworld.kr/req/address", params={"service": "address", "request": "getcoord", "version": "2.0", "crs": "EPSG:4326", "address": address, "type": kind, "key": key, "format": "json"}, headers=UA, timeout=30)
    try:
        p = r.json()["response"]["result"]["point"]
        return float(p["x"]), float(p["y"])
    except (ValueError, KeyError, TypeError):
        return None


def buildings(bbox: list[float], max_features: int = 600) -> list[dict]:
    """bbox(4326) 안의 건물 footprint GeoJSON feature 목록. 키가 없거나 실패하면 []."""
    key = config.KEYS["VWORLD_API_KEY"]
    if not key:
        return []
    r = requests.get("https://api.vworld.kr/req/wfs", params={"SERVICE": "WFS", "REQUEST": "GetFeature", "TYPENAME": "lt_c_spbd", "BBOX": ",".join(f"{v:.6f}" for v in bbox), "VERSION": "1.1.0", "MAXFEATURES": max_features, "SRSNAME": "EPSG:4326", "OUTPUT": "application/json", "EXCEPTIONS": "text/xml", "KEY": key, "DOMAIN": "localhost"}, headers=UA, timeout=60)
    try:
        return r.json().get("features", [])
    except ValueError:
        return []


def pick_blocks(feats: list[dict], complex_name: str, block_names: list[str]) -> list[dict]:
    """단지명(부분 일치)과 동명(정확 일치)으로 footprint를 고른다."""
    out = []
    for f in feats:
        p = f.get("properties", {})
        if complex_name in (p.get("buld_nm") or "") and (p.get("buld_nm_dc") or "") in block_names:
            out.append({"type": "Feature", "properties": {"name": f"{p.get('buld_nm')} {p.get('buld_nm_dc')}", "bd_mgt_sn": p.get("bd_mgt_sn"), "floors": p.get("gro_flo_co")}, "geometry": f["geometry"]})
    return out


def parse_bd_mgt_sn(sn: str) -> dict:
    """건물관리번호 → 건축물대장 조회 키(sigunguCd, bjdongCd, platGbCd, bun, ji)."""
    sn = str(sn)
    return {"sigunguCd": sn[0:5], "bjdongCd": sn[5:10], "platGbCd": sn[10:11], "bun": sn[11:15], "ji": sn[15:19]}
