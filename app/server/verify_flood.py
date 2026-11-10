"""침수 방재 사업 검증 — 1단계: 사건별 Sentinel-1 관측가능성 등급.

A: 호우 정점 후 48시간 이내 관측 / B: 48~120시간 / C: 120시간 초과 또는 미관측.
등급 C 사건은 침수 지도를 만들지 않고 "현장조사 전환"을 권고한다(물길잡이 설계 계승).
2단계(정비 전후 침수 범위 이중차분)는 A·B 사건이 전후 각각 1건 이상일 때만 실행 대상이 된다(본 버전은 설계·사건 목록까지).
"""
from __future__ import annotations

import datetime as dt

import numpy as np

from . import config, stac
from .envelope import metric
from .overlay_png import CHANGE_PALETTE, FLOOD_PALETTE, class_png

S1 = "sentinel-1-grd"
RTC = "sentinel-1-rtc"          # 지형보정 감마0(선형 전력). 익명 SAS로 읽힘(2026-10-12 실측)
WATER_DB = -16.0                 # VV 후방산란 임계(dB): 잔잔한 수면
CHANGE_DB = -3.0                 # 기준선 대비 감소 임계(dB)
REF_DAYS = (75, 4)               # 기준선: 정점 75일 전 ~ 4일 전, 같은 상대궤도


def grade(hours: float | None) -> str:
    if hours is None or hours > 120:
        return "C"
    return "A" if hours <= 48 else "B"


def observability(event_peak_iso: str, bbox: list[float], lookahead_days: int = 7) -> dict:
    peak = dt.datetime.fromisoformat(event_peak_iso)
    start = (peak - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"); end = (peak + dt.timedelta(days=lookahead_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    feats = stac.search_items(S1, bbox, f"{start}/{end}", limit=50)
    passes = []; seen = set()
    for f in feats:
        # 실측(2026-10-06): 같은 장면이 두 ID로 중복 반환됨 → 관측시각으로 중복 제거
        if f["properties"]["datetime"] in seen:
            continue
        seen.add(f["properties"]["datetime"])
        t = dt.datetime.fromisoformat(f["properties"]["datetime"].replace("Z", "")).replace(microsecond=0)
        hrs = (t - peak).total_seconds() / 3600
        if hrs < 0:
            continue
        passes.append({"id": f["id"], "datetime": f["properties"]["datetime"], "hours_after_peak": round(hrs, 1),
                       "relative_orbit": f["properties"].get("sat:relative_orbit"), "orbit_state": f["properties"].get("sat:orbit_state"),
                       "polarizations": f["properties"].get("sar:polarizations")})
    passes.sort(key=lambda x: x["hours_after_peak"])
    first = passes[0]["hours_after_peak"] if passes else None
    return {"event_peak": event_peak_iso, "grade": grade(first), "first_pass_hours": first, "passes": passes}


def auto_events(project: dict, progress) -> tuple[list[dict], list[str]]:
    """기상청 시간 강우에서 호우 사건을 자동 추출한다. 키·지점이 없으면 ([], 사유)."""
    from . import kma
    stn = project.get("kma_stn"); warnings = []
    if not stn:
        return [], ["kma_stn(관측 지점번호) 미지정"]
    out = []
    years = [(y, "before") for y in project.get("years_before", [])] + [(y, "after") for y in project.get("years_after", [])]
    for i, (y, phase) in enumerate(years):
        progress(i, len(years) + 1, f"기상청 시간강우 {y}년 (지점 {stn})")
        rows = kma.fetch_season(stn, int(y))
        if rows is None:
            warnings.append(f"{y}년 시간강우를 받지 못함(KMA_APIHUB_KEY·활용신청·504)"); continue
        for ev in kma.rain_events(rows):
            out.append({"name": f"{y} 호우(정점 {ev['peak_kst'][:16]} KST, 1h {ev['peak_rn']:.1f} mm, 3h {ev['max_3h']:.1f} mm, 총 {ev['total_mm']} mm)", "peak": ev["peak_utc"], "phase": phase, "source": "KMA kma_sfctm3", "rain": ev})
    return out, warnings


def _db(a: np.ndarray) -> np.ndarray:
    return 10 * np.log10(np.where(a > 0, a, np.nan))


def _passes(items: list[dict]) -> list[list[dict]]:
    """같은 관측시각(패스)의 타일을 묶는다(모자이크용)."""
    g: dict[str, list[dict]] = {}
    for it in items:
        g.setdefault(it["properties"]["datetime"][:16], []).append(it)
    return [g[k] for k in sorted(g)]


def flood_extent(ev: dict, bbox: list[float], res: float, epsg: int) -> tuple[dict, np.ndarray | None, np.ndarray | None]:
    """A/B 사건의 첫 패스 RTC VV(dB)를 같은 궤도의 건기 기준선 중앙값과 비교해 침수 화소를 뽑는다."""
    p0 = ev["passes"][0]; orbit = p0.get("relative_orbit")
    t = dt.datetime.fromisoformat(p0["datetime"].replace("Z", ""))
    win = f"{(t - dt.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')}/{(t + dt.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    post_items = [i for i in stac.search_items(RTC, bbox, win, limit=20) if i["properties"].get("sat:relative_orbit") == orbit]
    if not post_items:
        return {"error": "사건 직후 패스의 RTC 자료 없음"}, None, None
    peak = dt.datetime.fromisoformat(ev["event_peak"])
    fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    # 기준선: 같은 궤도의 건기 패스. 사건 전(75~4일 전)을 우선하고, 모자라면 물이 빠진 뒤(사건 후 6~75일)로 보충한다
    # (예: S1C 위성 궤도의 RTC는 2025-07-18부터 있어 그 전 기준선이 없다 — 2026-10-12 실측)
    before = [i for i in stac.search_items(RTC, bbox, f"{fmt(peak - dt.timedelta(days=REF_DAYS[0]))}/{fmt(peak - dt.timedelta(days=REF_DAYS[1]))}", limit=60) if i["properties"].get("sat:relative_orbit") == orbit]
    ref_passes = _passes(before)[-5:]; side = "before"
    if len(ref_passes) < 2:
        after = [i for i in stac.search_items(RTC, bbox, f"{fmt(peak + dt.timedelta(days=6))}/{fmt(peak + dt.timedelta(days=REF_DAYS[0]))}", limit=60) if i["properties"].get("sat:relative_orbit") == orbit]
        ref_passes = (ref_passes + _passes(after))[:5]; side = "mixed" if before else "after"
    if len(ref_passes) < 2:
        return {"error": f"기준선 패스 부족({len(ref_passes)}개, 같은 궤도 {orbit})"}, None, None
    post = _db(stac.load_bands(RTC, post_items, ["vv"], bbox, res, epsg)["vv"])
    ref = np.nanmedian(np.stack([_db(stac.load_bands(RTC, ps, ["vv"], bbox, res, epsg)["vv"]) for ps in ref_passes]), axis=0)
    okm = np.isfinite(post) & np.isfinite(ref)
    permanent = okm & (ref < WATER_DB)
    flooded = okm & ~permanent & (post < WATER_DB) & ((post - ref) < CHANGE_DB)
    px_ha = res * res / 10_000
    info = {"rtc_ids": [i["id"] for i in post_items], "reference_passes": len(ref_passes), "reference_side": side, "reference_dates": [ps[0]["properties"]["datetime"][:10] for ps in ref_passes],
            "flooded_ha": round(float(flooded.sum() * px_ha), 1), "permanent_water_ha": round(float(permanent.sum() * px_ha), 1),
            "valid_pct": round(float(okm.mean() * 100), 1), "hours_after_peak": p0["hours_after_peak"]}
    return info, flooded, permanent


def run(project: dict, progress=lambda done, total, msg: None) -> dict:
    p = project
    bbox = p["geometry"]["bbox"]; events = list(p.get("events", []))
    auto, auto_warn = auto_events(p, progress) if p.get("kma_stn") else ([], [])
    manual_peaks = {e["peak"][:10] for e in events}
    events += [e for e in auto if e["peak"][:10] not in manual_peaks]   # 수기 사건이 같은 날짜면 수기 우선
    if not events:
        return {"status": "waiting_input", "module": "flood", "project_id": p["id"], "reason": "호우 사건 목록(정점 시각)이 필요하다. 기상청 API허브(KMA_APIHUB_KEY)로 시간 강우에서 자동 추출하거나 수기로 입력한다.",
                "needs": ["events[].peak", "events[].phase(before|after)"], "metrics": {}, "limitations": []}
    out = []; failed = []
    for i, ev in enumerate(events):
        progress(i, len(events), f"관측가능성: {ev['peak'][:10]}")
        try:
            o = observability(ev["peak"], bbox); o["phase"] = ev.get("phase"); o["name"] = ev.get("name", ""); o["source"] = ev.get("source", "manual"); o["rain"] = ev.get("rain"); out.append(o)
        except Exception as e:
            failed.append({"event": ev, "error": f"{type(e).__name__}: {e}"})
    progress(len(events), len(events), "등급 집계")
    counts = {g: sum(1 for o in out if o["grade"] == g) for g in "ABC"}
    usable_before = [o for o in out if o["phase"] == "before" and o["grade"] in "AB"]
    usable_after = [o for o in out if o["phase"] == "after" and o["grade"] in "AB"]
    ready = bool(usable_before and usable_after)
    # ---- 2단계: 침수 범위 ----
    res = float(p.get("params", {}).get("res_m", 30)); epsg = stac.utm_epsg_for((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    union: dict[str, np.ndarray | None] = {"before": None, "after": None}; perm_any = None; stage2_done = 0; overlays = None
    ab = [o for o in out if o["grade"] in "AB"]
    for i, o in enumerate(ab):
        progress(i, len(ab), f"침수 범위: {o['event_peak'][:10]}")
        try:
            info, fl, pm = flood_extent(o, bbox, res, epsg)
        except Exception as e:
            info, fl, pm = {"error": f"{type(e).__name__}: {e}"}, None, None
        o["stage2"] = info
        if fl is not None:
            stage2_done += 1
            union[o["phase"]] = fl if union[o["phase"]] is None else (union[o["phase"]] | fl)
            perm_any = pm if perm_any is None else (perm_any | pm)
    # 강우 보정: 사건별 침수 ha를 최대 3시간 강우(mm)로 나눈 값(ha/mm)의 시기별 중앙값 — 강도가 다른 사건을 같은 자로 잰다
    for o in ab:
        s2 = o.get("stage2") or {}; r3 = (o.get("rain") or {}).get("max_3h")
        o["ha_per_mm"] = round(s2["flooded_ha"] / r3, 3) if (s2.get("flooded_ha") is not None and r3) else None
    def _med(ph):
        v = sorted(o["ha_per_mm"] for o in ab if o["phase"] == ph and o.get("ha_per_mm") is not None)
        if not v:
            return None
        m = len(v) // 2
        return round(v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2, 3)
    hpm_b, hpm_a = _med("before"), _med("after")
    norm_pct = round(100 * (hpm_a - hpm_b) / hpm_b, 1) if (hpm_a is not None and hpm_b) else None
    px_ha = res * res / 10_000
    ha_b = round(float(union["before"].sum() * px_ha), 1) if union["before"] is not None else None
    ha_a = round(float(union["after"].sum() * px_ha), 1) if union["after"] is not None else None
    change_ha = round(ha_a - ha_b, 1) if (ha_a is not None and ha_b is not None) else None
    change_pct = round(100 * change_ha / ha_b, 1) if (change_ha is not None and ha_b) else None
    if stage2_done:
        out_dir = config.RESULTS_DIR / p["id"]; out_dir.mkdir(parents=True, exist_ok=True)
        shape = next(a for a in union.values() if a is not None).shape
        pz = perm_any if perm_any is not None else np.zeros(shape, bool)
        u = f"/api/projects/{p['id']}/overlay/"; overlays = {"bounds": bbox, "legend": {}}
        for ph, lab in (("before", "정비 전"), ("after", "정비 후")):
            if union[ph] is not None:
                cls = np.where(union[ph], 1, np.where(pz, 2, 0)).astype("uint8")
                class_png(cls, out_dir / f"flood_{ph}.png", FLOOD_PALETTE); overlays[f"flood_{ph}"] = u + f"flood_{ph}.png"
                overlays["legend"][f"flood_{ph}"] = f"{lab} 호우 침수 추정(청) · 상시 수역(회) · VV<{WATER_DB:.0f} dB & 기준선 대비 {CHANGE_DB:.0f} dB"
        if union["before"] is not None and union["after"] is not None:
            cls = np.where(union["before"] & union["after"], 3, np.where(union["before"], 1, np.where(union["after"], 2, np.where(pz, 4, 0)))).astype("uint8")
            class_png(cls, out_dir / "flood_change.png", CHANGE_PALETTE); overlays["flood_change"] = u + "flood_change.png"
            overlays["legend"]["flood_change"] = "정비 전에만 침수(청) · 정비 후에만 침수(적) · 두 시기 모두(자) · 상시 수역(회)"
    n_auto = sum(1 for o in out if o.get("source") == "KMA kma_sfctm3")
    return {
        "status": "partial" if (failed or auto_warn) else "ok", "module": "flood", "project_id": p["id"], "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "design": {"collection": S1, "grades": {"A": "≤48h", "B": "48~120h", "C": ">120h 또는 미관측"}, "stage2": "정비 전후 A·B 사건의 침수 범위(VV dB, 동일 궤도·DOY±15일 다년 기준선 robust z) 이중차분",
                   "rain_events": f"기상청 지점 {p.get('kma_stn')} 시간강우, 3h≥60mm 또는 1h≥30mm, 24h 간격 묶음" if p.get("kma_stn") else "수기 입력"},
        "warnings": auto_warn,
        "metrics": {
            "events_total": metric(len(out), "OBSERVED", "건", note=f"기상청 자동 추출 {n_auto}건 + 수기 {len(out) - n_auto}건"),
            "grade_counts": metric(counts, "RULE", "건", note="관측 지연시간 규칙 판정"),
            "stage2_ready": metric(ready, "RULE", "", note="정비 전·후 각각 A/B 사건 1건 이상이면 2단계 실행 가능"),
            "flooded_ha_before": metric(ha_b, "MODEL", "ha", n=sum(1 for o in ab if o["phase"] == "before" and o.get("stage2", {}).get("flooded_ha") is not None), note="정비 전 A/B 사건 침수 추정 범위 합집합(상시 수역 제외)"),
            "flooded_ha_after": metric(ha_a, "MODEL", "ha", n=sum(1 for o in ab if o["phase"] == "after" and o.get("stage2", {}).get("flooded_ha") is not None), note="정비 후 A/B 사건 침수 추정 범위 합집합"),
            "flooded_change_ha": metric(change_ha, "MODEL", "ha", note="정비 후 − 정비 전. 사건 강우 강도 차이는 보정하지 않았다"),
            "flooded_change_pct": metric(change_pct, "MODEL", "%", note="정비 전 대비 변화율"),
            "flooded_ha_per_mm_before": metric(hpm_b, "MODEL", "ha/mm", n=sum(1 for o in ab if o["phase"] == "before" and o.get("ha_per_mm") is not None), note="사건별 침수 ha ÷ 최대 3시간 강우(mm)의 중앙값 — 정비 전"),
            "flooded_ha_per_mm_after": metric(hpm_a, "MODEL", "ha/mm", n=sum(1 for o in ab if o["phase"] == "after" and o.get("ha_per_mm") is not None), note="같은 자(ha/mm)로 잰 정비 후"),
            "flooded_change_pct_rain_adjusted": metric(norm_pct, "MODEL", "%", note="강우 보정 변화율(ha/mm 기준). 표본이 적어 사건 1건의 영향이 크다"),
        },
        "overlays": overlays,
        "events": out, "failed": failed,
        "verdict": _verdict(ready, ha_b, ha_a, change_pct, ab, hpm_b, hpm_a, norm_pct),
        "limitations": ["관측가능성은 통과 여부이며 실제 촬영·구름 무관(SAR) 조건만 반영한다.",
                        "침수 범위는 첫 통과 시점의 수면만 잡는다. 정점 후 2~3일이 지난 B등급 사건은 이미 물이 빠진 구역을 놓칠 수 있다.",
                        "VV 후방산란 임계는 잔잔한 수면 기준이며, 바람에 거친 수면·침수된 작물은 과소, 평탄한 포장면은 과대 추정될 수 있다.",
                        "정비 전후 사건의 강우 강도가 다르므로 범위 변화는 사업 효과만의 값이 아니다."],
    }


def _verdict(ready: bool, ha_b, ha_a, change_pct, ab: list[dict], hpm_b=None, hpm_a=None, norm_pct=None) -> dict:
    if ha_b is not None and ha_a is not None:
        rb = max([(o.get("rain") or {}).get("max_3h", 0) for o in ab if o["phase"] == "before"] or [0])
        ra = max([(o.get("rain") or {}).get("max_3h", 0) for o in ab if o["phase"] == "after"] or [0])
        rain = f" (최대 3시간 강우 전 {rb:.0f} mm · 후 {ra:.0f} mm)" if (rb or ra) else ""
        adj = f" 강우 보정(ha/mm) 전 {hpm_b:.2f} → 후 {hpm_a:.2f} ({norm_pct:+.0f}%)." if (hpm_b is not None and hpm_a is not None and norm_pct is not None) else ""
        key_pct = norm_pct if norm_pct is not None else change_pct
        if key_pct is not None and key_pct <= -10:
            return {"code": "reduced", "text": f"침수 추정 범위 정비 전 {ha_b:,.0f} ha → 후 {ha_a:,.0f} ha ({change_pct:+.0f}%){rain}.{adj} — 침수 범위 감소."}
        return {"code": "not_reduced", "text": f"침수 추정 범위 정비 전 {ha_b:,.0f} ha → 후 {ha_a:,.0f} ha ({change_pct:+.0f}%){rain}.{adj} — 감소를 확인하지 못함."}
    if ready:
        return {"code": "ready", "text": "2단계(침수 범위 비교) 실행 조건은 충족했으나 한쪽 시기의 침수 범위를 산출하지 못했다."}
    return {"code": "waiting", "text": "정비 전 또는 후에 위성으로 확인 가능한(A/B) 사건이 없어 침수 범위 비교를 수행하지 않는다. 현장조사 결과로 대체한다."}
