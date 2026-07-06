// sidepanel.js — Phase 3: Full rich editor, slash commands,
// floating selection toolbar, keyboard shortcuts, active toolbar states.

// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════
const state = {
  currentUrl:       null,
  currentPageTitle: null,
  currentPage:      null,
  currentNotebook:  null,
  selectedColor:    "#BFD7EA",
  autosaveTimer:    null,
  isDirty:          false,
  lastKnownUrl:     null,
  slashOpen:        false,
  slashIndex:       0,    // for keyboard nav inside slash menu
};

// ═══════════════════════════════════════════════════════════════
// DOM HELPERS
// ═══════════════════════════════════════════════════════════════
const $  = id  => document.getElementById(id);
const $$ = sel => [...document.querySelectorAll(sel)];

const SCREENS = {
  loading:         $("state-loading"),
  newUrl:          $("state-new-url"),
  chooseNotebook:  $("state-choose-notebook"),
  editor:          $("state-editor"),
  empty:           $("state-empty"),
};

function showScreen(name) {
  Object.keys(SCREENS).forEach(k =>
    SCREENS[k].classList.toggle("hidden", k !== name)
  );
}

// ═══════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════
function toast(msg, type = "info") {
  const el = $("toast");
  el.textContent = msg;
  el.className = `toast visible ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("visible"), 3200);
}

// ═══════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════
async function init() {
  showScreen("loading");
  await applySettings();

  let tab;
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    tab = tabs[0];
  } catch {
    return showScreen("empty");
  }

  if (!tab?.url || isRestricted(tab.url)) return showScreen("empty");

  const url = NotebookStorage.normalizeUrl(tab.url);
  state.currentUrl       = url;
  state.currentPageTitle = tab.title || "Untitled Page";
  state.lastKnownUrl     = url;

  let page;
  try {
    page = await NotebookStorage.getPageByUrl(url);
  } catch (err) {
    toast("Storage error — try reloading.", "error");
    return showScreen("empty");
  }

  if (page) {
    const notebook = await NotebookStorage.getNotebook(page.notebookId);
    state.currentPage     = page;
    state.currentNotebook = notebook;
    openEditor();
  } else {
    $("current-url-display").textContent = truncateUrl(url, 52);
    $("current-url-display").title = url;
    showScreen("newUrl");
  }
}

function isRestricted(url) {
  return ["chrome://","chrome-extension://","about:","edge://","file://","about:blank"]
    .some(p => url.startsWith(p));
}

function truncateUrl(url, max) {
  return url.length > max ? url.slice(0, max - 1) + "…" : url;
}

async function applySettings() {
  const s = await NotebookStorage.getSettings();
  document.documentElement.setAttribute("data-theme", s.darkMode ? "dark" : "");
}

// ═══════════════════════════════════════════════════════════════
// WELCOME SCREEN
// ═══════════════════════════════════════════════════════════════
$("btn-start-notes").addEventListener("click", async () => {
  await populateNotebookList();
  showScreen("chooseNotebook");
});

$("btn-dismiss").addEventListener("click", () => showScreen("empty"));

$("btn-goto-dashboard").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("pages/dashboard.html") });
});

// ═══════════════════════════════════════════════════════════════
// NOTEBOOK CHOOSER
// ═══════════════════════════════════════════════════════════════
async function populateNotebookList() {
  const notebooks = (await NotebookStorage.getAllNotebooks())
    .sort((a, b) => b.updatedAt - a.updatedAt);

  const list = $("notebook-list");
  list.innerHTML = "";

  if (!notebooks.length) {
    list.innerHTML = `<p class="text-sm text-muted" style="text-align:center;padding:14px 0">
      No notebooks yet — create one below.
    </p>`;
    return;
  }

  notebooks.forEach(nb => {
    const btn = document.createElement("button");
    btn.className = "notebook-item";
    btn.innerHTML = `
      <span class="nb-dot" style="background:${nb.color}"></span>
      <span class="truncate">${esc(nb.name)}</span>
      <span class="notebook-item-meta">${nb.pageIds.length}p</span>
    `;
    btn.addEventListener("click", () => chooseNotebook(nb));
    list.appendChild(btn);
  });
}

async function chooseNotebook(notebook) {
  try {
    const page = await NotebookStorage.createPage(
      notebook.id, state.currentUrl, state.currentPageTitle
    );
    state.currentPage     = page;
    state.currentNotebook = notebook;
    openEditor();
  } catch (err) {
    if (err.code === "DUPLICATE_URL") {
      // URL already has notes — just open them
      toast(`Already in "${(await NotebookStorage.getNotebook(err.existingPage.notebookId))?.name}". Opening.`, "info");
      state.currentPage     = err.existingPage;
      state.currentNotebook = await NotebookStorage.getNotebook(err.existingPage.notebookId);
      openEditor();
    } else {
      toast(err.message || "Failed to create page.", "error");
    }
  }
}

$("btn-back-to-welcome").addEventListener("click", () => {
  $("current-url-display").textContent = truncateUrl(state.currentUrl, 52);
  showScreen("newUrl");
});

// ── Create new notebook form ─────────────────────────────────
$("btn-show-create-form").addEventListener("click", () => {
  $("create-notebook-form").classList.remove("hidden");
  $("btn-show-create-form").classList.add("hidden");
  $("new-notebook-name").focus();
});

$$(".color-dot").forEach(dot => {
  dot.addEventListener("click", () => {
    $$(".color-dot").forEach(d => d.classList.remove("active"));
    dot.classList.add("active");
    state.selectedColor = dot.dataset.color;
  });
});

$("btn-create-notebook").addEventListener("click", async () => {
  const name = $("new-notebook-name").value.trim();
  if (!name) { $("new-notebook-name").focus(); return; }
  const nb = await NotebookStorage.createNotebook(name, state.selectedColor);
  await chooseNotebook(nb);
});

$("new-notebook-name").addEventListener("keydown", e => {
  if (e.key === "Enter") $("btn-create-notebook").click();
});

// ═══════════════════════════════════════════════════════════════
// EDITOR — OPEN
// ═══════════════════════════════════════════════════════════════
function openEditor() {
  const { currentPage: page, currentNotebook: nb } = state;

  $("editor-nb-name").textContent = nb.name;
  $("editor-nb-color").style.background = nb.color;
  $("page-title-input").value = page.title || "";
  $("editor").innerHTML = page.content || "";

  updateStats();
  setSaveStatus("idle");
  showScreen("editor");

  // Focus at end of content
  setTimeout(() => {
    const ed = $("editor");
    ed.focus();
    const range = document.createRange();
    range.selectNodeContents(ed);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }, 80);
}

// ═══════════════════════════════════════════════════════════════
// TOOLBAR — COMMANDS
// ═══════════════════════════════════════════════════════════════

// Map command name → executor function
const COMMANDS = {
  bold:                () => document.execCommand("bold"),
  italic:              () => document.execCommand("italic"),
  underline:           () => document.execCommand("underline"),
  strikeThrough:       () => document.execCommand("strikeThrough"),
  insertUnorderedList: () => document.execCommand("insertUnorderedList"),
  insertOrderedList:   () => document.execCommand("insertOrderedList"),
  hiliteColor:         (val) => document.execCommand("hiliteColor", false, val || "#FFF176"),
  h1:    () => formatBlock("h1"),
  h2:    () => formatBlock("h2"),
  h3:    () => formatBlock("h3"),
  quote: () => formatBlock("blockquote"),
  code:  () => wrapInlineCode(),
  codeblock: () => insertCodeBlock(),
  hr:    () => insertHR(),
  createLink: () => {
    const url = prompt("Enter URL:");
    if (url) document.execCommand("createLink", false, url);
  },
};

function formatBlock(tag) {
  // If already in that block, unwrap it (toggle)
  const el = getParentBlock();
  if (el && el.tagName.toLowerCase() === tag) {
    document.execCommand("formatBlock", false, "p");
  } else {
    document.execCommand("formatBlock", false, tag);
  }
}

function getParentBlock() {
  const sel = window.getSelection();
  if (!sel.rangeCount) return null;
  let node = sel.getRangeAt(0).commonAncestorContainer;
  while (node && node !== $("editor")) {
    if (node.nodeType === 1) return node;
    node = node.parentNode;
  }
  return null;
}

function wrapInlineCode() {
  const sel = window.getSelection();
  if (!sel.rangeCount || sel.isCollapsed) return;
  const range = sel.getRangeAt(0);
  try {
    const code = document.createElement("code");
    range.surroundContents(code);
  } catch {
    document.execCommand("insertHTML", false, `<code>${esc(sel.toString())}</code>`);
  }
}

function insertCodeBlock() {
  const pre = `<pre><code>// code here</code></pre><p></p>`;
  document.execCommand("insertHTML", false, pre);
}

function insertHR() {
  document.execCommand("insertHTML", false, "<hr><p></p>");
}

// ── Toolbar button click ─────────────────────────────────────
$$(".tool-btn").forEach(btn => {
  btn.addEventListener("mousedown", e => e.preventDefault()); // keep focus in editor
  btn.addEventListener("click", () => {
    $("editor").focus();
    const cmd = btn.dataset.cmd;
    const val = btn.dataset.value;
    if (COMMANDS[cmd]) COMMANDS[cmd](val);
    updateToolbarState();
    triggerAutosave();
  });
});

// ── Floating selection toolbar ───────────────────────────────
$$(".sel-btn").forEach(btn => {
  btn.addEventListener("mousedown", e => e.preventDefault());
  btn.addEventListener("click", () => {
    const cmd = btn.dataset.cmd;
    const val = btn.dataset.value;
    $("editor").focus();
    if (COMMANDS[cmd]) COMMANDS[cmd](val);
    hideSelectionToolbar();
    triggerAutosave();
  });
});

// Show/hide floating toolbar on selection change
document.addEventListener("selectionchange", () => {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.toString().trim()) {
    hideSelectionToolbar();
    return;
  }
  // Only show if selection is inside the editor
  const ed = $("editor");
  if (!ed || !ed.contains(sel.anchorNode)) {
    hideSelectionToolbar();
    return;
  }
  positionSelectionToolbar(sel);
});

function positionSelectionToolbar(sel) {
  const tb = $("selection-toolbar");
  const rect = sel.getRangeAt(0).getBoundingClientRect();
  if (!rect.width) return;

  tb.classList.remove("hidden");
  const tbW = 180; // approximate toolbar width
  let left = rect.left + rect.width / 2 - tbW / 2;
  left = Math.max(8, Math.min(left, window.innerWidth - tbW - 8));
  const top = rect.top - 44;

  tb.style.left = `${left}px`;
  tb.style.top  = `${top < 8 ? rect.bottom + 8 : top}px`;
}

function hideSelectionToolbar() {
  $("selection-toolbar")?.classList.add("hidden");
}

// ── Toolbar active state ─────────────────────────────────────
function updateToolbarState() {
  const cmds = ["bold","italic","underline","strikeThrough",
                "insertUnorderedList","insertOrderedList"];
  cmds.forEach(cmd => {
    const btn = document.querySelector(`.tool-btn[data-cmd="${cmd}"]`);
    if (btn) btn.classList.toggle("active", document.queryCommandState(cmd));
  });

  // Heading active state
  const block = getParentBlock();
  const tag = block?.tagName?.toLowerCase();
  ["h1","h2","h3"].forEach(h => {
    const btn = document.querySelector(`.tool-btn[data-cmd="${h}"]`);
    if (btn) btn.classList.toggle("active", tag === h);
  });
}

// ═══════════════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════════════
$("editor").addEventListener("keydown", e => {
  const ctrl = e.ctrlKey || e.metaKey;

  // Standard shortcuts
  if (ctrl && e.key === "b") { e.preventDefault(); COMMANDS.bold(); }
  if (ctrl && e.key === "i") { e.preventDefault(); COMMANDS.italic(); }
  if (ctrl && e.key === "u") { e.preventDefault(); COMMANDS.underline(); }
  if (ctrl && e.key === "k") { e.preventDefault(); COMMANDS.createLink(); }

  // Ctrl+` = inline code
  if (ctrl && e.key === "`") { e.preventDefault(); COMMANDS.code(); }

  // Ctrl+S = force save
  if (ctrl && e.key === "s") { e.preventDefault(); saveCurrentPage(true); }

  // Slash command
  if (e.key === "/" && isAtLineStart()) {
    // Let the "/" be typed, then show menu
    setTimeout(() => openSlashMenu(), 0);
    return;
  }

  // Slash menu navigation
  if (state.slashOpen) {
    if (e.key === "Escape") { e.preventDefault(); closeSlashMenu(); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); navigateSlash(1); return; }
    if (e.key === "ArrowUp")   { e.preventDefault(); navigateSlash(-1); return; }
    if (e.key === "Enter") {
      e.preventDefault();
      executeSlashItem();
      return;
    }
    // Any other key closes menu
    if (!["ArrowLeft","ArrowRight","Shift"].includes(e.key)) {
      closeSlashMenu();
    }
  }

  // Tab → indent in lists
  if (e.key === "Tab") {
    e.preventDefault();
    document.execCommand(e.shiftKey ? "outdent" : "indent");
  }
});

function isAtLineStart() {
  const sel = window.getSelection();
  if (!sel.rangeCount) return false;
  const range = sel.getRangeAt(0);
  return range.startOffset === 0 ||
    range.startContainer.textContent.slice(0, range.startOffset).trim() === "";
}

// ═══════════════════════════════════════════════════════════════
// SLASH COMMANDS
// ═══════════════════════════════════════════════════════════════
function openSlashMenu() {
  const menu = $("slash-menu");
  state.slashOpen = true;
  state.slashIndex = 0;

  // Position below cursor
  const sel = window.getSelection();
  if (!sel.rangeCount) return;
  const rect = sel.getRangeAt(0).getBoundingClientRect();

  menu.style.left = `${Math.max(8, rect.left)}px`;
  menu.style.top  = `${rect.bottom + 6}px`;
  menu.classList.remove("hidden");

  highlightSlashItem(0);
}

function closeSlashMenu() {
  $("slash-menu").classList.add("hidden");
  state.slashOpen = false;
  state.slashIndex = 0;
  $$(".slash-item").forEach(el => el.classList.remove("selected"));
}

function navigateSlash(dir) {
  const items = $$(".slash-item");
  state.slashIndex = Math.max(0, Math.min(items.length - 1, state.slashIndex + dir));
  highlightSlashItem(state.slashIndex);
}

function highlightSlashItem(idx) {
  $$(".slash-item").forEach((el, i) => el.classList.toggle("selected", i === idx));
}

function executeSlashItem() {
  const items = $$(".slash-item");
  const item  = items[state.slashIndex];
  if (!item) return;
  triggerSlashCommand(item.dataset.cmd);
}

$$(".slash-item").forEach(item => {
  item.addEventListener("mousedown", e => e.preventDefault());
  item.addEventListener("click", () => {
    triggerSlashCommand(item.dataset.cmd);
  });
});

function triggerSlashCommand(cmd) {
  $("editor").focus();
  closeSlashMenu();

  // Delete the "/" that triggered the menu
  const sel = window.getSelection();
  if (sel.rangeCount) {
    const range = sel.getRangeAt(0);
    const node  = range.startContainer;
    if (node.nodeType === 3) {
      const text   = node.textContent;
      const offset = range.startOffset;
      // Find and remove the leading "/"
      if (text[offset - 1] === "/") {
        node.textContent = text.slice(0, offset - 1) + text.slice(offset);
        range.setStart(node, offset - 1);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
      }
    }
  }

  if (COMMANDS[cmd]) COMMANDS[cmd]();
  triggerAutosave();
}

// ═══════════════════════════════════════════════════════════════
// EDITOR EVENTS
// ═══════════════════════════════════════════════════════════════
$("editor").addEventListener("input", () => {
  updateStats();
  updateToolbarState();
  triggerAutosave();
});

$("editor").addEventListener("mouseup",  updateToolbarState);
$("editor").addEventListener("keyup",    updateToolbarState);

$("page-title-input").addEventListener("input", triggerAutosave);

// Tab key in title → jump to editor
$("page-title-input").addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === "Tab") {
    e.preventDefault();
    $("editor").focus();
  }
});

// ═══════════════════════════════════════════════════════════════
// AUTOSAVE
// ═══════════════════════════════════════════════════════════════
function triggerAutosave() {
  state.isDirty = true;
  setSaveStatus("saving");
  clearTimeout(state.autosaveTimer);
  state.autosaveTimer = setTimeout(() => saveCurrentPage(), 2500);
}

async function saveCurrentPage(force = false) {
  if (!state.currentPage) return;
  if (!state.isDirty && !force) return;

  const content = $("editor").innerHTML;
  const title   = $("page-title-input").value.trim() || "Untitled Page";

  try {
    const updated = await NotebookStorage.savePage(state.currentPage.id, content, title);
    state.currentPage = updated;
    state.isDirty     = false;
    setSaveStatus("saved");
  } catch (err) {
    if (err.code === "QUOTA_EXCEEDED") {
      toast("Note too large! Remove some content.", "error");
    } else {
      toast("Save failed.", "error");
    }
    setSaveStatus("error");
    console.error("[NotebookOS]", err);
  }
}

window.addEventListener("beforeunload", () => {
  if (state.isDirty && state.currentPage) {
    NotebookStorage.savePage(
      state.currentPage.id,
      $("editor").innerHTML,
      $("page-title-input").value.trim() || "Untitled Page"
    ).catch(() => {});
  }
});

// ═══════════════════════════════════════════════════════════════
// STATUS BAR
// ═══════════════════════════════════════════════════════════════
function updateStats() {
  const text  = ($("editor").innerText || "").trim();
  const words = text ? text.split(/\s+/).length : 0;
  const chars = ($("editor").innerText || "").length;
  $("word-count").textContent = `${words} word${words !== 1 ? "s" : ""}`;
  $("char-count").textContent = `${chars} chars`;
}

function setSaveStatus(status) {
  const el = $("save-status");
  el.className = `footer-stat save-status ${status}`;
  if (status === "saved") {
    el.textContent = `Saved ${new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}`;
  } else if (status === "saving") {
    el.textContent = "Saving…";
  } else if (status === "error") {
    el.textContent = "Save failed";
  } else {
    el.textContent = "—";
  }
}

// ═══════════════════════════════════════════════════════════════
// HEADER BUTTONS
// ═══════════════════════════════════════════════════════════════
$("btn-toggle-dark").addEventListener("click", async () => {
  const dark = document.documentElement.getAttribute("data-theme") === "dark";
  document.documentElement.setAttribute("data-theme", dark ? "" : "dark");
  const s = await NotebookStorage.getSettings();
  await NotebookStorage.saveSettings({ ...s, darkMode: !dark });
});

$("btn-open-dashboard").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("pages/dashboard.html") });
});

// ═══════════════════════════════════════════════════════════════
// TAB CHANGE LISTENER
// ═══════════════════════════════════════════════════════════════
chrome.runtime.onMessage.addListener(async (msg) => {
  if (msg.type === "TAB_CHANGED") {
    const newUrl = NotebookStorage.normalizeUrl(msg.url);
    if (newUrl === state.lastKnownUrl) return; // No real change

    if (state.isDirty) await saveCurrentPage();

    // Reset
    state.currentUrl       = newUrl;
    state.currentPageTitle = msg.title;
    state.currentPage      = null;
    state.currentNotebook  = null;
    state.lastKnownUrl     = newUrl;
    closeSlashMenu();

    await init();
  }

  if (msg.type === "HIGHLIGHT_ADDED" && state.currentPage) {
    $("editor").innerHTML += `<blockquote class="highlight-quote">${esc(msg.text)}</blockquote><p></p>`;
    triggerAutosave();
    toast("Highlight added to notes.", "success");
  }
});

// ═══════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════
function esc(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// ═══════════════════════════════════════════════════════════════
// START
// ═══════════════════════════════════════════════════════════════
init();
