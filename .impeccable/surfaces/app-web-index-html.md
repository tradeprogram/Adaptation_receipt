---
version: 1
slug: "app-web-index-html"
primary_target: "app/web/index.html"
related_targets: ["app/web/sheet.css","app/web/app.js"]
---

# Surface brief — app/web/index.html (적응 영수증 대시보드)

Scope: 대시보드 한 화면(사업 목록·지도·성과 카드·설명). Mode: Operate.
Audience: 기초지자체 기후환경 부서 담당자, 적응대책 수립 컨설턴트, 공모전 심사위원. Job: 사업 하나를 골라 "효과가 검출되었는가·얼마나·근거·한계"를 10초 안에 읽고 보고서에 붙일 카드를 연다.
Proof/content: 실제 위성 검증 결과(의성·안동 산불), 장면 매니페스트, 출처 배지, 법정 달력. Constraints: 가상값 금지, 키 없는 모듈은 "키 필요"로 표시, 빌드 도구 없음(정적 HTML/CSS/JS).

## Direction contract

THESIS: 이 화면은 대시보드가 아니라 **국토지리정보원 1:25,000 지형도 도엽**이다. 사업 하나가 도엽 하나이고, 검증 결과는 도엽의 난외주기(欄外註記)에 적힌다. 카드 그리드·KPI 타일·사이드바 세 칸짜리 SaaS 배치를 거부한다.

OWN-WORLD: 종이 흰색 바탕(#f6f4ec 계열이 아닌 거의 순백 #fbfaf6), 검정 헤어라인 네트라인과 경위도 눈금, 지형도 의미색을 데이터 역할에만 쓴다 — 등고선 갈색 계열(피해·산불), 수계 청색(침수), 식생 녹색(대조지·회복), 도로 주홍(열). 판정은 붉은 검정(檢定) 도장. 글꼴은 Pretendard(한글 본문)와 Barlow Condensed(도엽 난외 활자: 좌표·수치·도엽번호, 탭 정렬 숫자). 모든 표는 헤어라인 괘선, 각주 기호로 출처 배지. 그림자 없음, 종이 위 잉크만.

STORY: 방문자는 도엽 색인에서 사업(도엽)을 고르고, 지면 위에서 피해등급 음영과 축척·좌표를 읽고, 오른쪽 난외주기에서 판정 도장·지표 장부·회복 단면도·한계를 읽은 뒤 "카드 인쇄"로 보고서 부록을 얻는다.

FIRST VIEWPORT: 화면 전체가 한 장의 도엽. 바깥 여백(네트라인)에 상단 중앙 도엽명(사업명), 좌상 도엽번호(사업 ID)와 축척 1:n(지도 줌에서 실측), 네 변에 경위도 눈금(지도 bounds에서 실시간). 지면(지도)이 가운데 60%를 차지하고 피해등급 음영이 pixelated로 올라간다. 오른쪽 난외주기 28%: 검정 도장(판정) → 지표 장부 → 회복 단면도 → 피해등급 범례(해치) → 한계 → 조제 매니페스트. 왼쪽 12%: 도엽 색인(사업 3개 작은 격자 타일) + 법정 기한 한 줄. 하단 여백: 축척 막대, 자료 출처·조제일, 관측 패스 눈금(장면 날짜). 1차 행동 "검증 실행 / 카드 인쇄"는 난외주기 맨 위 도장 옆.

FORM: 후보 6 "국토지리정보원 지형도 도엽" (내 그라운디드 목록 6위, 할당 인덱스 6, seed 6063aee1). 챌린저 판정: ikeda-datamatics 기각(데이터 밀도·탭 정렬 숫자 규율 이전), rw-timetable-slide-rack 경합(고정 셀 안의 상태 마크 ●○✕ 규율 이전), cassette-j-card 기각(우측 정렬 수치), emigre-bitmap 기각(정직한 픽셀 렌더링 image-rendering: pixelated 이전), streaming-wall 기각(선택 도엽 외 색인 흐림), manual-acetate-tab-board 기각(범위 비례 탭 레일 → 관측 패스 눈금 레일).

FINISH: unreviewed and undocumented until the shipped reviewer and documenter run.
