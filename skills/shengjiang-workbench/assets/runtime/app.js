(() => {
  "use strict";

  const config = window.WORKBENCH_CONFIG || {};
  const modules = Array.isArray(config.modules) ? config.modules : [];
  const storageKey = `shengjiang-workbench:${config.id || "default"}:v1`;
  const statuses = {
    tasks: ["todo", "doing", "done"],
    inbox: ["new", "sorted"],
    projects: ["planned", "active", "done"],
    knowledge: ["new", "reviewed"],
    content: ["idea", "draft", "review", "published"],
    meetings: ["open", "actioned"],
    metrics: ["recorded", "reviewed"],
    custom: ["new", "doing", "done"],
  };
  const statusLabels = {
    todo: "待办", doing: "进行中", done: "已完成",
    new: "待整理", sorted: "已整理",
    planned: "待开始", active: "推进中",
    reviewed: "已复盘", idea: "想法", draft: "草稿",
    review: "待审核", published: "已发布",
    open: "待处理", actioned: "已行动",
    recorded: "已记录",
  };

  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value = "") => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

  const nowId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const initialData = () => {
    const data = {};
    modules.forEach((module) => {
      const seeds = config.starter_items?.[module.id] || [];
      data[module.id] = seeds.map((item) => ({
        id: item.id || nowId(),
        title: item.title || "未命名",
        note: item.note || "",
        status: item.status || (statuses[module.type] || statuses.custom)[0],
        created_at: item.created_at || new Date().toISOString(),
      }));
    });
    return data;
  };

  const loadState = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey));
      if (saved && saved.data) return saved;
    } catch (_) {}
    return { version: 1, data: initialData(), updated_at: new Date().toISOString() };
  };

  let state = loadState();
  let activeRoute = modules[0]?.id || "settings";
  let searchQuery = "";

  const save = () => {
    state.updated_at = new Date().toISOString();
    localStorage.setItem(storageKey, JSON.stringify(state));
  };

  const showToast = (message) => {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 1800);
  };

  const moduleIcon = (type) => ({
    tasks: "✓", inbox: "⌁", projects: "◇", knowledge: "▤",
    content: "✎", meetings: "◷", metrics: "↗", custom: "□",
  })[type] || "□";

  const renderNavigation = () => {
    $("#navigation").innerHTML = modules.map((module) => `
      <button class="nav-item ${activeRoute === module.id ? "active" : ""}" type="button" data-route="${escapeHtml(module.id)}">
        <span>${moduleIcon(module.type)}</span><span>${escapeHtml(module.title)}</span>
      </button>
    `).join("");
    document.querySelector('[data-route="settings"]')?.classList.toggle("active", activeRoute === "settings");
  };

  const allItems = () => modules.flatMap((module) =>
    (state.data[module.id] || []).map((item) => ({ ...item, module }))
  );

  const renderDashboardIntro = (module) => {
    if (module.id !== modules[0]?.id) return "";
    const items = allItems();
    const completed = items.filter((item) => ["done", "published", "reviewed", "sorted", "actioned"].includes(item.status)).length;
    return `
      <section class="hero">
        <p class="eyebrow">YOUR SYSTEM, YOUR WAY</p>
        <h2>${escapeHtml(config.primary_goal || "把重要工作放进一个清晰的系统")}</h2>
        <p>${escapeHtml(config.persona || "个人用户")} · 数据默认保存在当前浏览器，可随时导出备份。</p>
      </section>
      <section class="stats">
        <div class="stat"><strong>${items.length}</strong><span>全部内容</span></div>
        <div class="stat"><strong>${items.length - completed}</strong><span>仍需处理</span></div>
        <div class="stat"><strong>${completed}</strong><span>已完成或已整理</span></div>
      </section>
    `;
  };

  const itemMatches = (item) => {
    if (!searchQuery) return true;
    const haystack = `${item.title} ${item.note}`.toLowerCase();
    return haystack.includes(searchQuery.toLowerCase());
  };

  const renderModule = (module) => {
    const items = (state.data[module.id] || []).filter(itemMatches);
    const cards = items.map((item) => `
      <article class="card">
        <button class="delete" type="button" data-delete="${escapeHtml(item.id)}" data-module="${escapeHtml(module.id)}" aria-label="删除">×</button>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.note || "暂无补充说明")}</p>
        <div class="card-meta">
          <button class="status" type="button" data-cycle="${escapeHtml(item.id)}" data-module="${escapeHtml(module.id)}">
            ${escapeHtml(statusLabels[item.status] || item.status)}
          </button>
          <small>${new Date(item.created_at).toLocaleDateString("zh-CN")}</small>
        </div>
      </article>
    `).join("");

    return `
      ${renderDashboardIntro(module)}
      <div class="section-heading">
        <div>
          <h2>${escapeHtml(module.title)}</h2>
          <p>${escapeHtml(module.description || "管理这一部分的工作")}</p>
        </div>
        <button class="button primary" type="button" data-add="${escapeHtml(module.id)}">＋ 新增</button>
      </div>
      ${cards ? `<div class="grid">${cards}</div>` : `
        <div class="empty">
          <p>${searchQuery ? "没有找到匹配内容。" : "这里还没有内容，从第一条开始。"}</p>
          ${searchQuery ? "" : `<button class="button primary" type="button" data-add="${escapeHtml(module.id)}">新增第一条</button>`}
        </div>
      `}
    `;
  };

  const renderSettings = () => `
    <section class="panel">
      <p class="eyebrow">LOCAL FIRST</p>
      <h2>设置与数据</h2>
      <p>当前版本的数据保存在这台设备的浏览器里。清理浏览器数据可能导致内容丢失，请定期导出 JSON 备份。</p>
      <div class="panel-actions">
        <button class="button primary" type="button" data-export>导出备份</button>
        <button class="button secondary" type="button" data-import>导入备份</button>
        <button class="button danger" type="button" data-reset>恢复初始数据</button>
      </div>
    </section>
    <section class="panel">
      <h2>模块说明</h2>
      <div class="module-links">
        ${modules.map((module) => `
          <div class="module-link">
            <div><strong>${escapeHtml(module.title)}</strong><br><small>${escapeHtml(module.description || "")}</small></div>
            <button type="button" data-route="${escapeHtml(module.id)}">打开</button>
          </div>
        `).join("")}
      </div>
    </section>
    <section class="panel">
      <h2>能力边界</h2>
      <p>本地版不包含云同步、账号登录和真实 AI API。需要跨设备或 AI 助手时，应增加后端服务，并把密钥保存在服务端环境变量中，不能写进网页文件。</p>
    </section>
  `;

  const render = () => {
    renderNavigation();
    const module = modules.find((item) => item.id === activeRoute);
    $("#pageTitle").textContent = activeRoute === "settings" ? "设置与数据" : (module?.title || "工作台");
    $("#content").innerHTML = activeRoute === "settings" ? renderSettings() : renderModule(module);
    document.body.classList.remove("menu-open");
  };

  const openComposer = (moduleId) => {
    const module = modules.find((item) => item.id === moduleId);
    if (!module) return;
    $("#composerModule").value = moduleId;
    $("#composerTitle").textContent = `新增到${module.title}`;
    $("#itemTitle").value = "";
    $("#itemNote").value = "";
    $("#composer").showModal();
    $("#itemTitle").focus();
  };

  const cycleStatus = (moduleId, itemId) => {
    const module = modules.find((item) => item.id === moduleId);
    const item = (state.data[moduleId] || []).find((entry) => entry.id === itemId);
    if (!module || !item) return;
    const options = statuses[module.type] || statuses.custom;
    item.status = options[(options.indexOf(item.status) + 1) % options.length];
    save();
    render();
  };

  const deleteItem = (moduleId, itemId) => {
    if (!window.confirm("确定删除这条内容吗？")) return;
    state.data[moduleId] = (state.data[moduleId] || []).filter((item) => item.id !== itemId);
    save();
    render();
    showToast("已删除");
  };

  const exportData = () => {
    const payload = { app: "shengjiang-workbench", config_id: config.id, ...state };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = `${config.id || "workbench"}-backup-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(anchor.href);
    showToast("备份已导出");
  };

  const importData = async (file) => {
    try {
      const payload = JSON.parse(await file.text());
      if (payload.app !== "shengjiang-workbench" || !payload.data) throw new Error("invalid");
      state = { version: payload.version || 1, data: payload.data, updated_at: new Date().toISOString() };
      modules.forEach((module) => { if (!Array.isArray(state.data[module.id])) state.data[module.id] = []; });
      save();
      render();
      showToast("备份已导入");
    } catch (_) {
      window.alert("这不是有效的生姜工作台备份文件。");
    }
  };

  document.addEventListener("click", (event) => {
    const route = event.target.closest("[data-route]")?.dataset.route;
    if (route) { activeRoute = route; render(); return; }
    const add = event.target.closest("[data-add]")?.dataset.add;
    if (add) { openComposer(add); return; }
    const cycle = event.target.closest("[data-cycle]");
    if (cycle) { cycleStatus(cycle.dataset.module, cycle.dataset.cycle); return; }
    const remove = event.target.closest("[data-delete]");
    if (remove) { deleteItem(remove.dataset.module, remove.dataset.delete); return; }
    if (event.target.closest("[data-close-dialog]")) $("#composer").close();
    if (event.target.closest("[data-export]")) exportData();
    if (event.target.closest("[data-import]")) $("#importFile").click();
    if (event.target.closest("[data-reset]") && window.confirm("确定恢复初始数据吗？当前内容会被替换。")) {
      state = { version: 1, data: initialData(), updated_at: new Date().toISOString() };
      save(); render(); showToast("已恢复初始数据");
    }
  });

  $("#composerForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const moduleId = $("#composerModule").value;
    const module = modules.find((item) => item.id === moduleId);
    const options = statuses[module?.type] || statuses.custom;
    const item = {
      id: nowId(),
      title: $("#itemTitle").value.trim(),
      note: $("#itemNote").value.trim(),
      status: options[0],
      created_at: new Date().toISOString(),
    };
    if (!item.title) return;
    if (!Array.isArray(state.data[moduleId])) state.data[moduleId] = [];
    state.data[moduleId].unshift(item);
    save();
    $("#composer").close();
    render();
    showToast("已保存");
  });

  $("#globalSearch").addEventListener("input", (event) => {
    searchQuery = event.target.value.trim();
    if (activeRoute === "settings") activeRoute = modules[0]?.id || "settings";
    render();
  });

  $("#importFile").addEventListener("change", (event) => {
    const [file] = event.target.files;
    if (file) importData(file);
    event.target.value = "";
  });
  $("#menuButton").addEventListener("click", () => document.body.classList.toggle("menu-open"));

  document.documentElement.style.setProperty("--accent", config.accent || "#2f6b57");
  $("#brandName").textContent = config.name || "个人 AI 工作台";
  $("#brandOwner").textContent = config.owner || "本地工作台";
  $("#personaLabel").textContent = String(config.persona || "PERSONAL WORKBENCH").toUpperCase();
  document.title = config.name || "个人 AI 工作台";
  render();
})();
