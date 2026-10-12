"""산불 피해지 복구·복원 검증 모듈.

설계: 동일 상대궤도 Sentinel-2 L2A, dNBR 피해등급(Key & Benson 2006), 피해지 vs 미피해 인접 산림 대조,
NDVI 회복률(피해지/대조지 중앙값 비)과 이중차분 효과·부트스트랩 CI·검출가능최소효과(MDE).
모든 장면은 캐시되고(장면 단위 체크포인트), 실패 장면은 결과에 이름과 함께 남는다.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np

from . import config, metrics, stac
from .envelope import metric

S2 = "sentinel-2-l2a"
BANDS = ["B02", "B03", "B04", "B08", "B12", "SCL"]
SCL_BAD = (0, 1, 3, 8, 9, 10, 11)
SEVERITY = [(0.10, 0.27, "경(low)"), (0.27, 0.44, "중(moderate-low)"), (0.44, 0.66, "중강(moderate-high)"), (0.66, 9.0, "강(high)")]


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def default_windows(event: dt.date, contained: dt.date, today: dt.date) -> list[tuple[str, str, str]]:
    """(라벨, 시작, 끝). 진화 직후 → 첫 생장기 → 이듬해부터 매년 생장기·생장기 말."""
    wins = [("pre", (event - dt.timedelta(days=60)).isoformat(), (event - dt.timedelta(days=1)).isoformat()),
            ("post", (contained + dt.timedelta(days=3)).isoformat(), (contained + dt.timedelta(days=45)).isoformat())]
    y = event.year
    if dt.date(y, 6, 15) > contained + dt.timedelta(days=45):
        wins.append((f"{y} 생장기", f"{y}-06-15", f"{y}-07-31"))
    yy = y + 1
    while dt.date(yy, 6, 1) <= today:
        wins.append((f"{yy} 생장기", f"{yy}-06-01", f"{yy}-07-31"))
        if dt.date(yy, 9, 1) <= today:
            wins.append((f"{yy} 생장기 말", f"{yy}-09-01", min(today, dt.date(yy, 10, 20)).isoformat()))
        yy += 1
    return wins


def pick_scene(bbox, start: str, end: str, orbit: str | None, max_cloud: float = 20.0) -> tuple[list[dict], str | None]:
    """창 안에서 구름이 가장 적은 날짜의 같은 패스 타일들을 고른다. 없으면 ([], None)."""
    feats = stac.search_items(S2, bbox, f"{start}T00:00:00Z/{end}T23:59:59Z", {"eo:cloud_cover": {"lt": max_cloud}}, limit=100)
    if orbit:
        feats = [f for f in feats if f["id"].split("_")[3] == orbit]
    if not feats:
        return [], None
    by_day: dict[str, list[dict]] = {}
    for f in feats:
        by_day.setdefault(f["properties"]["datetime"][:10], []).append(f)
    # 같은 날짜라도 궤도가 다르면 다른 패스다 → (날짜, 궤도) 단위로 묶고, AOI 커버리지(궤도 가장자리 제외)를 먼저, 구름을 다음으로 본다.
    groups: dict[tuple[str, str], list[dict]] = {}
    for d, fs in by_day.items():
        for f in fs:
            groups.setdefault((d, f["id"].split("_")[3]), []).append(f)
    scored = []
    for (d, orb), fs in groups.items():
        cov = coverage(fs, bbox); cc = float(np.mean([f["properties"].get("eo:cloud_cover", 100) for f in fs]))
        scored.append((round(cov, 1), -cc, d, orb))
    scored.sort(reverse=True)
    _, _, best_day, best_orb = scored[0]
    return groups[(best_day, best_orb)], best_day


def coverage(feats: list[dict], bbox) -> float:
    """장면 footprint 합집합이 AOI를 덮는 비율(0~1). footprint가 없으면 1로 간주."""
    from shapely.geometry import box, shape
    from shapely.ops import unary_union
    geoms = [shape(f["geometry"]) for f in feats if f.get("geometry")]
    if not geoms:
        return 1.0
    b = box(*bbox)
    return float(unary_union(geoms).intersection(b).area / b.area)


def refl(bands: dict[str, np.ndarray], pb: str) -> dict[str, np.ndarray]:
    """Processing Baseline ≥ 04.00이면 BOA_ADD_OFFSET(-1000) 적용. 비교 장면 간 기준선을 섞지 않도록 pb를 기록한다."""
    offset = 1000.0 if pb and pb >= "04.00" else 0.0
    bad = np.isin(bands["SCL"], SCL_BAD)
    out = {b: np.where(bad, np.nan, (bands[b] - offset) / 10000.0) for b in BANDS if b != "SCL"}
    out["valid_pct"] = float(100 * (1 - bad.mean()))
    return out


def severity_png(cls: np.ndarray, rgb: np.ndarray | None, path: Path) -> None:
    """피해등급을 반투명 PNG로 저장(지도 오버레이)."""
    from PIL import Image
    pal = {1: (233, 207, 156, 200), 2: (196, 138, 62, 215), 3: (138, 90, 30, 230), 4: (74, 42, 18, 240)}   # 등고선 갈색 계열(지형도 문법)
    h, w = cls.shape
    img = np.zeros((h, w, 4), dtype="uint8")
    for k, c in pal.items():
        img[cls == k] = c
    Image.fromarray(img, "RGBA").save(path)


def truecolor_png(r: dict[str, np.ndarray], path: Path) -> None:
    from PIL import Image
    arr = np.dstack([r["B04"], r["B03"], r["B02"]]) / 0.30
    arr = np.clip(np.nan_to_num(arr, nan=1.0), 0, 1)
    Image.fromarray((arr * 255).astype("uint8"), "RGB").save(path)


def run(project: dict, progress=lambda done, total, msg: None) -> dict:
    p = project; prm = p.get("params", {})
    bbox = p["geometry"]["bbox"]; res = float(prm.get("res_m", 40)); thr = float(prm.get("dnbr_threshold", 0.27))
    ndvi_min = float(prm.get("prefire_ndvi_min", 0.30)); ctrl_max = float(prm.get("control_abs_dnbr_max", 0.05))
    event = _d(p["event_date"]); contained = _d(p.get("contained_date", p["event_date"]))
    today = dt.date.today()
    epsg = stac.utm_epsg_for((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    windows = [tuple(w) for w in p.get("windows", [])] or default_windows(event, contained, today)
    out_dir = config.RESULTS_DIR / p["id"]; out_dir.mkdir(parents=True, exist_ok=True)

    scenes: list[dict] = []; failed: list[dict] = []; stack: dict[str, dict] = {}; orbit = None
    total = len(windows)
    for i, (label, start, end) in enumerate(windows):
        progress(i, total, f"장면 선택: {label}")
        try:
            items, day = pick_scene(bbox, start, end, orbit)
            if not items:
                scenes.append({"label": label, "window": [start, end], "date": None, "ids": [], "note": "구름<20%·동일 궤도 장면 없음"}); continue
            if orbit is None:
                orbit = items[0]["id"].split("_")[3]
            pb = items[0]["properties"].get("s2:processing_baseline", "")
            bands = stac.load_bands(S2, items, BANDS, bbox, res, epsg)
            r = refl(bands, pb)
            stack[label] = r
            scenes.append({"label": label, "window": [start, end], "date": day, "ids": [it["id"] for it in items], "orbit": orbit, "processing_baseline": pb,
                           "cloud_cover": float(np.mean([it["properties"].get("eo:cloud_cover", 0) for it in items])), "valid_pct": round(r["valid_pct"], 1)})
        except Exception as e:  # 장면 하나의 실패가 전체를 멈추지 않는다. 다만 이름을 남긴다.
            failed.append({"label": label, "window": [start, end], "error": f"{type(e).__name__}: {e}"})
    progress(total, total, "지표 계산")

    if "pre" not in stack or "post" not in stack:
        return {"status": "failed", "reason": "산불 전/후 기준 장면을 확보하지 못함", "scenes": scenes, "failed": failed}

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = {k: (r["B08"] - r["B04"]) / (r["B08"] + r["B04"]) for k, r in stack.items()}
        nbr = {k: (r["B08"] - r["B12"]) / (r["B08"] + r["B12"]) for k, r in stack.items()}
    dnbr = nbr["pre"] - nbr["post"]
    forest = ndvi["pre"] > ndvi_min
    burn = (dnbr > thr) & forest
    ctrl = (np.abs(dnbr) < ctrl_max) & forest & np.isfinite(dnbr)
    px_ha = res * res / 1e4
    cls = np.full(dnbr.shape, np.nan)
    for k, (lo, hi, _) in enumerate(SEVERITY, start=1):
        cls[(dnbr >= lo) & (dnbr < hi)] = k
    severity = [{"class": k, "label": lab, "ha": int(round(float(np.nansum(cls == k)) * px_ha))} for k, (lo, hi, lab) in enumerate(SEVERITY, start=1)]

    labels = [s["label"] for s in scenes if s["date"] and s["label"] in stack]
    series = []
    for lab in labels:
        tb = metrics.summarize(ndvi[lab][burn]); tc = metrics.summarize(ndvi[lab][ctrl])
        series.append({"label": lab, "date": next(s["date"] for s in scenes if s["label"] == lab), "burned": tb, "control": tc,
                       "recovery_ratio": metrics.recovery_ratio(ndvi[lab][burn], ndvi[lab][ctrl])})
    latest = labels[-1]
    did = metrics.did_effect(ndvi["pre"][burn], ndvi[latest][burn], ndvi["pre"][ctrl], ndvi[latest][ctrl])
    ci = metrics.bootstrap_ci(ndvi[latest][burn], ndvi[latest][ctrl])
    mde = metrics.mde(ndvi["pre"][ctrl], int(burn.sum()))
    base_ratio = series[0]["recovery_ratio"]; last_ratio = series[-1]["recovery_ratio"]
    gap_closed = None if (base_ratio is None or last_ratio is None) else float(min(1.0, max(0.0, last_ratio / base_ratio)) if base_ratio else None)

    severity_png(cls, None, out_dir / "dnbr.png"); truecolor_png(stack["pre"], out_dir / "pre.png"); truecolor_png(stack["post"], out_dir / "post.png")
    stac.save_json_atomic(out_dir / "scenes.json", {"scenes": scenes, "failed": failed})

    burned_ha = int(round(float(burn.sum()) * px_ha))
    return {
        "status": "partial" if failed else "ok",
        "module": "fire", "project_id": p["id"], "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "design": {"orbit": orbit, "resolution_m": res, "dnbr_threshold": thr, "prefire_ndvi_min": ndvi_min, "control_abs_dnbr_max": ctrl_max, "epsg": epsg,
                   "masking": "SCL 0·1·3·8·9·10·11", "reflectance": "(DN-1000)/10000 (PB≥04.00)", "severity_reference": "Key & Benson (2006)"},
        "metrics": {
            "burned_forest_ha": metric(burned_ha, "MODEL", "ha", n=int(burn.sum()), note="dNBR>임계 ∧ 산불 전 NDVI>임계인 화소 면적"),
            "control_ha": metric(int(round(float(ctrl.sum()) * px_ha)), "MODEL", "ha", n=int(ctrl.sum())),
            "recovery_ratio_latest": metric(last_ratio, "MODEL", "비", n=int(burn.sum()), note=f"{latest} 피해지/대조지 NDVI 중앙값 비"),
            "did_effect_ndvi": metric(did["effect"], "MODEL", "NDVI", n=did["n"].get("treat_post"), note=did["reason"] or "이중차분: (피해 후-전)-(대조 후-전)"),
            "ci95_median_diff": metric(list(ci) if ci else None, "MODEL", "NDVI", note="최근 시점 피해지-대조지 중앙값 차이의 부트스트랩 95% CI(seed 42)"),
            "mde_ndvi": metric(mde, "ASSUMPTION", "NDVI", note="독립 화소 가정의 근사치 — 공간 자기상관 때문에 실제 검출력은 더 낮다"),
            "valid_pct_min": metric(min(s["valid_pct"] for s in scenes if s.get("valid_pct") is not None), "OBSERVED", "%"),
        },
        "severity": severity, "series": series, "scenes": scenes, "failed": failed,
        "overlays": {"dnbr": f"/api/projects/{p['id']}/overlay/dnbr.png", "pre": f"/api/projects/{p['id']}/overlay/pre.png", "post": f"/api/projects/{p['id']}/overlay/post.png", "bounds": bbox},
        "verdict": _verdict(last_ratio, did["effect"], mde, ci),
        "limitations": [
            "복원 사업 구역(계획복원/자연복원) 자료가 결합되기 전의 예비 분석이다. 구역 자료가 들어오면 처리구를 복원구로, 대조구를 자연복원구로 재정의한다.",
            "NDVI 회복은 초본·관목 재생도 포함하므로 임목 회복과 다를 수 있다.",
            "검출가능최소효과는 화소 독립을 가정한 낙관적 근사치다.",
            "궤도 가장자리·타일 경계 밖은 분석에서 제외했다.",
        ],
    }


def _verdict(ratio, effect, mde, ci) -> dict:
    """산불 복구 모듈의 판정. 이중차분(피해지 변화 − 대조지 변화)이 음수로 유의하면 '회복 격차 잔존', 0과 구분되지 않으면 '대조지 수준 회복'."""
    if ratio is None or effect is None:
        return {"code": "unmeasured", "text": "회복률 또는 효과를 산출할 표본이 없어 판정하지 않는다."}
    below_mde = mde is not None and abs(effect) < mde
    ci_has_zero = ci is not None and ci[0] <= 0 <= ci[1]
    if below_mde or ci_has_zero:
        return {"code": "recovered", "text": f"최근 시점 회복률 {ratio:.2f}. 피해지와 대조지의 변화 차이({effect:+.3f} NDVI)가 검출 한계 안 — 대조지 수준으로 회복된 것으로 판정(미검출은 효과 없음의 증명이 아님)."}
    ci_txt = f" (피해지−대조지 95% CI {ci[0]:+.3f}~{ci[1]:+.3f})" if ci else ""
    if effect < 0:
        return {"code": "gap_remaining", "text": f"최근 시점 회복률 {ratio:.2f}. 피해지는 대조지 대비 {abs(effect):.3f} NDVI만큼 아직 회복되지 못함{ci_txt} — 회복 격차 잔존."}
    return {"code": "recovered", "text": f"최근 시점 회복률 {ratio:.2f}. 피해지 변화가 대조지를 {effect:+.3f} NDVI 상회{ci_txt} — 회복 완료."}
