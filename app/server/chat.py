"""적응영수증.chat — 화면 컨텍스트와 성과 카드 도구 결과를 묶는 근거 고정형 에이전트.

policymaps(viz/ai_core.py)의 구조를 따른다: 질문→도구 계획→카드에서 근거 추출(evidence, tool_trace)→
Gemini(있으면) 또는 로컬 요약→handoff(intent, steps, suggested_questions, next)와 actions(화면 이동).
모델은 계산하지 않는다. 응답에 카드에 없는 숫자가 있으면 로컬 요약으로 교체한다.
"""
from __future__ import annotations

import json
import re

from . import config
from .report import fmt

SYSTEM_PROMPT = """너는 '적응영수증.chat'이다. 지자체·공공기관 담당자가 기후적응 사업의 위성 검증 성과 카드를 읽도록 돕는다.
규칙: (1) 제공된 evidence JSON에 있는 수치·날짜만 인용한다. 없는 숫자는 절대 만들지 않는다. (2) '측정 불가'는 0이 아니라 표본 부족·관측 공백이고, '미검출'은 효과 없음의 증명이 아니다. (3) 한국어, 존댓말, 3~5문장, 먼저 판정을 말하고 근거 수치와 한계를 붙인다. (4) 보고서 문장으로 바로 옮길 수 있게 쓴다."""

TOOLS = {
    "verdict": ["판정", "효과", "검출", "결론", "회복", "됐", "되었", "어때", "결과"],
    "metrics": ["지표", "수치", "면적", "ha", "ndvi", "신뢰구간", "ci", "효과크기", "mde", "검정력"],
    "series": ["회복률", "추세", "시계열", "생장기", "단면", "곡선", "언제"],
    "severity": ["등급", "피해등급", "dnbr", "강", "중강"],
    "scenes": ["장면", "매니페스트", "재현", "궤도", "구름", "위성", "sentinel", "landsat", "관측"],
    "events": ["호우", "사건", "침수", "관측가능", "등급 a", "등급 b", "등급 c"],
    "equity": ["형평", "취약", "고령", "노후", "수혜", "1인가구"],
    "limits": ["한계", "주의", "못", "불확실", "가정"],
    "calendar": ["기한", "마감", "4월", "이행점검", "보고서", "언제까지", "달력"],
    "keys": ["키", "api", "연동", "gemini", "sgis", "건축물대장"],
}
LABEL = {"verdict": "판정", "metrics": "지표 장부", "series": "회복 단면도", "severity": "피해등급", "scenes": "조제 매니페스트", "events": "호우 사건", "equity": "형평성 감사", "limits": "한계", "calendar": "법정 달력", "keys": "연동 상태"}
SECTION = {"verdict": "#verdictText", "metrics": "#metricsBlock", "series": "#chartBlock", "severity": "#severityBlock", "scenes": "#scenesBlock", "events": "#eventsBlock", "equity": "#equityBlock", "limits": "#limitsBlock"}


def plan_tools(question: str, context: dict) -> list[str]:
    q = question.lower()
    plan = [t for t, kws in TOOLS.items() if any(k in q for k in kws)]
    if context.get("panel_context"):
        plan = ["verdict", "metrics", "limits"] + [t for t in plan if t not in ("verdict", "metrics", "limits")]
    if not plan:
        plan = ["verdict", "metrics", "limits"]
    return plan[:5]


def infer_intent(question: str, plan: list[str]) -> str:
    q = question.lower()
    if any(k in q for k in ["보고서", "문장", "첨부", "써줘", "정리"]):
        return "report_sentence"
    if "scenes" in plan:
        return "reproducibility"
    if "equity" in plan:
        return "equity_audit"
    if "calendar" in plan:
        return "deadline"
    return "verdict_brief"


def run_tools(plan: list[str], card: dict, calendar: list[dict], keys: dict) -> tuple[list[dict], list[dict]]:
    mod = card["modules"][0] if card.get("modules") else {}
    evidence, trace = [], []
    for tool in plan:
        status, detail = "ok", ""
        if tool == "verdict":
            v = mod.get("verdict") or {}
            if v.get("text"):
                evidence.append({"kind": "판정", "title": mod.get("label", ""), "summary": v["text"], "code": v.get("code"), "date": mod.get("computed_at")})
            else:
                status, detail = "miss", "판정 없음(미실행)"
        elif tool == "metrics":
            rows = mod.get("metrics") or []
            if rows:
                for r in rows[:6]:
                    evidence.append({"kind": "지표", "title": r["key"], "summary": f"{r['display']} ({r['badge_label']}{', n=' + format(r['n'], ',') if r.get('n') else ''})", "note": r.get("note", ""), "measured": r.get("measured")})
            else:
                status, detail = "miss", "지표 없음"
        elif tool == "series":
            s = mod.get("series") or []
            if s:
                evidence.append({"kind": "회복", "title": "피해지/대조지 NDVI 회복률", "summary": " → ".join(f"{x['label']} {x['recovery_ratio']:.2f}" if x.get("recovery_ratio") is not None else f"{x['label']} 측정 불가" for x in s)})
            else:
                status, detail = "miss", "시계열 없음"
        elif tool == "severity":
            sv = mod.get("severity") or []
            if sv:
                evidence.append({"kind": "피해등급", "title": "dNBR 등급별 면적", "summary": ", ".join(f"{x['label']} {x['ha']:,} ha" for x in sv)})
            else:
                status, detail = "miss", "등급 없음"
        elif tool == "scenes":
            sc = mod.get("scenes") or []
            if sc:
                used = [x for x in sc if x.get("date")]
                evidence.append({"kind": "재현", "title": f"장면 {len(used)}건" + (f", 실패 {len(mod.get('failed') or [])}건" if mod.get("failed") else ""),
                                 "summary": "; ".join(f"{x.get('label') or x.get('year')} {x['date']} 구름 {x.get('cloud_cover', 0):.1f}% 유효 {x.get('valid_pct', '')}%" for x in used[:6]),
                                 "design": mod.get("design", {})})
            else:
                status, detail = "miss", "장면 없음"
        elif tool == "events":
            ev = mod.get("events") or []
            if ev:
                evidence.append({"kind": "호우", "title": "관측가능성 등급", "summary": "; ".join(f"{e['name']} {e['grade']}" + (f"({e['first_pass_hours']}h)" if e.get("first_pass_hours") is not None else "(미관측)") for e in ev)})
            else:
                status, detail = "miss", "사건 없음"
        elif tool == "equity":
            eq = card.get("equity")
            if eq and eq.get("status") == "ok":
                evidence.append({"kind": "형평성", "title": "수혜 대상 취약도", "summary": json.dumps(eq["data"].get("metrics"), ensure_ascii=False)[:300]})
            else:
                status, detail = "miss", " / ".join((eq or {}).get("warnings") or ["미실행"])
                evidence.append({"kind": "형평성", "title": "키 필요·입력 대기", "summary": detail})
        elif tool == "limits":
            lim = mod.get("limitations") or []
            if lim:
                evidence.append({"kind": "한계", "title": f"한계 {len(lim)}건", "summary": " / ".join(lim[:3])})
            else:
                status, detail = "miss", "한계 기재 없음"
        elif tool == "calendar":
            nxt = sorted(calendar, key=lambda x: x["days_left"])[0] if calendar else None
            if nxt:
                evidence.append({"kind": "기한", "title": nxt["name"], "summary": f"{nxt['due']} (D-{nxt['days_left']}) · {nxt['basis']} · 납품물 {nxt['deliverable']}"})
            else:
                status, detail = "miss", "달력 없음"
        elif tool == "keys":
            missing = [k for k, v in keys.items() if not v]
            evidence.append({"kind": "연동", "title": f"키 {sum(keys.values())}/{len(keys)} 설정", "summary": "비어 있음: " + (", ".join(missing) if missing else "없음")})
        trace.append({"tool": tool, "label": LABEL.get(tool, tool), "status": status, "detail": detail})
    return evidence, trace


def local_answer(card: dict, evidence: list[dict], intent: str) -> str:
    mod = card["modules"][0] if card.get("modules") else {}
    p = card.get("project", {})
    parts = []
    ver = next((e for e in evidence if e["kind"] == "판정"), None)
    if ver:
        parts.append(f"{p.get('name', '')}의 판정은 '{ver['summary']}'")
    else:
        parts.append(f"{p.get('name', '')}은 아직 검증이 실행되지 않았거나 판정을 내릴 표본이 없습니다.")
    met = [e for e in evidence if e["kind"] == "지표"][:3]
    if met:
        parts.append("근거 수치: " + "; ".join(f"{e['title']} {e['summary']}" for e in met) + ".")
    for k in ("회복", "피해등급", "호우", "재현", "기한", "연동", "형평성"):
        e = next((x for x in evidence if x["kind"] == k), None)
        if e:
            parts.append(f"{k}: {e['summary']}.")
    lim = next((x for x in evidence if x["kind"] == "한계"), None)
    if lim:
        parts.append("한계: " + lim["summary"] + ".")
    if intent == "report_sentence" and ver:
        parts.append(f"보고서 문장 예시 — \"위성 관측(Sentinel-2) 기반 사후 검증 결과 {ver['summary']}\"")
    if not config.KEYS["GEMINI_API_KEY"]:
        parts.append("설명 모델 키(GEMINI_API_KEY)가 없어 카드 수치를 그대로 요약했습니다.")
    return "\n".join(parts)


def build_handoff(intent: str, trace: list[dict], card: dict, plan: list[str]) -> dict:
    mod = card["modules"][0] if card.get("modules") else {}
    code = (mod.get("verdict") or {}).get("code", "not_run")
    sugg = {
        "verdict_brief": ["이 결과를 이행점검 보고서 문장으로 정리해줘", "검출가능최소효과와 한계를 설명해줘", "어떤 장면으로 계산했는지 재현 정보를 보여줘"],
        "reproducibility": ["구름이 많았던 장면이 있었나요?", "동일 궤도를 쓴 이유를 설명해줘", "이 결과를 보고서 문장으로 정리해줘"],
        "equity_audit": ["형평성 감사에 어떤 키가 필요한가요?", "수혜 건물 목록은 어떤 형식으로 넣나요?", "판정 요약을 다시 보여줘"],
        "deadline": ["이행점검 보고서에 무엇을 첨부하나요?", "판정 요약을 보고서 문장으로 정리해줘", "다음 관측 시기는 언제인가요?"],
        "report_sentence": ["한계를 각주 형태로 정리해줘", "피해등급별 면적을 표로 설명해줘", "회복률 추세를 한 문장으로 요약해줘"],
    }.get(intent, [])
    if code in ("not_run", "waiting_input"):
        sugg = ["검증을 실행하려면 무엇이 필요한가요?", "다른 사업의 판정을 보여줘"] + sugg[:1]
    next_sec = next((SECTION[t] for t in plan if t in SECTION), "#verdictText")
    return {"intent": intent, "steps": [{"label": t["label"], "status": t["status"]} for t in trace], "suggested_questions": sugg[:3],
            "next": {"label": LABEL.get(plan[0], "카드"), "section": next_sec}}


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def handle_chat(payload: dict, card: dict, calendar: list[dict], keys: dict) -> dict:
    message = str(payload.get("message", "")).strip()
    context = payload.get("context") or {}
    history = payload.get("history") or []
    plan = plan_tools(message, context)
    intent = infer_intent(message, plan)
    evidence, trace = run_tools(plan, card, calendar, keys)
    actions = [{"label": LABEL[t], "section": SECTION[t]} for t in plan if t in SECTION][:3]
    handoff = build_handoff(intent, trace, card, plan)
    fallback = local_answer(card, evidence, intent)
    base = {"evidence": evidence[:6], "tool_trace": trace, "handoff": handoff, "actions": actions}
    key = config.KEYS["GEMINI_API_KEY"]
    if not key:
        return {**base, "answer": fallback, "model": None, "source": "local", "warnings": ["GEMINI_API_KEY 없음 — 로컬 요약"]}
    try:
        from google import genai
        client = genai.Client(api_key=key)
        prompt = (f"{SYSTEM_PROMPT}\n\n[화면 컨텍스트]\n{json.dumps(context, ensure_ascii=False)[:3000]}\n\n[evidence]\n{json.dumps(evidence, ensure_ascii=False)[:12000]}\n\n"
                  f"[대화]\n{json.dumps(history[-6:], ensure_ascii=False)[:3000]}\n\n[질문]\n{message}")
        resp = client.models.generate_content(model=config.KEYS["GEMINI_MODEL"], contents=prompt)
        text = (resp.text or "").strip()
        # 허용 수치: 근거·로컬 요약·질문·화면 컨텍스트에 있는 수치, 1~31(날짜·순번), 연도·기본 상수
        allowed = (_numbers(json.dumps(evidence, ensure_ascii=False)) | _numbers(fallback) | _numbers(message) | _numbers(json.dumps(context, ensure_ascii=False))
                   | {str(i) for i in range(0, 32)} | {"95", "100", "2024", "2025", "2026", "2027", "30", "48", "120"})
        bad = [n for n in _numbers(text) if n not in allowed and n.replace(",", "") not in allowed]
        if not text or bad:
            return {**base, "answer": fallback, "model": config.KEYS["GEMINI_MODEL"], "source": "local", "warnings": [f"모델 응답에 카드에 없는 수치({', '.join(bad[:3])})가 있어 로컬 요약으로 교체"]}
        return {**base, "answer": text, "model": config.KEYS["GEMINI_MODEL"], "source": "gemini", "warnings": []}
    except Exception as e:
        return {**base, "answer": fallback, "model": None, "source": "local", "warnings": [f"모델 호출 실패({type(e).__name__}) — 로컬 요약"]}
