// storage.js — The data layer of NotebookOS
// Phase 2: URL index for O(1) lookups, quota guard, integrity repair, export/import.

// ─── ID Generator ────────────────────────────────────────────────────────────
function generateId(prefix = "id") {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// ─── Low-level Chrome Storage Wrappers ───────────────────────────────────────
// Phase 1 used raw new Promise() everywhere. Phase 2 centralizes this.
// Now every storage call properly surfaces chrome.runtime.lastError.

function storageGet(keys) {
  return new Promise((resolve, reject) => {
    chrome.storage.sync.get(keys, (result) => {
      if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
      else resolve(result);
    });
  });
}

function storageSet(items) {
  return new Promise((resolve, reject) => {
    chrome.storage.sync.set(items, () => {
      if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
      else resolve();
    });
  });
}

function storageRemove(keys) {
  return new Promise((resolve, reject) => {
    chrome.storage.sync.remove(keys, () => {
      if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
      else resolve();
    });
  });
}

// ─── Quota Guard ─────────────────────────────────────────────────────────────
// Chrome Sync: 8192 bytes max per key. We warn at 7500 to give headroom.

const CONTENT_SIZE_LIMIT = 7500;

function estimateBytes(str) { return new Blob([str]).size; }

function checkContentSize(content) {
  const size = estimateBytes(content);
  if (size > CONTENT_SIZE_LIMIT) {
    const err = new Error(`Note is too large (${Math.round(size/1024)}KB). Max ~8KB per note.`);
    err.code = "QUOTA_EXCEEDED";
    throw err;
  }
}

// ─── URL Normalization ────────────────────────────────────────────────────────
// Strip #fragments (client-side only, same page).
// Keep ?query strings (different content).

function normalizeUrl(rawUrl) {
  try {
    const u = new URL(rawUrl);
    u.hash = "";
    return u.toString();
  } catch { return rawUrl; }
}

// ─── Settings ────────────────────────────────────────────────────────────────

async function getSettings() {
  const r = await storageGet("settings");
  return r.settings || { darkMode: false, overlayEnabled: true, dashboardLocked: false, passwordHash: null };
}

async function saveSettings(settings) { await storageSet({ settings }); }

// ─── Notebook Index ───────────────────────────────────────────────────────────

async function getNotebookIndex() {
  const r = await storageGet("notebook_index");
  return r.notebook_index || [];
}

async function saveNotebookIndex(index) { await storageSet({ notebook_index: index }); }

// ─── URL Index ────────────────────────────────────────────────────────────────
// THE KEY PHASE 2 ADDITION.
// Maps normalized URLs → page IDs for instant lookup.
// { "https://example.com/page": "pg_abc123" }
// Phase 1 searched ALL pages to find a URL match. That's O(n).
// Phase 2: getPageByUrl = 1 read always. O(1).

async function getUrlIndex() {
  const r = await storageGet("url_index");
  return r.url_index || {};
}

async function setUrlIndex(index) { await storageSet({ url_index: index }); }

async function registerUrl(url, pageId) {
  const idx = await getUrlIndex();
  idx[url] = pageId;
  await setUrlIndex(idx);
}

async function unregisterUrl(url) {
  const idx = await getUrlIndex();
  delete idx[url];
  await setUrlIndex(idx);
}

async function urlHasNotes(rawUrl) {
  const url = normalizeUrl(rawUrl);
  const idx = await getUrlIndex();
  return url in idx;
}

// ─── Notebooks ───────────────────────────────────────────────────────────────

async function getNotebook(notebookId) {
  const r = await storageGet(`notebook_${notebookId}`);
  return r[`notebook_${notebookId}`] || null;
}

async function getAllNotebooks() {
  const index = await getNotebookIndex();
  if (!index.length) return [];
  const keys = index.map(id => `notebook_${id}`);
  const r = await storageGet(keys);
  return keys.map(k => r[k]).filter(Boolean);
}

async function createNotebook(name, color = "#BFD7EA") {
  const id = generateId("nb");
  const notebook = { id, name, color, pageIds: [], createdAt: Date.now(), updatedAt: Date.now() };
  await storageSet({ [`notebook_${id}`]: notebook });
  const index = await getNotebookIndex();
  index.push(id);
  await saveNotebookIndex(index);
  return notebook;
}

async function updateNotebook(notebookId, updates) {
  const nb = await getNotebook(notebookId);
  if (!nb) throw new Error(`Notebook "${notebookId}" not found`);
  const updated = { ...nb, ...updates, updatedAt: Date.now() };
  await storageSet({ [`notebook_${notebookId}`]: updated });
  return updated;
}

async function renameNotebook(notebookId, newName) {
  return updateNotebook(notebookId, { name: newName.trim() });
}

async function deleteNotebook(notebookId) {
  const nb = await getNotebook(notebookId);
  if (!nb) return;
  for (const pageId of nb.pageIds) {
    await deletePage(pageId, { skipNotebookUpdate: true });
  }
  await storageRemove(`notebook_${notebookId}`);
  const index = await getNotebookIndex();
  await saveNotebookIndex(index.filter(id => id !== notebookId));
}

// ─── Pages ────────────────────────────────────────────────────────────────────

async function getPage(pageId) {
  const r = await storageGet(`page_${pageId}`);
  return r[`page_${pageId}`] || null;
}

// O(1) URL lookup — the payoff of maintaining the URL index
async function getPageByUrl(rawUrl) {
  const url = normalizeUrl(rawUrl);
  const idx = await getUrlIndex();
  const pageId = idx[url];
  if (!pageId) return null;
  return getPage(pageId);
}

async function createPage(notebookId, rawUrl, title = "Untitled Page") {
  const url = normalizeUrl(rawUrl);

  // Duplicate guard — typed error so callers can show appropriate UI
  const existing = await getPageByUrl(url);
  if (existing) {
    const err = new Error("This URL already has notes.");
    err.code = "DUPLICATE_URL";
    err.existingPage = existing;
    throw err;
  }

  const id = generateId("pg");
  const page = { id, notebookId, url, title, content: "", createdAt: Date.now(), updatedAt: Date.now() };

  await storageSet({ [`page_${id}`]: page });
  await registerUrl(url, id);

  const nb = await getNotebook(notebookId);
  if (!nb) throw new Error(`Notebook "${notebookId}" not found`);
  nb.pageIds.push(id);
  await updateNotebook(notebookId, { pageIds: nb.pageIds });

  return page;
}

async function savePage(pageId, content, title) {
  const page = await getPage(pageId);
  if (!page) throw new Error(`Page "${pageId}" not found`);
  if (content !== undefined) checkContentSize(content);

  const updated = {
    ...page,
    content:   content !== undefined ? content : page.content,
    title:     title   !== undefined ? (title.trim() || "Untitled Page") : page.title,
    updatedAt: Date.now()
  };

  await storageSet({ [`page_${pageId}`]: updated });
  return updated;
}

async function deletePage(pageId, opts = {}) {
  const page = await getPage(pageId);
  if (!page) return;
  await unregisterUrl(page.url);
  if (!opts.skipNotebookUpdate) {
    const nb = await getNotebook(page.notebookId);
    if (nb) await updateNotebook(nb.id, { pageIds: nb.pageIds.filter(id => id !== pageId) });
  }
  await storageRemove(`page_${pageId}`);
}

async function movePageToNotebook(pageId, newNotebookId) {
  const page = await getPage(pageId);
  if (!page) throw new Error(`Page "${pageId}" not found`);

  const oldNb = await getNotebook(page.notebookId);
  if (oldNb) await updateNotebook(oldNb.id, { pageIds: oldNb.pageIds.filter(id => id !== pageId) });

  const newNb = await getNotebook(newNotebookId);
  if (!newNb) throw new Error(`Target notebook "${newNotebookId}" not found`);
  newNb.pageIds.push(pageId);
  await updateNotebook(newNotebookId, { pageIds: newNb.pageIds });

  const updated = { ...page, notebookId: newNotebookId, updatedAt: Date.now() };
  await storageSet({ [`page_${pageId}`]: updated });
  return updated;
}

// ─── Storage Health & Repair ──────────────────────────────────────────────────
// Scans for and fixes: ghost page IDs, stale URL index entries, missing URL entries.

async function repairStorage() {
  const report = { fixed: [], warnings: [] };
  const notebooks = await getAllNotebooks();
  const urlIndex = await getUrlIndex();
  const newUrlIndex = { ...urlIndex };

  // 1. Remove ghost pageIds from notebooks
  for (const nb of notebooks) {
    const validPageIds = [];
    for (const pageId of nb.pageIds) {
      const page = await getPage(pageId);
      if (page) {
        validPageIds.push(pageId);
        // 3. Rebuild missing URL index entries
        if (!newUrlIndex[page.url]) {
          newUrlIndex[page.url] = pageId;
          report.fixed.push(`Rebuilt URL index for "${page.url}"`);
        }
      } else {
        report.fixed.push(`Removed ghost page "${pageId}" from "${nb.name}"`);
      }
    }
    if (validPageIds.length !== nb.pageIds.length) {
      await updateNotebook(nb.id, { pageIds: validPageIds });
    }
  }

  // 2. Remove stale URL index entries
  for (const [url, pageId] of Object.entries(urlIndex)) {
    const page = await getPage(pageId);
    if (!page) {
      delete newUrlIndex[url];
      report.fixed.push(`Removed stale URL entry for "${url}"`);
    }
  }

  await setUrlIndex(newUrlIndex);
  return report;
}

// ─── Storage Usage ────────────────────────────────────────────────────────────

async function getStorageUsage() {
  return new Promise((resolve) => {
    chrome.storage.sync.getBytesInUse(null, (bytes) => {
      const total = chrome.storage.sync.QUOTA_BYTES || 102400;
      resolve({ used: bytes, total, percent: Math.round((bytes / total) * 100), usedKB: Math.round(bytes / 1024), totalKB: Math.round(total / 1024) });
    });
  });
}

// ─── Export / Import ──────────────────────────────────────────────────────────

async function exportAllData() {
  const notebooks = await getAllNotebooks();
  const pages = [];
  for (const nb of notebooks) {
    for (const pageId of nb.pageIds) {
      const page = await getPage(pageId);
      if (page) pages.push(page);
    }
  }
  return {
    exportedAt: new Date().toISOString(),
    version: 2,
    settings: await getSettings(),
    notebooks,
    pages,
    urlIndex: await getUrlIndex()
  };
}

async function importAllData(data) {
  if (!data.notebooks || !data.pages) throw new Error("Invalid backup — missing notebooks or pages.");
  for (const nb of data.notebooks) await storageSet({ [`notebook_${nb.id}`]: nb });
  for (const pg of data.pages) await storageSet({ [`page_${pg.id}`]: pg });
  await saveNotebookIndex(data.notebooks.map(nb => nb.id));
  let urlIndex = data.urlIndex || {};
  if (!data.urlIndex) for (const pg of data.pages) urlIndex[pg.url] = pg.id;
  await setUrlIndex(urlIndex);
  if (data.settings) await saveSettings(data.settings);
}

// ─── Public API ───────────────────────────────────────────────────────────────
window.NotebookStorage = {
  normalizeUrl, urlHasNotes,
  getSettings, saveSettings,
  getNotebookIndex, getAllNotebooks, getNotebook, createNotebook, updateNotebook, renameNotebook, deleteNotebook,
  getPage, getPageByUrl, createPage, savePage, deletePage, movePageToNotebook,
  repairStorage, getStorageUsage, exportAllData, importAllData
};
