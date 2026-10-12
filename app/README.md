# 적응 영수증 (Adaptation Receipt) — 웹서비스

집행된 기후적응 사업(산불 피해지 복구, 하천·배수 정비, 옥상 차열)의 **효과와 수혜 형평성을 공개 위성 관측과 준실험 설계로 사후 검증**해, 지자체 이행점검 보고서(매년 4/30)·공공기관 이행실적·공시에 첨부할 **성과 카드**를 만드는 서비스. 기획안 `../2026_기후변화대응_비즈니스아이디어_기획안_적응영수증.docx`의 구현체.

## 실행

```bash
cd C:\for_huss
pip install fastapi uvicorn rasterio numpy scipy shapely pyproj jinja2 python-dotenv requests pillow google-genai pytest
copy app\.env.example app\.env        # 키를 채운다(비워 두면 해당 모듈은 "키 필요"로 표시)
python -m uvicorn app.server.main:app --port 8008
```

브라우저에서 `http://localhost:8008/`. 테스트는 `python -m pytest app/tests -q`.

## 구조

```
app/
  server/
    main.py         FastAPI 라우트 + 정적 프런트 마운트
    config.py       .env 키 슬롯, 경로
    envelope.py     응답 봉투 {status, fallback_tier, data, warnings, provenance} · 배지 OBSERVED/MODEL/RULE/ASSUMPTION
    metrics.py      robust z · 이중차분 · 부트스트랩 CI · 검출가능최소효과(MDE) — 표본 부족이면 None
    stac.py         Planetary Computer STAC 검색 · SAS 토큰(재시도·캐시) · COG 창 읽기 · 장면 캐시(원자적 저장)
    verify_fire.py  산불: 동일 궤도 Sentinel-2, dNBR 피해등급, 피해지/대조지 NDVI 회복률, DiD·CI·MDE, 오버레이 PNG
    verify_heat.py  열: Landsat C2 L2 지표면온도(lwir11·qa_pixel), 처리/대조 폴리곤 전후 DiD
    verify_flood.py 침수: Sentinel-1 관측가능성 등급(A/B/C) + 2단계 실행 조건
    equity.py       형평성: 건축물대장 표제부(동별 사용승인·구조·세대, 페이지 순회) · SGIS(노년부양비·노령화지수·가구) — 키 없으면 degraded
    vworld.py       브이월드 지오코딩·건물 footprint WFS(처리/대조 동 외곽선 자동 채움)
    jobs.py         백그라운드 잡(상태 JSON 원자적 저장, 실패 장면 이름 보존)
    report.py + templates/card.html   성과 카드 JSON·HTML(인쇄용)
    explain.py      설명 계층(구) — 카드 수치만 인용
    chat.py         적응영수증.chat — 도구 계획·근거 카드·handoff, Gemini/로컬 요약(수치 검증)
  web/              index.html · sheet.css · ink.css · layout.css · dashboard.js · chat.js · assets/(paper.jpg, ink-mask.jpg, stamp-mask.jpg) (MapLibre GL, Chart.js, 빌드 없음)
  data/projects/    사업 대장 JSON(3건 시드)
  cache/            scenes/(장면 npz) jobs/ results/{project}/{module}.json + 오버레이 PNG
  tests/
```

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/health` | 키 설정 여부(값 미노출), 목업 여부 |
| GET | `/api/projects` · `/api/projects/{id}` | 사업 목록·상세(결과 요약·최근 잡) |
| POST | `/api/projects` | 사업 등록 `{project:{id,name,type,geometry,...}}` |
| POST | `/api/projects/{id}/verify/{fire\|heat\|flood}` | 검증 잡 시작 |
| GET | `/api/jobs/{job_id}` · `/api/jobs?project_id=` | 잡 상태·진행률 |
| GET | `/api/projects/{id}/card` · `/card/{id}` | 성과 카드 JSON · HTML |
| GET | `/api/equity/{id}` | 형평성 감사 |
| POST | `/api/projects/{id}/explain` | 설명 `{question}` (구) |
| POST | `/api/chat` | 적응영수증.chat `{message, project_id, context, history}` → answer·evidence·tool_trace·handoff·actions |
| GET | `/api/projects/{id}/overlay/{dnbr\|pre\|post}.png` | 지도 오버레이 |
| GET | `/api/calendar` | 법정 보고 달력 |

## 사업 JSON 스키마(요약)

- 공통: `id, name, type(fire|heat|flood), modules[], agency, region, period, budget_krw, legal_basis, description, geometry.bbox[4326]`, `beneficiaries[]`(형평성 감사용 주소·지번)
- fire: `event_date, contained_date, params{res_m,dnbr_threshold,prefire_ndvi_min,control_abs_dnbr_max}`, 선택 `windows[[label,start,end],...]`
- heat: `years_before[], years_after[], geometry.treated[GeoJSON], geometry.control[GeoJSON]`
- flood: `events[{name, peak(ISO, UTC), phase(before|after)}]`

## 외부 동작 확인 기록(2026-10-06~07)
- PC STAC `/search` 200. Sentinel-2 장면 ID는 검색 결과로만 전체 ID 확보 가능. SAS 토큰 엔드포인트 간헐 504 → 6회 재시도.
- Landsat C2 L2 자산 키: `lwir11`, `qa_pixel`(`ST_B10`/`QA_PIXEL` 아님).
- Sentinel-1 GRD 검색은 같은 장면을 두 ID로 반환 → 관측시각으로 중복 제거.
- 건축물대장 getBrTitleInfo(2026-10-12 실측): `items.item`이 dict 또는 list, 한 페이지 10건 이하 → pageNo 순회, 간헐 `SERVICETIMEOUT_ERROR`. SGIS: 코드는 `addr/stage.json`(강서구 11160), `stats/population.json`은 `age_type` 미지원(412) → 노년부양비·노령화지수 필드 사용. 브이월드 WFS는 KEY+DOMAIN=localhost, MAXFEATURES 상한 주의. Gemini는 `gemini-3.8-flash`(2.5-flash는 신규 사용자 제공 종료). 기상청 API허브는 API별 활용신청 필요(403). 재난안전데이터 공유플랫폼 키는 등록 IP에서만 동작(UNREGISTERED IP ERROR).

## 운영 원칙
- 가상 데이터 금지. 표본 부족·관측 공백은 `None`→"측정 불가"로 표시(0이 아님).
- 미검출은 "효과 없음"의 증명이 아니다. 검출가능최소효과(MDE)는 독립 화소 가정의 낙관적 근사치다.
- 실패한 장면·사건은 결과의 `failed[]`에 이름과 함께 남고 잡 상태는 `partial`이 된다.


## 2026-10-12 추가 연동 (실측 확인)
- `server/kma.py` — 기상청 API허브 `kma_sfctm3`(지상관측 시간자료, 공백 구분 텍스트, 결측 -9). `fetch_season`으로 월 단위 수집, `rain_events`가 3h≥60mm 또는 1h≥30mm를 24h 간격으로 묶어 호우 사건(정점=1h 최대 시각, UTC 환산)을 만든다. 침수 사업은 `kma_stn`·`years_before/after`만 두면 사건을 자동 추출한다(부여 236: 2023 A등급 1건, 2025 B등급 2건 → 2단계 준비).
- `server/safetydata.py` — 행안부 재난안전데이터 공유플랫폼 무더위쉼터(DSSP-IF-10942) 61,948건을 `cache/shelters_heat.json`에 두고 AOI bbox로 거른다(등록 IP에서만 내려받기 가능). 열 사업 카드에 `shelters_in_aoi`(가양8단지 9곳)·`shelter_capacity_in_aoi`(290명) 행이 추가되고 채팅 근거로 쓰인다.
- 복구계획공공시설 키: DSSP-IF-00001~00159, 10800~11059 스윕에서 승인된 서비스 ID를 찾지 못함(모두 SERVICE ACCESS DENIED). 마이페이지 활용신청 내역의 DSSP-IF 번호가 필요하다.


## 배포 (GitHub → Vercel)
저장소: https://github.com/tradeprogram/Adaptation_receipt

- 진입점 `api/index.py`가 `app.server.main:app`을 그대로 노출하고, `vercel.json`이 모든 경로를 이 함수로 보낸다(리전 icn1, 60초, 1 GB).
- 배포본은 **읽기 전용**이다(`VERCEL` 환경변수 감지 → `config.READ_ONLY`). 카드·영수증·채팅·법정 달력·형평성 감사는 동작하고, 위성 재검정(`POST /verify`)은 503으로 거절한다. 재검정은 로컬에서 돌리고 `app/cache/results/`를 커밋하면 배포본에 반영된다.
- `requirements.txt`는 배포용 최소 의존성(rasterio 없음)이고, 로컬 전체 실행은 `pip install -r app/requirements-full.txt`.
- 무더위쉼터 전수는 `app/data/shelters_heat_slim.json`(필드 9개)으로 동봉되어 등록 IP가 아닌 서버에서도 AOI 집계가 된다.
- Vercel 프로젝트 환경변수(값은 대시보드에서만 입력): `GEMINI_API_KEY`, `GEMINI_MODEL`, `DATA_GO_KR_SERVICE_KEY`, `SGIS_CONSUMER_KEY`, `SGIS_CONSUMER_SECRET`, `VWORLD_API_KEY`(브이월드 키의 허용 도메인에 배포 도메인을 추가해야 한다), `KMA_APIHUB_KEY`. 행안부 키는 등록 IP 전용이라 배포본에서는 쓰지 않는다.
- 배포 순서: Vercel 대시보드 → Add New Project → GitHub `tradeprogram/Adaptation_receipt` Import → Framework Preset "Other" → 환경변수 입력 → Deploy. 이후 `main` 브랜치 푸시마다 자동 재배포.


## 2026-10-12 지도 레이어 확장
- **열(가양8단지)**: 검증 격자를 AOI 둘레 약 1.4 km까지 넓혀 한 번에 읽고(`params.context_pad_lon/lat`), 시공 전·후 여름 지표면온도 중앙값과 전후 차이를 오버레이 PNG(`lst_before/after/diff.png`)로 만든다(`overlay_png.py`). 통계는 종전대로 처리·대조 폴리곤 마스크로만 뽑는다. 카드에 `shelters`(AOI 안 무더위쉼터 목록)가 실려 지도에 점·팝업으로 표시된다. 처리(갈색 실선)·대조(녹색 점선) 폴리곤은 사업 대장의 `geometry.treated/control`을 그대로 그린다.
- **침수(부여)**: 2단계 침수 범위를 Sentinel-1 RTC(`sentinel-1-rtc`, 익명 SAS 가능 실측)로 구현. A/B 사건의 첫 패스 VV(dB)를 같은 상대궤도 건기 기준선 중앙값(사건 전 75~4일, 모자라면 사건 후 6~75일로 보충 — S1C 궤도 RTC는 2025-07-18부터 존재)과 비교해 `VV<−16 dB & 기준선 대비 −3 dB` 화소를 침수로 분류, 기준선 자체가 −16 dB 미만이면 상시 수역. 시기별 합집합 면적·전후 차이와 `flood_before/after/change.png`를 낸다. 판정 `reduced`(−10% 이하) / `not_reduced`. 실측(부여): 정비 전 149 ha(2023-06-29·09-20) → 후 182 ha(2025-07-16, 3h 강우 133 mm vs 80 mm) → 미감소. 2025-09-09 S1C 장면은 읽기 실패로 `stage2.error`에 남김.
- 프런트: 오버레이 버튼을 모듈 결과의 `overlays` 키로 동적 생성하고 범례(`overlays.legend`)를 지도 도구 옆에 표시. 기상 관측소(`kma_station`) 점 팝업에 사건별 1h/3h 강우.
