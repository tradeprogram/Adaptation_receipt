/* 적응영수증.chat — 화면 컨텍스트(현재 도엽·판정·난외주기 본문)를 모아 /api/chat에 보내고,
   근거 카드·도구 추적·다음 질문·화면 이동 버튼을 붙인다. (policymaps viz/public/js/agent.js의 구조를 따름) */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const el = (tag, attrs = {}, ...kids) => { const n = document.createElement(tag); for (const [k, v] of Object.entries(attrs)) { if (v == null) continue; if (k === "text") n.textContent = v; else if (k === "onclick") n.onclick = v; else n.setAttribute(k, v); } for (const c of kids.flat()) if (c) n.appendChild(c); return n; };
  const body = $("#agentBody"), form = $("#agentForm"), input = $("#agentInput"), send = $("#agentSend"), status = $("#agentStatus"), quick = $("#agentQuick"), root = $("#agent");
  const messages = []; let lastHandoff = null;
  const QUICK = [
    { label: "판정 요약", prompt: "이 사업의 효과가 검출되었나요? 판정과 근거를 요약해줘" },
    { label: "보고서 문장", prompt: "이 결과를 이행점검 보고서에 넣을 문장으로 정리해줘" },
    { label: "재현 정보", prompt: "어떤 위성 장면과 궤도로 계산했는지 재현 정보를 알려줘" },
    { label: "한계", prompt: "이 판정의 한계와 주의할 점을 설명해줘" },
  ];
  const AR = () => window.AR || {};

  function buildContext(panelContext) {
    const st = AR().getState ? AR().getState() : {};
    const card = st.card; const mod = card?.modules?.[0];
    const noteText = ($("#verdictText")?.textContent || "") + "\n" + ($("#metricsTable")?.textContent || "").slice(0, 1200);
    return { project_id: st.current || null, project_name: card?.project?.name || null, module: mod?.module || null, verdict: mod?.verdict || null,
             overlay: st.overlay || null, view: document.querySelector(".tab.is-active")?.dataset.view || "dashboard", panel_text: noteText.trim().slice(0, 1600), panel_context: panelContext };
  }

  async function ask(text, panelContext = null) {
    addUser(text); setBusy(true);
    const context = buildContext(panelContext);
    try {
      const res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, project_id: context.project_id, context, history: messages.slice(-8).map((m) => ({ role: m.role, text: m.text })) }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const env = await res.json(); const data = env.data || {};
      if (data.handoff) lastHandoff = data.handoff;
      addAssistant(data.answer || "답변을 만들지 못했습니다.", data.actions || [], { evidence: data.evidence, trace: data.tool_trace, handoff: data.handoff });
      status.textContent = data.source === "gemini" ? `Gemini · ${data.model}` : (data.warnings?.[0] || "로컬 요약");
    } catch (e) {
      addAssistant(`서버에 연결하지 못했습니다 (${e.message}). 난외주기의 판정과 지표 장부를 직접 확인해 주세요.`, []);
      status.textContent = "연결 실패";
    } finally { setBusy(false); }
  }

  function addUser(text) { messages.push({ role: "user", text }); body.appendChild(el("div", { class: "agent-msg agent-user", text })); body.scrollTop = body.scrollHeight; }
  function addAssistant(text, actions = [], meta = {}) {
    messages.push({ role: "assistant", text });
    const box = el("div", { class: "agent-msg agent-assistant" }); body.appendChild(box);
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const finish = () => { appendMeta(box, meta); appendActions(box, actions); appendSuggest(box, meta.handoff?.suggested_questions); body.scrollTop = body.scrollHeight; };
    if (reduce) { for (const p of String(text).split(/\n+/).filter(Boolean)) box.appendChild(el("p", { text: p })); finish(); return; }
    typeInto(box, String(text), finish);
  }
  function appendMeta(box, meta) {
    const ev = Array.isArray(meta.evidence) ? meta.evidence : []; const tr = Array.isArray(meta.trace) ? meta.trace : []; const h = meta.handoff;
    if (!ev.length && !tr.length && !h) return;
    const chips = [];
    if (h?.intent) chips.push(el("span", { class: "agent-chip intent", text: `intent · ${h.intent}` }));
    if (tr.length) { const ok = tr.filter((t) => t.status === "ok").length; chips.push(el("span", { class: `agent-chip ${ok < tr.length ? "miss" : ""}`, text: `도구 ${ok}/${tr.length}` })); }
    box.appendChild(el("div", { class: "agent-meta" }, chips));
    if (ev.length) box.appendChild(el("div", { class: "agent-ev" }, ev.slice(0, 4).map((e) => el("div", { class: `agent-ev-card ${e.measured === false || /키 필요|미실행|입력 대기/.test(e.title || "") ? "miss" : ""}` }, el("b", { text: `${e.kind} · ${e.title || ""}` }), el("span", { text: e.summary || "" })))));
    if (h?.steps?.length) box.appendChild(el("div", { class: "agent-plan" }, h.steps.map((s) => el("span", { class: `agent-step ${s.status === "ok" ? "" : "miss"}`, text: `${s.status === "ok" ? "✓" : "!"} ${s.label}` }))));
  }
  function appendActions(box, actions) {
    if (!actions?.length) return;
    box.appendChild(el("div", { class: "agent-actions" }, actions.map((a, i) => el("button", { class: "agent-action", type: "button", "data-primary": i === 0 ? "true" : null, text: a.label, onclick: () => goSection(a.section) }))));
  }
  function appendSuggest(box, qs) {
    const items = Array.isArray(qs) && qs.length ? qs : QUICK.map((q) => q.prompt);
    box.appendChild(el("div", { class: "agent-suggest" }, el("span", { class: "agent-suggest-title", text: "다음 질문" }), items.slice(0, 3).map((q) => el("button", { class: "agent-sbtn", type: "button", text: q, onclick: () => ask(q) }))));
  }
  function goSection(sel) { const t = sel && document.querySelector(sel); if (!t) return; t.scrollIntoView({ behavior: "smooth", block: "start" }); t.animate([{ outline: "2px solid rgba(143,26,16,.8)", outlineOffset: "4px" }, { outline: "2px solid rgba(143,26,16,0)", outlineOffset: "4px" }], { duration: 1400, easing: "ease-out" }); }
  function typeInto(box, text, done) {
    const paras = text.split(/\n+/).filter(Boolean); const cursor = el("span", { class: "agent-cursor" }); let pi = 0;
    const next = () => {
      if (pi >= paras.length) { cursor.remove(); done && done(); return; }
      const p = el("p"); box.appendChild(p); p.appendChild(cursor);
      const tokens = paras[pi].match(/\S+\s*/g) || [paras[pi]]; const burst = tokens.length > 80 ? 3 : tokens.length > 40 ? 2 : 1; let ti = 0;
      const step = () => { if (ti >= tokens.length) { pi += 1; next(); return; } for (let b = 0; b < burst && ti < tokens.length; b += 1) { cursor.insertAdjacentText("beforebegin", tokens[ti]); ti += 1; } body.scrollTop = body.scrollHeight; setTimeout(step, 10 + Math.random() * 14); };
      step();
    };
    next();
  }
  function setBusy(b) { root.setAttribute("aria-busy", b ? "true" : "false"); send.disabled = b; input.disabled = b; if (b) status.textContent = "카드 읽는 중…"; }

  // 인장 버튼으로 열고 닫기 — 패널 높이는 지면(.plate) 높이에 맞춘다
  const fab = $("#aiFab"), closeBtn = $("#agentClose");
  const fitHeight = () => { const plate = document.querySelector(".plate"); const h = plate ? plate.getBoundingClientRect().height : 560; root.style.setProperty("--chat-h", `${Math.max(360, Math.min(h, innerHeight - 130))}px`); };
  const open = () => { fitHeight(); root.hidden = false; fab.setAttribute("aria-expanded", "true"); fab.classList.remove("has-new"); setTimeout(() => input.focus(), 230); };
  const close = () => { root.hidden = true; fab.setAttribute("aria-expanded", "false"); };
  fab.addEventListener("click", () => (root.hidden ? open() : close()));
  closeBtn.addEventListener("click", close);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !root.hidden) close(); });
  window.addEventListener("resize", () => { if (!root.hidden) fitHeight(); });
  form.addEventListener("submit", (e) => { e.preventDefault(); const q = input.value.trim(); if (!q) return; input.value = ""; ask(q); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
  for (const q of QUICK) quick.appendChild(el("button", { type: "button", text: q.label, onclick: () => ask(q.prompt) }));
  window.addEventListener("ar:project-selected", () => { status.textContent = `도엽 ${(AR().getState?.().current || "").toUpperCase()}`; });
  addAssistant("무엇을 확인할까요? 저는 현재 도엽의 성과 카드(판정·지표·장면 매니페스트·한계)를 읽고, 거기 적힌 수치만 인용해 답합니다.", []);
})();
