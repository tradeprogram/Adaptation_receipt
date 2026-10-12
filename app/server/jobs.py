"""백그라운드 검증 잡. 상태는 JSON으로 원자적 저장되고, 결과는 results/{project}/{module}.json에 남는다.

상태: queued → running → done | partial | failed | waiting_input | unmeasured
진행률: progress{done,total,message}. 실패 장면·사건은 결과 안의 failed[]로 이름이 남는다(조용히 건너뛰지 않는다).
"""
from __future__ import annotations

import datetime as dt
import threading
import traceback
import uuid

from . import config
from .fsutil import save_json_atomic

MODULES = ("fire", "heat", "flood")   # 검증 모듈은 실행 시점에 import(배포본은 rasterio 없이 읽기 전용으로 뜬다)


def _runner(module: str):
    import importlib
    return importlib.import_module(f".verify_{module}", __package__).run
_lock = threading.Lock()


def _job_path(job_id: str):
    return config.JOBS_DIR / f"{job_id}.json"


def _save(job: dict) -> None:
    save_json_atomic(_job_path(job["id"]), job)


def load(job_id: str) -> dict | None:
    p = _job_path(job_id)
    if not p.exists():
        return None
    import json
    return json.loads(p.read_text(encoding="utf-8"))


def result_path(project_id: str, module: str):
    d = config.RESULTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{module}.json"


def load_result(project_id: str, module: str) -> dict | None:
    p = result_path(project_id, module)
    if not p.exists():
        return None
    import json
    return json.loads(p.read_text(encoding="utf-8"))


def list_jobs(project_id: str | None = None) -> list[dict]:
    import json
    out = []
    for p in sorted(config.JOBS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if project_id is None or j.get("project_id") == project_id:
            out.append(j)
    return out[:50]


def start(project: dict, module: str) -> dict:
    if module not in MODULES:
        raise ValueError(f"unknown module {module}")
    job = {"id": uuid.uuid4().hex[:12], "project_id": project["id"], "module": module, "status": "queued",
           "created_at": dt.datetime.now().isoformat(timespec="seconds"), "progress": {"done": 0, "total": 0, "message": "대기"}, "error": None}
    _save(job)
    t = threading.Thread(target=_run, args=(job, project, module), daemon=True)
    t.start()
    return job


def _run(job: dict, project: dict, module: str) -> None:
    def progress(done, total, msg):
        with _lock:
            job["progress"] = {"done": int(done), "total": int(total), "message": str(msg)}
            job["status"] = "running"
            _save(job)
    try:
        result = _runner(module)(project, progress)
        save_json_atomic(result_path(project["id"], module), result)
        with _lock:
            job["status"] = {"ok": "done"}.get(result.get("status"), result.get("status", "done"))
            job["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
            job["summary"] = {"failed": len(result.get("failed", [])), "verdict": result.get("verdict", {}).get("code")}
            _save(job)
    except Exception as e:
        with _lock:
            job["status"] = "failed"; job["error"] = f"{type(e).__name__}: {e}"; job["trace"] = traceback.format_exc()[-2000:]
            job["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
            _save(job)
