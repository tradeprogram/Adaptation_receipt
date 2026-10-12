"""기상청 API허브 — 지상관측 시간자료(기간 조회) kma_sfctm3.

실측(2026-10-12): 공백 구분 텍스트, '#' 주석 줄, 결측 -9/-99. 열 순서(앞 19개는 수치라 split 안전):
TM STN WD WS GST_WD GST_WS GST_TM PA PS PT PR TA TD HM PV RN RN_DAY RN_JUN RN_INT …(WW 문자열은 25번째)
RN은 4~10월 1시간 강수량(mm), RN_DAY는 당일 누적(mm). 시각은 KST.
간헐 504 → 재시도 3회.
"""
from __future__ import annotations

import datetime as dt
import time

import requests

from . import config

URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
UA = {"User-Agent": config.USER_AGENT}
KST = dt.timezone(dt.timedelta(hours=9))


def fetch_hourly(stn: str, tm1: str, tm2: str) -> list[dict] | None:
    """지점·기간(YYYYMMDDHHMM, KST)의 시간자료. 키가 없거나 3회 실패하면 None(0이 아니라 '못 가져옴')."""
    key = config.KEYS["KMA_APIHUB_KEY"]
    if not key:
        return None
    for attempt in range(3):
        try:
            r = requests.get(URL, params={"tm1": tm1, "tm2": tm2, "stn": stn, "help": "0", "authKey": key}, headers=UA, timeout=90)
            if r.status_code == 200 and "#START7777" in r.text:
                break
        except requests.RequestException:
            pass
        time.sleep(2 + 2 * attempt)
    else:
        return None
    out = []
    for line in r.text.splitlines():
        if not line or line.startswith("#"):
            continue
        t = line.split()
        if len(t) < 19:
            continue
        v = lambda s: (None if float(s) <= -9 else float(s))
        try:
            out.append({"tm": dt.datetime.strptime(t[0], "%Y%m%d%H%M").replace(tzinfo=KST), "stn": t[1], "ta": v(t[11]), "hm": v(t[13]), "rn": v(t[15]), "rn_day": v(t[16]), "ws": v(t[3])})
        except ValueError:
            continue
    return out


def fetch_season(stn: str, year: int, m1: int = 6, m2: int = 9) -> list[dict] | None:
    """여름철(기본 6~9월)을 월 단위로 나눠 받는다(한 번에 너무 길면 504)."""
    rows: list[dict] = []
    for m in range(m1, m2 + 1):
        last = (dt.date(year + (m // 12), (m % 12) + 1, 1) - dt.timedelta(days=1)).day
        part = fetch_hourly(stn, f"{year}{m:02d}010000", f"{year}{m:02d}{last:02d}2300")
        if part is None:
            return None
        rows.extend(part)
    return rows


def rain_events(rows: list[dict], min_3h_mm: float = 60.0, min_1h_mm: float = 30.0, gap_hours: int = 24) -> list[dict]:
    """시간 강우에서 호우 사건을 뽑는다: 3시간 합 ≥ min_3h 또는 1시간 ≥ min_1h인 시각들을 24시간 간격으로 묶고,
    사건의 정점은 1시간 강우 최대 시각. 결측은 0으로 메우지 않고 건너뛴다(측정 불가)."""
    seq = [(r["tm"], r["rn"]) for r in rows if r["rn"] is not None]
    seq.sort()
    hits = []
    for i, (t, rn) in enumerate(seq):
        s3 = sum(x[1] for x in seq[max(0, i - 2):i + 1])
        if s3 >= min_3h_mm or rn >= min_1h_mm:
            hits.append((t, rn, s3))
    events = []
    for t, rn, s3 in hits:
        if events and (t - events[-1]["end"]).total_seconds() <= gap_hours * 3600:
            ev = events[-1]; ev["end"] = t; ev["hours"] += 1
            if rn > ev["peak_rn"]:
                ev["peak"], ev["peak_rn"] = t, rn
            ev["max_3h"] = max(ev["max_3h"], s3)
        else:
            events.append({"start": t, "end": t, "peak": t, "peak_rn": rn, "max_3h": s3, "hours": 1})
    for ev in events:
        total = sum(rn for (t, rn) in seq if ev["start"] - dt.timedelta(hours=6) <= t <= ev["end"] + dt.timedelta(hours=6))
        ev["total_mm"] = round(total, 1)
        ev["peak_utc"] = ev["peak"].astimezone(dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="minutes")
        ev["peak_kst"] = ev["peak"].isoformat(timespec="minutes")
        for k in ("start", "end", "peak"):
            ev[k] = ev[k].isoformat(timespec="minutes")
    return events
