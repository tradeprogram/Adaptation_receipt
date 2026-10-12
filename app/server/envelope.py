"""공통 응답 봉투.

{status: ok|degraded|error|partial, fallback_tier: 1|2|3, data, warnings[], provenance{}}
한 모듈이 실패해도 파이프라인은 멈추지 않고 status/warnings로 표현한다.
배지: OBSERVED(실측) · MODEL(자체 계산) · RULE(규칙 판정) · ASSUMPTION(가정) · FORECAST(외부 예보)
"""
from __future__ import annotations

from typing import Any

BADGES = ("OBSERVED", "MODEL", "RULE", "ASSUMPTION", "FORECAST")


def ok(data: Any, warnings: list[str] | None = None, tier: int = 1, provenance: dict | None = None) -> dict:
    return {"status": "ok" if not warnings else "degraded", "fallback_tier": tier, "data": data,
            "warnings": warnings or [], "provenance": provenance or {}}


def degraded(data: Any, warnings: list[str], tier: int = 2, provenance: dict | None = None) -> dict:
    return {"status": "degraded", "fallback_tier": tier, "data": data, "warnings": warnings, "provenance": provenance or {}}


def error(message: str, tier: int = 3) -> dict:
    return {"status": "error", "fallback_tier": tier, "data": None, "warnings": [message], "provenance": {}}


def metric(value, badge: str, unit: str = "", n: int | None = None, note: str = "") -> dict:
    """값 하나에 출처 배지를 묶는다. value=None은 '측정 불가'이며 0이 아니다."""
    assert badge in BADGES, badge
    return {"value": value, "badge": badge, "unit": unit, "n": n, "measured": value is not None, "note": note}
