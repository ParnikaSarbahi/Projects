<div align="center">

# 📓 NotebookOS

### Your Browser's College Bag

*Context-aware notes that auto-link to every webpage, organized into subject notebooks — right inside Chrome.*

![Manifest V3](https://img.shields.io/badge/Manifest-V3-blue)
![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla-yellow)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

</div>

---

## 📖 Overview

Most note-taking tools live in a separate tab from whatever you're actually researching — constant context-switching, lost notes, manual organizing. **NotebookOS** closes that gap: every webpage can have its own notes, automatically linked to its URL.

Open a page you've taken notes on before → your notes are already there. Open a new page → NotebookOS asks if you'd like to start one. Organize everything into subject "notebooks," just like a physical college bag.

> Built from the ground up as a hands-on project — including real debugging of Chrome extension architecture, storage quota constraints, and Content Security Policy rules. See [Lessons Learned](#-lessons-learned).

---

## ✨ Features

| | |
|---|---|
| 🔗 **URL-linked notes** | Notes bind to the exact page URL and auto-load on revisit |
| 📚 **Subject notebooks** | Color-coded notebooks, like college subjects |
| ⚡ **O(1) URL lookup** | Maintained URL→page index avoids scanning every note |
| ✍️ **Rich text editor** | Headings, lists, code blocks, highlights, slash commands (`/`) |
| 🪟 **Floating overlay** | Draggable, minimizable note widget on any page |
| 📊 **Dashboard** | Grid/list views, search, sort, export/import JSON backups |
| 🔒 **Optional lock** | SHA-256 password gate on the dashboard |
| 💾 **Local-first storage** | All data stays in your browser via `chrome.storage.local` |

---



---

## 🚀 Installation

Since this isn't published to the Chrome Web Store yet, install it in developer mode:

```bash
git clone https://github.com/ParnikaSarbahi/Projects.git
```

1. Open Chrome and go to `chrome://extensions`
2. Toggle **Developer mode** on (top-right)
3. Click **Load unpacked**
4. Select the `NotebookOS` folder
5. Pin the extension from the puzzle-piece icon in your toolbar

---

## ⌨️ Keyboard Shortcuts

| Action | Shortcut |
|---|---|
| Open side panel | `Ctrl+Shift+N` |
| Slash command menu | `/` at line start |
| Bold / Italic | `Ctrl+B` / `Ctrl+I` |
| Insert link | `Ctrl+K` |
| Inline code | `` Ctrl+` `` |
| Force save | `Ctrl+S` |
| Add selection to notes | Right-click → *Add to NotebookOS* |

---

## 🏗️ Architecture

```
NotebookOS/
├── manifest.json
├── icons/
├── pages/
│   ├── sidepanel.html      # Main note-taking UI
│   ├── dashboard.html      # Notebook manager
│   └── onboarding.html     # First-run welcome page
├── scripts/
│   ├── background.js       # Service worker — badge, menus, tab events
│   ├── content.js          # Injected overlay widget
│   ├── storage.js          # Data layer — CRUD, URL index, export/import
│   ├── sidepanel.js        # Side panel controller + editor
│   └── dashboard.js        # Dashboard controller
└── styles/
    ├── main.css             # Design tokens & shared components
    ├── sidepanel.css
    ├── dashboard.css
    └── overlay.css
```

### Storage model

```
notebook_index   → string[]         # all notebook IDs
url_index        → { url: pageId }  # O(1) URL → page lookup
notebook_<id>    → Notebook object
page_<id>        → Page object
settings         → Settings object
```

All storage runs through `chrome.storage.local` (with the `unlimitedStorage` permission), accessed exclusively via `storage.js`'s public API — no other file touches `chrome.storage` directly except the isolated content script, which keeps its own minimal read/write helpers (content scripts can't import other extension scripts normally).

### Key design decisions

- **`chrome.storage.local` over `chrome.storage.sync`** — `sync` caps items at 8KB, which broke immediately with image-containing notes. Local storage + `unlimitedStorage` removes that ceiling at the cost of deferring cross-device sync to a future release.
- **Separation of concerns** — UI controllers never touch `chrome.storage` directly; they call `window.NotebookStorage`'s public methods.
- **Background-mediated side panel opening** — `chrome.sidePanel.open()` requires a trusted context, so the content script's "Open Notes" prompt messages the background service worker to open the panel on its behalf.
- **No inline scripts** — Chrome's extension CSP blocks inline `<script>` blocks; all logic lives in linked `.js` files.

---

## 🗺️ Roadmap

- [ ] Migrate to IndexedDB (via Dexie.js) for structured querying at scale
- [ ] Opt-in cloud sync (Supabase/Firebase) for real cross-device support
- [ ] Replace `document.execCommand`-based editor with Tiptap
- [ ] Normalize URL matching (strip query params/fragments) instead of exact-match
- [ ] Publish to Chrome Web Store

---

## 🧠 Lessons Learned

- **Storage quotas are a design decision, not an afterthought** — `chrome.storage.sync`'s 8KB/item limit looked fine on paper, broke immediately with real content. Validate storage limits against realistic data *before* building on top of them.
- **DOM load order matters** — `<script>` tags placed before the elements they reference cause `null` errors. Scripts belong just before `</body>`.
- **Extension CSP is strict by design** — inline scripts are blocked outright, forcing clean separation between markup and logic.
- **Extension contexts are isolated** — content scripts, the background worker, and extension pages can't share JS state directly; they communicate via `chrome.storage` and `chrome.runtime` message passing.

---

## 🔐 Privacy & Security

- No data leaves your browser — everything is stored locally via `chrome.storage.local`
- No analytics, no tracking, no external network requests
- Optional dashboard password is hashed locally with SHA-256 (Web Crypto API) — **note:** this is a UI-level deterrent, not encryption; it doesn't protect data from someone with direct filesystem access

See [`PRIVACY_POLICY.md`](./PRIVACY_POLICY.md) for full details.

---

## 🛠️ Built With

- Vanilla JavaScript (ES6+)
- Chrome Extension Manifest V3
- `chrome.storage`, `chrome.tabs`, `chrome.sidePanel`, `chrome.contextMenus`, `chrome.commands`
- Web Crypto API (SHA-256)

---

## 📄 License

MIT — free to use, modify, and distribute.

---

<div align="center">

Made as a learning project — feedback and issues welcome.

</div>
