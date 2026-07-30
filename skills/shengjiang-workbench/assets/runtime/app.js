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

  const iconSvg = (name) => {
    const paths = {
      tasks: '<path d="m9 11 2 2 4-5"/><path d="M5 4h14v16H5z"/>',
      inbox: '<path d="M4 5h16v13H4z"/><path d="M4 14h5l2 2h2l2-2h5"/>',
      projects: '<path d="M4 7h6l2 2h8v10H4z"/>',
      knowledge: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M8 4v16"/>',
      content: '<path d="M4 20h4l11-11-4-4L4 16z"/><path d="m13 7 4 4"/>',
      meetings: '<circle cx="12" cy="12" r="8"/><path d="M12 8v5l3 2"/>',
      metrics: '<path d="M5 19V9M12 19V5M19 19v-7"/>',
      custom: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
      search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
      assistant: '<path d="m12 3 1.4 4.6L18 9l-4.6 1.4L12 15l-1.4-4.6L6 9l4.6-1.4z"/><path d="m18 15 .7 2.3L21 18l-2.3.7L18 21l-.7-2.3L15 18l2.3-.7z"/>',
      settings: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A7 7 0 0 0 15 6l-.3-2.6h-4L10.5 6A7 7 0 0 0 9 7.1l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1A7 7 0 0 0 10.5 18l.3 2.6h4L15 18a7 7 0 0 0 1.5-1.1l2.4 1 2-3.4-2-1.5a7 7 0 0 0 .1-1z"/>',
    };
    return `<svg class="line-icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.custom}</svg>`;
  };

  const moduleIcon = (type) => iconSvg(type);

  const renderNavigation = () => {
    let currentGroup = "";
    $("#navigation").innerHTML = modules.map((module) => {
      const group = module.group || "工作台";
      const heading = group !== currentGroup ? `<p class="nav-group">${escapeHtml(group)}</p>` : "";
      currentGroup = group;
      return `${heading}
        <button class="nav-item ${activeRoute === module.id ? "active" : ""}" type="button" data-route="${escapeHtml(module.id)}">
          <span>${moduleIcon(module.type)}</span><span>${escapeHtml(module.title)}</span>
        </button>
      `;
    }).join("");
    document.querySelectorAll(".utility-navigation [data-route]").forEach((button) => {
      button.classList.toggle("active", activeRoute === button.dataset.route);
    });
    const mobileIds = [modules[0]?.id, "inbox", "search", "assistant", "settings"].filter(
      (id, index, values) => id && values.indexOf(id) === index && (modules.some((module) => module.id === id) || ["search", "assistant", "settings"].includes(id))
    );
    const mobileLabels = { search: "搜索", assistant: "AI助手", settings: "设置" };
    const mobileIcons = {
      search: iconSvg("search"),
      assistant: iconSvg("assistant"),
      settings: iconSvg("settings"),
    };
    $("#mobileNavigation").innerHTML = mobileIds.map((id) => {
      const module = modules.find((item) => item.id === id);
      return `
        <button class="${activeRoute === id ? "active" : ""}" type="button" data-route="${escapeHtml(id)}">
          <span>${module ? moduleIcon(module.type) : mobileIcons[id]}</span>
          <small>${escapeHtml(module?.title || mobileLabels[id])}</small>
        </button>
      `;
    }).join("");
  };

  const allItems = () => modules.flatMap((module) =>
    (state.data[module.id] || []).map((item) => ({ ...item, module }))
  );

  const renderDashboardIntro = (module) => {
    if (module.id !== modules[0]?.id) return "";
    const items = allItems();
    const completed = items.filter((item) => ["done", "published", "reviewed", "sorted", "actioned"].includes(item.status)).length;
    const todayItems = state.data[module.id] || [];
    const todayDone = todayItems.filter((item) => item.status === "done").length;
    const todayProgress = todayItems.length ? Math.round((todayDone / todayItems.length) * 100) : 0;
    return `
      <section class="dashboard-head">
        <div>
          <p class="eyebrow">TODAY OVERVIEW</p>
          <h2>今天，从最重要的一件事开始</h2>
          <p>${escapeHtml(config.primary_goal || "把重要工作放进一个清晰的系统")}</p>
        </div>
        <div class="progress-ring" style="--progress:${todayProgress * 3.6}deg">
          <div><strong>${todayProgress}%</strong><span>今日进度</span></div>
        </div>
      </section>
      <section class="stats">
        <div class="stat"><strong>${todayItems.length}</strong><span>今日任务</span></div>
        <div class="stat"><strong>${items.length - completed}</strong><span>待处理内容</span></div>
        <div class="stat"><strong>${completed}</strong><span>累计完成与复盘</span></div>
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
        <div class="heading-actions">
          <button class="help-button" type="button" data-help="${escapeHtml(module.id)}" aria-label="查看模块说明">?</button>
          <button class="button primary" type="button" data-add="${escapeHtml(module.id)}">＋ 新增</button>
        </div>
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

  const renderSearch = () => {
    const results = allItems().filter(itemMatches);
    return `
      <section class="panel search-panel">
        <p class="eyebrow">GLOBAL SEARCH</p>
        <h2>全局搜索</h2>
        <p>从所有模块中查找任务、文章、错题、笔记和收集内容。</p>
      </section>
      <div class="section-heading">
        <div>
          <h2>${searchQuery ? `“${escapeHtml(searchQuery)}”的结果` : "全部内容"}</h2>
          <p>共 ${results.length} 条</p>
        </div>
      </div>
      ${results.length ? `<div class="grid">${results.map((item) => `
        <article class="card search-result">
          <span class="module-badge">${escapeHtml(item.module.title)}</span>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.note || "暂无补充说明")}</p>
          <div class="card-meta">
            <button class="status" type="button" data-route="${escapeHtml(item.module.id)}">打开模块</button>
          </div>
        </article>
      `).join("")}</div>` : `<div class="empty"><p>输入关键词，搜索整个工作台。</p></div>`}
    `;
  };

  const renderAssistant = () => `
    <section class="assistant-hero">
      <div class="assistant-mark">${iconSvg("assistant")}</div>
      <p class="eyebrow">AI ASSISTANT</p>
      <h2>你的工作台 AI 助手</h2>
      <p>可以继续接入模型 API，用于生成阅读、分析数据、复盘会议或整理收集箱。本地演示版不会把密钥写在网页里。</p>
    </section>
    <section class="panel">
      <h2>你可以这样问</h2>
      <div class="prompt-grid">
        <button type="button" data-ai-placeholder>生成一篇雅思阅读并标注重点词汇</button>
        <button type="button" data-ai-placeholder>分析错题本里最薄弱的三个知识点</button>
        <button type="button" data-ai-placeholder>根据今日完成情况生成复盘</button>
        <button type="button" data-ai-placeholder>整理收集箱并建议归档模块</button>
      </div>
      <label class="assistant-input">
        <textarea rows="4" placeholder="输入你想让 AI 完成的任务"></textarea>
        <button class="button primary" type="button" data-ai-placeholder>发送</button>
      </label>
      <p class="security-note">安全说明：接入真实 AI 时，API Key 必须保存在服务端或本机安全存储中。</p>
    </section>
  `;

  const render = () => {
    renderNavigation();
    const module = modules.find((item) => item.id === activeRoute);
    const utilityTitles = { search: "全局搜索", assistant: "AI 助手", settings: "设置与数据" };
    $("#pageTitle").textContent = utilityTitles[activeRoute] || module?.title || "工作台";
    if (activeRoute === "settings") {
      $("#content").innerHTML = renderSettings();
    } else if (activeRoute === "search") {
      $("#content").innerHTML = renderSearch();
    } else if (activeRoute === "assistant") {
      $("#content").innerHTML = renderAssistant();
    } else if (module) {
      $("#content").innerHTML = renderModule(module);
    } else {
      activeRoute = modules[0]?.id || "settings";
      return render();
    }
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
    if (event.target.closest("[data-add-active]")) {
      const target = modules.some((module) => module.id === activeRoute) ? activeRoute : modules[0]?.id;
      if (target) openComposer(target);
      return;
    }
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
    if (event.target.closest("[data-ai-placeholder]")) {
      window.alert("本地演示版尚未连接 AI。正式接入时会把 API Key 安全地保存在服务端，而不是网页文件里。");
    }
    const helpId = event.target.closest("[data-help]")?.dataset.help;
    if (helpId) {
      const module = modules.find((item) => item.id === helpId);
      if (module) window.alert(`${module.title}\n\n${module.description || "管理这一部分的工作"}\n\n可以新增内容、切换状态、搜索、删除，并在设置中导出备份。`);
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
    if (searchQuery) activeRoute = "search";
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
