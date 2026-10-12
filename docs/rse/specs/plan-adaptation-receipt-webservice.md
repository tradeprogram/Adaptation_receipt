# Plan — 적응 영수증 웹서비스 (FastAPI + 지도 대시보드)

작성 2026-10-07. 근거: `2026_기후변화대응_비즈니스아이디어_기획안_적응영수증.docx`, `reports/열섬 처방전 수익성 검증.md`, `scripts/fig_fire_recovery.py`(검증 파이프라인 원형), `C:\aquaguard`(응답 봉투·출처 배지·폴백 규약).

## 1. Overview
집행된 기후적응 사업의 효과·형평성을 위성으로 사후 검증하는 서비스를 **동작하는 웹서비스**로 구현한다. 백엔드는 FastAPI, 검증 엔진은 Planetary Computer STAC(키 불필요) + rasterio 창 읽기, 프런트는 정적 SPA(MapLibre GL·Chart.js). 외부 키가 필요한 모듈(건축물대장·SGIS·기상청·Gemini)은 `.env` 슬롯만 두고 키 없이도 "키 필요" 상태로 정직하게 동작한다.

## 2. Current State
- `scripts/fig_fire_recovery.py:1-120` — 단일 AOI 산불 회복 분석(스크립트). STAC 검색·SAS 토큰·창 읽기·SCL 마스킹·dNBR·NDVI 회복률 계산이 들어 있으나 함수화·캐시·재개가 없다.
- `C:\aquaguard\module_o_orchestrator\orchestrator.py` — `status/fallback_tier/data/warnings` 봉투와 `meta.module_sources` 출처 추적 패턴. 본 서비스 봉투는 이 규약을 따른다.
- 외부 API 실측(2026-10-06): `POST https://planetarycomputer.microsoft.com/api/stac/v1/search` 200, 장면 ID는 `S2A_MSIL2A_<date>_R<orbit>_T<tile>_<proc>` 형식(검색 결과로만 전체 ID 확보 가능); `GET /api/sas/v1/token/sentinel-2-l2a`는 간헐 504 → 재시도 필요; Landsat `landsat-c2-l2` 여름 장면은 구름 30% 미만이 연 2~4장.

## 3. Desired End State
- `uvicorn app.server.main:app`로 기동, `http://localhost:8008/`에서 대시보드가 열린다.
- 사업 3건(산불 복원·쿨루프·침수 정비)이 목록에 있고, 산불 복원 사업은 검증 결과(dNBR 면적, 회복률 시계열, 효과크기·CI·검정력, 배지, 한계)가 성과 카드로 표시된다.
- 검증 작업은 백그라운드 잡으로 실행되고 장면 단위 체크포인트로 재개된다. 실패 장면은 요약에 이름과 함께 나온다.
- 열 모듈은 Landsat LST 전후·처리/대조 이중차분을 계산한다(가양8단지는 외곽선 자료 없으면 "입력 대기").
- 침수 모듈은 사건별 Sentinel-1 관측가능성 등급(A/B/C)을 즉시 산출한다.
- 형평성 모듈·설명 에이전트는 키가 없으면 `status: degraded`, `warnings: ["DATA_GO_KR_SERVICE_KEY 필요"]`를 돌려주고 UI가 그 상태를 그린다.
- `pytest app/tests`가 통과한다.

## 4. What We're NOT Doing
- 가상·합성 데이터로 결과를 채우지 않는다. 키 없는 모듈은 비워 둔다.
- Sentinel-1 침수 범위 래스터 판독 전체(물길잡이 수준)는 범위 밖. 관측가능성 등급 + 설계만 구현한다.
- 사용자 인증·결제·멀티테넌시 없음.
- PDF 생성 없음(브라우저 인쇄용 HTML 카드 제공).

## 5. Implementation Approach
- 응답 봉투: `{status: ok|degraded|error, fallback_tier: 1|2|3, data, warnings[], provenance{}}`.
- 지표 규약: 표본 부족 시 `None`, 임계 판정은 `measured` 게이트 뒤에서만, 모든 수치에 배지(`OBSERVED/MODEL/RULE/ASSUMPTION`).
- 잡 규약: 장면별 `.npz` 캐시(원자적 저장), 잡 상태 JSON 원자적 저장, 재시도 상한 5(장면 단위), 부분 실패는 `status: partial`로.
- 프런트: 빌드 없음. CDN은 unpkg(MapLibre GL 4.x), jsdelivr(Chart.js 4.x, Pretendard).

## 6. Phases
### Phase 1 — 코어 라이브러리 (`app/server/config.py`, `envelope.py`, `metrics.py`, `stac.py`)
- 테스트 `app/tests/test_metrics.py`: `recovery_ratio([0.2],[0.5]) == 0.4`, `robust_z(x, baseline)`에서 baseline 2개 미만 → `None`, `did_effect` 대조군 없음 → `None`과 reason.
- `metrics.py`: `robust_z`, `did_effect`, `bootstrap_ci`(seed 고정), `mde`(최소검출효과), 모두 `float|None`.
- `stac.py`: `search_items(collection,bbox,datetime,query)`, `sas_token(collection)`(재시도 6회·백오프·캐시 50분), `read_window(href,bbox4326,res_m,epsg)`(rasterio Env 고정), `scene_cache_path`, `save_npz_atomic`.
- 검증: `pytest app/tests/test_metrics.py -q`.

### Phase 2 — 검증 엔진 (`verify_fire.py`, `verify_heat.py`, `verify_flood.py`, `equity.py`)
- `verify_fire.run(project, progress_cb)`: 궤도 자동 선택(발화 전 2개월 안 구름 최저 장면의 상대궤도 고정) → 시점 창(진화 직후 30일, 첫 생장기 6~7월, 이듬해 6~7월, 이듬해 9~10월) 각 1장면 → 밴드 캐시 → dNBR·마스크·NDVI 시계열 → 카드.
- `verify_heat.run(project)`: Landsat `landsat-c2-l2` 6~9월, QA_PIXEL 비트 마스킹, `lst_c = DN*0.00341802+149.0-273.15`, 처리/대조 폴리곤 중앙값 연도별 → DiD, 표본(화소 수) 보고.
- `verify_flood.observability(event_date,bbox)`: `sentinel-1-grd` 통과 목록 → 등급(A ≤48h, B 48~120h, C >120h/미관측).
- `equity.run(project)`: 키 유무 분기. 키 있으면 건축물대장 `getBrTitleInfo`(sigunguCd·bjdongCd·bun·ji) 호출·SGIS 인증 토큰 → 비율 비교. 없으면 degraded.
- 테스트 `test_engines.py`: 마스크·등급 함수 순수 로직(합성 배열이 아니라 결정적 작은 배열로 수식 검증).

### Phase 3 — 잡·카드·설명 (`jobs.py`, `report.py`, `explain.py`, `main.py`)
- 잡: `start(project_id, module)` → 스레드, 상태 `queued|running|done|partial|failed`, `progress{done,total,failed[]}`.
- 카드: `build_card(result)` → 지표표(값·배지·n), 한계 목록, 재현 매니페스트; `templates/card.html`.
- 설명: 카드 JSON만 입력, Gemini 키 없으면 템플릿 문장.
- API: §3 목록. 테스트 `test_api.py`(TestClient, `/api/health`, `/api/projects`, 키 없는 `/api/equity/{id}`가 degraded).

### Phase 4 — 프런트 (`app/web/index.html`, `styles.css`, `app.js`)
- 레이아웃: 좌 사업 목록+법정 달력, 중앙 지도(사업 범위·dNBR 오버레이 PNG), 우 성과 카드·회복 차트·형평성·설명.
- 상태: 로딩/진행률/실패/키 필요/미검출 모두 전용 표시.
- 검증: `impeccable detect --json app/web` 1회, 데스크톱·모바일 스크린샷 1회.

### Phase 5 — 시드·사전 실행·문서
- `app/data/projects/*.json` 3건, 산불 사업 사전 실행으로 캐시 채움, `.env.example`, `app/README.md`, `.claude/launch.json`.

## 7. Success Criteria
Automated: `pytest app/tests -q` 통과; `curl localhost:8008/api/health` 200; `/api/projects` 3건; `/api/projects/fire-uiseong-2025/card` 에 `effect.recovery_ratio` 배열 길이 ≥4; 키 없는 `/api/equity/...` 가 `status=degraded`.
Manual: 대시보드에서 사업 클릭 → 카드·차트·지도 오버레이 표시; 모바일 폭에서 가로 스크롤 없음; 미검출·키 필요 상태가 시각적으로 구분됨.

## 8. Testing Strategy
단위(지표·마스크·등급), 통합(TestClient), 수동(브라우저 미리보기 스크린샷).

## 9. References
- 기획안 docx, 수익성 보고서, `scripts/fig_fire_recovery.py`, AquaGuard `ARCHITECTURE.md` §봉투.
