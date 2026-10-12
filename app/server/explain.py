"""설명 계층 — 카드에 있는 숫자만 인용한다. 모델은 계산하지 않는다.

GEMINI_API_KEY가 없으면 템플릿 문장으로 폴백(status degraded). 키가 있어도 숫자 생성은 금지하고,
응답에 카드에 없는 숫자가 포함되면 템플릿으로 교체한다(환각 차단).
"""
from __future__ import annotations

import re

from . import config
from .envelope import degraded, ok
from .report import fmt

SYSTEM = ("당신은 기후적응 사업 성과 카드를 담당 공무원에게 설명하는 보조자다. 반드시 제공된 카드 JSON에 있는 수치만 인용하고, "
          "카드에 없는 수치·날짜·비율은 절대 만들지 않는다. '측정 불가'와 '미검출'의 뜻을 과장 없이 전달한다. 한국어, 4문장 이내, 존댓말.")


def template_answer(card: dict, question: str) -> str:
    lines = []
    for m in card["modules"]:
        v = m["verdict"]
        lines.append(f"[{m['label']}] 판정: {v.get('text','')}")
        for r in m["metrics"][:3]:
            lines.append(f" - {r['key']}: {r['display']} ({r['badge_label']}{', n=' + str(r['n']) if r.get('n') else ''})")
    if card.get("equity") and card["equity"]["status"] != "ok":
        lines.append("[형평성 감사] " + " / ".join(card["equity"]["warnings"]))
    lines.append("질문에 대한 추가 해석은 설명 모델 키(GEMINI_API_KEY)가 설정되면 제공됩니다. 위 수치는 카드에서 그대로 인용한 값입니다.")
    return "\n".join(lines)


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def answer(card: dict, question: str, history: list[dict] | None = None) -> dict:
    key = config.KEYS["GEMINI_API_KEY"]
    fallback = template_answer(card, question)
    if not key:
        return degraded({"answer": fallback, "source": "template"}, ["GEMINI_API_KEY 없음 — 템플릿 설명으로 대체"])
    try:
        from google import genai
        client = genai.Client(api_key=key)
        import json
        prompt = f"{SYSTEM}\n\n[카드 JSON]\n{json.dumps(card, ensure_ascii=False)[:20000]}\n\n[질문]\n{question}"
        resp = client.models.generate_content(model=config.KEYS["GEMINI_MODEL"], contents=prompt)
        text = (resp.text or "").strip()
        allowed = _numbers(json.dumps(card, ensure_ascii=False)) | _numbers(fallback)
        bad = [n for n in _numbers(text) if n not in allowed and n not in {"1", "2", "3", "4", "95"}]
        if not text or bad:
            return degraded({"answer": fallback, "source": "template", "rejected": text[:400], "unknown_numbers": bad}, ["모델 응답에 카드에 없는 수치가 있어 템플릿으로 교체"])
        return ok({"answer": text, "source": config.KEYS["GEMINI_MODEL"]})
    except Exception as e:
        return degraded({"answer": fallback, "source": "template"}, [f"설명 모델 호출 실패({type(e).__name__}) — 템플릿으로 대체"])
