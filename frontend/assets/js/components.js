const API = {
  tools: "/api/tools",
  flows: "/api/flows",
  tasks: "/api/tasks",
  settings: "/api/settings",
};

const routes = {
  home: "index.html",
  tools: "tools.html",
  tool: "tool.html",
  flows: "flows.html",
  flow: "flow.html",
  records: "records.html",
  detail: "detail.html",
  settings: "settings.html",
  help: "help.html",
};

const navItems = [
  { id: "home", icon: "home", label: "首页", href: routes.home },
  { id: "tools", icon: "construction", label: "小工具", href: routes.tools },
  { id: "flows", icon: "account_tree", label: "固定流程", href: routes.flows },
  { id: "records", icon: "history", label: "执行记录", href: routes.records },
  { id: "settings", icon: "settings", label: "设置", href: routes.settings },
  { id: "help", icon: "help", label: "帮助", href: routes.help },
];

function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function apiJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function optionLabel(field, value) {
  if (field.name === "clean_mode") {
    return { basic: "基础清洗", ai: "AI 前置清洗" }[value] || value;
  }
  if (field.name === "delete_strategy") {
    return { _trash: "移动到 _trash", delete: "永久删除" }[value] || value;
  }
  return value;
}

const UI = {
  icon(name, extra = "") {
    return `<span class="material-symbols-outlined ${extra}">${name}</span>`;
  },

  button({ label, icon, href, variant = "secondary", id = "", disabled = false, extra = "" }) {
    const klass = [
      "btn",
      variant === "primary" ? "btn-primary" : "",
      variant === "danger" ? "btn-danger" : "",
      variant === "ghost" ? "btn-ghost" : "",
      extra,
    ].filter(Boolean).join(" ");
    const attrs = `${id ? ` id="${id}"` : ""}${disabled ? " disabled" : ""}`;
    const content = `${icon ? UI.icon(icon) : ""}<span>${esc(label)}</span>`;
    return href ? `<a class="${klass}" href="${href}"${attrs}>${content}</a>` : `<button class="${klass}"${attrs}>${content}</button>`;
  },

  tag(riskOrStatus) {
    const value = String(riskOrStatus || "safe").toLowerCase();
    const map = {
      high: ["tag-high", "危险"],
      danger: ["tag-high", "危险"],
      medium: ["tag-medium", "中等"],
      warning: ["tag-medium", "警告"],
      safe: ["tag-safe", "安全"],
      success: ["tag-safe", "成功"],
      failed: ["tag-high", "失败"],
      canceled: ["tag-medium", "已取消"],
      running: ["tag-status", "执行中"],
      queued: ["tag-status", "等待中"],
    };
    const [klass, label] = map[value] || ["tag-status", value];
    return `<span class="tag ${klass}">${esc(label)}</span>`;
  },

  card({ title, subtitle, description, icon = "widgets", tag = "", href = "", actionLabel = "打开" }) {
    return `<article class="card">
      <div class="toolbar-between">
        <div class="icon-tile">${UI.icon(icon)}</div>
        ${tag}
      </div>
      <div>
        <h3 class="section-title">${esc(title)}</h3>
        ${subtitle ? `<div class="muted small">${esc(subtitle)}</div>` : ""}
      </div>
      ${description ? `<p class="small muted">${esc(description)}</p>` : ""}
      <div class="toolbar">${href ? UI.button({ label: actionLabel, icon: "open_in_new", href, variant: "primary" }) : ""}</div>
    </article>`;
  },

  panel({ title, subtitle = "", actions = "", body = "", footer = "" }) {
    return `<section class="panel">
      <header class="panel-header">
        <div>
          <h3 class="section-title">${esc(title)}</h3>
          ${subtitle ? `<div class="muted small">${esc(subtitle)}</div>` : ""}
        </div>
        ${actions ? `<div class="toolbar">${actions}</div>` : ""}
      </header>
      <div class="panel-body">${body}</div>
      ${footer ? `<footer class="panel-footer">${footer}</footer>` : ""}
    </section>`;
  },

  metric({ value, label, icon = "analytics", href = "" }) {
    const inner = `<div class="metric">
      <div class="toolbar-between">
        <div>
          <div class="metric-value">${esc(value)}</div>
          <div class="metric-label">${esc(label)}</div>
        </div>
        <div class="icon-tile">${UI.icon(icon)}</div>
      </div>
    </div>`;
    return href ? `<a href="${href}">${inner}</a>` : inner;
  },

  shell(active, title, subtitle, actions = "") {
    document.body.innerHTML = `<div class="app-shell">
      <aside class="sidebar">
        <a class="brand" href="${routes.home}">
          <span class="brand-mark">${UI.icon("terminal")}</span>
          <span>Proton 本地工具箱</span>
        </a>
        <nav class="nav">
          <div class="nav-section">工作台</div>
          ${navItems.map(item => `<a class="nav-item ${active === item.id ? "active" : ""}" href="${item.href}">
            ${UI.icon(item.icon)}<span>${item.label}</span>
          </a>`).join("")}
        </nav>
      </aside>
      <main class="main">
        <header class="topbar">
          <div>
            <h1 class="page-title">${esc(title)}</h1>
            ${subtitle ? `<p class="page-subtitle">${esc(subtitle)}</p>` : ""}
          </div>
          <div class="toolbar">${actions || UI.button({ label: "刷新", icon: "sync", id: "refresh-page" })}</div>
        </header>
        <section id="content" class="content-stack"></section>
      </main>
    </div>`;
    const refresh = document.querySelector("#refresh-page");
    if (refresh) refresh.addEventListener("click", () => location.reload());
  },

  field(field) {
    const value = field.default ?? "";
    if (field.type === "boolean") {
      return `<label class="checkbox-field">
        <span><b>${esc(field.label)}</b></span>
        <input name="${esc(field.name)}" type="checkbox" ${value ? "checked" : ""}>
      </label>`;
    }
    if (field.type === "textarea") {
      return `<label class="form-field"><span>${esc(field.label)}</span><textarea name="${esc(field.name)}" ${field.required ? "required" : ""}>${esc(value)}</textarea></label>`;
    }
    if (field.type === "select") {
      return `<label class="form-field"><span>${esc(field.label)}</span><select name="${esc(field.name)}">${(field.options || []).map(o => `<option value="${esc(o)}" ${o === value ? "selected" : ""}>${esc(optionLabel(field, o))}</option>`).join("")}</select></label>`;
    }
    const type = field.type === "number" ? "number" : "text";
    return `<label class="form-field"><span>${esc(field.label)}</span><input name="${esc(field.name)}" type="${type}" value="${esc(value)}" ${field.required ? "required" : ""}></label>`;
  },

  empty(message) {
    return `<div class="empty">${esc(message)}</div>`;
  },
};

function readForm(form) {
  const params = {};
  [...form.elements].forEach(el => {
    if (!el.name) return;
    params[el.name] = el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value;
  });
  return params;
}

function recordsTable(tasks) {
  if (!tasks.length) return UI.empty("暂无执行记录");
  return `<div class="table-wrap"><table>
    <thead><tr><th>任务</th><th>类型</th><th>状态</th><th>开始时间</th><th>耗时</th><th>操作</th></tr></thead>
    <tbody>${tasks.map(t => `<tr>
      <td><b>${esc(t.name)}</b><div class="muted mono">${esc(t.task_id)}</div></td>
      <td>${t.type === "flow" ? "固定流程" : "小工具"}</td>
      <td>${UI.tag(t.status)}</td>
      <td>${esc(t.started_at || "")}</td>
      <td>${esc(t.duration_seconds ?? "")}</td>
      <td>${UI.button({ label: "查看", icon: "visibility", href: `detail.html?id=${encodeURIComponent(t.task_id)}` })}</td>
    </tr>`).join("")}</tbody>
  </table></div>`;
}

async function pollTask(taskId) {
  const status = document.querySelector("#task-status");
  const log = document.querySelector("#task-log");
  const interval = setInterval(async () => {
    try {
      const task = await apiJson(`${API.tasks}/${taskId}`);
      const text = await fetch(`${API.tasks}/${taskId}/logs`).then(r => r.text());
      status.innerHTML = `${UI.tag(task.status)} ${task.current_step ? `<span class="muted small">${esc(task.current_step)}</span>` : ""}`;
      log.textContent = text;
      log.scrollTop = log.scrollHeight;
      if (["success", "failed", "canceled"].includes(task.status)) clearInterval(interval);
    } catch (err) {
      status.textContent = err.message;
      clearInterval(interval);
    }
  }, 900);
}

function iconForCategory(category) {
  if (category.includes("图片") || category.includes("视频")) return "perm_media";
  if (category.includes("文本") || category.includes("小说")) return "text_snippet";
  if (category.includes("文件")) return "folder";
  return "widgets";
}

window.ProtonCore = { API, routes, qs, esc, apiJson, UI, readForm, recordsTable, pollTask, iconForCategory };
