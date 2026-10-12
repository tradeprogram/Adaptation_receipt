import os
from pathlib import Path

os.environ.setdefault("AR_CACHE_DIR", str(Path(__file__).resolve().parents[1] / "cache_test"))

from fastapi.testclient import TestClient  # noqa: E402

from app.server.main import app  # noqa: E402
from app.server import verify_flood, verify_heat  # noqa: E402
import numpy as np  # noqa: E402

client = TestClient(app)


def test_health_lists_key_slots_without_values():
    r = client.get("/api/health"); assert r.status_code == 200
    body = r.json(); assert body["status"] in ("ok", "degraded")
    assert set(body["data"]["keys"]) >= {"GEMINI_API_KEY", "DATA_GO_KR_SERVICE_KEY", "SGIS_CONSUMER_KEY"}
    assert all(isinstance(v, bool) for v in body["data"]["keys"].values())


def test_projects_seeded():
    r = client.get("/api/projects"); assert r.status_code == 200
    ids = {p["id"] for p in r.json()["data"]}
    assert {"fire-uiseong-2025", "heat-gayang8-coolroof", "flood-buyeo-drainage"} <= ids


def test_equity_without_keys_is_degraded_not_fabricated():
    r = client.get("/api/equity/fire-uiseong-2025"); assert r.status_code == 200
    b = r.json(); assert b["status"] == "degraded"
    assert any("DATA_GO_KR_SERVICE_KEY" in w for w in b["warnings"]) or os.getenv("DATA_GO_KR_SERVICE_KEY")
    assert b["data"]["metrics"] == {} or all(m["value"] is None for m in b["data"]["metrics"].values())


def test_card_json_and_html_render_without_results():
    r = client.get("/api/projects/heat-gayang8-coolroof/card"); assert r.status_code == 200
    mods = r.json()["data"]["modules"]; assert mods[0]["module"] == "heat"
    h = client.get("/card/heat-gayang8-coolroof"); assert h.status_code == 200 and "적응 영수증" in h.text


def test_explain_without_key_is_template():
    r = client.post("/api/projects/fire-uiseong-2025/explain", json={"question": "효과가 있었나요?"})
    assert r.status_code == 200
    b = r.json(); assert b["data"]["source"] == "template" or os.getenv("GEMINI_API_KEY")


def test_chat_grounded_local_answer_and_tools():
    r = client.post("/api/chat", json={"message": "이 사업의 효과가 검출되었나요? 한계도 알려줘", "project_id": "flood-buyeo-drainage", "context": {"view": "dashboard"}, "history": []})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["answer"] and isinstance(d["evidence"], list) and isinstance(d["tool_trace"], list)
    assert {t["tool"] for t in d["tool_trace"]} >= {"verdict", "limits"}
    assert d["handoff"]["intent"] in ("verdict_brief", "report_sentence", "reproducibility", "equity_audit", "deadline")
    assert d["source"] == "local" or os.getenv("GEMINI_API_KEY")


def test_chat_without_project_does_not_fabricate():
    r = client.post("/api/chat", json={"message": "기한이 언제까지인가요?", "context": {}})
    assert r.status_code == 200
    d = r.json()["data"]
    assert any(t["tool"] == "calendar" and t["status"] == "ok" for t in d["tool_trace"])
    assert "검증이 실행되지 않았거나" in d["answer"] or d["source"] == "gemini"


def test_flood_grade_rule():
    assert verify_flood.grade(10) == "A" and verify_flood.grade(48) == "A"
    assert verify_flood.grade(49) == "B" and verify_flood.grade(120) == "B"
    assert verify_flood.grade(121) == "C" and verify_flood.grade(None) == "C"


def test_heat_qa_mask_and_lst_formula():
    qa = np.array([[0, 1 << 3], [1 << 1, 1 << 7]], dtype="uint16")   # 0=nodata, bit3 cloud, bit1 dilated, bit7 clear-ish
    bad = verify_heat.qa_mask(qa)
    assert bad.tolist() == [[True, True], [True, False]]
    dn = np.array([[0, 44000], [44000, 44000]], dtype="float32")
    lst = verify_heat.lst_celsius(dn, bad)
    assert np.isnan(lst[0, 0]) and abs(lst[1, 1] - (44000 * 0.00341802 + 149.0 - 273.15)) < 1e-3


def test_create_project_rejects_path_ids():
    r = client.post("/api/projects", json={"project": {"id": "../x", "name": "n", "type": "fire", "geometry": {"bbox": [0, 0, 1, 1]}}})
    assert r.status_code == 400
