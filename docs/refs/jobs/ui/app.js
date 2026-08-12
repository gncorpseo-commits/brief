const state = {
  index: null,
  jobs: new Map(),
  selectedId: null,
  tab: "summary",
};

const $ = (sel) => document.querySelector(sel);

async function loadIndex() {
  const res = await fetch("../index.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`index.json 로드 실패 (${res.status})`);
  return res.json();
}

async function loadJob(file) {
  if (state.jobs.has(file)) return state.jobs.get(file);
  const res = await fetch(`../${file}`, { cache: "no-store" });
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

async function boot() {
  try {
    state.index = await loadIndex();
    renderList();
    $("#q").addEventListener("input", renderList);
    $("#kind").addEventListener("change", renderList);
    const first = filteredItems()[0];
    if (first) selectJob(first);
  } catch (err) {
    $("#meta").textContent = "오류";
    $("#detail").innerHTML = `<div class="error">${escapeHtml(err.message)}<br/><br/>로컬에서는 <code>scripts/serve-job-refs.ps1</code> 로 서버를 띄운 뒤 <code>/ui/</code> 로 접속하세요. 파일 직접 열기(file://)는 fetch가 막힐 수 있습니다.</div>`;
  }
}

boot();
