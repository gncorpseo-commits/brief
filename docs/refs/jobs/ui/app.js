const state = {
  index: null,
  jobs: new Map(),
  selectedId: null,
  tab: "summary",
  view: "browse",
  lastJobId: null,
  refsBase: "../",
  apiBase: "",
};

const $ = (sel) => document.querySelector(sel);

async function detectBases() {
  // Prefer Brief API if available
  try {
    const r = await fetch("/api/health", { cache: "no-store" });
    if (r.ok) {
      const h = await r.json();
      state.apiBase = "";
      state.refsBase = "/refs/";
      $("#health").textContent = h.ollama ? "API · Ollama ON" : "API · heuristic";
      $("#health").className = "health " + (h.ollama ? "on" : "off");
      return;
    }
  } catch (_) {}
  state.apiBase = null;
  state.refsBase = "../";
  $("#health").textContent = "정적 모드 (structure는 API 필요)";
  $("#health").className = "health off";
}

async function loadIndex() {
  const res = await fetch(`${state.refsBase}index.json`, { cache: "no-store" });
  if (!res.ok) throw new Error(`index.json 로드 실패 (${res.status})`);
  return res.json();
}

async function loadJob(file) {
  if (state.jobs.has(file)) return state.jobs.get(file);
  const res = await fetch(`${state.refsBase}${file}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${file} 로드 실패 (${res.status})`);
  const data = await res.json();
  state.jobs.set(file, data);
  return data;
}

function filteredItems() {
  const q = ($("#q").value || "").trim().toLowerCase();
  const kind = $("#kind").value;
  return (state.index?.items || []).filter((item) => {
    if (kind && item.kind !== kind) return false;
    if (!q) return true;
    const hay = [item.title, item.id, item.url, ...(item.tags || [])].join(" ").toLowerCase();
    return hay.includes(q);
  });
}

function renderList() {
  const items = filteredItems();
  $("#meta").textContent = `${items.length} / ${state.index.count} · 업데이트 ${state.index.updated}`;
  const list = $("#list");
  list.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = item.id === state.selectedId ? "active" : "";
    btn.innerHTML = `
      <div class="title">${escapeHtml(item.title)}</div>
      <div class="row">
        <span class="chip kind-${escapeHtml(item.kind)}">${escapeHtml(item.kind)}</span>
        ${(item.tags || []).slice(0, 3).map((t) => `<span class="chip">${escapeHtml(t)}</span>`).join("")}
      </div>
    `;
    btn.addEventListener("click", () => selectJob(item));
    li.appendChild(btn);
    list.appendChild(li);
  }
}

async function selectJob(item) {
  state.selectedId = item.id;
  state.tab = "summary";
  renderList();
  const detail = $("#detail");
  detail.innerHTML = `<p class="meta">불러오는 중… ${escapeHtml(item.file)}</p>`;
  try {
    const job = await loadJob(item.file);
    renderDetail(job, item);
  } catch (err) {
    detail.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
  }
}

function renderDetail(job, item) {
  const url = job.url || item.url || job.source?.url || "";
  const applyUrl = job.apply?.url || "";
  const detail = $("#detail");
  detail.innerHTML = `
    <article class="detail-head">
      <h1>${escapeHtml(job.title || item.title)}</h1>
      <div class="links">
        ${url ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">공고 페이지 열기</a>` : ""}
        ${applyUrl && applyUrl !== url ? `<a href="${escapeAttr(applyUrl)}" target="_blank" rel="noopener">지원/관련 링크</a>` : ""}
        <button type="button" class="linkish" id="use-in-work">이 원문으로 구조화 탭</button>
        <span class="chip kind-${escapeHtml(item.kind)}">${escapeHtml(item.kind)}</span>
      </div>
    </article>

    <div class="grid">
      ${stat("URL", url || "—")}
      ${stat("급여", job.pay || "—")}
      ${stat("일정", job.schedule || "—")}
      ${stat("근무", formatRemote(job.remote) + (job.location ? ` · ${job.location}` : ""))}
      ${stat("고용형태", job.employment_type || "—")}
      ${stat("구현난이도", job.impl_difficulty_hint != null ? String(job.impl_difficulty_hint) : "—")}
    </div>

    <div class="tabs" role="tablist">
      <button type="button" data-tab="summary" class="${state.tab === "summary" ? "active" : ""}">요약</button>
      <button type="button" data-tab="text" class="${state.tab === "text" ? "active" : ""}">상세 본문</button>
      <button type="button" data-tab="json" class="${state.tab === "json" ? "active" : ""}">원본 JSON</button>
    </div>

    <div class="panel" data-panel="summary" ${state.tab === "summary" ? "" : "hidden"}>
      ${blockList("하는 일", job.duties)}
      ${blockList("자격", job.requirements)}
      ${blockList("우대", job.preferred)}
      ${blockList("매핑 task", job.mapped_task_ids)}
      ${job.automation_notes ? `<div class="block"><h2>자동화 메모</h2><p>${escapeHtml(job.automation_notes)}</p></div>` : ""}
      ${job.details?.summary ? `<div class="block"><h2>요약</h2><p>${escapeHtml(job.details.summary)}</p></div>` : ""}
      ${renderSections(job.details?.sections)}
      ${renderListingSamples(job.details?.listing_samples)}
      ${renderTags(job.tags)}
    </div>

    <div class="panel" data-panel="text" ${state.tab === "text" ? "" : "hidden"}>
      <pre class="job-text">${escapeHtml(job.job_text || "(job_text 없음)")}</pre>
    </div>

    <div class="panel" data-panel="json" ${state.tab === "json" ? "" : "hidden"}>
      <pre class="json-view">${escapeHtml(JSON.stringify(job, null, 2))}</pre>
    </div>
  `;

  detail.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.tab = btn.dataset.tab;
      detail.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
      detail.querySelectorAll("[data-panel]").forEach((p) => {
        p.hidden = p.dataset.panel !== state.tab;
      });
    });
  });

  const useBtn = detail.querySelector("#use-in-work");
  if (useBtn) {
    useBtn.addEventListener("click", () => {
      $("#work-url").value = url || "";
      $("#work-text").value = job.job_text || "";
      setView("work");
    });
  }
}

function setView(name) {
  state.view = name;
  $("#view-browse").hidden = name !== "browse";
  $("#view-work").hidden = name !== "work";
  $("#tab-browse").classList.toggle("active", name === "browse");
  $("#tab-work").classList.toggle("active", name === "work");
}

function stat(k, v) {
  return `<div class="stat"><span class="k">${escapeHtml(k)}</span><span class="v">${escapeHtml(v)}</span></div>`;
}

function blockList(title, arr) {
  if (!arr || !arr.length) return "";
  return `<div class="block"><h2>${escapeHtml(title)}</h2><ul>${arr.map((x) => `<li>${escapeHtml(String(x))}</li>`).join("")}</ul></div>`;
}

function renderSections(sections) {
  if (!sections?.length) return "";
  return sections
    .map(
      (s) =>
        `<div class="block"><h2>${escapeHtml(s.heading || "section")}</h2><p>${escapeHtml(s.body || "")}</p></div>`
    )
    .join("");
}

function renderListingSamples(samples) {
  if (!samples?.length) return "";
  const rows = samples
    .map(
      (s) =>
        `<li><strong>${escapeHtml(s.title || "")}</strong> — ${escapeHtml(s.pay || "")} · ${escapeHtml(s.hours || "")}</li>`
    )
    .join("");
  return `<div class="block"><h2>목록 표본</h2><ul>${rows}</ul></div>`;
}

function renderTags(tags) {
  if (!tags?.length) return "";
  return `<div class="block"><h2>태그</h2><div class="tags">${tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div></div>`;
}

function formatRemote(remote) {
  if (remote === true) return "재택";
  if (remote === false) return "출근";
  if (remote === "hybrid") return "하이브리드";
  return remote ? String(remote) : "—";
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(s) {
  return escapeHtml(s).replaceAll("'", "&#39;");
}

function requireApi() {
  if (state.apiBase === null) {
    throw new Error("Brief API가 필요합니다. scripts/serve-brief.ps1 로 서버를 띄우세요.");
  }
}

async function doStructure() {
  requireApi();
  const raw_text = $("#work-text").value.trim();
  const url = $("#work-url").value.trim();
  if (raw_text.length < 20) throw new Error("원문 20자 이상 필요");
  $("#work-status").textContent = "구조화 중…";
  $("#btn-structure").disabled = true;
  try {
    const r = await fetch("/api/structure", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        raw_text,
        url,
        heuristic: $("#work-heuristic").checked,
        save: true,
      }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
    state.lastJobId = data.job.id;
    $("#btn-draft").disabled = false;
    $("#btn-apply").disabled = true;
    $("#work-status").textContent = `OK · engine=${data.engine} · id=${data.job.id}`;
    $("#work-out").textContent = JSON.stringify(data.job, null, 2);
    // refresh index if possible
    try {
      state.index = await loadIndex();
      renderList();
    } catch (_) {}
  } finally {
    $("#btn-structure").disabled = false;
  }
}

async function doDraft() {
  requireApi();
  if (!state.lastJobId) throw new Error("먼저 구조화하세요");
  $("#work-status").textContent = "초안 생성 중…";
  $("#btn-draft").disabled = true;
  try {
    const r = await fetch("/api/draft", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_id: state.lastJobId, save: true }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
    $("#btn-apply").disabled = false;
    $("#work-status").textContent = `draft OK · engine=${data.engine} · pending_approval`;
    $("#work-out").textContent = JSON.stringify(data.package, null, 2);
  } finally {
    $("#btn-draft").disabled = false;
  }
}

async function doApply() {
  requireApi();
  if (!state.lastJobId) throw new Error("job_id 없음");
  const ok = confirm("이 공고 지원을 승인할까요? (클립보드/파일 기록, 무인 대량 전송 없음)");
  if (!ok) return;
  $("#work-status").textContent = "지원 기록 중…";
  const r = await fetch("/api/apply", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ job_id: state.lastJobId, approved: true }),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
  $("#work-status").textContent = `apply: ${data.submit?.status || "ok"}`;
  $("#work-out").textContent = JSON.stringify(data, null, 2);
}

async function boot() {
  try {
    await detectBases();
    state.index = await loadIndex();
    renderList();
    $("#q").addEventListener("input", renderList);
    $("#kind").addEventListener("change", renderList);
    $("#tab-browse").addEventListener("click", () => setView("browse"));
    $("#tab-work").addEventListener("click", () => setView("work"));
    $("#btn-structure").addEventListener("click", () =>
      doStructure().catch((e) => {
        $("#work-status").textContent = e.message;
        $("#work-out").textContent = e.message;
      })
    );
    $("#btn-draft").addEventListener("click", () =>
      doDraft().catch((e) => {
        $("#work-status").textContent = e.message;
      })
    );
    $("#btn-apply").addEventListener("click", () =>
      doApply().catch((e) => {
        $("#work-status").textContent = e.message;
      })
    );
    const first = filteredItems()[0];
    if (first) selectJob(first);
  } catch (err) {
    $("#meta").textContent = "오류";
    $("#detail").innerHTML = `<div class="error">${escapeHtml(err.message)}<br/><br/><code>scripts/serve-brief.ps1</code> 권장 (API+UI). 정적만 쓰려면 <code>serve-job-refs.ps1</code>.</div>`;
  }
}

boot();
