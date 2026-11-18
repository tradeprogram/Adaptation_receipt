"""성과 카드(Adaptation Receipt) 조립 — 보고서 부록에 그대로 붙는 단위.

카드 = 사업 메타 + 판정 + 지표(값·배지·n·주석) + 설계 + 한계 + 재현 매니페스트. HTML은 Jinja2 템플릿(인쇄용).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config

_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=select_autoescape(["html"]))

MODULE_LABEL = {"fire": "산불 피해지 복원", "heat": "옥상 차열(열 저감)", "flood": "배수 정비(침수 방재)", "equity": "형평성 감사"}
BADGE_LABEL = {"OBSERVED": "실측", "MODEL": "계산", "RULE": "규칙", "ASSUMPTION": "가정", "FORECAST": "예보"}


def fmt(v, unit: str = "") -> str:
    if v is None:
        return "측정 불가"
    if isinstance(v, bool):
        return "예" if v else "아니오"
    if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
        return f"{v[0]:+.3f} ~ {v[1]:+.3f} {unit}".strip()
    if isinstance(v, dict):
        return ", ".join(f"{k} {fmt(x)}" for k, x in v.items())
    if isinstance(v, float):
        return (f"{v:,.3f}" if abs(v) < 10 else f"{v:,.1f}") + (f" {unit}" if unit else "")
    if isinstance(v, int):
        return f"{v:,}" + (f" {unit}" if unit else "")
    return str(v)


PLAIN_VERDICT = {"detected": "효과 확인", "recovered": "주변 수준으로 회복", "gap_remaining": "아직 덜 회복", "reduced": "침수 줄어듦", "not_reduced": "침수 줄지 않음",
                 "undetected": "효과 확인 안 됨", "unmeasured": "자료 부족", "ready": "비교 가능", "waiting": "자료 기다리는 중", "waiting_input": "입력 필요",
                 "not_run": "검정 전", "failed": "실패", "partial": "부분 완료", "ok": "완료"}
# 화면과 인쇄 카드에 적는 항목 이름. 기술 키는 JSON에 남는다
PLAIN_KEY = {
    "burned_forest_ha": "피해 산림 면적", "control_ha": "비교 구역(주변 숲) 면적", "recovery_ratio_latest": "회복률(피해지 ÷ 주변 숲)", "did_effect_ndvi": "주변 숲 대비 변화(식생지수)",
    "ci95_median_diff": "오차 범위(95%)", "mde_ndvi": "알아볼 수 있는 최소 변화(식생지수)", "valid_pct_min": "구름 없는 화소 비율(최소)",
    "did_effect_lst_c": "비교 동 대비 온도 변화", "medians": "구역별 낮 지표면 온도", "ci95": "오차 범위(95%)", "mde_c": "알아볼 수 있는 최소 온도 변화", "scenes_used": "사용한 위성 사진 수",
    "treated_area_ha": "시공 면적", "area_for_mde_1c_ha": "1℃ 변화를 알아보려면 필요한 면적", "area_for_mde_05c_ha": "0.5℃ 변화를 알아보려면 필요한 면적",
    "shelters_in_aoi": "구역 안 무더위쉼터", "shelter_capacity_in_aoi": "쉼터 수용 인원",
    "events_total": "호우 횟수", "grade_counts": "위성이 제때 찍은 횟수(등급별)", "stage2_ready": "정비 전후 비교 가능", "flooded_ha_before": "정비 전 침수 면적", "flooded_ha_after": "정비 후 침수 면적",
    "flooded_change_ha": "침수 면적 변화", "flooded_change_pct": "침수 면적 변화율", "flooded_ha_per_mm_before": "정비 전 비 1 mm당 침수", "flooded_ha_per_mm_after": "정비 후 비 1 mm당 침수",
    "flooded_change_pct_rain_adjusted": "비의 세기를 감안한 변화율",
    "old_building_share": "30년 넘은 건물 비율", "median_building_age": "건물 나이(중간값)", "households_total": "세대 수", "jurisdiction_oldage_support": "관할 노년부양비", "jurisdiction_aging_index": "관할 고령화지수",
}


def plain_summary(m: str, r: dict) -> dict:
    """담당자가 읽는 요약: 결론 한 줄, 쉬운 설명, 핵심 수치 3개, 다음에 할 일. 수치는 모듈 결과에서만 가져온다."""
    v = r.get("verdict") or {}; code = v.get("code") or r.get("status") or "not_run"
    mt = r.get("metrics") or {}
    val = lambda k: (mt.get(k) or {}).get("value")
    head = PLAIN_VERDICT.get(code, code); expl = v.get("text", ""); key: list = []; nxt: list = []
    if m == "fire":
        ratio, eff, ci, ha = val("recovery_ratio_latest"), val("did_effect_ndvi"), val("ci95_median_diff"), val("burned_forest_ha")
        series = r.get("series") or []; last = series[-1] if series else {}
        key = [{"label": "피해 산림 면적", "value": ha, "unit": "ha"}, {"label": "회복률(피해지 ÷ 주변 숲)", "value": round(ratio * 100) if ratio is not None else None, "unit": "%"},
               {"label": "주변 숲과의 차이", "value": round(eff, 3) if eff is not None else None, "unit": "식생지수", "signed": True}]
        if code == "gap_remaining" and ratio is not None:
            head = "피해지가 아직 주변 숲만큼 회복되지 않았습니다"
            expl = f"최근 관측({last.get('date', '')})에서 피해지의 식생지수는 주변 숲의 {ratio * 100:.0f}% 수준입니다. 주변 숲과 견준 변화 차이는 {eff:+.3f}이며" + (f" 오차 범위({ci[0]:+.3f}~{ci[1]:+.3f})가 0을 포함하지 않아 우연으로 보기 어렵습니다." if ci else "입니다.")
            nxt = ["회복이 늦은 구역(지도의 붉은 피해 정도가 짙은 사면)부터 보식과 사방 예산을 배정합니다.", "내년 같은 생장기에 같은 방법으로 다시 검정해 회복률 변화를 보고서에 이어 적습니다.", "식생지수는 풀과 관목의 회복도 포함하므로, 나무의 활착은 현장조사로 확인합니다."]
        elif code == "recovered" and ratio is not None:
            head = "피해지가 주변 숲 수준으로 회복되었습니다"
            expl = f"최근 관측({last.get('date', '')})에서 피해지의 식생지수는 주변 숲의 {ratio * 100:.0f}% 수준이며, 주변 숲과의 변화 차이({eff:+.3f})는 오차 범위 안입니다."
            nxt = ["이 카드를 이행점검 보고서 부록으로 첨부합니다.", "나무의 활착은 현장조사로 따로 확인합니다."]
    elif m == "heat":
        eff, mde, area, a1 = val("did_effect_lst_c"), val("mde_c"), val("treated_area_ha"), val("area_for_mde_1c_ha")
        key = [{"label": "비교 동 대비 온도 변화", "value": round(eff, 2) if eff is not None else None, "unit": "℃", "signed": True},
               {"label": "알아볼 수 있는 최소 변화", "value": round(mde, 2) if mde is not None else None, "unit": "℃"}, {"label": "시공 면적", "value": round(area, 2) if area is not None else None, "unit": "ha"}]
        if code == "undetected" and eff is not None and mde is not None:
            head = "이 시공 규모로는 온도 효과를 확인할 수 없습니다"
            expl = f"시공 동의 낮 지표면 온도는 비교 동보다 {eff:+.2f}℃ 변했지만, 시공 면적 {area:.2f} ha에서 위성 사진(30 m)으로 알아볼 수 있는 최소 변화는 {mde:.2f}℃입니다. 효과가 없다는 뜻이 아니라, 사진 해상도에 비해 시공 면적이 작다는 뜻입니다."
            nxt = [f"다음 시공은 한 블록({a1:.1f} ha 이상)으로 묶어야 1℃ 변화를 확인할 수 있습니다." if a1 else "다음 시공은 블록 단위로 묶어 발주합니다.", "세대 밀도가 높은 동부터 시공하는 다음 집행 순위(아래 '누가 혜택을 받았나')를 참고합니다.", "낮 지표면 온도이므로 밤 더위와 실내 온도는 별도 자료로 봅니다."]
        elif code == "detected" and eff is not None:
            head = f"시공 동의 낮 지표면 온도가 비교 동보다 {eff:+.2f}℃ 변했습니다"
            expl = f"알아볼 수 있는 최소 변화 {mde:.2f}℃를 넘는 차이입니다." if mde else ""
            nxt = ["이 카드를 이행점검 보고서 부록으로 첨부합니다.", "같은 설계로 다른 단지에도 시공 전후를 비교합니다."]
    elif m == "flood":
        hb, ha_, hpb, hpa, npct = val("flooded_ha_before"), val("flooded_ha_after"), val("flooded_ha_per_mm_before"), val("flooded_ha_per_mm_after"), val("flooded_change_pct_rain_adjusted")
        key = [{"label": "정비 전 침수 면적", "value": round(hb) if hb is not None else None, "unit": "ha"}, {"label": "정비 후 침수 면적", "value": round(ha_) if ha_ is not None else None, "unit": "ha"},
               {"label": "비의 세기를 감안한 변화", "value": round(npct) if npct is not None else None, "unit": "%", "signed": True}]
        ev = r.get("events") or []; rb = [e for e in ev if e.get("phase") == "before" and (e.get("stage2") or {}).get("flooded_ha") is not None]; ra = [e for e in ev if e.get("phase") == "after" and (e.get("stage2") or {}).get("flooded_ha") is not None]
        if code in ("not_reduced", "reduced") and hb is not None and ha_ is not None:
            head = "정비 후에도 침수 면적이 줄지 않았습니다" if code == "not_reduced" else "정비 후 침수 면적이 줄었습니다"
            rain_b = max((e.get("rain") or {}).get("max_3h", 0) for e in rb) if rb else None; rain_a = max((e.get("rain") or {}).get("max_3h", 0) for e in ra) if ra else None
            expl = f"정비 전 호우에는 {hb:,.0f} ha, 정비 후 호우에는 {ha_:,.0f} ha가 잠긴 것으로 위성 레이더에 잡혔습니다."
            if hpb is not None and hpa is not None:
                expl += f" 비 1 mm당 침수 면적은 {hpb:.2f}에서 {hpa:.2f} ha로 {npct:+.0f}% 변했습니다."
            if rain_b and rain_a:
                expl += f" 정비 후 호우(3시간 최대 {rain_a:.0f} mm)가 정비 전({rain_b:.0f} mm)보다 강했으므로, 이 변화는 사업 효과만의 결과가 아닙니다."
            nxt = ["정비 후에도 잠긴 구역(지도의 '정비 후에만 침수')을 현장조사 대상에 올립니다.", "다음 호우 뒤 같은 방법으로 다시 비교해 보고서에 이어 적습니다.", "위성이 지나간 시각의 수면이므로 최대 침수 범위와 다를 수 있습니다."] if code == "not_reduced" else ["이 카드를 이행점검 보고서 부록으로 첨부합니다.", "다음 호우 뒤 같은 방법으로 다시 비교합니다."]
    if code in ("not_run", "waiting_input"):
        head = "아직 검정하지 않았습니다" if code == "not_run" else "검정에 필요한 입력이 있습니다"; nxt = ["'다시 검정'을 누르면 공개 위성 자료로 계산합니다."]
    return {"code": code, "verdict_plain": PLAIN_VERDICT.get(code, code), "headline": head, "explain": expl, "key": key, "next": nxt}


def build_card(project: dict, results: dict[str, dict | None], equity: dict | None) -> dict:
    modules = []
    for m, r in results.items():
        if r is None:
            modules.append({"module": m, "label": MODULE_LABEL.get(m, m), "status": "not_run", "verdict": {"code": "not_run", "text": "아직 검정하지 않았다."}, "summary": plain_summary(m, {}), "metrics": [], "limitations": []})
            continue
        rows = []
        for k, mt in (r.get("metrics") or {}).items():
            rows.append({"key": k, "label": PLAIN_KEY.get(k, k), "value": mt["value"], "display": fmt(mt["value"], mt.get("unit", "")), "badge": mt["badge"], "badge_label": BADGE_LABEL[mt["badge"]],
                         "n": mt.get("n"), "measured": mt.get("measured", mt["value"] is not None), "note": mt.get("note", "")})
        modules.append({"module": m, "label": MODULE_LABEL.get(m, m), "status": r.get("status"), "verdict": r.get("verdict", {"code": r.get("status"), "text": r.get("reason", "")}), "summary": plain_summary(m, r),
                        "metrics": rows, "design": r.get("design", {}), "limitations": r.get("limitations", []), "scenes": r.get("scenes", []), "failed": r.get("failed", []),
                        "series": r.get("series"), "severity": r.get("severity"), "events": r.get("events"), "overlays": r.get("overlays"), "shelters": r.get("shelters"), "computed_at": r.get("computed_at"), "needs": r.get("needs")})
    eq = None
    if equity is not None:
        eq = {"status": equity["status"], "warnings": equity["warnings"], "data": equity["data"]}
    snap = None
    sp = config.RESULTS_DIR / project["id"] / "snapshot.json"
    if sp.exists() and (config.RESULTS_DIR / project["id"] / "snapshot.jpg").exists():
        import json as _json
        meta = _json.loads(sp.read_text(encoding="utf-8"))
        snap = {"url": f"/api/projects/{project['id']}/snapshot.jpg", "caption": meta.get("caption", ""), "at": meta.get("at", "")}
    return {"snapshot": snap, "project": {k: project.get(k) for k in ("id", "name", "type", "agency", "region", "budget_krw", "period", "legal_basis", "description", "event_date", "contained_date", "geometry", "kma_station")},
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"), "modules": modules, "equity": eq,
            "badges": BADGE_LABEL, "labels": PLAIN_KEY, "plain_verdict": PLAIN_VERDICT, "disclaimer": "모든 수치에는 출처 배지가 붙는다. 측정 불가는 표본 부족이나 관측 공백을 뜻하며 0이 아니다. 미검출은 효과가 없다는 증명이 아니다."}


def render_html(card: dict) -> str:
    return _env.get_template("card.html").render(card=card, mock=config.MOCK)
