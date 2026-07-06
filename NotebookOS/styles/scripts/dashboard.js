// dashboard.js — Phase 4
// Full rewrite: grid/list toggle, sort, search, sidebar shortcuts,
// notebook detail, page management, storage bar, export/import, repair.

// ── State ──────────────────────────────────────────────────
const S = {
  notebooks: [],
  view: "all",           // all | recent | detail
  layout: "grid",        // grid | list
  sort: "updated",
  activeNbId: null,
  selectedColor: "#BFD7EA",
  editingNbId: null,     // null = creating, id = editing
};

// ── DOM ────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = s => [...document.querySelectorAll(s)];

function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

function toast(msg, type = "") {
  const el = $("toast");
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3000);
}

function fmt(ts) {
  return new Date(ts).toLocaleDateString([], { month: "short", day: "numeric" });
}

// ── Init ───────────────────────────────────────────────────
async function init() {
  await applyTheme();
  await loadNotebooks();
  renderAll();
  renderStorageBar();
  bindEvents();
}

async function applyTheme() {
  const s = await NotebookStorage.getSettings();
  document.documentElement.setAttribute("data-theme", s.darkMode ? "dark" : "");
}

async function loadNotebooks() {
  S.notebooks = await NotebookStorage.getAllNotebooks();
  sortNotebooks();
}

function sortNotebooks() {
  S.notebooks.sort((a, b) => {
    if (S.sort === "updated") return b.updatedAt - a.updatedAt;
    if (S.sort === "created") return b.createdAt - a.createdAt;
    if (S.sort === "name")    return a.name.localeCompare(b.name);
    if (S.sort === "pages")   return b.pageIds.length - a.pageIds.length;
  });
}

// ── Render all ─────────────────────────────────────────────
function renderAll() {
  renderSidebarShortcuts();
  if (S.view === "all")    renderGrid();
  if (S.view === "recent") renderRecent();
  if (S.view === "detail") renderDetail(S.activeNbId);
}

// ── Sidebar shortcuts ──────────────────────────────────────
function renderSidebarShortcuts() {
  const el = $("nb-shortcuts");
  el.innerHTML = "";
  S.notebooks.forEach(nb => {
    const btn = document.createElement("button");
    btn.className = "nav-nb-item" + (S.activeNbId === nb.id && S.view === "detail" ? " active" : "");
    btn.innerHTML = `
      <span class="nav-nb-dot" style="background:${nb.color}"></span>
      <span class="truncate" style="flex:1">${esc(nb.name)}</span>
      <span class="nav-nb-count">${nb.pageIds.length}</span>
    `;
    btn.addEventListener("click", () => switchView("detail", nb.id));
    el.appendChild(btn);
  });
}

// ── Notebooks grid / list ──────────────────────────────────
function renderGrid(query = "") {
  const grid = $("notebooks-grid");
  const q = query.toLowerCase();
  const filtered = S.notebooks.filter(nb => !q || nb.name.toLowerCase().includes(q));

  if (!filtered.length) {
    grid.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div class="empty-icon">📚</div>
      <div class="empty-msg">${q ? "No notebooks match your search." : "No notebooks yet. Create one →"}</div>
    </div>`;
    return;
  }

  grid.className = `nb-grid${S.layout === "list" ? " list-layout" : ""}`;
  grid.innerHTML = "";

  filtered.forEach(nb => {
    const el = S.layout === "grid" ? makeGridCard(nb) : makeListRow(nb);
    grid.appendChild(el);
  });
}

function makeGridCard(nb) {
  const card = document.createElement("div");
  card.className = "nb-card";
  card.innerHTML = `
    <div class="nb-card-banner" style="background:${nb.color}20;border-bottom:3px solid ${nb.color}">
      <span class="nb-card-emoji">📓</span>
    </div>
    <div class="nb-card-body">
      <div class="nb-card-name">${esc(nb.name)}</div>
      <div class="nb-card-meta">${nb.pageIds.length} page${nb.pageIds.length !== 1 ? "s" : ""} · ${fmt(nb.updatedAt)}</div>
    </div>
    <div class="nb-card-foot">
      <button class="btn btn-ghost btn-sm" data-action="open" data-id="${nb.id}">Open</button>
      <button class="btn btn-ghost btn-sm" data-action="rename" data-id="${nb.id}">Rename</button>
      <button class="btn btn-ghost btn-sm" data-action="delete" data-id="${nb.id}" style="color:#e05;margin-left:auto">Delete</button>
    </div>
  `;
  card.querySelector(".nb-card-banner").addEventListener("click", () => switchView("detail", nb.id));
  card.querySelector(".nb-card-body").addEventListener("click", () => switchView("detail", nb.id));
  card.querySelectorAll("[data-action]").forEach(btn => btn.addEventListener("click", e => {
    e.stopPropagation();
    handleNbAction(btn.dataset.action, btn.dataset.id);
  }));
  return card;
}

function makeListRow(nb) {
  const row = document.createElement("div");
  row.className = "nb-list-row";
  row.innerHTML = `
    <div class="nb-list-color" style="background:${nb.color}"></div>
    <div class="nb-list-info">
      <div class="nb-list-name">${esc(nb.name)}</div>
      <div class="nb-list-meta">${nb.pageIds.length} pages · edited ${fmt(nb.updatedAt)}</div>
    </div>
    <div class="nb-list-actions">
      <button class="btn btn-ghost btn-sm" data-action="rename" data-id="${nb.id}">Rename</button>
      <button class="btn btn-ghost btn-sm" data-action="delete" data-id="${nb.id}" style="color:#e05">Delete</button>
    </div>
  `;
  row.addEventListener("click", e => {
    if (!e.target.closest("[data-action]")) switchView("detail", nb.id);
  });
  row.querySelectorAll("[data-action]").forEach(btn => btn.addEventListener("click", e => {
    e.stopPropagation();
    handleNbAction(btn.dataset.action, btn.dataset.id);
  }));
  return row;
}

async function handleNbAction(action, id) {
  if (action === "open")   return switchView("detail", id);
  if (action === "rename") return openModal(id);
  if (action === "delete") {
    const nb = S.notebooks.find(n => n.id === id);
    if (!nb) return;
    if (!confirm(`Delete "${nb.name}" and all ${nb.pageIds.length} pages?`)) return;
    await NotebookStorage.deleteNotebook(id);
    await loadNotebooks();
    if (S.activeNbId === id) switchView("all");
    else renderAll();
    toast("Notebook deleted.");
  }
}

// ── Recent pages ───────────────────────────────────────────
async function renderRecent(query = "") {
  const list = $("recent-list");
  list.innerHTML = `<div class="empty"><div class="empty-icon">⏳</div><div class="empty-msg">Loading…</div></div>`;

  const q = query.toLowerCase();
  let rows = [];
  for (const nb of S.notebooks) {
    for (const pid of nb.pageIds) {
      const p = await NotebookStorage.getPage(pid);
      if (p) rows.push({ page: p, nb });
    }
  }

  rows.sort((a, b) => b.page.updatedAt - a.page.updatedAt);
  if (q) rows = rows.filter(r => r.page.title.toLowerCase().includes(q) || r.page.url.toLowerCase().includes(q));
  rows = rows.slice(0, 40);

  list.innerHTML = "";
  if (!rows.length) {
    list.innerHTML = `<div class="empty"><div class="empty-icon">📄</div><div class="empty-msg">No pages yet.</div></div>`;
    return;
  }

  rows.forEach(({ page, nb }) => list.appendChild(makePageRow(page, nb, true)));
}

// ── Notebook detail ────────────────────────────────────────
async function renderDetail(nbId, query = "") {
  const nb = await NotebookStorage.getNotebook(nbId);
  if (!nb) return switchView("all");

  // Header
  const head = $("detail-head");
  head.innerHTML = `
    <div class="detail-stripe" style="background:${nb.color}"></div>
    <div>
      <div class="detail-name">${esc(nb.name)}</div>
      <div class="detail-meta">${nb.pageIds.length} page${nb.pageIds.length !== 1 ? "s" : ""} · created ${fmt(nb.createdAt)}</div>
    </div>
    <div class="detail-actions">
      <button class="btn btn-ghost btn-sm" id="det-rename">Rename</button>
      <button class="btn btn-ghost btn-sm" id="det-delete" style="color:#e05">Delete</button>
    </div>
  `;

  $("det-rename").addEventListener("click", () => openModal(nbId));
  $("det-delete").addEventListener("click", () => handleNbAction("delete", nbId));

  // Pages
  const list = $("detail-list");
  list.innerHTML = "";

  const q = query.toLowerCase();
  const pages = [];
  for (const pid of nb.pageIds) {
    const p = await NotebookStorage.getPage(pid);
    if (p) pages.push(p);
  }
  pages.sort((a, b) => b.updatedAt - a.updatedAt);

  const filtered = q ? pages.filter(p => p.title.toLowerCase().includes(q) || p.url.toLowerCase().includes(q)) : pages;

  if (!filtered.length) {
    list.innerHTML = `<div class="empty">
      <div class="empty-icon">📄</div>
      <div class="empty-msg">${q ? "No pages match." : "Open a webpage and start taking notes to add pages here."}</div>
    </div>`;
    return;
  }

  filtered.forEach(p => list.appendChild(makePageRow(p, nb, false)));
}

function makePageRow(page, nb, showNb) {
  const row = document.createElement("div");
  row.className = "page-row";
  row.innerHTML = `
    <div class="page-row-icon">📄</div>
    <div class="page-row-body">
      <div class="page-row-title">${esc(page.title || "Untitled")}</div>
      <div class="page-row-url">${esc(page.url)}</div>
    </div>
    <div class="page-row-right">
      <span class="page-row-date">${fmt(page.updatedAt)}</span>
      ${showNb ? `<span class="page-nb-tag">
        <span style="width:6px;height:6px;border-radius:50%;background:${nb.color};display:inline-block"></span>
        ${esc(nb.name)}
      </span>` : ""}
      <button class="btn btn-ghost btn-sm" data-pid="${page.id}" style="color:#e05;font-size:0.7rem">Delete</button>
    </div>
  `;
  row.addEventListener("click", e => {
    if (!e.target.closest("[data-pid]")) chrome.tabs.create({ url: page.url });
  });
  row.querySelector("[data-pid]").addEventListener("click", async e => {
    e.stopPropagation();
    if (!confirm(`Delete notes for "${page.title || page.url}"?`)) return;
    await NotebookStorage.deletePage(page.id);
    row.remove();
    // Refresh notebook count in state
    const nbIdx = S.notebooks.findIndex(n => n.id === nb.id);
    if (nbIdx !== -1) S.notebooks[nbIdx].pageIds = S.notebooks[nbIdx].pageIds.filter(id => id !== page.id);
    renderSidebarShortcuts();
    toast("Page deleted.");
  });
  return row;
}

// ── View switcher ──────────────────────────────────────────
function switchView(view, nbId = null) {
  S.view = view;
  S.activeNbId = nbId;

  $("view-all").classList.toggle("hidden", view !== "all");
  $("view-recent").classList.toggle("hidden", view !== "recent");
  $("view-detail").classList.toggle("hidden", view !== "detail");

  $$(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === view));
  $$(".nav-nb-item").forEach((el, i) => {
    el.classList.toggle("active", view === "detail" && S.notebooks[i]?.id === nbId);
  });

  if (view === "all") {
    $("view-title").textContent = "All Notebooks";
    $("view-sub").textContent = `${S.notebooks.length} notebook${S.notebooks.length !== 1 ? "s" : ""}`;
    renderGrid($("search-input").value);
    $("view-toggle").style.display = "";
  }
  if (view === "recent") {
    $("view-title").textContent = "Recent";
    $("view-sub").textContent = "Your latest notes";
    $("view-toggle").style.display = "none";
    renderRecent($("search-input").value);
  }
  if (view === "detail") {
    const nb = S.notebooks.find(n => n.id === nbId);
    $("view-title").textContent = nb?.name || "Notebook";
    $("view-sub").textContent = `${nb?.pageIds.length || 0} pages`;
    $("view-toggle").style.display = "none";
    renderDetail(nbId, $("search-input").value);
  }
}

// ── Storage bar ────────────────────────────────────────────
async function renderStorageBar() {
  const u = await NotebookStorage.getStorageUsage();
  const color = u.percent > 80 ? "#e05" : u.percent > 60 ? "#f90" : "var(--text-muted)";
  $("storage-bar").innerHTML = `
    <div style="display:flex;justify-content:space-between;margin-bottom:3px">
      <span>Sync storage</span>
      <span style="color:${color}">${u.percent}%</span>
    </div>
    <div class="storage-track">
      <div class="storage-fill" style="width:${u.percent}%;background:${color}"></div>
    </div>
    <div style="margin-top:3px">${u.usedKB}KB / ${u.totalKB}KB</div>
  `;
}

// ── Modal ──────────────────────────────────────────────────
function openModal(editId = null) {
  S.editingNbId = editId;
  S.selectedColor = "#BFD7EA";

  const nb = editId ? S.notebooks.find(n => n.id === editId) : null;
  $("modal-nb-title").textContent = editId ? "Rename Notebook" : "New Notebook";
  $("btn-modal-save").textContent = editId ? "Save" : "Create";
  $("modal-nb-name").value = nb?.name || "";

  if (nb) {
    S.selectedColor = nb.color;
    $$(".clr").forEach(d => d.classList.toggle("active", d.dataset.c === nb.color));
  } else {
    $$(".clr").forEach((d, i) => d.classList.toggle("active", i === 0));
  }

  $("modal-bg").classList.remove("hidden");
  $("modal-nb").style.display = "";
  setTimeout(() => $("modal-nb-name").focus(), 50);
}

function closeModal() {
  $("modal-bg").classList.add("hidden");
  $("modal-nb").style.display = "none";
}

$$(".clr").forEach(dot => {
  dot.addEventListener("click", () => {
    $$(".clr").forEach(d => d.classList.remove("active"));
    dot.classList.add("active");
    S.selectedColor = dot.dataset.c;
  });
});

$("btn-modal-save").addEventListener("click", async () => {
  const name = $("modal-nb-name").value.trim();
  if (!name) { $("modal-nb-name").focus(); return; }

  if (S.editingNbId) {
    await NotebookStorage.updateNotebook(S.editingNbId, { name, color: S.selectedColor });
    toast("Notebook updated.");
  } else {
    await NotebookStorage.createNotebook(name, S.selectedColor);
    toast("Notebook created.", "ok");
  }

  closeModal();
  await loadNotebooks();
  renderAll();
  renderStorageBar();
});

$("modal-nb-name").addEventListener("keydown", e => {
  if (e.key === "Enter") $("btn-modal-save").click();
  if (e.key === "Escape") closeModal();
});

$("btn-modal-close").addEventListener("click", closeModal);
$("btn-modal-cancel").addEventListener("click", closeModal);
$("modal-bg").addEventListener("click", e => { if (e.target === $("modal-bg")) closeModal(); });

// ── Bind all events ────────────────────────────────────────
function bindEvents() {
  // New notebook button
  $("btn-new-notebook").addEventListener("click", () => openModal(null));

  // Nav items
  $$(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => {
      switchView(btn.dataset.view);
    });
  });

  // Search
  let searchTimer;
  $("search-input").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const q = $("search-input").value;
      if (S.view === "all")    renderGrid(q);
      if (S.view === "recent") renderRecent(q);
      if (S.view === "detail") renderDetail(S.activeNbId, q);
    }, 200);
  });

  // Layout toggle
  $$(".vt-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      S.layout = btn.dataset.layout;
      $$(".vt-btn").forEach(b => b.classList.toggle("active", b === btn));
      if (S.view === "all") renderGrid($("search-input").value);
    });
  });

  // Sort
  $("sort-select").addEventListener("change", async () => {
    S.sort = $("sort-select").value;
    sortNotebooks();
    renderAll();
  });

  // Dark mode
  $("btn-dark").addEventListener("click", async () => {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    document.documentElement.setAttribute("data-theme", dark ? "" : "dark");
    const s = await NotebookStorage.getSettings();
    await NotebookStorage.saveSettings({ ...s, darkMode: !dark });
  });

  // Export
  $("btn-export").addEventListener("click", async () => {
    try {
      const data = await NotebookStorage.exportAllData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href = url;
      a.download = `notebookos-${new Date().toISOString().slice(0,10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast("Backup exported.", "ok");
    } catch (e) { toast("Export failed.", "err"); }
  });

  // Import
  $("btn-import").addEventListener("click", () => $("file-import").click());
  $("file-import").addEventListener("change", async e => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      if (!confirm(`Import ${data.notebooks?.length || 0} notebooks and ${data.pages?.length || 0} pages? Merges with existing data.`)) return;
      await NotebookStorage.importAllData(data);
      await loadNotebooks();
      renderAll();
      renderStorageBar();
      toast("Import complete.", "ok");
    } catch (e) { toast("Import failed: " + e.message, "err"); }
    e.target.value = "";
  });

  // Repair
  $("btn-repair").addEventListener("click", async () => {
    const r = await NotebookStorage.repairStorage();
    await loadNotebooks();
    renderAll();
    renderStorageBar();
    toast(r.fixed.length ? `Fixed ${r.fixed.length} issue(s).` : "Storage healthy.", "ok");
  });
}

// ── Start ──────────────────────────────────────────────────
init();
