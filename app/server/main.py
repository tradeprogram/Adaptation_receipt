"""적응 영수증 API + 정적 대시보드.

실행: cd C:\\for_huss && python -m uvicorn app.server.main:app --port 8008 --reload
"""
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, equity, explain, jobs, report
from .envelope import ok

app = FastAPI(title="적응 영수증 API", version="0.1.0")


# ---------- 사업 대장 ----------
def load_projects() -> dict[str, dict]:
    out = {}
    for p in sorted(config.PROJECTS_DIR.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[d["id"]] = d
    return out


def get_project(pid: str) -> dict:
    prj = load_projects().get(pid)
    if not prj:
        raise HTTPException(404, f"project {pid} not found")
    return prj


@app.get("/api/health")
def health():
    return ok({"time": dt.datetime.now().isoformat(timespec="seconds"), "keys": config.key_status(), "mock": config.MOCK})


@app.get("/api/projects")
def list_projects():
    items = []
    for prj in load_projects().values():
        res = {m: jobs.load_result(prj["id"], m) for m in prj.get("modules", [prj["type"]])}
        items.append({**{k: prj.get(k) for k in ("id", "name", "type", "agency", "region", "budget_krw", "period", "event_date", "modules")},
                      "bbox": prj["geometry"]["bbox"],
                      "results": {m: ({"status": r.get("status"), "verdict": r.get("verdict", {}).get("code"), "computed_at": r.get("computed_at")} if r else None) for m, r in res.items()}})
    return ok(items)


@app.get("/api/projects/{pid}")
def project_detail(pid: str):
    prj = get_project(pid)
    return ok({"project": prj, "results": {m: jobs.load_result(pid, m) for m in prj.get("modules", [prj["type"]])}, "jobs": jobs.list_jobs(pid)[:5]})


class ProjectIn(BaseModel):
    project: dict


@app.post("/api/projects")
def create_project(body: ProjectIn):
    prj = body.project
    for k in ("id", "name", "type", "geometry"):
        if k not in prj:
            raise HTTPException(400, f"missing field {k}")
    if not Path(prj["id"]).name == prj["id"] or "/" in prj["id"] or "\\" in prj["id"] or ".." in prj["id"]:
        raise HTTPException(400, "invalid id")
    path = config.PROJECTS_DIR / f"{prj['id']}.json"
    if path.exists():
        raise HTTPException(409, "exists")
    path.write_text(json.dumps(prj, ensure_ascii=False, indent=1), encoding="utf-8")
    return ok(prj)


# ---------- 검증 잡 ----------
@app.post("/api/projects/{pid}/verify/{module}")
def verify(pid: str, module: str):
    prj = get_project(pid)
    if module not in jobs.MODULES:
        raise HTTPException(400, f"unknown module {module}")
    if config.READ_ONLY:
        return JSONResponse(status_code=503, content={"status": "degraded", "fallback_tier": 3, "data": None,
                            "warnings": ["배포본은 읽기 전용이다. 위성 재검정은 로컬 서버(uvicorn)에서 실행하고 결과(app/cache/results)를 커밋해 배포한다."], "provenance": {}})
    running = [j for j in jobs.list_jobs(pid) if j["module"] == module and j["status"] in ("queued", "running")]
    if running:
        return ok(running[0], ["이미 실행 중인 작업이 있어 새로 시작하지 않았다"])
    return ok(jobs.start(prj, module))


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    j = jobs.load(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    return ok(j)


@app.get("/api/jobs")
def job_list(project_id: str | None = None):
    return ok(jobs.list_jobs(project_id))


# ---------- 카드·형평성·설명 ----------
_equity_cache: dict[str, tuple[float, dict]] = {}
EQUITY_TTL = 600  # 초 — 건축물대장·SGIS 실호출은 수 초~수십 초라 카드마다 다시 부르지 않는다


def _equity_cached(prj: dict) -> dict:
    import time
    now = time.time(); hit = _equity_cache.get(prj["id"])
    if hit and now - hit[0] < EQUITY_TTL:
        return hit[1]
    res = equity.run(prj)
    if res.get("status") == "ok" or not prj.get("beneficiaries"):
        _equity_cache[prj["id"]] = (now, res)       # 실패(degraded with failed)는 캐시하지 않고 다음 요청에서 재시도
    return res


def _card(pid: str) -> dict:
    prj = get_project(pid)
    results = {m: jobs.load_result(pid, m) for m in prj.get("modules", [prj["type"]])}
    return report.build_card(prj, results, _equity_cached(prj))


@app.get("/api/projects/{pid}/card")
def card_json(pid: str):
    return ok(_card(pid))


@app.get("/card/{pid}", response_class=HTMLResponse)
def card_html(pid: str):
    return report.render_html(_card(pid))


@app.get("/api/equity/{pid}")
def equity_api(pid: str):
    return _equity_cached(get_project(pid))


class Ask(BaseModel):
    question: str
    history: list[dict] = []


@app.post("/api/projects/{pid}/explain")
def explain_api(pid: str, body: Ask):
    return explain.answer(_card(pid), body.question, body.history)


class ChatIn(BaseModel):
    message: str
    project_id: str | None = None
    context: dict = {}
    history: list[dict] = []


@app.post("/api/chat")
def chat_api(body: ChatIn):
    """적응영수증.chat — 화면 컨텍스트 + 카드 도구 결과 + (키가 있으면) Gemini."""
    from . import chat
    pid = body.project_id or (body.context or {}).get("project_id")
    card = _card(pid) if pid else {"project": {}, "modules": [], "equity": None}
    return ok(chat.handle_chat(body.model_dump(), card, calendar()["data"], config.key_status()))


@app.get("/api/projects/{pid}/overlay/{name}")
def overlay(pid: str, name: str):
    import re
    if not re.fullmatch(r"[a-z_]+\.png", name):          # dnbr/pre/post, lst_before/after/diff, flood_before/after/change
        raise HTTPException(404)
    p = config.RESULTS_DIR / pid / name
    if not p.exists():
        raise HTTPException(404, "overlay not computed")
    return FileResponse(p, media_type="image/png", headers={"Cache-Control": "no-store"})


# ---------- 법정 달력 ----------
@app.get("/api/calendar")
def calendar():
    y = dt.date.today().year
    nxt = y if dt.date.today() <= dt.date(y, 4, 30) else y + 1
    items = [
        {"name": "지자체 적응대책 이행점검 결과보고서 제출", "due": f"{nxt}-04-30", "basis": "탄소중립기본법 §40, 시행령 §43", "deliverable": "성과 카드 부록"},
        {"name": "공공기관 적응대책 이행실적 제출(상반기)", "due": f"{nxt}-06-30", "basis": "탄소중립기본법 §41, 2026-01 지침", "deliverable": "사업장별 정량 카드"},
        {"name": "여름철 자연재난 대책 확정", "due": f"{nxt}-05-15", "basis": "재난안전법(폭염 2018~ 자연재난)", "deliverable": "전년 사업 효과 요약"},
        {"name": "위성 관측 축적(생장기·강우기·폭염기)", "due": f"{nxt}-10-31", "basis": "Sentinel-2/1, Landsat", "deliverable": "장면 캐시"},
    ]
    for it in items:
        it["days_left"] = (dt.date.fromisoformat(it["due"]) - dt.date.today()).days
    return ok(items)


# ---------- 정적 프런트 ----------
app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
