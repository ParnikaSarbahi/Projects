// background.js — Service Worker for NotebookOS
// Phase 2: initializes url_index on install, smarter tab change detection.

// ─── On Install ──────────────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    chrome.storage.sync.set({
      settings: { darkMode: false, overlayEnabled: true, dashboardLocked: false, passwordHash: null },
      notebook_index: [],
      url_index: {}    // Phase 2: URL → pageId map
    });
    console.log("[NotebookOS] Installed. Storage initialized.");
  }

  // Register context menu
  chrome.contextMenus.create({
    id: "add-to-notebookos",
    title: "Add to NotebookOS",
    contexts: ["selection"]
  });
});

// ─── Open Side Panel on Icon Click ───────────────────────────────────────────
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

// ─── Context Menu Handler ─────────────────────────────────────────────────────
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "add-to-notebookos") {
    chrome.runtime.sendMessage({
      type: "HIGHLIGHT_ADDED",
      text: info.selectionText,
      url: tab.url
    }).catch(() => {});
  }
});

// ─── Tab Navigation Listener ──────────────────────────────────────────────────
// Fires when user switches to a different tab
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab.url) notifyTabChanged(tab.url, tab.title);
  } catch {}
});

// Fires when the URL changes within a tab (navigation, SPA routing)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only fire on full load completion to avoid mid-navigation noise
  if (changeInfo.status === "complete" && tab.url) {
    notifyTabChanged(tab.url, tab.title);
  }
});

function notifyTabChanged(url, title) {
  chrome.runtime.sendMessage({ type: "TAB_CHANGED", url, title }).catch(() => {
    // Side panel not open — silently ignore
  });
}
