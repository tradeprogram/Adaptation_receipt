/* 적응 영수증 — 도엽형 대시보드. 빌드 없이 동작하는 단일 스크립트 */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const api = async (path, opt) => { const r = await fetch(path, opt); if (!r.ok) throw new Error(`${r.status} ${path}`); return r.json(); };
  const TYPE_LABEL = { fire: "산불 피해지 복구·복원", heat: "옥상 차열·녹화(열 저감)", flood: "하천·배수 정비(침수 방재)" };
  const TYPE_CODE = { fire: "FIRE", heat: "HEAT", flood: "FLOOD" };
  const VERDICT = { detected: "효과 검출", recovered: "대조지 수준 회복", gap_remaining: "회복 격차 잔존", undetected: "미검출", unmeasured: "측정 불가", ready: "2단계 실행 가능", waiting: "대기", waiting_input: "입력 대기", not_run: "미실행", failed: "실패", partial: "부분 완료", ok: "완료", done: "완료", queued: "대기", running: "진행" };
  const SRC = { OBSERVED: "실측", MODEL: "계산", RULE: "규칙", ASSUMPTION: "가정", FORECAST: "예보" };
  const SEV_COLORS = ["#e9cf9c", "#c48a3e", "#8a5a1e", "#4a2a12"];
  const state = { projects: [], current: null, card: null, overlay: "dnbr", chart: null, poll: null };

  // ---------- 지면(지도) ----------
  const map = new maplibregl.Map({ container: "map", style: "https://tiles.openfreemap.org/styles/liberty", center: [127.8, 36.4], zoom: 6.3, attributionControl: { compact: true } });
  const SAT = { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, attribution: "Esri World Imagery" };
  const firstSymbolLayer = () => (map.getStyle().layers.find((l) => l.type === "symbol") || {}).id;
  const bboxPoly = (b) => ({ type: "Polygon", coordinates: [[[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]], [b[0], b[1]]]] });
  map.on("load", () => {
    map.addSource("sat", SAT);
    map.addLayer({ id: "sat", type: "raster", source: "sat", layout: { visibility: "none" } }, firstSymbolLayer());
    map.addSource("aois", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "aoi-fill", type: "fill", source: "aois", paint: { "fill-color": "#141414", "fill-opacity": 0.04 } });
    map.addLayer({ id: "aoi-line", type: "line", source: "aois", paint: { "line-color": "#141414", "line-width": 1, "line-dasharray": [4, 3] } });
    map.addLayer({ id: "aoi-active", type: "line", source: "aois", filter: ["==", ["get", "id"], ""], paint: { "line-color": "#141414", "line-width": 2 } });
    map.on("click", "aoi-fill", (e) => { const id = e.features?.[0]?.properties?.id; if (id) selectProject(id); });
    map.on("mouseenter", "aoi-fill", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "aoi-fill", () => (map.getCanvas().style.cursor = ""));
    drawAois(); updateMarginalia();
  });
  map.on("moveend", updateMarginalia); map.on("resize", updateMarginalia);
  // 지면 크기가 바뀌면(글꼴·채팅 로드로 격자 재배치) 현재 도엽 범위로 다시 맞춘다
  let fitTimer = null;
  new ResizeObserver(() => { if (!state.focusBbox) return; clearTimeout(fitTimer); fitTimer = setTimeout(() => { map.resize(); const b = state.focusBbox; map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 40, duration: 300 }); }, 120); }).observe(document.querySelector(".plate"));
  function drawAois() {
    const src = map.getSource("aois"); if (!src) return;
    src.setData({ type: "FeatureCollection", features: state.projects.map((p) => ({ type: "Feature", properties: { id: p.id, name: p.name }, geometry: bboxPoly(p.bbox) })) });
  }
  // 경위도 눈금·축척: 지도 bounds와 줌에서 실측해 난외에 적는다
  const dms = (v, lonlat) => { let t = Math.round(Math.abs(v) * 3600); const d = Math.floor(t / 3600); t -= d * 3600; const m = Math.floor(t / 60); const s = t - m * 60; return `${d}°${String(m).padStart(2, "0")}′${String(s).padStart(2, "0")}″${lonlat === "lon" ? (v >= 0 ? "E" : "W") : (v >= 0 ? "N" : "S")}`; };
  function updateMarginalia() {
    const b = map.getBounds(); const el = map.getContainer();
    const n = Math.max(2, Math.min(6, Math.floor(el.clientWidth / 170) + 1)); const nl = Math.max(2, Math.min(5, Math.floor(el.clientHeight / 150) + 1));
    const lons = Array.from({ length: n }, (_, i) => b.getWest() + (b.getEast() - b.getWest()) * i / (n - 1));
    const lats = Array.from({ length: nl }, (_, i) => b.getNorth() - (b.getNorth() - b.getSouth()) * i / (nl - 1));
    const h = (arr, k) => arr.map((v) => `<span>${dms(v, k)}</span>`).join("");
    $("#grTop").innerHTML = h(lons, "lon"); $("#grBottom").innerHTML = h(lons, "lon"); $("#grLeft").innerHTML = h(lats.slice().reverse(), "lat"); $("#grRight").innerHTML = h(lats, "lat");
    const lat = map.getCenter().lat; const mPerPx = 156543.03392 * Math.cos(lat * Math.PI / 180) / Math.pow(2, map.getZoom());
    const target = 120 * mPerPx; const nice = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000].reduce((a, c) => Math.abs(c - target) < Math.abs(a - target) ? c : a);
    $("#scalebar").style.setProperty("--w", `${nice / mPerPx}px`); $("#scalebarText").textContent = nice >= 1000 ? `${nice / 1000} km` : `${nice} m`;
    const denom = Math.round(mPerPx * 96 / 0.0254 / 1000) * 1000; $("#sheetScale").textContent = `1 : ${denom.toLocaleString("ko-KR")}`;
  }
  function setOverlay(name) {
    state.overlay = name;
    if (!map.getLayer("aoi-fill")) { map.once("load", () => setOverlay(name)); return; }
    if (map.getLayer("overlay")) { map.removeLayer("overlay"); map.removeSource("overlay"); }
    const mod = state.card?.modules?.find((m) => m.overlays);
    if (!mod || name === "none") return;
    const b = mod.overlays.bounds; const url = mod.overlays[name] + "?t=" + Date.now();
    map.addSource("overlay", { type: "image", url, coordinates: [[b[0], b[3]], [b[2], b[3]], [b[2], b[1]], [b[0], b[1]]] });
    map.addLayer({ id: "overlay", type: "raster", source: "overlay", paint: { "raster-opacity": +$("#opacity").value / 100, "raster-fade-duration": 120, "raster-resampling": "nearest" } }, "aoi-fill");
  }
  document.querySelectorAll("[data-base]").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("[data-base]").forEach((x) => x.classList.toggle("is-active", x === b)); map.setLayoutProperty("sat", "visibility", b.dataset.base === "sat" ? "visible" : "none");
  }));
  document.querySelectorAll("[data-ov]").forEach((b) => b.addEventListener("click", () => { document.querySelectorAll("[data-ov]").forEach((x) => x.classList.toggle("is-active", x === b)); setOverlay(b.dataset.ov); }));
  $("#opacity").addEventListener("input", (e) => { if (map.getLayer("overlay")) map.setPaintProperty("overlay", "raster-opacity", +e.target.value / 100); });

  // ---------- 도엽 색인 ----------
  async function loadProjects() {
    const r = await api("/api/projects"); state.projects = r.data;
    const ol = $("#projectList"); ol.innerHTML = "";
    for (const p of r.data) {
      const li = document.createElement("li");
      const res = Object.values(p.results)[0]; const code = res ? (res.verdict || res.status) : "not_run";
      li.innerHTML = `<button class="index-tile" data-id="${p.id}"><span class="code"><span>${TYPE_CODE[p.type] || p.type}</span><span>${(p.event_date || p.period || "").slice(0, 7)}</span></span><span class="name">${p.name}</span><span class="mark ${code}">${VERDICT[code] || code}</span></button>`;
      li.querySelector("button").addEventListener("click", () => selectProject(p.id)); ol.appendChild(li);
    }
    document.querySelectorAll(".index-tile").forEach((b) => b.classList.toggle("is-active", b.dataset.id === state.current)); drawAois();
  }

  // ---------- 난외주기(카드) ----------
  async function selectProject(id) {
    state.current = id;
    document.querySelectorAll(".index-tile").forEach((b) => b.classList.toggle("is-active", b.dataset.id === id));
    const p = state.projects.find((x) => x.id === id);
    const focus = () => { map.resize(); map.setFilter("aoi-active", ["==", ["get", "id"], id]); map.fitBounds([[p.bbox[0], p.bbox[1]], [p.bbox[2], p.bbox[3]]], { padding: 40, duration: 600 }); };
    if (p) { state.focusBbox = p.bbox; if (map.getLayer("aoi-active")) focus(); else map.once("load", focus); }
    const r = await api(`/api/projects/${id}/card`); state.card = r.data; renderCard(); setOverlay(state.overlay);
    if (state.poll) { clearInterval(state.poll); state.poll = null; }
    const jobs = (await api(`/api/jobs?project_id=${id}`)).data.filter((j) => ["queued", "running"].includes(j.status));
    if (jobs.length) watchJob(jobs[0].id);
  }
  const fmt = (v, unit) => v == null ? `<span class="none">측정 불가</span>` : Array.isArray(v) ? `${v[0].toFixed(3)} ~ ${v[1].toFixed(3)}${unit ? " " + unit : ""}` : typeof v === "object" ? Object.entries(v).map(([k, x]) => `${k} ${typeof x === "number" ? (Number.isInteger(x) ? x : x.toFixed(2)) : x}`).join(" · ") : typeof v === "boolean" ? (v ? "예" : "아니오") : typeof v === "number" ? (Number.isInteger(v) ? v.toLocaleString("ko-KR") : (Math.abs(v) < 10 ? v.toFixed(3) : v.toFixed(1))) + (unit ? ` ${unit}` : "") : String(v);
  function renderCard() {
    const c = state.card; const p = c.project; const mod = c.modules[0];
    $("#cardEmpty").hidden = true; $("#card").hidden = false;
    printReceipt(p, mod);
    $("#sheetId").textContent = p.id.toUpperCase(); $("#sheetName").textContent = p.name;
    $("#cardMeta").textContent = [TYPE_LABEL[p.type], p.agency, p.region, p.period, p.budget_krw ? `${(p.budget_krw / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}억 원` : null].filter(Boolean).join(" · ");
    $("#btnCard").href = `/card/${p.id}`; $("#btnJson").href = `/api/projects/${p.id}/card`;
    const v = mod.verdict || {}; const code = v.code || mod.status || "not_run";
    const st = $("#stamp"); st.className = `stamp ${["not_run", "waiting_input", "unmeasured", "waiting"].includes(code) ? "neutral" : code}`;
    $("#stampWord").textContent = VERDICT[code] || code; $("#stampDate").textContent = mod.computed_at ? mod.computed_at.slice(0, 10).replaceAll("-", ".") + " 검정" : "검정 전";
    st.classList.remove("press"); void st.offsetWidth; st.classList.add("press");
    $("#verdictText").textContent = v.text || "";
    $("#needs").hidden = !mod.needs; if (mod.needs) $("#needs").textContent = "필요한 입력: " + mod.needs.join(", ");
    $("#metricsBlock").hidden = !mod.metrics.length;
    // 영수증 행: 항목 ······ 값 / n / 출처
    $("#metricsTable").outerHTML = `<div class="rcpt" id="metricsTable">` + mod.metrics.map((r) => `<div class="row"><span class="lbl">${r.key}${r.note ? `<span class="sub">${r.note}</span>` : ""}</span><span class="lead"></span><span class="val">${fmt(r.value, r.unit)}${r.n != null ? `<span class="n">n ${r.n.toLocaleString("ko-KR")}</span>` : ""}<span class="src ${r.badge}">${SRC[r.badge]}</span></span></div>`).join("") + `</div>`;
    $("#chartBlock").hidden = !mod.series; if (mod.series) renderChart(mod.series);
    $("#severityBlock").hidden = !mod.severity; if (mod.severity) renderSeverity(mod.severity);
    $("#eventsBlock").hidden = !mod.events;
    if (mod.events) $("#eventsTable").innerHTML = `<tr><th>사건</th><th>단계</th><th>등급</th><th class="num">첫 관측(h)</th><th>궤도</th></tr>` + mod.events.map((e) => `<tr><td>${e.name}<span class="sub">${e.event_peak}</span></td><td>${e.phase === "before" ? "정비 전" : "정비 후"}</td><td><span class="mark ${e.grade === "C" ? "undetected" : "detected"}">${e.grade}</span></td><td class="num">${e.first_pass_hours ?? "미관측"}</td><td><span class="sub">${(e.passes || []).slice(0, 2).map((x) => `${x.relative_orbit}${x.orbit_state?.[0]?.toUpperCase() || ""}`).join(", ")}</span></td></tr>`).join("");
    const eq = c.equity; const eb = $("#equityBody");
    if (!eq) eb.innerHTML = `<div class="errata">형평성 감사 미실행</div>`;
    else if (eq.status !== "ok") eb.innerHTML = `<div class="errata">${eq.warnings.join("<br>")}</div><p class="meta">지표 설계: ${eq.data.design.indicators.join(" · ")}</p>`;
    else eb.innerHTML = `<table class="tbl">${Object.entries(eq.data.metrics).map(([k, m]) => `<tr><td>${k}</td><td class="num">${fmt(m.value, m.unit)}</td><td><span class="src ${m.badge}">${SRC[m.badge]}</span></td></tr>`).join("")}</table>`;
    $("#limitsBlock").hidden = !(mod.limitations || []).length; $("#limitsList").innerHTML = (mod.limitations || []).map((l) => `<li>${l}</li>`).join("");
    const sc = mod.scenes || []; $("#scenesBlock").hidden = !sc.length; $("#scenesCount").textContent = sc.length ? `장면 ${sc.length}${mod.failed?.length ? ` · 실패 ${mod.failed.length}` : ""}` : "";
    $("#scenesTable").innerHTML = `<tr><th>시점</th><th>관측일</th><th>장면</th><th>기준선</th><th class="num">구름%</th><th class="num">유효%</th></tr>` + sc.map((s) => `<tr><td>${s.label ?? s.year ?? ""}</td><td class="num">${s.date ?? "없음"}</td><td>${(s.ids || [s.id]).join("<br>")}</td><td class="num">${s.processing_baseline ?? ""}</td><td class="num">${s.cloud_cover != null ? s.cloud_cover.toFixed(1) : ""}</td><td class="num">${s.valid_pct ?? ""}</td></tr>`).join("") + (mod.failed || []).map((f) => `<tr><td colspan="6" class="none">실패: ${f.label || f.year || f.event?.name || ""} — ${f.error}</td></tr>`).join("");
    renderPassRail(sc);
    const hasOv = !!mod.overlays; $("#overlaySeg").hidden = !hasOv; $("#opacityWrap").hidden = !hasOv;
    $("#btnVerify").disabled = false; $("#btnVerify").querySelector("span").textContent = mod.status === "not_run" ? "검증 실행" : "다시 검정";
    $("#colophonRight").textContent = `조제 ${(mod.computed_at || c.generated_at).slice(0, 10)}${mod.design?.orbit ? " · 궤도 " + mod.design.orbit : ""}${mod.design?.resolution_m ? " · " + mod.design.resolution_m + " m" : ""}`;
    window.dispatchEvent(new CustomEvent("ar:project-selected", { detail: { id: p.id } }));
  }
  // 3D 출력: 프린터 헤드에서 카드가 뽑혀 나온다. 같은 도엽을 다시 그릴 때마다 새로 출력한다.
  let printSeq = 0, printGuard = null;
  function printReceipt(p, mod) {
    const note = $("#card"), printer = $("#printer"); if (!note || !printer) return;
    $("#printerCounter").textContent = `NO. ${String(printSeq + 1).padStart(4, "0")} · ${p.id.toUpperCase()}`;
    $("#printerState").textContent = "PRINTING"; printer.classList.add("busy");
    $(".margin-right").scrollTo({ top: 0 });
    // 단계는 타이머로 진행한다(CSS 지속시간과 동일). animationend는 탭이 숨겨지면 오지 않는다.
    const STAGES = [["feeding", 1600, "PRINTING"], ["cutting", 240, "CUT"], ["settling", 1100, "DONE"]];
    const clear = () => note.classList.remove("printed", "feeding", "cutting", "settling");
    const finish = () => { clear(); note.classList.add("printed"); printer.classList.remove("busy"); $("#printerState").textContent = "READY"; clearTimeout(printGuard); };
    const seq = ++printSeq;
    const run = (i) => {
      if (seq !== printSeq) return;                         // 새 출력이 시작되면 이전 시퀀스는 중단
      if (i >= STAGES.length) { finish(); return; }
      const [cls, ms, label] = STAGES[i];
      clear(); void note.offsetWidth; note.classList.add(cls); $("#printerState").textContent = label;
      if (cls !== "feeding") printer.classList.remove("busy");
      printGuard = setTimeout(() => run(i + 1), ms + 40);
    };
    clearTimeout(printGuard);
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) finish(); else run(0);
  }
  function renderPassRail(scenes) {
    const rail = $("#passrail"); rail.innerHTML = "";
    const dated = scenes.filter((s) => s.date || (s.window && s.window[0])); if (!dated.length) return;
    const t = (s) => new Date(s.date || s.window[0]).getTime(); const t0 = Math.min(...dated.map(t)), t1 = Math.max(...dated.map(t)); const span = Math.max(1, t1 - t0);
    let prevX = -1e9; const railW = rail.clientWidth || 800;
    dated.sort((a, b) => t(a) - t(b)).forEach((s) => { const x = 2 + 94 * (t(s) - t0) / span; const px = x / 100 * railW; const alt = px - prevX < 96; if (!alt) prevX = px;
      rail.insertAdjacentHTML("beforeend", `<div class="tick ${s.date ? "" : "miss"}${alt ? " alt" : ""}" style="left:${x}%">${s.date || "미관측"}<small>${s.label ?? s.year ?? ""}</small></div>`); });
  }
  function renderChart(series) {
    const labels = series.map((s) => s.date || s.label);
    const data = { labels, datasets: [
      { label: "피해지 중앙값", data: series.map((s) => s.burned.median), borderColor: "#8a5a1e", backgroundColor: "#8a5a1e", tension: .25, pointRadius: 3.5, borderWidth: 2 },
      { label: "피해지 사분위", data: series.map((s) => s.burned.q75), borderColor: "transparent", backgroundColor: "rgba(138,90,30,.16)", fill: "+1", pointRadius: 0, tension: .25 },
      { label: "", data: series.map((s) => s.burned.q25), borderColor: "transparent", backgroundColor: "rgba(138,90,30,.16)", pointRadius: 0, tension: .25 },
      { label: "대조지 중앙값", data: series.map((s) => s.control.median), borderColor: "#2f7d4f", backgroundColor: "#2f7d4f", borderDash: [4, 3], tension: .25, pointRadius: 3.5, pointStyle: "rect", borderWidth: 1.6 },
    ] };
    if (state.chart) state.chart.destroy();
    Chart.defaults.font.family = '"Barlow Condensed", Pretendard, sans-serif'; Chart.defaults.color = "#3a3a3a";
    state.chart = new Chart($("#chart"), { type: "line", data, options: { animation: { duration: 350 }, plugins: { legend: { labels: { filter: (l) => l.text !== "", boxWidth: 9, boxHeight: 9, font: { size: 11 } } } },
      scales: { y: { min: 0, max: 1, grid: { color: "rgba(20,20,20,.12)" }, ticks: { font: { size: 10 } }, title: { display: true, text: "NDVI", font: { size: 10 } } }, x: { grid: { color: "rgba(20,20,20,.08)" }, ticks: { font: { size: 10 } } } } } });
    $("#ratioStrip").innerHTML = series.map((s) => `<div class="ratio">${s.label}<b>${s.recovery_ratio == null ? "—" : s.recovery_ratio.toFixed(2)}</b></div>`).join("");
  }
  function renderSeverity(sev) {
    const max = Math.max(...sev.map((s) => s.ha), 1);
    $("#severityTable").innerHTML = `<tr><th>등급</th><th class="num">면적</th></tr>` + sev.map((s, i) => `<tr><td><span class="sev-swatch" style="background:${SEV_COLORS[i]}"></span>${s.label}<div class="sev-bar"><i style="--w:${s.ha / max}"></i></div></td><td class="num">${s.ha.toLocaleString("ko-KR")} ha</td></tr>`).join("");
    requestAnimationFrame(() => document.querySelectorAll(".sev-bar i").forEach((i) => (i.style.transform = `scaleX(${i.style.getPropertyValue("--w")})`)));
  }

  // ---------- 검증 잡 ----------
  $("#btnVerify").addEventListener("click", async () => {
    const mod = state.card.modules[0].module;
    const res = await fetch(`/api/projects/${state.current}/verify/${mod}`, { method: "POST" });
    const r = await res.json().catch(() => ({}));
    if (!res.ok || !r.data) { toast(r.warnings?.[0] || `재검정 요청 실패 (${res.status})`); return; }   // 배포본(읽기 전용)은 503 + 안내문
    toast(r.warnings?.[0] || "검정을 시작했습니다. 장면 수에 따라 수 분 걸립니다."); watchJob(r.data.id);
  });
  function watchJob(jobId) {
    $("#jobBar").hidden = false; $("#btnVerify").disabled = true;
    const tick = async () => {
      const j = (await api(`/api/jobs/${jobId}`)).data; const pr = j.progress || {};
      $("#jobFill").style.transform = `scaleX(${pr.total ? pr.done / pr.total : 0.08})`;
      $("#jobText").textContent = `${VERDICT[j.status] || j.status} · ${pr.message || ""}${pr.total ? ` (${pr.done}/${pr.total})` : ""}`;
      if (!["queued", "running"].includes(j.status)) {
        clearInterval(state.poll); state.poll = null;
        toast(j.status === "failed" ? `실패: ${j.error}` : `검정 완료 · ${VERDICT[j.summary?.verdict] || j.status}`);
        setTimeout(() => { $("#jobBar").hidden = true; }, 1200);
        await loadProjects(); await selectProject(state.current);
      }
    };
    if (state.poll) clearInterval(state.poll); state.poll = setInterval(tick, 2500); tick();
  }

  // ---------- 채팅(chat.js)에 노출하는 화면 상태 ----------
  window.AR = { getState: () => ({ current: state.current, card: state.card, overlay: state.overlay }), selectProject, setOverlay };

  // ---------- 달력·키 ----------
  async function loadCalendar() {
    const r = await api("/api/calendar"); const items = r.data; const next = items.slice().sort((a, b) => a.days_left - b.days_left)[0];
    $("#deadlineNext").textContent = next.name; $("#deadlineSub").textContent = `${next.due} · D-${next.days_left}`;
    $("#calendarTable").innerHTML = `<tr><th>항목</th><th class="num">기한</th><th class="num">D-day</th><th>근거</th><th>납품물</th></tr>` + items.map((i) => `<tr><td>${i.name}</td><td class="num">${i.due}</td><td class="num">D-${i.days_left}</td><td><span class="sub">${i.basis}</span></td><td>${i.deliverable}</td></tr>`).join("");
  }
  async function loadKeys() {
    const r = await api("/api/health"); const keys = r.data.keys;
    const DESC = { GEMINI_API_KEY: "설명 에이전트(Gemini)", DATA_GO_KR_SERVICE_KEY: "건축물대장 표제부(노후도·구조)", SGIS_CONSUMER_KEY: "SGIS 인증 키", SGIS_CONSUMER_SECRET: "SGIS 시크릿", VWORLD_API_KEY: "브이월드 건물 WFS", KMA_APIHUB_KEY: "기상청 API허브(강우·기온)", SAFETYDATA_SERVICE_KEY: "재난안전데이터 공유플랫폼", PC_SDK_SUBSCRIPTION_KEY: "Planetary Computer 구독키(선택)" };
    $("#keyChips").innerHTML = Object.entries(keys).filter(([k]) => !k.includes("SECRET")).map(([k, v]) => `<span class="chip ${v ? "on" : ""}">${k.replace(/_API_KEY|_SERVICE_KEY|_CONSUMER_KEY|_SDK_SUBSCRIPTION_KEY/, "")}</span>`).join("");
    $("#keysTable").innerHTML = `<tr><th>키</th><th>용도</th><th>상태</th></tr>` + Object.entries(keys).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${DESC[k] || ""}</td><td><span class="mark ${v ? "detected" : "waiting_input"}">${v ? "설정됨" : "비어 있음 · 키 필요"}</span></td></tr>`).join("");
  }
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("is-active", x === b));
    const v = b.dataset.view; $("#viewDashboard").hidden = v !== "dashboard"; $("#viewCalendar").hidden = v !== "calendar"; $("#viewKeys").hidden = v !== "keys";
    if (v === "dashboard") setTimeout(() => map.resize(), 50);
  }));
  let toastTimer; function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false; t.classList.remove("hide"); clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.classList.add("hide"); setTimeout(() => (t.hidden = true), 220); }, 3600); }

  (async () => {
    try { await Promise.all([loadProjects(), loadCalendar(), loadKeys()]); const first = state.projects.find((p) => p.results?.fire) || state.projects[0]; if (first) selectProject(first.id); }
    catch (e) { toast(`초기화 실패: ${e.message}`); }
  })();
})();
