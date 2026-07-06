// background.js

function registerMenus() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: "add-to-notebookos", title: "📓 Add to NotebookOS", contexts: ["selection"] });
    chrome.contextMenus.create({ id: "toggle-overlay",    title: "📓 Toggle Overlay",     contexts: ["page"] });
  });
}

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    chrome.storage.sync.set({
      settings: { darkMode: false, overlayEnabled: false, dashboardLocked: false, passwordHash: null },
      notebook_index: [],
      url_index: {}
    });
    chrome.tabs.create({ url: chrome.runtime.getURL("pages/onboarding.html") });
  }
  registerMenus();
});

chrome.runtime.onStartup.addListener(registerMenus);

// ── Keyboard commands ──────────────────────────────────────
chrome.commands.onCommand.addListener(async (command) => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  if (command === "open-panel")    chrome.sidePanel.open({ tabId: tab.id });
  if (command === "toggle-overlay") chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_OVERLAY" }).catch(() => {});
});

// ── Icon click ─────────────────────────────────────────────
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

// ── Content script prompt button → open side panel ─────────
// Must be handled here because sidePanel.open() requires a trusted context.
// The content script sends OPEN_SIDE_PANEL_FOR_TAB with its tabId via sender.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "OPEN_SIDE_PANEL_FOR_TAB") {
    const tabId = sender.tab?.id;
    if (tabId) {
      chrome.sidePanel.open({ tabId })
        .then(() => sendResponse({ ok: true }))
        .catch((err) => sendResponse({ ok: false, err: err.message }));
    }
    return true; // keep channel open for async sendResponse
  }
});

// ── Context menus ──────────────────────────────────────────
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "add-to-notebookos") {
    chrome.runtime.sendMessage({ type: "HIGHLIGHT_ADDED", text: info.selectionText, url: tab.url }).catch(() => {});
    chrome.tabs.sendMessage(tab.id, { type: "HIGHLIGHT_ADDED", text: info.selectionText }).catch(() => {});
  }
  if (info.menuItemId === "toggle-overlay") {
    chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_OVERLAY" }).catch(() => {});
  }
});

// ── Badge ──────────────────────────────────────────────────
async function updateBadge(tabId, url) {
  if (!url || url.startsWith("chrome://") || url.startsWith("about:")) {
    chrome.action.setBadgeText({ text: "", tabId });
    return;
  }
  try {
    let normalized = url;
    try { const u = new URL(url); u.hash = ""; normalized = u.toString(); } catch {}
    const { url_index = {} } = await chrome.storage.sync.get("url_index");
    chrome.action.setBadgeText({ text: normalized in url_index ? "●" : "", tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#BFD7EA", tabId });
    chrome.action.setBadgeTextColor({ color: "#1A1A1A", tabId });
  } catch {
    chrome.action.setBadgeText({ text: "", tabId });
  }
}

// ── Tab listeners ──────────────────────────────────────────
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (tab.url) {
      updateBadge(tabId, tab.url);
      chrome.runtime.sendMessage({ type: "TAB_CHANGED", url: tab.url, title: tab.title }).catch(() => {});
    }
  } catch {}
});

chrome.tabs.onUpdated.addListener((tabId, change, tab) => {
  if (change.status === "complete" && tab.url) {
    updateBadge(tabId, tab.url);
    chrome.runtime.sendMessage({ type: "TAB_CHANGED", url: tab.url, title: tab.title }).catch(() => {});
  }
});

chrome.storage.onChanged.addListener(async (changes, area) => {
  if (area !== "sync" || !changes.url_index) return;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url) updateBadge(tab.id, tab.url);
  } catch {}
});