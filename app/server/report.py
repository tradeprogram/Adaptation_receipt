"""성과 카드(Adaptation Receipt) 조립 — 보고서 부록에 그대로 붙는 단위.

카드 = 사업 메타 + 판정 + 지표(값·배지·n·주석) + 설계 + 한계 + 재현 매니페스트. HTML은 Jinja2 템플릿(인쇄용).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config

_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=select_autoescape(["html"]))

MODULE_LABEL = {"fire": "산불 피해지 복구·복원", "heat": "옥상 차열·녹화(열 저감)", "flood": "하천·배수 정비(침수 방재)", "equity": "형평성 감사"}
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


def build_card(project: dict, results: dict[str, dict | None], equity: dict | None) -> dict:
    modules = []
    for m, r in results.items():
        if r is None:
            modules.append({"module": m, "label": MODULE_LABEL.get(m, m), "status": "not_run", "verdict": {"code": "not_run", "text": "아직 실행되지 않음"}, "metrics": [], "limitations": []})
            continue
        rows = []
        for k, mt in (r.get("metrics") or {}).items():
            rows.append({"key": k, "value": mt["value"], "display": fmt(mt["value"], mt.get("unit", "")), "badge": mt["badge"], "badge_label": BADGE_LABEL[mt["badge"]],
                         "n": mt.get("n"), "measured": mt.get("measured", mt["value"] is not None), "note": mt.get("note", "")})
        modules.append({"module": m, "label": MODULE_LABEL.get(m, m), "status": r.get("status"), "verdict": r.get("verdict", {"code": r.get("status"), "text": r.get("reason", "")}),
                        "metrics": rows, "design": r.get("design", {}), "limitations": r.get("limitations", []), "scenes": r.get("scenes", []), "failed": r.get("failed", []),
                        "series": r.get("series"), "severity": r.get("severity"), "events": r.get("events"), "overlays": r.get("overlays"), "computed_at": r.get("computed_at"), "needs": r.get("needs")})
    eq = None
    if equity is not None:
        eq = {"status": equity["status"], "warnings": equity["warnings"], "data": equity["data"]}
    return {"project": {k: project.get(k) for k in ("id", "name", "type", "agency", "region", "budget_krw", "period", "legal_basis", "description", "event_date", "contained_date")},
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"), "modules": modules, "equity": eq,
            "badges": BADGE_LABEL, "disclaimer": "모든 수치에는 출처 배지가 붙는다. '측정 불가'는 0이 아니라 표본 부족·관측 공백을 뜻한다. 미검출은 효과가 없다는 증명이 아니다."}


def render_html(card: dict) -> str:
    return _env.get_template("card.html").render(card=card, mock=config.MOCK)
