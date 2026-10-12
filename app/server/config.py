"""환경 설정과 API 키 슬롯.

키는 .env 또는 환경변수로 들어온다. 비어 있으면 해당 모듈은 degraded 상태로 동작한다(가상값 금지).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]          # C:\for_huss\app
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
PROJECTS_DIR = DATA_DIR / "projects"
# 배포본(Vercel 서버리스)은 저장소 파일이 읽기 전용이라 결과(results)만 읽고, 잡·장면 캐시는 /tmp에 둔다.
READ_ONLY = bool(os.getenv("VERCEL") or os.getenv("AR_READ_ONLY") == "1")
CACHE_DIR = Path(os.getenv("AR_CACHE_DIR", ROOT / "cache"))
_WRITABLE = Path(os.getenv("AR_TMP_DIR", "/tmp/ar-cache")) if READ_ONLY else CACHE_DIR
JOBS_DIR = _WRITABLE / "jobs"
SCENES_DIR = _WRITABLE / "scenes"
RESULTS_DIR = CACHE_DIR / "results"
WEB_DIR = ROOT / "web"
for _d in (CACHE_DIR, JOBS_DIR, SCENES_DIR, RESULTS_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

# ---- API 키 슬롯 (발급 후 .env에 채운다) ----
KEYS = {
    # 설명 에이전트 (Google Gemini). 없으면 템플릿 문장으로 폴백.
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
    "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    # 건축물대장 표제부 (공공데이터포털, 서비스: 1613000/BldRgstHubService) — 형평성 감사(노후도·구조)
    "DATA_GO_KR_SERVICE_KEY": os.getenv("DATA_GO_KR_SERVICE_KEY", ""),
    # 통계청 SGIS OpenAPI — 고령·1인가구 격자/집계구 통계
    "SGIS_CONSUMER_KEY": os.getenv("SGIS_CONSUMER_KEY", ""),
    "SGIS_CONSUMER_SECRET": os.getenv("SGIS_CONSUMER_SECRET", ""),
    # 브이월드 — 건물 footprint WFS(처리구/대조구 외곽선)
    "VWORLD_API_KEY": os.getenv("VWORLD_API_KEY", ""),
    # 기상청 API허브 — 사건 강도 보정(강우·기온)
    "KMA_APIHUB_KEY": os.getenv("KMA_APIHUB_KEY", ""),
    # 행안부 재난안전데이터 공유플랫폼 — 데이터셋별 서비스키(무더위쉼터 / 복구계획공공시설)
    "SAFETYDATA_KEY_SHELTER": os.getenv("SAFETYDATA_KEY_SHELTER", os.getenv("SAFETYDATA_SERVICE_KEY", "")),
    "SAFETYDATA_KEY_RECOVERY": os.getenv("SAFETYDATA_KEY_RECOVERY", os.getenv("SAFETYDATA_SERVICE_KEY", "")),
    # Microsoft Planetary Computer — 익명 가능. 구독키가 있으면 속도 제한 완화.
    "PC_SDK_SUBSCRIPTION_KEY": os.getenv("PC_SDK_SUBSCRIPTION_KEY", ""),
}

# 산불 원자료 CSV(산림청 발생대장 기반, 2015~2025) — 사업 대장 자동 생성·사건 조회에 사용
FIRE_RAW_CSV = Path(os.getenv("FIRE_RAW_CSV", "")) if os.getenv("FIRE_RAW_CSV") else None

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token"
USER_AGENT = "adaptation-receipt/0.1 (+for_huss)"
HTTP_TIMEOUT = 60
MAX_SCENE_RETRIES = 5
MOCK = os.getenv("AR_MOCK", "0") == "1"


def key_status() -> dict[str, bool]:
    """어떤 키가 채워져 있는지(값은 노출하지 않는다)."""
    return {k: bool(v) for k, v in KEYS.items() if k != "GEMINI_MODEL"}
