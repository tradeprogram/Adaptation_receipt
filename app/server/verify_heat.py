"""열 저감 사업(쿨루프·옥상녹화) 검증 모듈 — Landsat 8/9 Collection 2 Level-2 지표면온도.

처리 폴리곤(시공)과 대조 폴리곤(인접 미시공)의 여름(6~9월) 지표면온도 중앙값을 시공 전 연도와 후 연도에 대해 산출해 이중차분한다.
ST_B10: LST[K] = DN*0.00341802 + 149.0 ; QA_PIXEL 비트 1(dilated cloud)·3(cloud)·4(cloud shadow)·5(snow) 마스킹.
30 m(열적외 원 해상도 100 m 재표집)이므로 단일 소형 건물은 검출 불가 — 블록 단위 폴리곤을 권장한다.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
from rasterio import features
from rasterio.transform import from_origin
from shapely.geometry import shape

from . import metrics, stac
from .envelope import metric

LS = "landsat-c2-l2"
QA_BAD_BITS = (1, 3, 4, 5)


def qa_mask(qa: np.ndarray) -> np.ndarray:
    q = qa.astype("uint32")
    bad = np.zeros(q.shape, dtype=bool)
    for b in QA_BAD_BITS:
        bad |= ((q >> b) & 1).astype(bool)
    return bad | (q == 0)


def lst_celsius(dn: np.ndarray, bad: np.ndarray) -> np.ndarray:
    return np.where(bad | (dn == 0), np.nan, dn * 0.00341802 + 149.0 - 273.15)


def rasterize(polys: list[dict], x0, y1, res, w, h, epsg) -> np.ndarray:
    from pyproj import Transformer
    from shapely.ops import transform as shp_transform
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True).transform
    geoms = [shp_transform(tr, shape(f["geometry"] if "geometry" in f else f)) for f in polys]
    if not geoms:
        return np.zeros((h, w), dtype=bool)
    return features.rasterize([(g, 1) for g in geoms], out_shape=(h, w), transform=from_origin(x0, y1, res, res), fill=0, all_touched=True).astype(bool)


def run(project: dict, progress=lambda done, total, msg: None) -> dict:
    p = project; prm = p.get("params", {})
    treated = p["geometry"].get("treated", []); control = p["geometry"].get("control", [])
    if not treated or not control:
        return {"status": "waiting_input", "module": "heat", "project_id": p["id"],
                "reason": "처리(시공) 폴리곤과 대조(미시공) 폴리곤이 필요하다. 브이월드 건물 WFS(VWORLD_API_KEY) 또는 사용자 업로드로 채운다.",
                "needs": ["geometry.treated[]", "geometry.control[]"], "metrics": {}, "limitations": []}
    bbox = p["geometry"]["bbox"]; res = float(prm.get("res_m", 30)); max_cloud = float(prm.get("max_cloud", 40))
    years_before = p["years_before"]; years_after = p["years_after"]
    epsg = stac.utm_epsg_for((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    x0, y0, x1, y1, w, h = stac.grid_for(bbox, res, epsg)
    tmask = rasterize(treated, x0, y1, res, w, h, epsg); cmask = rasterize(control, x0, y1, res, w, h, epsg)
    scenes = []; failed = []; per_year: dict[int, dict[str, list]] = {}
    years = list(years_before) + list(years_after); total = len(years)
    for i, yr in enumerate(years):
        progress(i, total, f"Landsat {yr} 여름 장면")
        try:
            feats = stac.search_items(LS, bbox, f"{yr}-06-15T00:00:00Z/{yr}-09-20T23:59:59Z",
                                      {"eo:cloud_cover": {"lt": max_cloud}, "platform": {"in": ["landsat-8", "landsat-9"]}}, limit=50)
            per_year[yr] = {"treated": [], "control": []}
            for f in sorted(feats, key=lambda f: f["properties"].get("eo:cloud_cover", 100)):
                try:
                    b = stac.load_bands(LS, [f], ["lwir11", "qa_pixel"], bbox, res, epsg, nearest_bands=("qa_pixel",))
                except RuntimeError:
                    b = stac.load_bands(LS, [f], ["ST_B10", "QA_PIXEL"], bbox, res, epsg, nearest_bands=("QA_PIXEL",))
                    b = {"lwir11": b["ST_B10"], "qa_pixel": b["QA_PIXEL"]}
                bad = qa_mask(b["qa_pixel"]); lst = lst_celsius(b["lwir11"], bad)
                tv = lst[tmask]; cv = lst[cmask]
                tv = tv[np.isfinite(tv)]; cv = cv[np.isfinite(cv)]
                scenes.append({"year": yr, "id": f["id"], "date": f["properties"]["datetime"][:10], "cloud_cover": f["properties"].get("eo:cloud_cover"),
                               "treated_px": int(tv.size), "control_px": int(cv.size)})
                if tv.size and cv.size:
                    per_year[yr]["treated"].append(tv); per_year[yr]["control"].append(cv)
        except Exception as e:
            failed.append({"year": yr, "error": f"{type(e).__name__}: {e}"})
    progress(total, total, "이중차분")

    def pool(ys, key):
        arrs = [a for y in ys for a in per_year.get(y, {}).get(key, [])]
        return np.concatenate(arrs) if arrs else np.array([])
    tp, ta, cp, ca = pool(years_before, "treated"), pool(years_after, "treated"), pool(years_before, "control"), pool(years_after, "control")
    did = metrics.did_effect(tp, ta, cp, ca)
    ci = metrics.bootstrap_ci(ta - np.median(tp) if tp.size else ta, ca - np.median(cp) if cp.size else ca) if (tp.size and cp.size) else None
    mde = metrics.mde(cp, int(tmask.sum()))
    try:
        from . import safetydata
        sh = safetydata.shelters_in_bbox(bbox)
    except Exception:
        sh = None
    return {
        "status": "partial" if failed else ("ok" if did["effect"] is not None else "unmeasured"),
        "module": "heat", "project_id": p["id"], "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "design": {"collection": LS, "lst_formula": "DN*0.00341802+149.0 K", "qa_bits_masked": list(QA_BAD_BITS), "resolution_m": res, "season": "6/15~9/20", "epsg": epsg,
                   "treated_px": int(tmask.sum()), "control_px": int(cmask.sum())},
        "metrics": {
            "did_effect_lst_c": metric(did["effect"], "MODEL", "℃", n=did["n"].get("treat_post"), note=did["reason"] or "(시공 후-전)-(대조 후-전), 여름 장면 중앙값"),
            "medians": metric(did.get("medians"), "OBSERVED", "℃"),
            "ci95": metric(list(ci) if ci else None, "MODEL", "℃"),
            "mde_c": metric(mde, "ASSUMPTION", "℃", note="독립 화소 가정 근사"),
            "scenes_used": metric(len(scenes), "OBSERVED", "장면"),
            "shelters_in_aoi": metric(sh["in_bbox"] if sh else None, "OBSERVED", "곳", n=sh["total"] if sh else None, note="재난안전데이터 공유플랫폼 무더위쉼터(DSSP-IF-10942) 중 AOI 안" if sh else "무더위쉼터 자료 없음(키·IP 등록 필요)"),
            "shelter_capacity_in_aoi": metric(sh["capacity_sum"] if sh else None, "OBSERVED", "명", note="AOI 안 쉼터 이용가능인원 합"),
        },
        "shelters": (sh or {}).get("items", [])[:50],
        "scenes": scenes, "failed": failed, "verdict": _verdict(did["effect"], mde, ci),
        "limitations": ["30 m 열적외(원 100 m) 해상도에서 단일 동 효과는 검출되기 어렵다. 블록 단위 폴리곤 권장.",
                        "Landsat은 오전 통과라 야간 열섬을 보지 못한다.", "지표면온도는 기온·실내온도가 아니다."],
    }


def _verdict(effect, mde, ci) -> dict:
    if effect is None:
        return {"code": "unmeasured", "text": "전후·처리/대조 네 집단 중 관측이 없는 집단이 있어 판정하지 않는다."}
    if mde is not None and abs(effect) < mde:
        return {"code": "undetected", "text": f"이중차분 {effect:+.2f}℃가 검출가능최소효과 {mde:.2f}℃ 미만 — 미검출."}
    if ci is not None and ci[0] <= 0 <= ci[1]:
        return {"code": "undetected", "text": "95% 신뢰구간이 0을 포함 — 미검출."}
    return {"code": "detected", "text": f"시공 블록 지표면온도 이중차분 {effect:+.2f}℃."}
