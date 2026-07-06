// content.js — Injected into every webpage
// Phase 6 fix: no auto-overlay. Shows a clean prompt when page has no notes.
// Overlay only appears if user explicitly enables it in Settings.

(function () {
  if (window.__notebookos_injected) return;
  window.__notebookos_injected = true;

  // ── Constants ──────────────────────────────────────────
  const PROMPT_DELAY_MS = 1200; // wait for page to settle before showing prompt
  const PROMPT_ID  = "__nos_prompt";
  const OVERLAY_ID = "__nos_overlay";

  // ── On load: check URL, show prompt if no notes ────────
  setTimeout(async () => {
    const settings = await getSettings();

    // Show prompt if page has no existing notes
    const url = normalizeUrl(location.href);
    const idx = await getUrlIndex();

    if (!idx[url]) {
      showNotePrompt();
    }

    // Overlay only if user explicitly enabled it AND notes exist
    if (settings.overlayEnabled && idx[url]) {
      createOverlay(idx[url]);
    }
  }, PROMPT_DELAY_MS);

  // ── Listen for messages from background/panel ──────────
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "TOGGLE_OVERLAY")  handleToggleOverlay();
    if (msg.type === "HIGHLIGHT_ADDED") appendHighlight(msg.text);
    if (msg.type === "NOTES_CREATED")   {
      // Side panel created notes — dismiss prompt, show overlay
      dismissPrompt();
    }
  });

  // ══════════════════════════════════════════════════════
  // PROMPT — "Take notes for this page?"
  // ══════════════════════════════════════════════════════
  function showNotePrompt() {
    if (document.getElementById(PROMPT_ID)) return;

    const el = document.createElement("div");
    el.id = PROMPT_ID;
    el.innerHTML = `
      <div class="nos-p-icon">📓</div>
      <div class="nos-p-text">Take notes for this page?</div>
      <div class="nos-p-btns">
        <button class="nos-p-yes" id="nos-p-yes">Open Notes</button>
        <button class="nos-p-no"  id="nos-p-no">✕</button>
      </div>
    `;
    document.documentElement.appendChild(el);

    // Animate in
    requestAnimationFrame(() => el.classList.add("nos-p-visible"));

    el.querySelector("#nos-p-yes").addEventListener("click", () => {
      dismissPrompt();
      // Ask background to open the side panel
      chrome.runtime.sendMessage({ type: "OPEN_SIDE_PANEL_FOR_TAB" }).catch(() => {});
    });

    el.querySelector("#nos-p-no").addEventListener("click", dismissPrompt);

    // Auto-dismiss after 8 seconds
    setTimeout(dismissPrompt, 8000);
  }

  function dismissPrompt() {
    const el = document.getElementById(PROMPT_ID);
    if (!el) return;
    el.classList.remove("nos-p-visible");
    setTimeout(() => el.remove(), 300);
  }

  // ══════════════════════════════════════════════════════
  // OVERLAY — only shown when explicitly enabled + notes exist
  // ══════════════════════════════════════════════════════
  let overlayEl   = null;
  let isDragging  = false;
  let dragOffX    = 0, dragOffY = 0;
  let currentPageId = null;

  async function createOverlay(pageId) {
    if (document.getElementById(OVERLAY_ID)) return;

    currentPageId = pageId;
    const result = await storageGet(`page_${pageId}`);
    const page   = result[`page_${pageId}`];
    if (!page) return;

    overlayEl = document.createElement("div");
    overlayEl.id = OVERLAY_ID;
    overlayEl.innerHTML = `
      <div class="nos-handle">
        <span class="nos-logo">📓</span>
        <span class="nos-title" id="nos-title">${esc(page.title || "Untitled")}</span>
        <div class="nos-hbtns">
          <button class="nos-ibtn" id="nos-min">−</button>
          <button class="nos-ibtn" id="nos-cls">✕</button>
        </div>
      </div>
      <div class="nos-body" id="nos-body">
        <div class="nos-editor" id="nos-editor" contenteditable="true"
          spellcheck="true" data-ph="Quick notes…"></div>
        <div class="nos-foot">
          <span class="nos-stat" id="nos-wc">0w</span>
          <span class="nos-stat" id="nos-sv">—</span>
        </div>
      </div>
    `;

    overlayEl.style.cssText = "right:24px;bottom:24px;";
    document.documentElement.appendChild(overlayEl);
    requestAnimationFrame(() => overlayEl.classList.add("nos-visible"));

    overlayEl.querySelector("#nos-editor").innerHTML = page.content || "";
    updateWordCount();

    bindOverlayEvents();
  }

  function bindOverlayEvents() {
    const handle = overlayEl.querySelector(".nos-handle");
    const body   = overlayEl.querySelector("#nos-body");
    const editor = overlayEl.querySelector("#nos-editor");

    // Drag
    handle.addEventListener("mousedown", e => {
      if (e.target.closest(".nos-ibtn")) return;
      isDragging = true;
      const r = overlayEl.getBoundingClientRect();
      dragOffX = e.clientX - r.left;
      dragOffY = e.clientY - r.top;
      e.preventDefault();
    });
    document.addEventListener("mousemove", e => {
      if (!isDragging) return;
      const x = Math.max(0, Math.min(e.clientX - dragOffX, window.innerWidth  - overlayEl.offsetWidth));
      const y = Math.max(0, Math.min(e.clientY - dragOffY, window.innerHeight - overlayEl.offsetHeight));
      overlayEl.style.left = x + "px"; overlayEl.style.top = y + "px";
      overlayEl.style.right = "auto";  overlayEl.style.bottom = "auto";
    });
    document.addEventListener("mouseup", () => { isDragging = false; });

    // Minimize
    overlayEl.querySelector("#nos-min").addEventListener("click", () => {
      const hidden = body.style.display === "none";
      body.style.display = hidden ? "" : "none";
      overlayEl.querySelector("#nos-min").textContent = hidden ? "−" : "+";
    });

    // Close
    overlayEl.querySelector("#nos-cls").addEventListener("click", () => {
      overlayEl.classList.remove("nos-visible");
      setTimeout(() => { overlayEl?.remove(); overlayEl = null; }, 300);
    });

    // Autosave
    let saveTimer;
    editor.addEventListener("input", () => {
      updateWordCount();
      setSv("saving");
      clearTimeout(saveTimer);
      saveTimer = setTimeout(saveNote, 2500);
    });

    overlayEl.addEventListener("click", e => e.stopPropagation());
  }

  async function saveNote() {
    if (!currentPageId) return;
    const editor  = overlayEl?.querySelector("#nos-editor");
    if (!editor) return;
    const result  = await storageGet(`page_${currentPageId}`);
    const page    = result[`page_${currentPageId}`];
    if (!page) return;
    await storageSet({ [`page_${currentPageId}`]: { ...page, content: editor.innerHTML, updatedAt: Date.now() } });
    setSv("saved");
  }

  function updateWordCount() {
    const editor = overlayEl?.querySelector("#nos-editor");
    const el     = overlayEl?.querySelector("#nos-wc");
    if (!editor || !el) return;
    const words = (editor.innerText || "").trim().split(/\s+/).filter(Boolean).length;
    el.textContent = words + "w";
  }

  function setSv(s) {
    const el = overlayEl?.querySelector("#nos-sv");
    if (!el) return;
    el.textContent  = s === "saved" ? "Saved" : s === "saving" ? "Saving…" : "—";
    el.style.color  = s === "saved" ? "#4caf50" : "";
  }

  async function handleToggleOverlay() {
    if (overlayEl) {
      overlayEl.classList.remove("nos-visible");
      setTimeout(() => { overlayEl?.remove(); overlayEl = null; }, 300);
      return;
    }
    const url = normalizeUrl(location.href);
    const idx = await getUrlIndex();
    if (idx[url]) createOverlay(idx[url]);
  }

  function appendHighlight(text) {
    // If overlay is open, append there
    if (overlayEl) {
      const editor = overlayEl.querySelector("#nos-editor");
      const bq = document.createElement("blockquote");
      bq.className = "nos-hl"; bq.textContent = text;
      editor.appendChild(bq);
      updateWordCount();
      setTimeout(saveNote, 2500);
    }
    // Always also send to side panel via runtime message (handled in sidepanel.js)
  }

  // ── Helpers ────────────────────────────────────────────
  function normalizeUrl(raw) {
    try { const u = new URL(raw); u.hash = ""; return u.toString(); } catch { return raw; }
  }
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
  function storageGet(k) { return new Promise(r => chrome.storage.sync.get(k, r)); }
  function storageSet(i) { return new Promise(r => chrome.storage.sync.set(i, r)); }
  async function getUrlIndex() { const r = await storageGet("url_index"); return r.url_index || {}; }
  async function getSettings() { const r = await storageGet("settings"); return r.settings || {}; }

})();
