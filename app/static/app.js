let activeRunId = null;
let selectedRunId = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toggleTargetForm() {
  document.getElementById("target-form-card")?.classList.toggle("hidden");
}

function closeSuitePreview() {
  document.getElementById("suite-preview-card")?.classList.add("hidden");
}

function renderCapabilities(target) {
  const container = document.getElementById(`caps-${target.id}`);
  if (!container) return;
  const capabilities = target.profile?.capabilities || [];
  container.innerHTML = capabilities.length
    ? capabilities.map((cap) => `<span class="chip">${escapeHtml(cap)}</span>`).join("")
    : '<span class="chip muted-chip">No capabilities declared</span>';
}

function ensureTargetCard(target) {
  if (document.getElementById(`card-${target.id}`)) return;
  const grid = document.getElementById("targets-grid");
  if (!grid) return;
  const modes = (target.available_modes || ["demo"]).map((mode) => `<option value="${escapeHtml(mode)}">${escapeHtml(mode.charAt(0).toUpperCase() + mode.slice(1))}</option>`).join("");
  grid.insertAdjacentHTML(
    "beforeend",
    `<div class="card target" id="card-${escapeHtml(target.id)}">
      <div class="row">
        <div>
          <div class="pill">${escapeHtml(target.platform || target.kind)}</div>
          <h2>${escapeHtml(target.name)}</h2>
        </div>
        <div id="status-${escapeHtml(target.id)}" class="status"></div>
      </div>
      <p class="small">${escapeHtml(target.description || target.target_spec?.purpose || "")}</p>
      <div class="small muted">${escapeHtml(target.target_spec?.role || "")}</div>
      <div class="meta-grid meta-grid-4">
        <div><span class="meta-label">Platform</span><span id="platform-${escapeHtml(target.id)}"></span></div>
        <div><span class="meta-label">Family</span><span id="family-${escapeHtml(target.id)}"></span></div>
        <div><span class="meta-label">Status</span><span id="status-copy-${escapeHtml(target.id)}"></span></div>
        <div><span class="meta-label">Last trust</span><span id="trust-${escapeHtml(target.id)}"></span></div>
      </div>
      <div class="meta-grid meta-grid-3 compact-grid">
        <div><span class="meta-label">Domain</span><span id="domain-${escapeHtml(target.id)}"></span></div>
        <div><span class="meta-label">Suite source</span><span id="suite-source-${escapeHtml(target.id)}"></span></div>
        <div><span class="meta-label">Last score</span><span id="score-${escapeHtml(target.id)}"></span></div>
      </div>
      <div class="small muted" id="detail-${escapeHtml(target.id)}"></div>
      <div class="small muted warning-text" id="warning-${escapeHtml(target.id)}"></div>
      <div class="caps" id="caps-${escapeHtml(target.id)}"></div>
      <div class="actions">
        <label class="mode-picker small" for="mode-${escapeHtml(target.id)}">Mode</label>
        <select id="mode-${escapeHtml(target.id)}" class="mode-select">${modes}</select>
        <div class="stack-actions">
          <button class="ghost small-action" onclick="previewSuite('${escapeHtml(target.id)}')">Preview Suite</button>
          <button class="ghost small-action" onclick="generatePlan('${escapeHtml(target.id)}')">Generate Test Plan</button>
          <button class="ghost small-action" onclick="probeTarget('${escapeHtml(target.id)}')">Probe Target</button>
          <button id="run-${escapeHtml(target.id)}" onclick="runTarget('${escapeHtml(target.id)}')">Run CrashLab</button>
        </div>
      </div>
      <div class="progress"><div id="bar-${escapeHtml(target.id)}"></div></div>
      <div class="small muted" id="summary-${escapeHtml(target.id)}">No run yet.</div>
    </div>`
  );
}

function renderTargetCard(target) {
  ensureTargetCard(target);
  const status = document.getElementById(`status-${target.id}`);
  const statusCopy = document.getElementById(`status-copy-${target.id}`);
  const detail = document.getElementById(`detail-${target.id}`);
  const warning = document.getElementById(`warning-${target.id}`);
  const button = document.getElementById(`run-${target.id}`);
  const family = document.getElementById(`family-${target.id}`);
  const domain = document.getElementById(`domain-${target.id}`);
  const platform = document.getElementById(`platform-${target.id}`);
  const trust = document.getElementById(`trust-${target.id}`);
  const score = document.getElementById(`score-${target.id}`);
  const summary = document.getElementById(`summary-${target.id}`);
  const suiteSource = document.getElementById(`suite-source-${target.id}`);
  const modeSelect = document.getElementById(`mode-${target.id}`);
  if (status) {
    status.textContent = target.status.label;
    status.className = `status status-${target.status.code}`;
  }
  if (statusCopy) statusCopy.textContent = target.status.label;
  if (detail) detail.textContent = target.run_blocked_reason || target.status.detail || "No readiness detail available.";
  if (warning) warning.textContent = target.warning || "";
  if (button) button.disabled = !target.status.usable;
  if (family) family.textContent = target.profile?.family || "unknown";
  if (domain) domain.textContent = target.profile?.domain || "unknown";
  if (platform) platform.textContent = target.platform || target.kind;
  if (trust) trust.textContent = target.last_run?.trust_label || "No run yet";
  if (score) score.textContent = target.last_run?.score_display || "No run yet";
  if (suiteSource) suiteSource.textContent = target.plan_summary?.source || target.suite_source || "none";
  if (summary && summary.dataset.liveRun !== "true") summary.textContent = "No run yet.";
  if (modeSelect) {
    const modes = target.available_modes || ["demo"];
    const currentValue = modeSelect.value;
    modeSelect.innerHTML = modes.map((mode) => `<option value="${escapeHtml(mode)}">${escapeHtml(mode.charAt(0).toUpperCase() + mode.slice(1))}</option>`).join("");
    modeSelect.value = modes.includes(currentValue) ? currentValue : modes[0];
    modeSelect.disabled = !target.status.usable;
  }
  renderCapabilities(target);
}

function summarizeRunMeta(runMeta) {
  if (!runMeta || !Object.keys(runMeta).length) return "No run metadata recorded.";
  const parts = [];
  if (runMeta.suite_source) parts.push(`suite ${runMeta.suite_source}`);
  if (runMeta.plan_id) parts.push(`plan ${runMeta.plan_id}`);
  if (runMeta.target_source) parts.push(`target source ${runMeta.target_source}`);
  if (runMeta.base_url) parts.push(`base ${runMeta.base_url}`);
  if (runMeta.flow_id) parts.push(`flow ${runMeta.flow_id}`);
  if (runMeta.endpoint_path) parts.push(`endpoint ${runMeta.endpoint_path}`);
  if (runMeta.analysis_conversation_id) parts.push(`conversation ${runMeta.analysis_conversation_id}`);
  if (runMeta.analysis_message_id) parts.push(`message ${runMeta.analysis_message_id}`);
  if (runMeta.analysis_task_id) parts.push(`task ${runMeta.analysis_task_id}`);
  if (runMeta.analysis_response_mode) parts.push(`mode ${runMeta.analysis_response_mode}`);
  if (runMeta.analysis_selection_reason) parts.push(`selection ${runMeta.analysis_selection_reason}`);
  if (runMeta.execution_id) parts.push(`execution ${runMeta.execution_id}`);
  if (runMeta.chat_id) parts.push(`chat ${runMeta.chat_id}`);
  if (runMeta.chat_message_id) parts.push(`message ${runMeta.chat_message_id}`);
  if (runMeta.session_id) parts.push(`session ${runMeta.session_id}`);
  const steps = runMeta.step_count || runMeta.last_agent_flow_summary?.step_count;
  if (steps) parts.push(`${steps} recorded flow steps`);
  return parts.join(" | ") || "Run metadata recorded.";
}

function setExportControls(runId) {
  selectedRunId = runId;
  const jsonLink = document.getElementById("export-json-link");
  const csvLink = document.getElementById("export-csv-link");
  const copyButton = document.getElementById("copy-md-button");
  if (!runId) {
    jsonLink.href = "#";
    csvLink.href = "#";
    jsonLink.classList.add("disabled-link");
    csvLink.classList.add("disabled-link");
    copyButton.disabled = true;
    return;
  }
  jsonLink.href = `/api/run/${runId}/export.json`;
  csvLink.href = `/api/run/${runId}/export.csv`;
  jsonLink.classList.remove("disabled-link");
  csvLink.classList.remove("disabled-link");
  copyButton.disabled = false;
}

function updateBanner(run) {
  const bannerTitle = document.getElementById("banner-title");
  const bannerText = document.getElementById("banner-text");
  if (!run) {
    bannerTitle.textContent = "Run trust summary";
    bannerText.textContent = "No run selected yet.";
    setExportControls(null);
    return;
  }
  bannerTitle.textContent = `${run.target_name} - ${run.trust_label}`;
  bannerText.textContent = `${run.trust_reason} ${run.summary} Mode: ${run.run_mode || "demo"}.`;
  setExportControls(run.run_id);
}

function historyExportButtons(runId) {
  return `<div class="history-actions"><a class="ghost button-link mini-link" href="/api/run/${runId}/export.json">JSON</a><a class="ghost button-link mini-link" href="/api/run/${runId}/export.csv">CSV</a><button class="ghost mini-button" onclick="copyMarkdownSummary('${runId}')">Copy MD</button></div>`;
}

async function copyMarkdownSummary(runId = selectedRunId) {
  if (!runId) return;
  const res = await fetch(`/api/run/${runId}/summary.md`);
  const text = await res.text();
  await navigator.clipboard.writeText(text);
  const bannerText = document.getElementById("banner-text");
  if (bannerText) bannerText.textContent = "Markdown summary copied to clipboard.";
}

function renderSuitePreview(payload) {
  const card = document.getElementById("suite-preview-card");
  const title = document.getElementById("suite-preview-title");
  const meta = document.getElementById("suite-preview-meta");
  const warning = document.getElementById("suite-preview-warning");
  const tbody = document.querySelector("#suite-preview-table tbody");
  card.classList.remove("hidden");
  title.textContent = `${payload.target_name || "Target"} - ${payload.mode || "demo"} suite`;
  meta.textContent = `Source: ${payload.source || "none"} | Approved: ${payload.approved ? "yes" : "no"} | ${payload.message || ""}`;
  warning.textContent = payload.warning || "No side-effect warning recorded.";
  tbody.innerHTML = "";
  for (const item of payload.cases || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${escapeHtml(item.case_id)}</td><td>${escapeHtml(item.category)}</td><td>${escapeHtml(item.prompt)}</td><td>${escapeHtml(item.expected_behavior || "")}</td><td>${escapeHtml(item.risk_weight || 1)}</td>`;
    tbody.appendChild(tr);
  }
  if (!(payload.cases || []).length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="5" class="muted">No cases available for this suite yet.</td>';
    tbody.appendChild(tr);
  }
}

async function previewSuite(targetId) {
  const mode = document.getElementById(`mode-${targetId}`)?.value || "demo";
  const res = await fetch(`/api/targets/${targetId}/suite-preview?mode=${encodeURIComponent(mode)}`);
  const data = await res.json();
  renderSuitePreview(data);
}

async function generatePlan(targetId) {
  const res = await fetch(`/api/targets/${targetId}/plans/generate`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById(`summary-${targetId}`).textContent = data.detail || "Test plan could not be generated.";
    return;
  }
  document.getElementById(`summary-${targetId}`).textContent = data.message || "Generated target-specific test plan.";
  await refreshTargets();
  await previewSuite(targetId);
}

async function probeTarget(targetId) {
  const res = await fetch(`/api/targets/${targetId}/probe`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById(`summary-${targetId}`).textContent = data.detail || "Probe failed.";
    return;
  }
  document.getElementById(`summary-${targetId}`).textContent = data.probe?.ok ? "Probe completed." : `Probe returned: ${data.probe?.error || "unusable output"}`;
  renderSuitePreview({
    target_name: targetId,
    mode: "probe",
    source: "probe_assisted",
    approved: false,
    message: data.probe?.ok ? `Response style: ${data.probe.response_style}` : data.probe?.error,
    warning: data.warning,
    cases: [{
      case_id: "probe",
      category: data.probe?.response_style || "probe",
      prompt: data.probe?.prompt || "",
      expected_behavior: data.probe?.response_preview || data.probe?.error || "",
      risk_weight: 0,
    }],
  });
  await refreshTargets();
}

async function refreshTargets() {
  const res = await fetch("/api/targets");
  const targets = await res.json();
  const values = Object.values(targets);
  const targetCount = document.getElementById("target-count");
  if (targetCount) targetCount.textContent = `${values.length}`;
  values.forEach(renderTargetCard);
}

async function runTarget(targetId) {
  const mode = document.getElementById(`mode-${targetId}`)?.value || "demo";
  const res = await fetch(`/api/run/${targetId}?mode=${encodeURIComponent(mode)}`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById(`summary-${targetId}`).textContent = data.detail || "Run could not be started.";
    await refreshTargets();
    return;
  }
  activeRunId = data.run_id;
  setExportControls(data.run_id);
  document.getElementById(`summary-${targetId}`).textContent = `Run started with ${data.suite_source || "selected"} suite...`;
  document.getElementById("live-target").textContent = targetId;
  document.getElementById("live-summary").textContent = "CrashLab is checking live cases.";
  updateBanner({ run_id: data.run_id, target_name: targetId, trust_label: "Running", trust_reason: "CrashLab is still collecting results.", summary: "", run_mode: mode });
  pollRun();
}

async function pollRun() {
  if (!activeRunId) return;
  const res = await fetch(`/api/run/${activeRunId}`);
  const run = await res.json();
  const bar = document.getElementById(`bar-${run.target_id}`);
  if (bar) bar.style.width = `${Math.round((run.completed / Math.max(1, run.total)) * 100)}%`;
  const summary = document.getElementById(`summary-${run.target_id}`);
  if (summary) { summary.textContent = `${run.trust_label}: ${run.score_display}`; summary.dataset.liveRun = "true"; }
  const liveSummary = document.getElementById("live-summary");
  if (liveSummary) liveSummary.textContent = run.status === "complete" ? `${run.trust_label}: ${run.summary}` : `Progress ${run.completed}/${run.total}`;
  const liveMeta = document.getElementById("live-meta");
  if (liveMeta) liveMeta.textContent = summarizeRunMeta(run.selected_run_metadata || run.run_meta);
  updateBanner(run);
  const log = document.getElementById("live-log");
  log.innerHTML = "";
  for (const item of run.logs || []) {
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `<div class="small"><b>${escapeHtml(item.t)}</b> - ${escapeHtml(item.message)}</div>`;
    log.appendChild(div);
  }
  log.scrollTop = log.scrollHeight;
  if (run.status !== "complete") {
    setTimeout(pollRun, 800);
  } else {
    activeRunId = null;
    await refreshTargets();
    await refreshCompare();
    await refreshHistory();
  }
}

async function refreshCompare() {
  const res = await fetch("/api/compare");
  const data = await res.json();
  document.getElementById("highest-risk").textContent = data.highest_risk_target || "—";
  document.getElementById("top-issue").textContent = data.top_issue || "—";
  const tbody = document.querySelector("#fail-table tbody");
  tbody.innerHTML = "";
  for (const row of data.failed_examples || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${escapeHtml(row.target)}</td><td>${escapeHtml(row.category)}</td><td>${escapeHtml(row.prompt)}</td>`;
    tbody.appendChild(tr);
  }
  if (!(data.failed_examples || []).length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="3" class="muted">No evaluated failures in the latest visible runs.</td>';
    tbody.appendChild(tr);
  }
}

async function refreshHistory() {
  const res = await fetch("/api/history");
  const data = await res.json();
  const tbody = document.querySelector("#history-table tbody");
  tbody.innerHTML = "";
  for (const run of data.runs || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${escapeHtml(run.target_name)}</td><td>${escapeHtml(run.trust_label)} (${escapeHtml(run.run_mode || "demo")})</td><td>${escapeHtml(run.score_display || "—")}</td><td>${escapeHtml(run.summary || "")}</td><td>${escapeHtml(summarizeRunMeta(run.selected_run_metadata || run.run_meta))}</td><td>${historyExportButtons(run.run_id)}</td>`;
    tbody.appendChild(tr);
  }
  if (!(data.runs || []).length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="6" class="muted">No runs recorded yet.</td>';
    tbody.appendChild(tr);
  }
}

function serializeTargetForm() {
  const form = document.getElementById("target-form");
  const data = new FormData(form);
  const payload = Object.fromEntries(data.entries());
  payload.enabled = form.querySelector("input[name='enabled']").checked;
  payload.timeout_seconds = Number(payload.timeout_seconds || 60);
  payload.preferred_output_index = payload.preferred_output_index === "" ? null : Number(payload.preferred_output_index);
  payload.preferred_nested_index = payload.preferred_nested_index === "" ? null : Number(payload.preferred_nested_index);
  return payload;
}

async function suggestTargetPlan() {
  const feedback = document.getElementById("target-form-feedback");
  feedback.textContent = "Generating a family-template suggestion...";
  const res = await fetch("/api/targets/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(serializeTargetForm()),
  });
  const data = await res.json();
  if (!res.ok) {
    feedback.textContent = data.detail || "Could not suggest a suite.";
    return;
  }
  feedback.textContent = `Suggested family: ${data.suggested_family}. Demo cases: ${(data.suggested_demo_cases || []).join(", ")}. ${data.warning || ""}`;
}

async function submitTargetForm(event) {
  event.preventDefault();
  const feedback = document.getElementById("target-form-feedback");
  feedback.textContent = "Saving target...";
  const res = await fetch("/api/targets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(serializeTargetForm()),
  });
  const data = await res.json();
  if (!res.ok) {
    feedback.textContent = data.detail || "Target could not be saved.";
    return;
  }
  feedback.textContent = `Saved ${data.target.name}. Reloading target cards...`;
  window.location.reload();
}

document.getElementById("target-form")?.addEventListener("submit", submitTargetForm);
refreshTargets();
refreshCompare();
refreshHistory();
