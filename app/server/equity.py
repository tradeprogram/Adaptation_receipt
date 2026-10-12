"""형평성 감사 — 수혜 건물·필지의 취약 속성 분포 vs 관할 전체.

입력: project.beneficiaries[] = {name, sigunguCd, bjdongCd, platGbCd, bun, ji} 또는 {name, bd_mgt_sn}
외부(실측 2026-10-12):
- 건축물대장 표제부 getBrTitleInfo: response.body.items.item[] (dict 또는 list), 필드 useAprDay(YYYYMMDD), roofCdNm, strctCdNm, mainPurpsCdNm, grndFlrCnt, hhldCnt, dongNm
- SGIS: auth → accessToken; addr/stage.json?cd= 로 행정구역 코드(강서구 11160 등 SGIS 자체 코드); stats/population.json(adm_cd, low_search=0) → oldage_suprt_per(노년부양비), aged_child_idx(노령화지수), avg_age, tot_ppltn; stats/household.json → household_cnt, avg_family_member_cnt
키가 없으면 degraded 상태를 돌려주고 가상값으로 채우지 않는다.
"""
from __future__ import annotations

import datetime as dt

import requests

from . import config
from .envelope import degraded, metric, ok
from .vworld import parse_bd_mgt_sn

BLD_URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
SGIS = "https://sgisapi.kostat.go.kr/OpenAPI3"
OLD_YEARS = 30
UA = {"User-Agent": config.USER_AGENT}


def fetch_title(b: dict, key: str) -> list[dict] | None:
    q = parse_bd_mgt_sn(b["bd_mgt_sn"]) if b.get("bd_mgt_sn") else {k: b.get(k) for k in ("sigunguCd", "bjdongCd", "platGbCd", "bun", "ji")}
    params = {"serviceKey": key, "sigunguCd": q["sigunguCd"], "bjdongCd": q["bjdongCd"], "platGbCd": q.get("platGbCd") or "0",
              "bun": str(q["bun"]).zfill(4), "ji": str(q.get("ji") or 0).zfill(4), "_type": "json", "numOfRows": 10}
    # 실측: totalCount가 16이어도 한 페이지에 10건 이하만 온다 → pageNo로 끝까지 읽는다(최대 10쪽, 호출 간 0.4초)
    out: list[dict] = []
    import time
    for page in range(1, 11):
        body = None
        for attempt in range(3):   # 실측: 간헐 SERVICETIMEOUT_ERROR(비JSON 본문) → 짧게 쉬고 재시도
            r = requests.get(BLD_URL, params={**params, "pageNo": page}, timeout=config.HTTP_TIMEOUT, headers=UA)
            try:
                body = r.json()["response"]["body"] if r.status_code == 200 else None
            except (ValueError, KeyError):
                body = None
            if body is not None:
                break
            time.sleep(1.0 + attempt)
        if body is None:
            return None if not out else out
        items = body.get("items") or {}
        it = items.get("item") if isinstance(items, dict) else None
        it = it if isinstance(it, list) else ([it] if it else [])
        out.extend(it)
        total = int(body.get("totalCount") or 0)
        if not it or len(out) >= total:
            break
        import time; time.sleep(0.4)
    return out


def sgis_token() -> str | None:
    k, s = config.KEYS["SGIS_CONSUMER_KEY"], config.KEYS["SGIS_CONSUMER_SECRET"]
    if not (k and s):
        return None
    try:
        return requests.get(f"{SGIS}/auth/authentication.json", params={"consumer_key": k, "consumer_secret": s}, timeout=config.HTTP_TIMEOUT).json()["result"]["accessToken"]
    except (ValueError, KeyError):
        return None


def sgis_find_code(token: str, sido_name: str, sigungu_name: str) -> str | None:
    """시도명·시군구명으로 SGIS 행정구역 코드를 찾는다(예: 서울특별시 강서구 → 11160)."""
    try:
        sidos = requests.get(f"{SGIS}/addr/stage.json", params={"accessToken": token}, timeout=30).json().get("result", [])
        sido = next((x for x in sidos if sido_name[:2] in x["addr_name"]), None)
        if not sido:
            return None
        guns = requests.get(f"{SGIS}/addr/stage.json", params={"accessToken": token, "cd": sido["cd"]}, timeout=30).json().get("result", [])
        g = next((x for x in guns if x["addr_name"].startswith(sigungu_name[:2])), None)
        return g["cd"] if g else None
    except (ValueError, KeyError):
        return None


def sgis_reference(token: str, adm_cd: str, year: str = "2023") -> dict | None:
    try:
        pop = requests.get(f"{SGIS}/stats/population.json", params={"accessToken": token, "year": year, "adm_cd": adm_cd, "low_search": "0"}, timeout=30).json().get("result", [None])[0]
        hh = requests.get(f"{SGIS}/stats/household.json", params={"accessToken": token, "year": year, "adm_cd": adm_cd, "low_search": "0"}, timeout=30).json().get("result", [None])[0]
    except (ValueError, IndexError, AttributeError):
        return None
    if not pop:
        return None
    return {"adm_cd": adm_cd, "adm_nm": pop.get("adm_nm"), "year": year, "tot_ppltn": pop.get("tot_ppltn"), "oldage_suprt_per": pop.get("oldage_suprt_per"),
            "aged_child_idx": pop.get("aged_child_idx"), "avg_age": pop.get("avg_age"), "household_cnt": (hh or {}).get("household_cnt"), "avg_family_member_cnt": (hh or {}).get("avg_family_member_cnt")}


def run(project: dict) -> dict:
    bens = project.get("beneficiaries", [])
    key = config.KEYS["DATA_GO_KR_SERVICE_KEY"]
    warnings = []
    if not bens:
        warnings.append("수혜 건물·필지 목록(beneficiaries)이 없다. 사업 집행 대장에서 주소를 받아 입력한다.")
    if not key:
        warnings.append("DATA_GO_KR_SERVICE_KEY 필요 — 건축물대장 표제부(노후도·구조) 조회 불가")
    if not (config.KEYS["SGIS_CONSUMER_KEY"] and config.KEYS["SGIS_CONSUMER_SECRET"]):
        warnings.append("SGIS_CONSUMER_KEY/SECRET 필요 — 관할 고령·1인가구 기준 분포 조회 불가")
    design = {"indicators": ["노후건물(사용승인 30년 초과) 비율", "수혜 지역 노년부양비·노령화지수 vs 관할", "집중지수"], "unit": "건물·필지·격자(개인 식별 없음)"}
    if not bens or not key:
        return degraded({"module": "equity", "project_id": project["id"], "beneficiaries_n": len(bens), "metrics": {}, "design": design}, warnings)

    rows, failed = [], []
    for b in bens:
        items = fetch_title(b, key)
        if items is None:
            failed.append(b.get("name", str(b))); continue
        want = b.get("dong")
        for t in items:
            if want and (t.get("dongNm") or "").strip() != want:
                continue
            yr = str(t.get("useAprDay", ""))[:4]
            age = (dt.date.today().year - int(yr)) if yr.isdigit() else None
            rows.append({"name": b.get("name") or t.get("bldNm"), "dong": t.get("dongNm"), "use_approved": yr or None, "age_years": age, "roof": t.get("roofCdNm"),
                         "structure": t.get("strctCdNm"), "purpose": t.get("mainPurpsCdNm"), "floors": t.get("grndFlrCnt"), "households": t.get("hhldCnt")})
    aged = [r["age_years"] for r in rows if r["age_years"] is not None]
    old_share = (sum(1 for a in aged if a > OLD_YEARS) / len(aged)) if aged else None
    ref = None
    tok = sgis_token()
    if tok:
        adm = project.get("adm_cd") or (sgis_find_code(tok, project.get("sido", ""), project.get("sigungu", "")) if project.get("sigungu") else None)
        if adm:
            ref = sgis_reference(tok, adm)
    data = {"module": "equity", "project_id": project["id"], "beneficiaries_n": len(bens), "rows": rows, "failed": failed, "design": design,
            "metrics": {"old_building_share": metric(old_share, "OBSERVED", "비율", n=len(aged), note=f"사용승인 {OLD_YEARS}년 초과 건물 비율(건축물대장 표제부)"),
                        "median_building_age": metric((sorted(aged)[len(aged) // 2] if aged else None), "OBSERVED", "년", n=len(aged)),
                        "households_total": metric((sum(r["households"] or 0 for r in rows) or None), "OBSERVED", "세대", n=len(rows)),
                        "jurisdiction_oldage_support": metric((float(ref["oldage_suprt_per"]) if ref and ref.get("oldage_suprt_per") not in (None, "N/A") else None), "OBSERVED", "%", note=f"SGIS {ref['adm_nm']} {ref['year']} 노년부양비" if ref else "SGIS 관할 코드 미확인"),
                        "jurisdiction_aging_index": metric((float(ref["aged_child_idx"]) if ref and ref.get("aged_child_idx") not in (None, "N/A") else None), "OBSERVED", "", note="노령화지수(65세 이상/0~14세×100)" if ref else "")},
            "reference": ref}
    if failed:
        warnings.append(f"조회 실패 {len(failed)}건: {failed}")
    return ok(data, warnings)
