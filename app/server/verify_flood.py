"""침수 방재 사업 검증 — 1단계: 사건별 Sentinel-1 관측가능성 등급.

A: 호우 정점 후 48시간 이내 관측 / B: 48~120시간 / C: 120시간 초과 또는 미관측.
등급 C 사건은 침수 지도를 만들지 않고 "현장조사 전환"을 권고한다(물길잡이 설계 계승).
2단계(정비 전후 침수 범위 이중차분)는 A·B 사건이 전후 각각 1건 이상일 때만 실행 대상이 된다(본 버전은 설계·사건 목록까지).
"""
from __future__ import annotations

import datetime as dt

from . import stac
from .envelope import metric

S1 = "sentinel-1-grd"


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
        },
        "events": out, "failed": failed,
        "verdict": {"code": "ready" if ready else "waiting", "text": ("2단계(침수 범위 이중차분) 실행 조건 충족." if ready else "정비 전 또는 후에 위성으로 확인 가능한(A/B) 사건이 없어 침수 범위 비교를 수행하지 않는다. 현장조사 결과로 대체한다.")},
        "limitations": ["관측가능성은 통과 여부이며 실제 촬영·구름 무관(SAR) 조건만 반영한다.", "2단계 범위 판독은 본 버전에 포함되지 않았다."],
    }
