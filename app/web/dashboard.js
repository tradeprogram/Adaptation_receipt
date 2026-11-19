/* 적응 영수증 — 도엽형 대시보드. 빌드 없이 동작하는 단일 스크립트 */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const api = async (path, opt) => { const r = await fetch(path, opt); if (!r.ok) throw new Error(`${r.status} ${path}`); return r.json(); };
  const TYPE_LABEL = { fire: "산불 피해지 복원", heat: "옥상 차열(열 저감)", flood: "배수 정비(침수 방재)" };
  const TYPE_CODE = { fire: "FIRE", heat: "HEAT", flood: "FLOOD" };
  // 화면에는 쉬운 말만 적는다. 기술 용어(이중차분, dNBR 등)는 '자세한 수치와 근거'와 JSON에 남긴다
  const VERDICT = { detected: "효과 확인", recovered: "회복 수준 도달", gap_remaining: "회복 미달", reduced: "침수 저감 확인", not_reduced: "침수 저감 미확인", undetected: "효과 미확인", unmeasured: "측정 불가", ready: "비교 가능", waiting: "관측 대기", waiting_input: "입력 대기", not_run: "미검정", failed: "검정 실패", partial: "부분 완료", ok: "완료", done: "완료", queued: "대기", running: "진행" };
  const SRC = { OBSERVED: "실측", MODEL: "계산", RULE: "규칙", ASSUMPTION: "가정", FORECAST: "예보" };
  const OV_LABEL = { dnbr: "피해등급", pre: "산불 전", post: "진화 직후", lst_before: "시공 전 온도", lst_after: "시공 후 온도", lst_diff: "전후 차이", flood_before: "정비 전 침수", flood_after: "정비 후 침수", flood_change: "전후 비교", none: "없음" };
  const PAIRS = [["pre", "post", "산불 전", "진화 직후"], ["lst_before", "lst_after", "시공 전", "시공 후"], ["flood_before", "flood_after", "정비 전", "정비 후"]];
  const SEV_COLORS = ["#f7e26b", "#f29e2e", "#d7301f", "#7a0177"];
  const AGING_STOPS = ["#f6f1e4", "#e9cf9c", "#cf9a5a", "#9a6421", "#5a3412"];
  OV_LABEL.aging = "읍면 고령화";
  // 지표 장부의 항목 이름. 키는 JSON(재현용)에 남고 화면에는 한글만 적는다
  const KEY_LABEL = {
    burned_forest_ha: "피해 산림 면적", control_ha: "비교 구역(주변 숲) 면적", recovery_ratio_latest: "회복률(피해지 ÷ 주변 숲)", did_effect_ndvi: "주변 숲 대비 변화(식생지수)", ci95_median_diff: "오차 범위(95%)", mde_ndvi: "알아볼 수 있는 최소 변화(식생지수)", valid_pct_min: "구름 없는 화소 비율(최소)",
    did_effect_lst_c: "비교 동 대비 온도 변화", medians: "구역별 낮 지표면 온도", ci95: "오차 범위(95%)", mde_c: "알아볼 수 있는 최소 온도 변화", scenes_used: "사용한 위성 사진 수", treated_area_ha: "시공 면적", area_for_mde_1c_ha: "1℃ 변화를 알아보려면 필요한 면적", area_for_mde_05c_ha: "0.5℃ 변화를 알아보려면 필요한 면적", shelters_in_aoi: "구역 안 무더위쉼터", shelter_capacity_in_aoi: "쉼터 수용 인원",
    events_total: "호우 횟수", grade_counts: "위성이 제때 찍은 횟수(등급별)", stage2_ready: "정비 전후 비교 가능", flooded_ha_before: "정비 전 침수 면적", flooded_ha_after: "정비 후 침수 면적", flooded_change_ha: "침수 면적 변화", flooded_change_pct: "침수 면적 변화율", flooded_ha_per_mm_before: "정비 전 비 1 mm당 침수", flooded_ha_per_mm_after: "정비 후 비 1 mm당 침수", flooded_change_pct_rain_adjusted: "비의 세기를 감안한 변화율",
    old_building_share: "30년 넘은 건물 비율", median_building_age: "건물 나이(중간값)", households_total: "세대 수", jurisdiction_oldage_support: "관할 노년부양비", jurisdiction_aging_index: "관할 고령화지수",
  };
  const SUB_LABEL = { treat_pre: "시공 전", treat_post: "시공 후", ctrl_pre: "대조 전", ctrl_post: "대조 후", A: "A등급", B: "B등급", C: "C등급" };
  const label = (k, row) => row?.label || KEY_LABEL[k] || k;
  const state = { projects: [], current: null, card: null, cards: {}, overlay: "dnbr", chart: null, poll: null, compare: false, loading: 0, reg: null };
  const legendOf = (mod, key) => { const L = mod?.overlays?.legend?.[key]; return typeof L === "string" ? { label: OV_LABEL[key] || key, type: "text", text: L } : L; };
  const ovLabel = (mod, key) => legendOf(mod, key)?.label || OV_LABEL[key] || key;
  const OV_META = new Set(["bounds", "legend", "default", "focus", "focus_share", "opacity"]);
  const ovKeys = (mod) => Object.keys(mod?.overlays || {}).filter((k) => !OV_META.has(k));
  const mainKeys = (mod) => ovKeys(mod).filter((k) => { const L = legendOf(mod, k); return !(L?.event || L?.series); });
  const eventKeys = (mod) => ovKeys(mod).filter((k) => legendOf(mod, k)?.event);
  // 시간 순 프레임: 호우 사건(침수) 또는 장면별 NDVI(산불). 라벨의 날짜로 정렬한다
  const frameKeys = (mod) => ovKeys(mod).filter((k) => { const L = legendOf(mod, k); return L?.event || L?.series; }).sort((a, b) => String(legendOf(mod, a).date || legendOf(mod, a).label).localeCompare(String(legendOf(mod, b).date || legendOf(mod, b).label)));

  // ---------- 지면(지도) ----------
  const STYLE = "https://tiles.openfreemap.org/styles/liberty";
  const map = new maplibregl.Map({ container: "map", style: STYLE, center: [127.8, 36.4], zoom: 6.3, maxPitch: 70, attributionControl: { compact: true }, canvasContextAttributes: { preserveDrawingBuffer: true, antialias: true } });
  map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
  // 3D 지형: AWS 공개 지형 타일(terrarium, 키 불필요). 같은 버킷의 주소 셋으로 나눠 동시 요청 수를 늘린다
  const TERRAIN = { type: "raster-dem", tiles: ["https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png", "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png", "https://elevation-tiles-prod.s3.us-east-1.amazonaws.com/terrarium/{z}/{x}/{y}.png"], tileSize: 256, encoding: "terrarium", maxzoom: 15, attribution: "Terrain: Mapzen, AWS" };
  const EXAGG = 1.2, PITCH3D = 58, BEARING3D = -18;
  const is3D = () => $("#btn3d").getAttribute("aria-pressed") === "true";
  // 종이 세계관의 하늘: 회청색 하늘, 종이빛 지평선과 안개, 오후의 낮은 햇빛(건물 옆면에 음영)
  const dressMap = (m, buildings = true) => {
    if (!m.getSource("terrain")) m.addSource("terrain", TERRAIN);
    if (!m.getSource("terrain-hs")) m.addSource("terrain-hs", TERRAIN);   // 음영기복은 별도 소스(같은 소스를 쓰면 품질 경고)
    if (!m.getLayer("hills")) m.addLayer({ id: "hills", type: "hillshade", source: "terrain-hs", paint: { "hillshade-exaggeration": 0.55, "hillshade-shadow-color": "#3b2f22", "hillshade-highlight-color": "#fffaf0", "hillshade-accent-color": "#5a4a3a" } }, m.getLayer("aoi-fill") ? "aoi-fill" : firstSymbolLayer(m));
    if (buildings && !m.getLayer("bld-3d") && m.getSource("openmaptiles")) m.addLayer({ id: "bld-3d", type: "fill-extrusion", source: "openmaptiles", "source-layer": "building", minzoom: 13, paint: { "fill-extrusion-color": "#efe9dc", "fill-extrusion-height": ["coalesce", ["get", "render_height"], 6], "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0], "fill-extrusion-opacity": 0.92 } }, firstSymbolLayer(m));
    m.setSky({ "sky-color": "#8fa9c7", "horizon-color": "#e9e3d5", "fog-color": "#efe9dc", "fog-ground-blend": 0.55, "horizon-fog-blend": 0.7, "sky-horizon-blend": 0.6, "atmosphere-blend": 0.5 });
    m.setLight({ anchor: "viewport", color: "#fff4e0", intensity: 0.45, position: [1.15, 210, 40] });
  };
  const apply3D = (m, on) => { m.setTerrain(on ? { source: "terrain", exaggeration: EXAGG } : null); for (const id of ["hills", "bld-3d", "tc-3d"]) if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", on ? "visible" : "none"); };
  const camOpts = () => (is3D() ? { pitch: PITCH3D, bearing: BEARING3D } : { pitch: 0, bearing: 0 });
  const SAT = { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, attribution: "Esri World Imagery" };
  const firstSymbolLayer = (m) => (m.getStyle().layers.find((l) => l.type === "symbol") || {}).id;
  const bboxPoly = (b) => ({ type: "Polygon", coordinates: [[[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]], [b[0], b[1]]]] });
  // 지명을 한글 우선으로: OpenMapTiles의 name:ko가 있으면 쓰고 없으면 현지명
  const koreanize = (m) => { for (const l of m.getStyle().layers) { if (l.type === "symbol" && l.layout && l.layout["text-field"]) { try { m.setLayoutProperty(l.id, "text-field", ["coalesce", ["get", "name:ko"], ["get", "name"]]); } catch (e) { /* 스타일 표현식이 다른 층은 건너뛴다 */ } } } };
  const addOverlayTo = (m, id, url, b, opacity) => {
    if (m.getLayer(id)) { m.removeLayer(id); m.removeSource(id); }
    m.addSource(id, { type: "image", url, coordinates: [[b[0], b[3]], [b[2], b[3]], [b[2], b[1]], [b[0], b[1]]] });
    m.addLayer({ id, type: "raster", source: id, paint: { "raster-opacity": opacity, "raster-fade-duration": 120, "raster-resampling": "nearest" } }, m.getLayer("aoi-fill") ? "aoi-fill" : firstSymbolLayer(m));
  };
  map.on("load", () => {
    koreanize(map);
    map.addSource("sat", SAT);
    map.addLayer({ id: "sat", type: "raster", source: "sat", layout: { visibility: document.querySelector("[data-base].is-active")?.dataset.base === "sat" ? "visible" : "none" } }, firstSymbolLayer(map));
    map.addSource("aois", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "aoi-fill", type: "fill", source: "aois", paint: { "fill-color": "#141414", "fill-opacity": 0.04 } });
    map.addLayer({ id: "aoi-line", type: "line", source: "aois", paint: { "line-color": "#141414", "line-width": 1, "line-dasharray": [4, 3] } });
    map.addLayer({ id: "aoi-active", type: "line", source: "aois", filter: ["==", ["get", "id"], ""], paint: { "line-color": "#141414", "line-width": 2 } });
    // 사업별 부가 레이어: 처리(시공)·대조 폴리곤, 무더위쉼터, 기상 관측소
    map.addSource("tc", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "tc-fill", type: "fill", source: "tc", paint: { "fill-color": ["match", ["get", "role"], "treated", "#8a5a1e", "#2f7d4f"], "fill-opacity": 0.18 } });
    map.addLayer({ id: "tc-line-t", type: "line", source: "tc", filter: ["==", ["get", "role"], "treated"], paint: { "line-color": "#8a5a1e", "line-width": 2.2 } });
    map.addLayer({ id: "tc-line-c", type: "line", source: "tc", filter: ["==", ["get", "role"], "control"], paint: { "line-color": "#2f7d4f", "line-width": 1.6, "line-dasharray": [3, 2] } });
    // 시공·대조 동을 층수 곱하기 3 m로 세워 올린다(건축물대장 층수)
    map.addLayer({ id: "tc-3d", type: "fill-extrusion", source: "tc", paint: { "fill-extrusion-color": ["match", ["get", "role"], "treated", "#8a5a1e", "#2f7d4f"], "fill-extrusion-height": ["*", ["coalesce", ["get", "floors"], 4], 3], "fill-extrusion-opacity": 0.82 } });
    dressMap(map); apply3D(map, is3D());
    map.addSource("pts", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "pts-halo", type: "circle", source: "pts", paint: { "circle-radius": ["match", ["get", "kind"], "station", 9, 7], "circle-color": "#fbfaf6", "circle-opacity": 0.9 } });
    map.addLayer({ id: "pts", type: "circle", source: "pts", paint: { "circle-radius": ["match", ["get", "kind"], "station", 5, 4.2], "circle-color": ["match", ["get", "kind"], "station", "#141414", "#1f5aa0"], "circle-stroke-color": "#fbfaf6", "circle-stroke-width": 1.2 } });
    map.on("click", (e) => {
      if (state.reg?.pick) { pickBuilding(e); return; }
      if (state.reg?.drawing) return;
      const hit = map.queryRenderedFeatures(e.point, { layers: ["pts", "aoi-fill"] });
      const pt = hit.find((f) => f.layer.id === "pts");
      if (pt) { popup.setLngLat(pt.geometry.coordinates).setHTML(pt.properties.html).addTo(map); return; }
      const aoi = hit.find((f) => f.layer.id === "aoi-fill");
      if (aoi && aoi.properties.id !== state.current) { selectProject(aoi.properties.id); return; }
      queryPixel(e.lngLat);
    });
    map.on("mousemove", (e) => {
      const hit = map.queryRenderedFeatures(e.point, { layers: ["pts", "aoi-fill"] });
      map.getCanvas().style.cursor = hit.some((f) => f.layer.id === "pts" || f.properties.id !== state.current) ? "pointer" : (state.overlay !== "none" && state.card ? "crosshair" : "");
      $("#cursorPos").textContent = `${e.lngLat.lat.toFixed(4)}°N ${e.lngLat.lng.toFixed(4)}°E`;
    });
    map.on("mouseout", () => { $("#cursorPos").textContent = ""; });
    drawAois(); updateMarginalia();
  });
  const popup = new maplibregl.Popup({ closeButton: true, maxWidth: "280px" });
  map.on("moveend", updateMarginalia); map.on("resize", updateMarginalia);
  // 지면 크기가 바뀌면(글꼴·채팅 로드로 격자 재배치) 현재 도엽 범위로 다시 맞춘다
  let fitTimer = null;
  new ResizeObserver(() => { if (!state.focusBbox) return; clearTimeout(fitTimer); fitTimer = setTimeout(() => { map.resize(); if (mapB) mapB.resize(); const b = state.focusBbox; flyToBbox(b, 300); }, 120); }).observe(document.querySelector(".plate"));
  // 사업 범위가 화면을 채우도록 맞춘다. 도구막대(위)와 타임라인·범례(아래) 자리만 비우고, 기울인 카메라는 범위가 사다리꼴로 느슨하게 잡히므로 한 단계 더 당긴다
  function flyToBbox(b, duration) {
    const cam = map.cameraForBounds([[b[0], b[1]], [b[2], b[3]]], { padding: { top: 64, bottom: 96, left: 28, right: 28 }, ...camOpts() });
    if (!cam) return;
    if (is3D()) cam.zoom += 0.3;
    map.easeTo({ ...cam, ...camOpts(), duration, essential: true });
  }
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
  function drawExtras(p, card) {
    if (!map.getSource("tc")) { map.once("load", () => drawExtras(p, card)); return; }
    const g = card?.project?.geometry || {}; const feats = [];
    (g.treated || []).forEach((f) => feats.push({ type: "Feature", properties: { role: "treated", floors: f.properties?.floors }, geometry: f.geometry || f }));
    (g.control || []).forEach((f) => feats.push({ type: "Feature", properties: { role: "control", floors: f.properties?.floors }, geometry: f.geometry || f }));
    map.getSource("tc").setData({ type: "FeatureCollection", features: feats });
    const mod = card?.modules?.[0] || {}; const pts = [];
    (mod.shelters || []).forEach((s) => pts.push({ type: "Feature", properties: { kind: "shelter", html: `<b>${s.name}</b><span class="sub">${s.addr || ""}</span>무더위쉼터, 이용 가능 ${s.capacity ?? "—"}명` }, geometry: { type: "Point", coordinates: [s.lon, s.lat] } }));
    const st = card?.project?.kma_station; if (st && st.lon) {
      const evs = (mod.events || []).filter((e) => e.rain).map((e) => `${(e.rain.peak_kst || e.event_peak).slice(0, 10)}: 1시간 ${e.rain.peak_rn} mm, 3시간 ${e.rain.max_3h} mm`).join("<br>");
      pts.push({ type: "Feature", properties: { kind: "station", html: `<b>기상청 ${st.name} 관측소 (${st.stn})</b><span class="sub">호우 사건을 뽑은 시간강우 지점</span>${evs}` }, geometry: { type: "Point", coordinates: [st.lon, st.lat] } });
    }
    map.getSource("pts").setData({ type: "FeatureCollection", features: pts });
    const ex = card?.exposure;
    if (ex) {
      if (!map.getSource("expo")) {
        map.addSource("expo", { type: "geojson", data: ex.geojson });
        map.addLayer({ id: "expo-fill", type: "fill", source: "expo", layout: { visibility: "none" }, paint: { "fill-color": ["interpolate", ["linear"], ["get", "aged_idx"], 300, AGING_STOPS[0], 850, AGING_STOPS[1], 1400, AGING_STOPS[2], 1950, AGING_STOPS[3], 2500, AGING_STOPS[4]], "fill-opacity": 0.62 } }, "tc-fill");
        map.addLayer({ id: "expo-line", type: "line", source: "expo", layout: { visibility: "none" }, paint: { "line-color": "#ffffff", "line-width": 1.1, "line-opacity": 0.9 } }, "tc-fill");
      } else map.getSource("expo").setData(ex.geojson);
    } else if (map.getSource("expo")) map.getSource("expo").setData({ type: "FeatureCollection", features: [] });
  }

  // ---------- 오버레이·범례 ----------
  function setOverlay(name) {
    state.overlay = name;
    if (!map.getLayer("aoi-fill")) { map.once("load", () => setOverlay(name)); return; }
    if (map.getLayer("overlay")) { map.removeLayer("overlay"); map.removeSource("overlay"); }
    const mod = state.card?.modules?.find((m) => m.overlays);
    renderLegend(mod, name);
    document.querySelectorAll("#overlaySeg [data-ov]").forEach((x) => x.classList.toggle("is-active", x.dataset.ov === name));
    document.querySelectorAll("#timeline .frame").forEach((x) => x.classList.toggle("is-active", x.dataset.ov === name));
    const Lcur = legendOf(mod, name); if (Lcur?.date) highlightSeries(Lcur.date);
    if (state.compare) { disableCompare(false); }
    if (map.getLayer("expo-fill")) map.setLayoutProperty("expo-fill", "visibility", name === "aging" ? "visible" : "none");
    if (map.getLayer("expo-line")) map.setLayoutProperty("expo-line", "visibility", name === "aging" ? "visible" : "none");
    if (!mod || name === "none" || !mod.overlays[name]) return;
    addOverlayTo(map, "overlay", mod.overlays[name] + "?t=" + Date.now(), mod.overlays.bounds, +$("#opacity").value / 100);
  }
  function renderLegend(mod, key) {
    const box = $("#legend"); const L = key === "aging" ? { label: "읍면 고령화지수", type: "ramp", min: 300, max: 2500, unit: "", stops: AGING_STOPS, note: "65세 이상 인구 ÷ 0~14세 인구 × 100, 통계청 SGIS 2023. 읍면을 누르면 피해·침수 면적 표시" } : legendOf(mod, key);
    if (!L || key === "none") { box.hidden = true; return; }
    let body = "";
    if (L.type === "classes") body = `<div class="lg-items">${L.items.map((i) => `<span class="lg-item"><i class="sw" style="background:${i.c}"></i>${i.t}</span>`).join("")}</div>`;
    else if (L.type === "ramp") body = `<div class="ramp" style="background:linear-gradient(90deg,${L.stops.join(",")})"></div><div class="ramp-ticks"><span>${L.min}${L.unit || ""}</span><span>${((L.min + L.max) / 2).toFixed(L.unit === "℃" || Math.abs(L.max) >= 100 ? 0 : 1)}${L.unit || ""}</span><span>${L.max}${L.unit || ""}</span></div>`;
    else body = L.text ? `<span class="lg-note" style="margin-top:0">${L.text}</span>` : "";
    box.innerHTML = `<span class="lg-title">${L.label || OV_LABEL[key] || key}</span>${body}${L.note ? `<span class="lg-note">${L.note}</span>` : ""}`;
    box.hidden = false;
  }
  function syncOverlayUI(mod) {
    const keys = mainKeys(mod), evs = eventKeys(mod); const seg = $("#overlaySeg"); const has = keys.length > 0;
    seg.hidden = !has; $("#opacityWrap").hidden = !has; $("#mapActions").hidden = !has;
    if (has && mod.overlays.opacity != null) $("#opacity").value = Math.round(mod.overlays.opacity * 100);
    if (!has) { if (map.getLayer("overlay")) { map.removeLayer("overlay"); map.removeSource("overlay"); } $("#legend").hidden = true; return; }
    if (!ovKeys(mod).includes(state.overlay) && state.overlay !== "none") state.overlay = (mod.overlays.default && keys.includes(mod.overlays.default)) ? mod.overlays.default : keys[0];
    if (state.card?.exposure) keys.push("aging");
    seg.innerHTML = [...keys, "none"].map((k) => `<button class="seg-btn${k === state.overlay ? " is-active" : ""}" data-ov="${k}">${ovLabel(mod, k)}</button>`).join("");
    $("#btnCompare").hidden = !PAIRS.some((pr) => mod.overlays[pr[0]] && mod.overlays[pr[1]]);
    renderTimeline(mod);
  }
  // ---------- 시간 순 재생(호우 사건, 회복 시계열) ----------
  let playTimer = null;
  function renderTimeline(mod) {
    const frames = frameKeys(mod); const tl = $("#timeline"); stopPlay();
    tl.hidden = !frames.length; $("#btnPlay").hidden = !frames.length; if (!frames.length) { tl.innerHTML = ""; return; }
    const isEvt = !!legendOf(mod, frames[0]).event;
    tl.innerHTML = `<span class="tl-title">${isEvt ? "호우 사건" : "회복 시계열"}</span><div class="tl-track">` + frames.map((k) => { const L = legendOf(mod, k); const ph = isEvt ? (L.note || "").slice(0, 4) : ""; return `<button class="frame${k === state.overlay ? " is-active" : ""}" data-ov="${k}" title="${L.note || ""}"><i></i><span class="d">${L.date || L.label}</span><span class="s">${isEvt ? ph : (L.label || "").replace(/^\S+\s*/, "")}</span></button>`; }).join("") + `</div>`;
    tl.querySelectorAll(".frame").forEach((b) => b.addEventListener("click", () => { stopPlay(); setOverlay(b.dataset.ov); }));
  }
  function stopPlay() { if (playTimer) { clearInterval(playTimer); playTimer = null; } $("#btnPlay").setAttribute("aria-pressed", "false"); $("#btnPlay").textContent = "재생"; }
  $("#btnPlay").addEventListener("click", () => {
    if (playTimer) { stopPlay(); return; }
    const mod = state.card?.modules?.find((m) => m.overlays); const frames = frameKeys(mod); if (!frames.length) return;
    let i = Math.max(0, frames.indexOf(state.overlay)); if (i === frames.length - 1 || frames.indexOf(state.overlay) < 0) i = -1;
    const step = () => { i = (i + 1) % frames.length; setOverlay(frames[i]); if (i === frames.length - 1) { setTimeout(stopPlay, 2400); } };
    $("#btnPlay").setAttribute("aria-pressed", "true"); $("#btnPlay").textContent = "정지"; step(); playTimer = setInterval(step, 2400);
  });
  // 회복 단면도에서 해당 날짜 점을 키운다
  function highlightSeries(date) {
    const mod = state.card?.modules?.[0]; if (!state.chart || !mod?.series) return;
    const idx = mod.series.findIndex((x) => x.date === date);
    state.chart.data.datasets.forEach((d, di) => { if (di === 0 || di === 3) d.pointRadius = mod.series.map((_, k) => (k === idx ? 7 : 3.5)); }); state.chart.update("none");
    $("#passrail").querySelectorAll(".tick").forEach((x) => x.classList.toggle("is-active", x.dataset.date === date));
  }
  $("#overlaySeg").addEventListener("click", (e) => { const b = e.target.closest("[data-ov]"); if (!b) return; stopPlay(); setOverlay(b.dataset.ov); });
  document.querySelectorAll("[data-base]").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("[data-base]").forEach((x) => x.classList.toggle("is-active", x === b));
    map.setLayoutProperty("sat", "visibility", b.dataset.base === "sat" ? "visible" : "none");
    if (mapB && mapB.getLayer("sat")) mapB.setLayoutProperty("sat", "visibility", b.dataset.base === "sat" ? "visible" : "none");
  }));
  $("#btn3d").addEventListener("click", () => {
    const on = !is3D(); $("#btn3d").setAttribute("aria-pressed", String(on));
    apply3D(map, on); if (mapB && mapB.getSource("terrain")) apply3D(mapB, on);
    if (state.focusBbox) flyToBbox(state.focusBbox, 900); else map.easeTo({ ...camOpts(), duration: 900 });
  });
  $("#opacity").addEventListener("input", (e) => { const o = +e.target.value / 100; if (map.getLayer("overlay")) map.setPaintProperty("overlay", "raster-opacity", o); if (mapB && mapB.getLayer("overlayB")) mapB.setPaintProperty("overlayB", "raster-opacity", o); });

  // 클릭 지점의 값: 서버의 격자(layers.npz)에서 읽는다
  async function queryPixel(lngLat) {
    const mod = state.card?.modules?.find((m) => m.overlays); const key = state.overlay;
    if (key === "aging") {
      const f = map.queryRenderedFeatures(map.project(lngLat), { layers: ["expo-fill"] })[0]; if (!f) return; const q = f.properties; const lab = state.card.exposure.hazard_label;
      popup.setLngLat(lngLat).setHTML(`<b>${q.name}</b><span class="q-val">고령화지수 ${Math.round(q.aged_idx).toLocaleString("ko-KR")}</span><span class="sub">노년부양비 ${q.oldage}, 인구 ${Math.round(q.pop).toLocaleString("ko-KR")}</span><span class="sub">${lab} ${(+q.hazard_ha).toLocaleString("ko-KR")} ha, 읍면 면적의 ${q.hazard_pct_of_area}%</span>`).addTo(map); return;
    }
    if (!mod || key === "none" || !mod.overlays[key]) return;
    const L = legendOf(mod, key); const q = L?.query; if (!q) return;
    let r; try { r = (await api(`/api/projects/${state.current}/query?layer=${q}&lon=${lngLat.lng.toFixed(6)}&lat=${lngLat.lat.toFixed(6)}`)).data; } catch (e) { return; }
    if (!r.available || r.inside === false) return;
    let val;
    if (r.value == null) val = `<span class="q-val none">측정 불가</span><span class="sub">구름 마스킹 또는 범위 밖</span>`;
    else if (r.kind === "class") { const it = L.items?.[r.value - 1]; val = r.value === 0 || !it ? `<span class="q-val">해당 없음</span>` : `<span class="q-val"><i class="sw" style="display:inline-block;width:12px;height:12px;background:${it.c};border:1px solid rgba(20,20,20,.35);vertical-align:-1px;margin-right:6px"></i>${it.t}</span>`; }
    else val = `<span class="q-val">${r.value > 0 && L.min < 0 ? "+" : ""}${r.value}${L.unit || ""}</span>`;
    popup.setLngLat(lngLat).setHTML(`<b>${L.label || OV_LABEL[key]}</b>${val}<span class="sub">${lngLat.lat.toFixed(4)}°N ${lngLat.lng.toFixed(4)}°E</span>`).addTo(map);
  }

  // ---------- 전후 비교(좌우 가름) ----------
  let mapB = null, cmpPct = 50;
  const setCmp = (pct) => { cmpPct = Math.max(2, Math.min(98, pct)); $("#mapB").style.clipPath = `inset(0 0 0 ${cmpPct}%)`; $("#cmpHandle").style.left = `${cmpPct}%`; $("#cmpHandle").setAttribute("aria-valuenow", Math.round(cmpPct)); };
  function enableCompare() {
    const mod = state.card?.modules?.find((m) => m.overlays); const pr = PAIRS.find((x) => mod?.overlays[x[0]] && mod.overlays[x[1]]); if (!pr) return;
    state.compare = true; document.querySelector(".plate").classList.add("compare");
    $("#btnCompare").setAttribute("aria-pressed", "true"); $("#mapB").hidden = false; $("#cmp").hidden = false; $("#cmpA").textContent = pr[2]; $("#cmpB").textContent = pr[3];
    const o = +$("#opacity").value / 100; const b = mod.overlays.bounds;
    const place = () => { addOverlayTo(mapB, "overlayB", mod.overlays[pr[1]] + "?t=" + Date.now(), b, o); mapB.resize(); };
    if (!mapB) {
      mapB = new maplibregl.Map({ container: "mapB", style: STYLE, center: map.getCenter(), zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing(), maxPitch: 70, interactive: false, attributionControl: false, canvasContextAttributes: { preserveDrawingBuffer: true, antialias: true } });
      mapB.on("load", () => { koreanize(mapB); mapB.addSource("sat", SAT); mapB.addLayer({ id: "sat", type: "raster", source: "sat", layout: { visibility: map.getLayoutProperty("sat", "visibility") || "none" } }, firstSymbolLayer(mapB)); dressMap(mapB); apply3D(mapB, is3D()); place(); });
      map.on("move", () => { if (mapB) mapB.jumpTo({ center: map.getCenter(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch() }); });
    } else { mapB.jumpTo({ center: map.getCenter(), zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing() }); if (mapB.isStyleLoaded()) place(); else mapB.once("load", place); }
    if (map.getLayer("overlay")) { map.removeLayer("overlay"); map.removeSource("overlay"); }
    addOverlayTo(map, "overlay", mod.overlays[pr[0]] + "?t=" + Date.now(), b, o);
    state.overlay = pr[0]; document.querySelectorAll("#overlaySeg [data-ov]").forEach((x) => x.classList.toggle("is-active", x.dataset.ov === pr[0]));
    renderLegend(mod, pr[1].startsWith("lst") || pr[1].startsWith("flood") ? pr[1] : pr[0]);
    setCmp(50);
  }
  function disableCompare(restore = true) {
    state.compare = false; document.querySelector(".plate").classList.remove("compare");
    $("#btnCompare").setAttribute("aria-pressed", "false"); $("#mapB").hidden = true; $("#cmp").hidden = true;
    if (mapB && mapB.getLayer("overlayB")) { mapB.removeLayer("overlayB"); mapB.removeSource("overlayB"); }
    if (restore) setOverlay(state.overlay);
  }
  $("#btnCompare").addEventListener("click", () => (state.compare ? disableCompare() : enableCompare()));
  (() => {
    const h = $("#cmpHandle"); const plate = document.querySelector(".plate"); let drag = false;
    const pctOf = (x) => { const r = $("#map").getBoundingClientRect(); return (x - r.left) / r.width * 100; };
    h.addEventListener("pointerdown", (e) => { drag = true; h.setPointerCapture(e.pointerId); });
    h.addEventListener("pointermove", (e) => { if (drag) setCmp(pctOf(e.clientX)); });
    h.addEventListener("pointerup", () => { drag = false; }); h.addEventListener("pointercancel", () => { drag = false; });
    h.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") setCmp(cmpPct - 2); if (e.key === "ArrowRight") setCmp(cmpPct + 2); });
    plate.addEventListener("dblclick", () => { if (state.compare) setCmp(50); });
  })();

  // ---------- 지도 저장(PNG): 지도 + 범례 + 축척 + 제목 ----------
  function composeMap() {
    const src = map.getCanvas(); const W = src.width, H = src.height; const dpr = W / src.clientWidth;
    const c = document.createElement("canvas"); c.width = W; c.height = H + Math.round(120 * dpr); const g = c.getContext("2d");
    g.fillStyle = "#fbfaf6"; g.fillRect(0, 0, c.width, c.height);
    g.drawImage(src, 0, 0);
    if (state.compare && mapB) { const sb = mapB.getCanvas(); const x = Math.round(W * cmpPct / 100); g.drawImage(sb, x, 0, W - x, H, x, 0, W - x, H); g.fillStyle = "#141414"; g.fillRect(x - dpr, 0, 2 * dpr, H); }
    const mod = state.card?.modules?.find((m) => m.overlays); const L = legendOf(mod, state.overlay); const p = state.card?.project;
    const f = (px) => `${Math.round(px * dpr)}px Pretendard, "Malgun Gothic", sans-serif`;
    let y = H + 28 * dpr; g.fillStyle = "#141414"; g.font = `700 ${f(15)}`; g.fillText(`${p?.name || ""}`, 16 * dpr, y);
    g.font = f(12); g.fillStyle = "#3a3a3a"; g.fillText(`${L?.label || ""}  ${state.compare ? "전후 비교" : ""}  ${$("#scalebarText").textContent} 축척 막대 기준  ${new Date().toISOString().slice(0, 10)}`, 16 * dpr, y + 22 * dpr);
    y += 48 * dpr; let x = 16 * dpr;
    if (L?.type === "classes") { for (const it of L.items) { g.fillStyle = it.c; g.fillRect(x, y - 10 * dpr, 16 * dpr, 11 * dpr); g.strokeStyle = "rgba(20,20,20,.4)"; g.strokeRect(x, y - 10 * dpr, 16 * dpr, 11 * dpr); g.fillStyle = "#141414"; g.font = f(12); g.fillText(it.t, x + 22 * dpr, y); x += (28 + g.measureText(it.t).width / dpr + 14) * dpr; } }
    else if (L?.type === "ramp") { const gr = g.createLinearGradient(x, 0, x + 220 * dpr, 0); L.stops.forEach((s, i) => gr.addColorStop(i / (L.stops.length - 1), s)); g.fillStyle = gr; g.fillRect(x, y - 10 * dpr, 220 * dpr, 11 * dpr); g.strokeStyle = "rgba(20,20,20,.4)"; g.strokeRect(x, y - 10 * dpr, 220 * dpr, 11 * dpr); g.fillStyle = "#141414"; g.font = f(12); g.fillText(`${L.min}${L.unit || ""}`, x, y + 16 * dpr); g.fillText(`${L.max}${L.unit || ""}`, x + 200 * dpr, y + 16 * dpr); }
    g.fillStyle = "#6e6a62"; g.font = f(10); g.fillText("적응 영수증, OpenFreeMap © OpenMapTiles, OpenStreetMap, Esri World Imagery, Mapzen terrain, Copernicus Sentinel, USGS Landsat", 16 * dpr, c.height - 10 * dpr);
    return { canvas: c, caption: `${p?.name || ""}. ${L?.label || ""}${state.compare ? ", 전후 비교" : ""}${is3D() ? ", 3D 지형" : ""}. ${new Date().toISOString().slice(0, 10)} 화면 갈무리` };
  }
  $("#btnExport").addEventListener("click", () => {
    const { canvas: c } = composeMap();
    const a = document.createElement("a"); a.download = `adaptation-receipt_${state.current}_${state.overlay}.png`; a.href = c.toDataURL("image/png"); a.click();
  });
  // 카드 인쇄: 지금 보이는 지면 장면을 인쇄 카드에 싣는다(브라우저 저장소 + 서버가 쓰기 가능하면 결과 폴더)
  $("#btnLink").addEventListener("click", async () => {
    if (!state.current) return; const url = `${location.origin}/card/${state.current}`;
    try { await navigator.clipboard.writeText(url); toast(`공개 카드 주소 복사: ${url}`); } catch (e) { toast(url); }
  });
  $("#btnCard").addEventListener("click", () => {
    if (!state.card) return;
    try {
      const { canvas: c, caption } = composeMap(); const img = c.toDataURL("image/jpeg", 0.82);
      try { localStorage.setItem(`ar-snap-${state.current}`, JSON.stringify({ img, caption, at: new Date().toISOString() })); } catch (e) { /* 저장소 한도 초과 시 서버 저장만 */ }
      fetch(`/api/projects/${state.current}/snapshot`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ image: img, caption }) }).catch(() => {});
    } catch (e) { /* 장면 없이 인쇄 */ }
  });

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
  const setLoading = (on) => { state.loading += on ? 1 : -1; $("#mapLoading").hidden = state.loading <= 0; };
  async function selectProject(id) {
    state.current = id;
    document.querySelectorAll(".index-tile").forEach((b) => b.classList.toggle("is-active", b.dataset.id === id));
    const p = state.projects.find((x) => x.id === id);
    const focus = () => { map.resize(); map.setFilter("aoi-active", ["==", ["get", "id"], id]); flyToBbox(p.bbox, 1400); };
    if (p) { state.focusBbox = p.bbox; if (map.getLayer("aoi-active")) focus(); else map.once("load", focus); }
    if (state.compare) disableCompare(false);
    setLoading(true); $("#cardEmpty").hidden = false; $("#cardEmpty p").textContent = "성과 카드를 불러오는 중"; $("#card").hidden = true;
    try {
      const r = await api(`/api/projects/${id}/card`); if (state.current !== id) return;
      state.card = r.data; renderCard(); setOverlay(state.overlay); drawExtras(p, state.card);
      // 침수처럼 결과가 범위의 일부에만 있으면 그곳으로 카메라를 보낸다
      const ov0 = state.card.modules?.[0]?.overlays; const fb = ov0?.focus; if (fb) { state.focusBbox = fb; flyToBbox(fb, 1200); if (ov0.focus_share) toast(`침수 밀집 구역으로 확대, 전체 침수의 ${Math.round(ov0.focus_share * 100)}%. 전체 범위는 축소해 확인`); }
    } catch (e) { toast(`카드 불러오기 실패 (${e.message})`); $("#cardEmpty p").textContent = "카드 불러오기 실패"; }
    finally { setLoading(false); }
    if (state.poll) { clearInterval(state.poll); state.poll = null; }
    const jobs = (await api(`/api/jobs?project_id=${id}`)).data.filter((j) => ["queued", "running"].includes(j.status));
    if (jobs.length) watchJob(jobs[0].id);
  }
  const fmt = (v, unit) => v == null ? `<span class="none">측정 불가</span>` : Array.isArray(v) ? `${v[0].toFixed(3)} ~ ${v[1].toFixed(3)}${unit ? " " + unit : ""}` : typeof v === "object" ? `<span class="obj">${Object.entries(v).map(([k, x]) => `<span><em>${SUB_LABEL[k] || k}</em>${typeof x === "number" ? (Number.isInteger(x) ? x : x.toFixed(2)) : x}${unit && typeof x === "number" && !Number.isInteger(x) ? unit : ""}</span>`).join("")}</span>` : typeof v === "boolean" ? (v ? "예" : "아니오") : typeof v === "number" ? (Number.isInteger(v) ? v.toLocaleString("ko-KR") : (Math.abs(v) < 10 ? v.toFixed(3) : v.toFixed(1))) + (unit ? ` ${unit}` : "") : String(v);
  function renderCard() {
    const c = state.card; const p = c.project; const mod = c.modules[0];
    $("#cardEmpty").hidden = true; $("#card").hidden = false; $("#regPanel").hidden = true;
    printReceipt(p, mod);
    $("#sheetId").textContent = p.id.toUpperCase(); $("#sheetName").textContent = p.name;
    $("#cardMeta").textContent = [TYPE_LABEL[p.type], p.agency, p.region, p.period, p.budget_krw ? `${(p.budget_krw / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}억 원` : null].filter(Boolean).join(" · ");
    $("#btnCard").href = `/card/${p.id}`; $("#btnJson").href = `/api/projects/${p.id}/card`;
    const v = mod.verdict || {}; const code = v.code || mod.status || "not_run";
    const st = $("#stamp"); st.className = `stamp ${["not_run", "waiting_input", "unmeasured", "waiting"].includes(code) ? "neutral" : code}`;
    $("#stampWord").textContent = VERDICT[code] || code; $("#stampDate").textContent = mod.computed_at ? mod.computed_at.slice(0, 10).replaceAll("-", ".") + " 검정" : "검정 전";
    st.classList.remove("press"); void st.offsetWidth; st.classList.add("press");
    $("#verdictText").textContent = v.text || "";
    renderSummary(mod);
    $("#needs").hidden = !mod.needs; if (mod.needs) $("#needs").textContent = "필요한 입력: " + mod.needs.join(", ");
    $("#metricsBlock").hidden = !mod.metrics.length;
    // 영수증 행: 항목 ······ 값 / n / 출처
    $("#metricsTable").outerHTML = `<div class="rcpt" id="metricsTable">` + mod.metrics.map((r) => `<div class="row"><span class="lbl">${label(r.key, r)}<span class="tech">${r.key}</span>${r.note ? `<span class="sub">${r.note}</span>` : ""}</span><span class="lead"></span><span class="val">${fmt(r.value, r.unit)}${r.n != null ? `<span class="n">표본 ${r.n.toLocaleString("ko-KR")}</span>` : ""}<span class="src ${r.badge}">${SRC[r.badge]}</span></span></div>`).join("") + `</div>`;
    $("#chartBlock").hidden = !mod.series; if (mod.series) renderChart(mod.series);
    $("#severityBlock").hidden = !mod.severity; if (mod.severity) renderSeverity(mod.severity);
    $("#eventsBlock").hidden = !mod.events;
    if (mod.events) {
      $("#eventsTable").innerHTML = `<tr><th>사건</th><th>단계</th><th>등급</th><th class="num">첫 관측(시간)</th><th class="num">침수 ha</th></tr>` + mod.events.map((e) => { const key = "flood_evt_" + e.event_peak.slice(0, 10).replaceAll("-", ""); const link = mod.overlays?.[key]; return `<tr${link ? ` class="is-link" data-ov="${key}" title="지도에서 보기"` : ""}><td>${e.name}<span class="sub">${e.event_peak} UTC${e.passes?.[0] ? ", 궤도 " + e.passes[0].relative_orbit : ""}</span></td><td>${e.phase === "before" ? "정비 전" : "정비 후"}</td><td><span class="mark ${e.grade === "C" ? "undetected" : "detected"}">${e.grade}</span></td><td class="num">${e.first_pass_hours ?? "미관측"}</td><td class="num">${e.stage2?.flooded_ha != null ? e.stage2.flooded_ha.toLocaleString("ko-KR") : (e.stage2?.error ? `<span class="sub">${e.stage2.error}</span>` : "—")}</td></tr>`; }).join("");
      $("#eventsTable").querySelectorAll("tr.is-link").forEach((tr) => tr.addEventListener("click", () => { stopPlay(); setOverlay(tr.dataset.ov); }));
    }
    const eq = c.equity; const eb = $("#equityBody"); const ex = c.exposure;
    $("#equitySub").textContent = ex ? "피해 지역의 고령 지표, 읍면 단위" : "수혜 건물과 관할 전체 비교";
    if (ex) {
      const n0 = (v) => v == null ? "측정 불가" : Math.round(v).toLocaleString("ko-KR");
      eb.innerHTML = `<ul class="sum-points"><li>${ex.hazard_label} 면적 ${n0(ex.hazard_ha)} ha 가운데 ${Math.round(ex.share_in_high_aging * 100)}%가 고령화지수 중앙값(${n0(ex.median_aged_idx)}) 이상 읍면에 분포</li><li>${ex.hazard_label} 면적 가중 고령화지수 ${n0(ex.exposed_aged_idx)}, 분석 범위 ${ex.n_areas}개 읍면 인구 가중 ${n0(ex.ref_aged_idx)}</li><li>노년부양비 ${ex.exposed_oldage} 대 ${ex.ref_oldage}</li></ul>`
        + `<table class="tbl"><tr><th>읍면</th><th class="num">${ex.hazard_label} ha</th><th class="num">고령화지수</th><th class="num">노년부양비</th></tr>` + ex.top.map((t) => `<tr><td>${t.name}<span class="sub">인구 ${n0(t.pop)}, 읍면 면적의 ${t.hazard_pct_of_area}%</span></td><td class="num">${n0(t.hazard_ha)}</td><td class="num">${n0(t.aged_idx)}</td><td class="num">${t.oldage ?? "측정 불가"}</td></tr>`).join("") + `</table><p class="meta">${ex.source}. 지도의 '읍면 고령화'로 분포 확인</p>`;
    } else if (!eq) eb.innerHTML = `<div class="errata">형평성 감사 미실행</div>`;
    else if (eq.status !== "ok") eb.innerHTML = `<div class="errata">${eq.warnings.join("<br>")}</div><p class="meta">지표: ${eq.data.design.indicators.join(", ")}</p>`;
    else {
      eb.innerHTML = `<table class="tbl">${Object.entries(eq.data.metrics).map(([k, m]) => `<tr><td>${label(k)}</td><td class="num">${fmt(m.value, m.unit)}</td><td><span class="src ${m.badge}">${SRC[m.badge]}</span></td></tr>`).join("")}</table>`;
      const ra = eq.data.reallocation;
      if (ra && ra.rows?.length) {
        const ST = { treated: "시공", control: "대조", candidate: "후보" };
        eb.insertAdjacentHTML("beforeend", `<h3 class="sub-h">다음 집행 순위 <small>${ra.rule}</small></h3>
          <table class="tbl realloc"><tr><th>순위</th><th>동</th><th class="num">세대</th><th class="num">지붕 m²</th><th class="num">세대/100m²</th><th class="num">누적 세대</th><th class="num">${ra.unit_cost_krw_m2 ? "누적 비용" : "누적 지붕 m²"}</th><th>상태</th></tr>` +
          ra.rows.map((r) => `<tr class="${r.status}"><td class="num">${r.rank}</td><td>${r.dong}</td><td class="num">${r.households}</td><td class="num">${r.roof_area_m2.toLocaleString("ko-KR")}</td><td class="num">${r.households_per_100m2}</td><td class="num">${r.cum_households ?? "—"}</td><td class="num">${ra.unit_cost_krw_m2 ? (r.cum_cost_krw != null ? r.cum_cost_krw.toLocaleString("ko-KR") + "원" : "—") : (r.cum_roof_area_m2 != null ? r.cum_roof_area_m2.toLocaleString("ko-KR") : "—")}</td><td><span class="mark ${r.status === "treated" ? "detected" : (r.status === "control" ? "undetected" : "")}">${ST[r.status]}</span></td></tr>`).join("") +
          `</table><p class="meta">${ra.note}${ra.within_budget?.length ? ` 예산 ${ra.budget_krw.toLocaleString("ko-KR")}원 안: ${ra.within_budget.join(", ")}` : ""}</p>`);
      }
    }
    $("#limitsBlock").hidden = !(mod.limitations || []).length; $("#limitsList").innerHTML = (mod.limitations || []).map((l) => `<li>${l}</li>`).join("");
    const sc = mod.scenes || []; $("#scenesBlock").hidden = !sc.length; $("#scenesCount").textContent = sc.length ? `장면 ${sc.length}${mod.failed?.length ? `, 실패 ${mod.failed.length}` : ""}` : "";
    $("#scenesTable").innerHTML = `<tr><th>시점</th><th>관측일</th><th>장면</th><th>처리 버전</th><th class="num">구름 %</th><th class="num">구름 없는 비율 %</th></tr>` + sc.map((s) => `<tr><td>${s.label ?? s.year ?? ""}</td><td class="num">${s.date ?? "없음"}</td><td>${(s.ids || [s.id]).join("<br>")}</td><td class="num">${s.processing_baseline ?? ""}</td><td class="num">${s.cloud_cover != null ? s.cloud_cover.toFixed(1) : ""}</td><td class="num">${s.valid_pct ?? ""}</td></tr>`).join("") + (mod.failed || []).map((f) => `<tr><td colspan="6" class="none">실패: ${f.label || f.year || f.event?.name || ""}, ${f.error}</td></tr>`).join("");
    renderPassRail(sc, mod);
    syncOverlayUI(mod);
    $("#btnVerify").disabled = false; $("#btnVerify").querySelector("span").textContent = mod.status === "not_run" ? "검정 실행" : "다시 검정";
    $("#colophonRight").textContent = `작성 ${(mod.computed_at || c.generated_at).slice(0, 10)}${mod.design?.orbit ? ", 궤도 " + mod.design.orbit : ""}${mod.design?.resolution_m ? ", " + mod.design.resolution_m + " m" : ""}`;
    window.dispatchEvent(new CustomEvent("ar:project-selected", { detail: { id: p.id } }));
  }
  // 3D 출력: 프린터 헤드에서 카드가 뽑혀 나온다. 같은 도엽을 다시 그릴 때마다 새로 출력한다.
  let printSeq = 0, printGuard = null;
  function printReceipt(p, mod) {
    const note = $("#card"), printer = $("#printer"); if (!note || !printer) return;
    $("#printerCounter").textContent = `NO. ${String(printSeq + 1).padStart(4, "0")} · ${p.id.toUpperCase()}`;
    $("#printerState").textContent = "PRINTING"; printer.classList.add("busy");
    $(".margin-right").scrollTo({ top: 0 });
    const STAGES = [["feeding", 1600, "PRINTING"], ["cutting", 240, "CUT"], ["settling", 1100, "DONE"]];
    const clear = () => note.classList.remove("printed", "feeding", "cutting", "settling");
    const finish = () => { clear(); note.classList.add("printed"); printer.classList.remove("busy"); $("#printerState").textContent = "READY"; clearTimeout(printGuard); };
    const seq = ++printSeq;
    const run = (i) => {
      if (seq !== printSeq) return;
      if (i >= STAGES.length) { finish(); return; }
      const [cls, ms, label] = STAGES[i];
      clear(); void note.offsetWidth; note.classList.add(cls); $("#printerState").textContent = label;
      if (cls !== "feeding") printer.classList.remove("busy");
      printGuard = setTimeout(() => run(i + 1), ms + 40);
    };
    clearTimeout(printGuard);
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) finish(); else run(0);
  }
  // 관측 눈금: 누르면 그 장면의 오버레이(있으면)로 바꾸고 회복률을 표시한다
  function renderPassRail(scenes, mod) {
    const rail = $("#passrail"); rail.innerHTML = "";
    const dated = scenes.filter((s) => s.date || (s.window && s.window[0])); if (!dated.length) return;
    const t = (s) => new Date(s.date || s.window[0]).getTime(); const t0 = Math.min(...dated.map(t)), t1 = Math.max(...dated.map(t)); const span = Math.max(1, t1 - t0);
    let prevX = -1e9; const railW = rail.clientWidth || 800;
    dated.sort((a, b) => t(a) - t(b)).forEach((s) => { const x = 2 + 94 * (t(s) - t0) / span; const px = x / 100 * railW; const alt = px - prevX < 96; if (!alt) prevX = px;
      const key = mod?.overlays?.[s.label] ? s.label : null;
      rail.insertAdjacentHTML("beforeend", `<div class="tick ${s.date ? "" : "miss"}${alt ? " alt" : ""}" style="left:${x}%" data-date="${s.date || ""}" data-label="${s.label ?? ""}"${key ? ` data-ov="${key}"` : ""} title="${s.date || "미관측"}">${s.date || "미관측"}<small>${OV_LABEL[s.label] || s.label || s.year || ""}</small></div>`); });
    rail.querySelectorAll(".tick").forEach((el) => el.addEventListener("click", () => {
      stopPlay();
      const fk = frameKeys(mod).find((k) => legendOf(mod, k).date === el.dataset.date);
      if (fk) setOverlay(fk); else if (el.dataset.ov) setOverlay(el.dataset.ov); else highlightSeries(el.dataset.date);
      const sr = (mod?.series || []).find((x) => x.date === el.dataset.date);
      if (sr) toast(`${sr.date} ${sr.label ? OV_LABEL[sr.label] || sr.label : ""}: 피해지 NDVI ${sr.burned.median?.toFixed(2) ?? "측정 불가"}, 대조지 ${sr.control.median?.toFixed(2) ?? "측정 불가"}, 회복률 ${sr.recovery_ratio?.toFixed(2) ?? "측정 불가"}`);
    }));
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
    $("#ratioStrip").innerHTML = series.map((s) => `<div class="ratio">${OV_LABEL[s.label] || s.label}<b>${s.recovery_ratio == null ? "—" : s.recovery_ratio.toFixed(2)}</b></div>`).join("");
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
    if (!res.ok || !r.data) { toast(r.warnings?.[0] || `재검정 시작 실패 (${res.status})`); return; }
    toast(r.warnings?.[0] || "검정 시작. 위성 사진 수에 따라 수 분 소요"); watchJob(r.data.id);
  });
  function watchJob(jobId) {
    $("#jobBar").hidden = false; $("#btnVerify").disabled = true;
    const tick = async () => {
      const j = (await api(`/api/jobs/${jobId}`)).data; const pr = j.progress || {};
      $("#jobFill").style.transform = `scaleX(${pr.total ? pr.done / pr.total : 0.08})`;
      $("#jobText").textContent = `${VERDICT[j.status] || j.status}, ${pr.message || ""}${pr.total ? ` (${pr.done}/${pr.total})` : ""}`;
      if (!["queued", "running"].includes(j.status)) {
        clearInterval(state.poll); state.poll = null;
        toast(j.status === "failed" ? `실패: ${j.error}` : `검정 완료: ${VERDICT[j.summary?.verdict] || j.status}`);
        setTimeout(() => { $("#jobBar").hidden = true; }, 1200);
        await loadProjects(); await selectProject(state.current);
      }
    };
    if (state.poll) clearInterval(state.poll); state.poll = setInterval(tick, 2500); tick();
  }

  // ---------- 채팅(chat.js)에 노출하는 화면 상태 ----------
  window.AR = { getState: () => ({ current: state.current, card: state.card, overlay: state.overlay }), selectProject, setOverlay, map, get mapB() { return mapB; } };

  // ---------- 달력·키 ----------
  async function loadCalendar() {
    const r = await api("/api/calendar"); const items = r.data; const next = items.slice().sort((a, b) => a.days_left - b.days_left)[0];
    state.calendar = items; $("#deadlineNext").textContent = next.name; $("#deadlineSub").textContent = `${next.due} · D-${next.days_left}`;
    $("#calendarTable").innerHTML = `<tr><th>항목</th><th class="num">기한</th><th class="num">D-day</th><th>근거</th><th>납품물</th></tr>` + items.map((i) => `<tr><td>${i.name}</td><td class="num">${i.due}</td><td class="num">D-${i.days_left}</td><td><span class="sub">${i.basis}</span></td><td>${i.deliverable}</td></tr>`).join("");
  }
  async function loadKeys() {
    const r = await api("/api/health"); const keys = r.data.keys;
    const DESC = { GEMINI_API_KEY: "설명 대화(Gemini)", DATA_GO_KR_SERVICE_KEY: "건축물대장 표제부", SGIS_CONSUMER_KEY: "통계청 SGIS 인증 키", SGIS_CONSUMER_SECRET: "통계청 SGIS 시크릿", VWORLD_API_KEY: "브이월드 건물 외곽선", KMA_APIHUB_KEY: "기상청 시간강우", SAFETYDATA_KEY_SHELTER: "무더위쉼터(행정안전부)", SAFETYDATA_KEY_RECOVERY: "복구계획 공공시설(행정안전부)", PC_SDK_SUBSCRIPTION_KEY: "Planetary Computer 구독키(선택)" };
    $("#keyChips").innerHTML = Object.entries(keys).filter(([k]) => !k.includes("SECRET")).map(([k, v]) => `<span class="chip ${v ? "on" : ""}">${k.replace(/_API_KEY|_SERVICE_KEY|_CONSUMER_KEY|_SDK_SUBSCRIPTION_KEY|_KEY/, "")}</span>`).join("");
    $("#keysTable").innerHTML = `<tr><th>키</th><th>용도</th><th>상태</th></tr>` + Object.entries(keys).map(([k, v]) => `<tr><td><code>${k}</code></td><td>${DESC[k] || ""}</td><td><span class="mark ${v ? "detected" : "waiting_input"}">${v ? "설정됨" : "키 필요"}</span></td></tr>`).join("");
  }
  const VIEWS = { dashboard: "#viewDashboard", summary: "#viewSummary", calendar: "#viewCalendar", keys: "#viewKeys" };
  function showView(v) {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("is-active", x.dataset.view === v));
    for (const [k, sel] of Object.entries(VIEWS)) $(sel).hidden = k !== v;
    document.querySelector(".margin-right").hidden = v !== "dashboard";
    if (v === "dashboard") setTimeout(() => map.resize(), 50);
    if (v === "summary") loadSummaryView();
  }
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));

  // ---------- 담당자 요약(쉬운 말) ----------
  const fmtKey = (k) => k.value == null ? `<b class="none">측정 불가</b>` : `<b>${k.signed && k.value > 0 ? "+" : ""}${k.value.toLocaleString("ko-KR")}${k.unit ? `<small>${k.unit}</small>` : ""}</b>`;
  function renderSummary(mod) {
    const dl = mod.design_level; $("#dlevel").hidden = !dl; if (dl) { $("#dlevel").className = `dlevel ${dl.code}`; $("#dlevel b").textContent = dl.level; $("#dlevel span").textContent = dl.text; }
    const s = mod.summary || {}; $("#sumHead").textContent = s.headline || VERDICT[mod.verdict?.code] || ""; $("#sumPoints").innerHTML = (s.points || []).map((p) => `<li>${p}</li>`).join(""); $("#sumPoints").hidden = !(s.points || []).length;
    $("#keyNums").innerHTML = (s.key || []).map((k) => `<div class="keynum">${fmtKey(k)}<span>${k.label}</span></div>`).join(""); $("#keyNums").hidden = !(s.key || []).length;
    $("#nextList").innerHTML = (s.next || []).map((n) => `<li>${n}</li>`).join(""); $("#nextBlock").hidden = !(s.next || []).length;
    $("#expert").open = true;
  }

  // ---------- 관할 요약(과장·의회용) ----------
  async function loadSummaryView() {
    const kpi = $("#kpi"), tb = $("#sumTable"); kpi.innerHTML = `<div><b>…</b><span>불러오는 중</span></div>`;
    const cards = await Promise.all(state.projects.map(async (p) => { if (!state.cards[p.id]) { try { state.cards[p.id] = (await api(`/api/projects/${p.id}/card`)).data; } catch (e) { return null; } } return state.cards[p.id]; }));
    const rows = cards.filter(Boolean).map((c) => ({ c, m: c.modules[0], s: c.modules[0].summary || {} }));
    const code = (r) => r.s.code || r.m.verdict?.code || "not_run";
    const good = rows.filter((r) => ["detected", "recovered", "reduced"].includes(code(r))).length;
    const bad = rows.filter((r) => ["gap_remaining", "not_reduced", "undetected"].includes(code(r))).length;
    const none = rows.length - good - bad;
    const budget = rows.reduce((a, r) => a + (r.c.project.budget_krw || 0), 0);
    const next = state.calendar?.slice().sort((a, b) => a.days_left - b.days_left)[0];
    kpi.innerHTML = `<div><b>${rows.length}</b><span>검정한 사업</span></div><div><b class="ok">${good}</b><span>효과 확인</span></div><div><b class="warn">${bad}</b><span>효과 미확인 또는 미달</span></div><div><b>${none}</b><span>측정 불가 또는 미검정</span></div><div><b>${budget ? (budget / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 0 }) : "—"}<small>억 원</small></b><span>예산 합계(기재분)</span></div>${next ? `<div><b>D-${next.days_left}</b><span>${next.name}</span></div>` : ""}`;
    tb.innerHTML = `<tr><th>사업</th><th>종류</th><th>기간</th><th class="num">예산</th><th>결론</th><th>핵심 수치</th><th>다음에 할 일</th></tr>` + rows.map((r) => {
      const p = r.c.project; const k = (r.s.key || []).filter((x) => x.value != null).slice(0, 2).map((x) => `${x.label} ${x.signed && x.value > 0 ? "+" : ""}${x.value.toLocaleString("ko-KR")}${x.unit ? " " + x.unit : ""}`).join(", ");
      return `<tr class="is-link" data-id="${p.id}"><td><b>${p.name}</b><span class="sub">${p.agency || ""}${p.region ? ", " + p.region : ""}</span></td><td>${TYPE_LABEL[p.type]}</td><td>${p.period || ""}</td><td class="num">${p.budget_krw ? (p.budget_krw / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 1 }) + "억" : "—"}</td><td><span class="mark ${code(r)}">${VERDICT[code(r)] || code(r)}</span><span class="sub">${r.s.headline || ""}</span></td><td>${k}</td><td>${(r.s.next || [])[0] || ""}</td></tr>`; }).join("");
    tb.querySelectorAll("tr.is-link").forEach((tr) => tr.addEventListener("click", () => { showView("dashboard"); selectProject(tr.dataset.id); }));
    const eqRows = rows.filter((r) => r.c.equity?.status === "ok" && r.c.equity.data.reallocation?.rows?.length);
    const exRows = rows.filter((r) => r.c.exposure);
    const exText = exRows.map((r) => { const e = r.c.exposure; return `${r.c.project.name}: ${e.hazard_label} 면적의 ${Math.round(e.share_in_high_aging * 100)}%가 고령화 상위 읍면, ${e.hazard_label} 가중 고령화지수 ${Math.round(e.exposed_aged_idx).toLocaleString("ko-KR")}(범위 평균 ${Math.round(e.ref_aged_idx).toLocaleString("ko-KR")})`; });
    $("#sumEquity").textContent = [...exText, ...eqRows.map((r) => { const ra = r.c.equity.data.reallocation; const t = ra.rows.filter((x) => x.status === "treated"); const first = ra.rows[0]; return `${r.c.project.name}: 세대 밀도 기준 1순위 ${first.dong}(${first.households}세대), 실제 시공 ${t.map((x) => x.dong).join(", ")}은 ${t.map((x) => x.rank + "순위").join(", ")}`; })].join(". ");
  }

  // ---------- 새 사업 등록 ----------
  const reg = { form: $("#regPanel"), type: $("#rType") };
  const regSync = () => { const t = reg.type.value; reg.form.querySelectorAll(".only").forEach((el) => { el.hidden = !el.classList.contains("only-" + t); }); };
  reg.type.addEventListener("change", regSync);
  $("#btnNew").addEventListener("click", () => {
    showView("dashboard"); state.reg = { bbox: null, treated: [], control: [], pick: null, drawing: false };
    $("#card").hidden = true; $("#cardEmpty").hidden = true; reg.form.hidden = false; regSync(); $("#drawInfo").textContent = "범위 없음"; $("#pickInfo").textContent = "지도의 건물 선택 시 추가"; $("#regMsg").textContent = "";
    if (!map.getSource("draw")) { map.addSource("draw", { type: "geojson", data: { type: "FeatureCollection", features: [] } }); map.addLayer({ id: "draw-line", type: "line", source: "draw", paint: { "line-color": "#b3261e", "line-width": 2, "line-dasharray": [2, 2] } }); map.addLayer({ id: "draw-fill", type: "fill", source: "draw", paint: { "fill-color": "#b3261e", "fill-opacity": 0.08 } }); }
    map.getSource("tc").setData({ type: "FeatureCollection", features: [] }); map.getSource("pts").setData({ type: "FeatureCollection", features: [] });
    if (map.getLayer("overlay")) { map.removeLayer("overlay"); map.removeSource("overlay"); } $("#legend").hidden = true; $("#timeline").hidden = true; $("#overlaySeg").hidden = true; $("#opacityWrap").hidden = true; $("#mapActions").hidden = true;
  });
  const closeReg = () => { state.reg = null; reg.form.hidden = true; $("#cardEmpty").hidden = !!state.card; $("#card").hidden = !state.card; if (map.getSource("draw")) map.getSource("draw").setData({ type: "FeatureCollection", features: [] }); map.dragPan.enable(); map.getCanvas().style.cursor = ""; if (state.current) selectProject(state.current); };
  $("#regClose").addEventListener("click", closeReg);
  // 범위 그리기: 누른 채 끌어 직사각형. 끝나면 끌기 복구
  $("#btnDraw").addEventListener("click", () => {
    if (!state.reg) return; state.reg.drawing = true; state.reg.pick = null; $("#btnPickT").setAttribute("aria-pressed", "false"); $("#btnPickC").setAttribute("aria-pressed", "false");
    map.dragPan.disable(); map.getCanvas().style.cursor = "crosshair"; toast("지도 위에서 누른 채 끌어 범위 지정"); let start = null;
    const rect = (a, b) => ({ type: "Feature", properties: {}, geometry: bboxPoly([Math.min(a.lng, b.lng), Math.min(a.lat, b.lat), Math.max(a.lng, b.lng), Math.max(a.lat, b.lat)]) });
    const onDown = (e) => { start = e.lngLat; };
    const onMove = (e) => { if (start) map.getSource("draw").setData({ type: "FeatureCollection", features: [rect(start, e.lngLat)] }); };
    const onUp = (e) => { if (!start) return; const b = [Math.min(start.lng, e.lngLat.lng), Math.min(start.lat, e.lngLat.lat), Math.max(start.lng, e.lngLat.lng), Math.max(start.lat, e.lngLat.lat)]; start = null;
      map.off("mousedown", onDown); map.off("mousemove", onMove); map.off("mouseup", onUp); map.dragPan.enable(); map.getCanvas().style.cursor = "";
      if (b[2] - b[0] < 1e-4 || b[3] - b[1] < 1e-4) { toast("범위 과소, 다시 지정 필요"); state.reg.drawing = false; return; }
      state.reg.bbox = b.map((x) => +x.toFixed(5)); setTimeout(() => { state.reg.drawing = false; }, 50);
      const km2 = (b[2] - b[0]) * 111 * Math.cos(b[1] * Math.PI / 180) * (b[3] - b[1]) * 111;
      $("#drawInfo").textContent = `범위 ${km2.toFixed(1)} km² (${b[1].toFixed(3)}~${b[3].toFixed(3)}°N, ${b[0].toFixed(3)}~${b[2].toFixed(3)}°E)`; };
    map.on("mousedown", onDown); map.on("mousemove", onMove); map.on("mouseup", onUp);
  });
  // 건물 고르기(옥상 차열): 바탕 지도의 건물 외곽선을 그대로 담는다
  const setPick = (mode) => { state.reg.pick = state.reg.pick === mode ? null : mode; $("#btnPickT").setAttribute("aria-pressed", String(state.reg.pick === "treated")); $("#btnPickC").setAttribute("aria-pressed", String(state.reg.pick === "control")); map.getCanvas().style.cursor = state.reg.pick ? "pointer" : ""; if (state.reg.pick && map.getZoom() < 15) toast("건물이 보이도록 확대 필요"); };
  $("#btnPickT").addEventListener("click", () => setPick("treated")); $("#btnPickC").addEventListener("click", () => setPick("control"));
  function pickBuilding(e) {
    const layers = ["bld-3d", "building", "building-3d"].filter((l) => map.getLayer(l));
    const f = map.queryRenderedFeatures(e.point, { layers })[0]; if (!f) { toast("이 지점에 건물 외곽선 없음"); return; }
    const role = state.reg.pick; const h = f.properties.render_height || f.properties.height || 12; const floors = Math.max(1, Math.round(h / 3));
    const feat = { type: "Feature", properties: { name: `${role === "treated" ? "시공" : "비교"} ${state.reg[role].length + 1}`, floors, role }, geometry: f.geometry };
    state.reg[role].push(feat);
    map.getSource("tc").setData({ type: "FeatureCollection", features: [...state.reg.treated, ...state.reg.control] });
    $("#pickInfo").textContent = `시공 ${state.reg.treated.length}동, 비교 ${state.reg.control.length}동 담김`;
  }
  reg.form.addEventListener("submit", async (ev) => {
    ev.preventDefault(); if (!state.reg) return; const t = reg.type.value; const msg = $("#regMsg");
    if (!state.reg.bbox) { msg.textContent = "지도에서 범위 지정 필요"; return; }
    if (t === "heat" && (!state.reg.treated.length || !state.reg.control.length)) { msg.textContent = "시공 동과 비교 동 각 1개 이상 선택 필요"; return; }
    const id = `${t}-${Date.now().toString(36)}`; const budget = $("#rBudget").value ? Math.round(+$("#rBudget").value * 1e8) : null;
    const prj = { id, name: $("#rName").value.trim(), type: t, modules: [t], agency: $("#rAgency").value.trim(), region: $("#rRegion").value.trim(), budget_krw: budget, geometry: { bbox: state.reg.bbox }, beneficiaries: [], notes: ["화면에서 등록"] };
    if (t === "fire") { if (!$("#rEvent").value) { msg.textContent = "산불 발생일 입력 필요"; return; } prj.event_date = $("#rEvent").value; prj.contained_date = $("#rContained").value || $("#rEvent").value; prj.period = `${prj.event_date.slice(0, 7)} ~`; prj.params = { res_m: 40, dnbr_threshold: 0.27, prefire_ndvi_min: 0.3, control_abs_dnbr_max: 0.05 }; }
    else { const yb = +$("#rBefore").value, ya = +$("#rAfter").value; if (!yb || !ya) { msg.textContent = "사업 전후 연도 입력 필요"; return; } prj.years_before = [yb]; prj.years_after = [ya]; prj.period = `${yb} ~ ${ya}`;
      if (t === "heat") { prj.geometry.treated = state.reg.treated.map((f) => ({ type: "Feature", properties: { name: f.properties.name, floors: f.properties.floors }, geometry: f.geometry })); prj.geometry.control = state.reg.control.map((f) => ({ type: "Feature", properties: { name: f.properties.name, floors: f.properties.floors }, geometry: f.geometry })); prj.params = { res_m: 30, max_cloud: 40 }; }
      if (t === "flood") { if (!$("#rStn").value.trim()) { msg.textContent = "기상청 지점번호 입력 필요"; return; } prj.kma_stn = $("#rStn").value.trim(); prj.events = []; } }
    msg.textContent = "저장 중";
    const res = await fetch("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project: prj }) });
    const r = await res.json().catch(() => ({}));
    if (!res.ok) { msg.textContent = r.detail || `저장 실패 (${res.status})`; return; }
    await loadProjects(); state.reg = null; reg.form.hidden = true; if (map.getSource("draw")) map.getSource("draw").setData({ type: "FeatureCollection", features: [] });
    await selectProject(id);
    const vr = await fetch(`/api/projects/${id}/verify/${t}`, { method: "POST" }); const vj = await vr.json().catch(() => ({}));
    if (vr.ok && vj.data) { toast("등록 완료, 위성 자료 검정 시작"); watchJob(vj.data.id); } else toast(vj.warnings?.[0] || vj.detail || "등록 완료, 검정 시작 실패");
  });
  let toastTimer; function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false; t.classList.remove("hide"); clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.classList.add("hide"); setTimeout(() => (t.hidden = true), 220); }, 4200); }

  (async () => {
    try { await Promise.all([loadProjects(), loadCalendar(), loadKeys()]); const first = state.projects.find((p) => p.results?.fire) || state.projects[0]; if (first) selectProject(first.id); }
    catch (e) { toast(`초기화 실패 (${e.message})`); }
  })();
})();
