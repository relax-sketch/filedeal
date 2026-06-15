(() => {
const { API, routes, qs, esc, apiJson, UI, readForm, recordsTable, pollTask, iconForCategory } = window.ProtonCore;

function summarizeLog(text, headLines = 100, tailLines = 200) {
  const lines = String(text || "").split(/\r?\n/);
  if (lines.length <= headLines + tailLines) return text;
  const head = lines.slice(0, headLines).join("\n");
  const tail = lines.slice(-tailLines).join("\n");
  return `${head}\n\n....\n\n${tail}`;
}

async function resumeTaskFromRecord(taskId) {
  const resp = await apiJson(`${API.tasks}/${taskId}/resume`, { method: "POST" });
  if (resp.task_id) {
    location.href = `detail.html?id=${encodeURIComponent(resp.task_id)}`;
  }
}

async function homePage() {
  UI.shell("home", "欢迎回来", "本地小工具合集，用于快速执行图片视频、TXT 清洗、文件批处理和固定流程。");
  const [tools, flows, tasks] = await Promise.all([apiJson(API.tools), apiJson(API.flows), apiJson(API.tasks)]);
  const content = document.querySelector("#content");
  content.innerHTML = `
    <div class="dashboard-grid">
      ${UI.metric({ value: tools.length, label: "已注册小工具", icon: "construction", href: routes.tools })}
      ${UI.metric({ value: flows.length, label: "固定流程", icon: "account_tree", href: routes.flows })}
      ${UI.metric({ value: tasks.length, label: "执行记录", icon: "history", href: routes.records })}
      ${UI.metric({ value: "本地", label: "安全运行环境", icon: "shield", href: routes.settings })}
    </div>
    ${UI.panel({
      title: "最近执行记录",
      subtitle: "最近 5 条执行任务",
      actions: UI.button({ label: "查看全部", icon: "arrow_forward", href: routes.records }),
      body: recordsTable(tasks.slice(0, 5)),
    })}`;
}

async function toolsPage() {
  UI.shell("tools", "小工具目录", "单个工具独立执行，参数表单由注册信息自动渲染。");
  const tools = await apiJson(API.tools);
  const categories = [...new Set(tools.map(t => t.category))];
  const content = document.querySelector("#content");
  content.innerHTML = `
    <div class="toolbar">${categories.map(cat => `<button class="btn btn-ghost" data-filter="${esc(cat)}">${esc(cat)}</button>`).join("")}</div>
    <div class="grid" id="tool-grid">${tools.map(toolCard).join("")}</div>`;

  document.querySelectorAll("[data-filter]").forEach(btn => {
    btn.addEventListener("click", () => {
      const category = btn.dataset.filter;
      document.querySelector("#tool-grid").innerHTML = tools.filter(t => t.category === category).map(toolCard).join("");
    });
  });

  function toolCard(t) {
    return UI.card({
      title: t.name,
      subtitle: t.category,
      description: t.description,
      icon: iconForCategory(t.category),
      tag: UI.tag(t.risk),
      href: `tool.html?id=${encodeURIComponent(t.id)}`,
      actionLabel: "打开",
    });
  }
}

async function flowsPage() {
  UI.shell("flows", "固定流程", "固定流程由程序预设，只允许填写参数与开关预设步骤。");
  const flows = await apiJson(API.flows);
  const content = document.querySelector("#content");
  content.innerHTML = `<div class="grid">${flows.map(f => UI.card({
    title: f.name,
    subtitle: `${f.category} · ${f.steps.length} 步`,
    description: f.description,
    icon: "account_tree",
    tag: UI.tag(f.risk),
    href: `flow.html?id=${encodeURIComponent(f.id)}`,
    actionLabel: "打开流程",
  })).join("")}</div>`;
}

function runFormStorageKey(kind, id) {
  return `proton:${kind}:${id}:run-form:v1`;
}

function advancedOpenStorageKey(kind, id) {
  return `proton:${kind}:${id}:advanced-open:v1`;
}

function usageOpenStorageKey(kind, id) {
  return `proton:${kind}:${id}:usage-open:v1`;
}

function outputAutoStorageKey(kind, id, fieldName) {
  return `proton:${kind}:${id}:${fieldName}:auto-output:v1`;
}

function readStoredRunForm(kind, id) {
  try {
    return JSON.parse(localStorage.getItem(runFormStorageKey(kind, id)) || "{}");
  } catch {
    return {};
  }
}

function schemaWithStoredDefaults(schema, kind, id) {
  const stored = readStoredRunForm(kind, id);
  return schema.map(field => Object.prototype.hasOwnProperty.call(stored, field.name)
    ? { ...field, default: stored[field.name] }
    : field);
}

function renderRunForm(schema, kind, id) {
  const normalFields = schema.filter(field => !field.advanced);
  const advancedFields = schema.filter(field => field.advanced);
  let advancedOpen = false;
  try {
    advancedOpen = localStorage.getItem(advancedOpenStorageKey(kind, id)) === "1";
  } catch {
    advancedOpen = false;
  }
  const normalHtml = normalFields.map(UI.field).join("");
  if (!advancedFields.length) return `<form id="run-form" class="form">${normalHtml}</form>`;

  const groups = [];
  advancedFields.forEach(field => {
    const title = field.advanced_group || "高级设置";
    let group = groups.find(item => item.title === title);
    if (!group) {
      group = { title, fields: [] };
      groups.push(group);
    }
    group.fields.push(field);
  });

  const advancedHtml = groups.map(group => `<div class="advanced-group">
    <div class="advanced-group-title">${esc(group.title)}</div>
    <div class="advanced-grid">${group.fields.map(UI.field).join("")}</div>
  </div>`).join("");

  return `<form id="run-form" class="form">${normalHtml}
    <details class="advanced-settings" ${advancedOpen ? "open" : ""}>
      <summary>
        <span class="advanced-summary-main">
          ${UI.icon("tune")}
          <b>高级设置</b>
          <span class="muted small">小工具参数，自动保存上次更改</span>
        </span>
        ${UI.icon("expand_more", "advanced-chevron")}
      </summary>
      <div class="advanced-settings-body">${advancedHtml}</div>
    </details>
  </form>`;
}

function renderUsageDetails(item, kind, id) {
  const usage = item.usage || {};
  const rows = [
    ["做什么", usage.purpose],
    ["输入什么", usage.input],
    ["输入结构", usage.input_structure],
    ["输入规范", usage.input_rules],
    ["输出结构", usage.output],
    ["作用说明", usage.notes],
  ].filter(([, value]) => value);
  if (!rows.length) return "";

  let usageOpen = false;
  try {
    usageOpen = localStorage.getItem(usageOpenStorageKey(kind, id)) === "1";
  } catch {
    usageOpen = false;
  }

  return `<details class="usage-details" ${usageOpen ? "open" : ""}>
    <summary>
      <span class="advanced-summary-main">
        ${UI.icon("help")}
        <b>使用说明</b>
        <span class="muted small">输入、结构、规范和输出</span>
      </span>
      ${UI.icon("expand_more", "advanced-chevron")}
    </summary>
    <div class="usage-details-body">
      ${rows.map(([label, value]) => `<div class="usage-row"><div class="usage-label">${esc(label)}</div><div class="usage-value">${esc(value)}</div></div>`).join("")}
    </div>
  </details>`;
}

function bindRunFormPersistence(form, kind, id) {
  const outputFields = [...form.querySelectorAll("[name=output_dir], [name=output_file]")];
  outputFields.forEach(input => bindAutoOutputControl(form, input, kind, id));

  const save = () => {
    try {
      localStorage.setItem(runFormStorageKey(kind, id), JSON.stringify(readForm(form)));
    } catch {
      // Storage can be unavailable in restricted browser contexts.
    }
  };
  form.addEventListener("input", save);
  form.addEventListener("change", save);

  const advanced = form.querySelector(".advanced-settings");
  if (advanced) {
    advanced.addEventListener("toggle", () => {
      try {
        localStorage.setItem(advancedOpenStorageKey(kind, id), advanced.open ? "1" : "0");
      } catch {
        // Ignore storage failures; the form still works.
      }
    });
  }
}

function bindAutoOutputControl(form, input, kind, id) {
  const field = input.closest(".form-field");
  if (!field || field.querySelector("[data-auto-output-for]")) return;

  const title = field.querySelector("span");
  const titleText = title ? title.textContent : "输出路径";
  const header = document.createElement("div");
  header.className = "form-field-title";
  header.innerHTML = `<span>${esc(titleText)}</span>
    <label class="auto-output-toggle">
      <input type="checkbox" data-auto-output-for="${esc(input.name)}">
      <span>自动生成默认输出</span>
    </label>`;
  if (title) title.replaceWith(header);
  else field.prepend(header);

  const toggle = header.querySelector("[data-auto-output-for]");
  let auto = !input.value;
  try {
    const stored = localStorage.getItem(outputAutoStorageKey(kind, id, input.name));
    if (stored !== null) auto = stored === "1";
  } catch {
    auto = !input.value;
  }

  const apply = () => {
    if (toggle.checked) {
      input.value = "";
      input.disabled = true;
      input.placeholder = "自动生成默认输出";
    } else {
      input.disabled = false;
      input.placeholder = "";
      input.focus();
    }
  };

  toggle.checked = auto;
  apply();
  toggle.addEventListener("change", () => {
    apply();
    try {
      localStorage.setItem(outputAutoStorageKey(kind, id, input.name), toggle.checked ? "1" : "0");
      localStorage.setItem(runFormStorageKey(kind, id), JSON.stringify(readForm(form)));
    } catch {
      // Ignore storage failures; the form still works.
    }
  });
}

async function executionPage(kind) {
  const id = qs("id");
  const item = await apiJson(`${kind === "tool" ? API.tools : API.flows}/${id}`);
  const schema = schemaWithStoredDefaults(item.schema, kind, id);
  UI.shell(kind === "tool" ? "tools" : "flows", item.name, item.description, UI.tag(item.risk));

  const steps = item.steps?.length
    ? `<div class="step-list">${item.steps.map((s, i) => `<div class="step-item"><span class="step-index">${i + 1}</span><div><b>${esc(s)}</b><div class="muted small">预设步骤</div></div></div>`).join("")}</div>`
    : `<div class="danger-callout"><b>安全提示</b><div class="muted small">点击执行会先生成结构预览，确认后才会真正开始任务。</div></div>`;
  const usageDetails = renderUsageDetails(item, kind, id);

  const formPanel = UI.panel({
    title: "参数配置",
    subtitle: "根据工具注册信息生成",
    body: renderRunForm(schema, kind, id),
    footer: `${UI.button({ label: "结构预览", icon: "visibility", id: "action-btn", variant: "primary" })}
      ${UI.button({ label: "取消", icon: "stop_circle", id: "cancel-btn", variant: "danger", disabled: true })}`,
  });

  const logPanel = UI.panel({
    title: "预览 / 执行日志",
    subtitle: "先生成结构预览，确认后再执行真实任务",
    actions: `<span id="task-status">${UI.tag("queued")}</span>`,
    body: `<pre id="task-log" class="log-panel"></pre>`,
  });

  const infoPanel = UI.panel({
    title: kind === "tool" ? "工具说明" : "流程步骤",
    subtitle: item.category,
    body: `<div class="content-stack">${usageDetails}${steps}</div>`,
  });

  const content = document.querySelector("#content");
  content.innerHTML = `<div class="workbench-grid"><div class="content-stack">${formPanel}${infoPanel}</div>${logPanel}</div>`;

  let taskId = null;
  let confirmedPreviewSignature = "";
  const runForm = document.querySelector("#run-form");
  const statusEl = document.querySelector("#task-status");
  const logEl = document.querySelector("#task-log");
  const actionBtn = document.querySelector("#action-btn");
  const cancelBtn = document.querySelector("#cancel-btn");
  bindRunFormPersistence(runForm, kind, id);
  const usage = document.querySelector(".usage-details");
  if (usage) {
    usage.addEventListener("toggle", () => {
      try {
        localStorage.setItem(usageOpenStorageKey(kind, id), usage.open ? "1" : "0");
      } catch {
        // Ignore storage failures; the help block still works.
      }
    });
  }

  function applyAutoOutputValues() {
    runForm.querySelectorAll("[data-auto-output-for]").forEach(toggle => {
      if (!toggle.checked) return;
      const input = runForm.elements[toggle.dataset.autoOutputFor];
      if (input) input.value = "";
    });
  }

  function currentParams() {
    applyAutoOutputValues();
    const params = readForm(runForm);
    try {
      localStorage.setItem(runFormStorageKey(kind, id), JSON.stringify(params));
    } catch {
      // Ignore storage failures; submission should still proceed.
    }
    return params;
  }

  function paramsSignature(params) {
    return JSON.stringify(params);
  }

  function setActionButton({ label, icon, disabled = false }) {
    actionBtn.innerHTML = `${UI.icon(icon)}<span>${esc(label)}</span>`;
    actionBtn.disabled = disabled;
  }

  function setIdlePreviewState(message = "") {
    confirmedPreviewSignature = "";
    if (!taskId) {
      statusEl.innerHTML = UI.tag("queued");
      cancelBtn.disabled = true;
    }
    setActionButton({ label: "结构预览", icon: "visibility" });
    if (message) logEl.textContent = message;
  }

  async function requestPreview() {
    const params = currentParams();
    const preview = await apiJson(`${kind === "tool" ? API.tools : API.flows}/${id}/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    confirmedPreviewSignature = paramsSignature(params);
    statusEl.innerHTML = `${UI.tag("confirm")} <span class="muted small">已生成结构预览，请确认执行</span>`;
    logEl.textContent = preview.markdown || "";
    cancelBtn.disabled = false;
    setActionButton({ label: "开始执行", icon: "play_arrow" });
    return params;
  }

  async function submitRun() {
    const params = currentParams();
    if (paramsSignature(params) !== confirmedPreviewSignature) {
      await requestPreview();
      return;
    }
    setActionButton({ label: "开始执行", icon: "play_arrow" });
    confirmedPreviewSignature = "";
    statusEl.innerHTML = `${UI.tag("running")} <span class="muted small">正在启动真实任务</span>`;
    const resp = await apiJson(`${kind === "tool" ? API.tools : API.flows}/${id}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    taskId = resp.task_id;
    cancelBtn.disabled = false;
    pollTask(taskId);
  }

  runForm.addEventListener("input", () => {
    if (taskId) return;
    if (!confirmedPreviewSignature) return;
    const params = currentParams();
    if (paramsSignature(params) === confirmedPreviewSignature) return;
    statusEl.innerHTML = `${UI.tag("preview")} <span class="muted small">参数已更改，需要重新预览</span>`;
    confirmedPreviewSignature = "";
    setActionButton({ label: "结构预览", icon: "visibility" });
  });

  actionBtn.addEventListener("click", async e => {
    e.preventDefault();
    if (confirmedPreviewSignature) {
      await submitRun();
      return;
    }
    await requestPreview();
  });
  cancelBtn.addEventListener("click", async e => {
    e.preventDefault();
    if (taskId) {
      await apiJson(`${API.tasks}/${taskId}/cancel`, { method: "POST" });
      return;
    }
    setIdlePreviewState("");
  });
  setIdlePreviewState("");
}

async function recordsPage() {
  UI.shell("records", "执行记录", "查看历史任务、复制日志、导出 CSV。", UI.button({ label: "导出 CSV", icon: "download", href: "/api/tasks/export.csv" }));
  const tasks = await apiJson(API.tasks);
  const content = document.querySelector("#content");
  content.innerHTML = recordsTable(tasks);
  document.querySelectorAll("[data-task-resume]").forEach(btn => {
    btn.addEventListener("click", async e => {
      e.preventDefault();
      await resumeTaskFromRecord(btn.dataset.taskResume);
    });
  });
}

async function detailPage() {
  const id = qs("id");
  const task = await apiJson(`${API.tasks}/${id}`);
  const resumable = ["running", "failed", "canceled"].includes(String(task.status || "").toLowerCase());
  UI.shell(
    "records",
    "执行详情",
    "完整任务摘要、参数快照、步骤日志和输出操作。",
    resumable ? UI.button({ label: "继续执行", icon: "play_arrow", id: "resume-task", variant: "primary" }) : ""
  );
  const log = await fetch(`${API.tasks}/${id}/logs`).then(r => r.text());
  const labelMap = {
    status: "状态",
    type: "类型",
    started_at: "开始时间",
    finished_at: "结束时间",
    duration_seconds: "耗时秒数",
    input_path: "输入路径",
    output_path: "输出路径",
    error: "错误信息",
  };
  const rows = Object.keys(labelMap)
    .map(k => `<tr><th>${labelMap[k]}</th><td>${k === "status" ? UI.tag(task[k]) : esc(task[k] ?? "")}</td></tr>`).join("");
  const displayLog = summarizeLog(log, 100, 200);
  const content = document.querySelector("#content");
  content.innerHTML = `<div class="workbench-grid">
    <div class="content-stack">
      ${UI.panel({ title: task.name, subtitle: task.task_id, body: `<div class="table-wrap"><table><tbody>${rows}</tbody></table></div>` })}
      ${UI.panel({ title: "参数快照", body: `<pre class="log-panel">${esc(JSON.stringify(task.params || {}, null, 2))}</pre>` })}
    </div>
    ${UI.panel({ title: "完整日志", actions: UI.button({ label: "导出日志", icon: "download", href: `/api/tasks/${id}/logs/export` }), body: `<pre class="log-panel">${esc(displayLog)}</pre>` })}
  </div>`;
  const resumeBtn = document.querySelector("#resume-task");
  if (resumeBtn) {
    resumeBtn.addEventListener("click", async e => {
      e.preventDefault();
      await resumeTaskFromRecord(id);
    });
  }
}

async function settingsPage() {
  UI.shell("settings", "设置", "管理默认路径、执行参数和危险操作策略。");
  const settings = await apiJson(API.settings);
  const content = document.querySelector("#content");
  content.innerHTML = UI.panel({
    title: "本地配置",
    subtitle: "保存到 config.json",
    body: `<form id="settings-form" class="form">
      <div class="form-grid">
        <label class="form-field"><span>默认输入目录</span><input name="default_input_dir" value="${esc(settings.default_input_dir || "")}"></label>
        <label class="form-field"><span>默认输出目录</span><input name="default_output_dir" value="${esc(settings.default_output_dir || "")}"></label>
        <label class="form-field"><span>日志目录</span><input name="log_dir" value="${esc(settings.log_dir || "")}"></label>
        <label class="form-field"><span>删除策略</span><select name="delete_strategy"><option value="_trash">移动到 _trash</option><option value="delete">永久删除</option></select></label>
        <label class="form-field"><span>最大并发数</span><input type="number" name="max_concurrency" value="${esc(settings.max_concurrency || 2)}"></label>
      </div>
      ${UI.field({ name: "recursive_default", label: "默认递归处理", type: "boolean", default: settings.recursive_default })}
      ${UI.field({ name: "dangerous_confirm", label: "危险操作二次确认", type: "boolean", default: settings.dangerous_confirm })}
    </form>`,
    footer: `${UI.button({ label: "保存设置", icon: "save", id: "save-settings", variant: "primary" })}
      ${UI.button({ label: "关闭服务", icon: "power_settings_new", id: "shutdown-service", variant: "danger" })}`,
  });
  document.querySelector("[name=delete_strategy]").value = settings.delete_strategy || "_trash";
  document.querySelector("#save-settings").addEventListener("click", async e => {
    e.preventDefault();
    await apiJson(API.settings, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(readForm(document.querySelector("#settings-form"))) });
    alert("设置已保存");
  });
  document.querySelector("#shutdown-service").addEventListener("click", async e => {
    e.preventDefault();
    if (!confirm("确定关闭本地服务？正在运行的任务会中断。")) return;
    const res = await fetch(`${API.settings}/shutdown`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    alert("服务正在关闭");
  });
}

function helpPage() {
  UI.shell("help", "帮助 / 关于", "本地运行说明和风险操作提醒。");
  const content = document.querySelector("#content");
  content.innerHTML = UI.panel({
    title: "Proton 本地工具箱",
    subtitle: "本地优先的批量文件处理工具",
    body: `<div class="content-stack">
      <p>小工具适合单独执行某个处理任务；固定流程适合执行程序预设好的组合任务。</p>
      <div class="danger-callout"><b>危险操作提醒</b><div class="muted small">删除类操作默认关闭；启用后会遵循设置中的删除策略，默认移动到 _trash。</div></div>
      <p class="mono">records/tasks/{task_id}/task.json<br>records/tasks/{task_id}/log.txt</p>
    </div>`,
  });
}

window.Proton = { homePage, toolsPage, flowsPage, executionPage, recordsPage, detailPage, settingsPage, helpPage };
})();
