"""취약 지역 노출 분석 — 산불 피해·침수 화소가 어느 읍면동에 떨어지는지 세고, 그 읍면동의 고령 지표를 분석 범위 전체와 비교한다.

입력
- 검증 모듈이 저장한 조회 격자(results/<pid>/layers.npz): 산불 dnbr(1~4 등급), 침수 flood_before/flood_after(1 = 침수)
- 국가데이터처 SGIS(실측 2026-11-19): stats/population.json(low_search=1) → 읍면동별 aged_child_idx(노령화지수), oldage_suprt_per(노년부양비), tot_ppltn
  boundary/hadmarea.geojson(low_search=1) → 읍면동 경계, 좌표계 EPSG:5179
- project.sgis_areas = [[시도명, 시군구명], ...] 분석 범위 후보 시군
출력: results/<pid>/exposure.json(표·요약), exposure_areas.geojson(지도용 단순화 경계)
네트워크와 rasterio가 필요하므로 로컬에서 실행하고 결과만 커밋한다(배포본은 읽기만 한다).
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import requests

from . import config
from .equity import SGIS, sgis_token
from .fsutil import save_json_atomic

YEAR = "2023"


def _sgis_code(token: str, sido: str, sigungu: str) -> str | None:
    sidos = requests.get(f"{SGIS}/addr/stage.json", params={"accessToken": token}, timeout=30).json().get("result") or []
    sd = next((x for x in sidos if x["addr_name"] == sido), None)
    if not sd:
        return None
    guns = requests.get(f"{SGIS}/addr/stage.json", params={"accessToken": token, "cd": sd["cd"]}, timeout=30).json().get("result") or []
    g = next((x for x in guns if x["addr_name"] == sigungu), None)
    return g["cd"] if g else None


def run(project: dict) -> dict:
    from pyproj import Transformer
    from rasterio import features
    from rasterio.transform import from_bounds
    from shapely.geometry import mapping, shape
    from shapely.ops import transform as shp_transform

    pid = project["id"]; kind = project["type"]
    path = config.RESULTS_DIR / pid / "layers.npz"
    if not path.exists():
        return {"status": "failed", "reason": "조회 격자 없음, 검증 모듈을 먼저 실행"}
    z = np.load(path); bbox = [float(v) for v in z["bbox"]]
    if kind == "fire":
        hazard = z["dnbr"] > 0; severe = z["dnbr"] >= 3; hz_label = "피해 산림"
    elif kind == "flood":
        b = z["flood_before"] == 1 if "flood_before" in z.files else 0
        a = z["flood_after"] == 1 if "flood_after" in z.files else 0
        hazard = np.asarray(b | a, bool); severe = np.asarray(a, bool); hz_label = "침수 추정"
    else:
        return {"status": "skipped", "reason": "열 사업은 건물 단위 형평성 감사를 사용"}
    h, w = hazard.shape
    lat0 = (bbox[1] + bbox[3]) / 2
    px_ha = ((bbox[2] - bbox[0]) * 111.32 * np.cos(np.radians(lat0)) * (bbox[3] - bbox[1]) * 110.57) * 100 / (h * w)

    token = sgis_token()
    if not token:
        return {"status": "degraded", "reason": "SGIS 키 부재"}
    to4326 = Transformer.from_crs(5179, 4326, always_xy=True).transform
    areas = []
    for sido, sgg in project.get("sgis_areas", []):
        cd = _sgis_code(token, sido, sgg)
        if not cd:
            continue
        pop = requests.get(f"{SGIS}/stats/population.json", params={"accessToken": token, "year": YEAR, "adm_cd": cd, "low_search": "1"}, timeout=30).json().get("result") or []
        bd = requests.get(f"{SGIS}/boundary/hadmarea.geojson", params={"accessToken": token, "year": YEAR, "adm_cd": cd, "low_search": "1"}, timeout=60).json().get("features") or []
        stats = {r["adm_cd"]: r for r in pop}
        for f in bd:
            g = shp_transform(to4326, shape(f["geometry"]))
            if not g.intersects(shape({"type": "Polygon", "coordinates": [[[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]], [bbox[0], bbox[1]]]]})):
                continue
            s = stats.get(f["properties"]["adm_cd"], {})
            num = lambda k: (float(s[k]) if s.get(k) not in (None, "", "N/A") else None)
            areas.append({"adm_cd": f["properties"]["adm_cd"], "name": f["properties"]["adm_nm"].replace(f"{sido} ", ""), "sigungu": sgg, "geom": g,
                          "aged_idx": num("aged_child_idx"), "oldage": num("oldage_suprt_per"), "pop": num("tot_ppltn")})
    if not areas:
        return {"status": "failed", "reason": "분석 범위에 걸리는 읍면동 없음"}

    tr = from_bounds(bbox[0], bbox[1], bbox[2], bbox[3], w, h)
    ids = features.rasterize(((mapping(a["geom"]), i + 1) for i, a in enumerate(areas)), out_shape=(h, w), transform=tr, fill=0, dtype="int32")
    hz_total = int(hazard.sum())
    for i, a in enumerate(areas):
        m = ids == i + 1
        a["area_ha"] = round(float(m.sum()) * px_ha, 1)
        a["hazard_ha"] = round(float((hazard & m).sum()) * px_ha, 1)
        a["severe_ha"] = round(float((severe & m).sum()) * px_ha, 1)
        a["hazard_share"] = round(float((hazard & m).sum()) / hz_total, 4) if hz_total else 0.0
        a["hazard_pct_of_area"] = round(100 * float((hazard & m).sum()) / max(1, int(m.sum())), 1)
    inside = [a for a in areas if a["area_ha"] > 0 and a["aged_idx"] is not None]
    hit = [a for a in inside if a["hazard_ha"] > 0]
    # 노출 가중 평균(피해 화소 수 가중) 대 분석 범위 인구 가중 평균
    wavg = lambda rows, key, wk: (sum(r[key] * r[wk] for r in rows if r[key] is not None) / sum(r[wk] for r in rows if r[key] is not None)) if rows and sum(r[wk] for r in rows if r[key] is not None) else None
    exp_aged = wavg(hit, "aged_idx", "hazard_ha"); exp_old = wavg(hit, "oldage", "hazard_ha")
    ref_aged = wavg(inside, "aged_idx", "pop"); ref_old = wavg(inside, "oldage", "pop")
    med = float(np.median([a["aged_idx"] for a in inside])) if inside else None
    share_high = sum(a["hazard_share"] for a in hit if med is not None and a["aged_idx"] >= med)
    top = sorted(hit, key=lambda a: -a["hazard_ha"])[:8]
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {k: a[k] for k in ("adm_cd", "name", "aged_idx", "oldage", "pop", "hazard_ha", "hazard_pct_of_area")},
                                                     "geometry": mapping(a["geom"].simplify(0.0008, preserve_topology=True))} for a in inside]}
    out_dir = config.RESULTS_DIR / pid
    save_json_atomic(out_dir / "exposure_areas.geojson", gj)
    res = {"status": "ok", "project_id": pid, "computed_at": dt.datetime.now().isoformat(timespec="seconds"), "hazard_label": hz_label,
           "source": f"국가데이터처 SGIS {YEAR} 읍면동 인구 통계와 행정구역 경계, 피해·침수 화소는 위성 검증 결과",
           "n_areas": len(inside), "n_hit": len(hit), "hazard_ha": round(hz_total * px_ha, 1),
           # 소수 둘째 자리까지 저장: 1자리로 저장하면 정수 표기 때 두 번 반올림되어 1,804.55가 1,804로 내려가는 오차가 생긴다
           "exposed_aged_idx": round(exp_aged, 2) if exp_aged is not None else None, "ref_aged_idx": round(ref_aged, 2) if ref_aged is not None else None,
           "exposed_oldage": round(exp_old, 1) if exp_old is not None else None, "ref_oldage": round(ref_old, 1) if ref_old is not None else None,
           "median_aged_idx": round(med, 1) if med is not None else None, "share_in_high_aging": round(share_high, 3),
           "top": [{k: a[k] for k in ("name", "sigungu", "hazard_ha", "severe_ha", "hazard_share", "hazard_pct_of_area", "aged_idx", "oldage", "pop")} for a in top],
           "geojson": f"/api/projects/{pid}/overlay/exposure_areas.geojson"}
    save_json_atomic(out_dir / "exposure.json", res)
    return res
