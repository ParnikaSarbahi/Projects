# NotebookOS — Your Browser's College Bag

> Context-aware notes that auto-link to every webpage, organized into subject notebooks, synced across devices via your Google account.

---

## What it does

Every webpage you visit can have its own notes. Open NotebookOS, choose a subject notebook (like "Operating Systems" or "DBMS"), and start writing. When you come back to that URL — even days later — your notes are right there.

No searching. No copy-pasting URLs. No manual organizing.

---

## Installation (Development)

1. Download and unzip the extension folder
2. Open Chrome → `chrome://extensions`
3. Enable **Developer Mode** (top-right toggle)
4. Click **Load Unpacked** → select the `notebookos` folder
5. Pin the extension — click the 🧩 puzzle icon in the toolbar

---

## Keyboard Shortcuts

| Action | Shortcut |
|---|---|
| Open side panel | `Ctrl+Shift+N` |
| Toggle overlay | `Ctrl+Shift+O` |
| Slash command menu | `/` at line start |
| Bold | `Ctrl+B` |
| Italic | `Ctrl+I` |
| Insert link | `Ctrl+K` |
| Inline code | `Ctrl+`` ` |
| Force save | `Ctrl+S` |
| Add highlight to notes | Right-click → Add to NotebookOS |

---

## Features

### Core
- **URL-linked notes** — notes are bound to exact URLs, auto-loaded on revisit
- **Subject notebooks** — color-coded, like college subjects
- **Chrome Sync** — syncs across all devices via your Google account, zero infrastructure

### Editor
- Rich text: headings, lists, bold/italic/underline/strikethrough, code blocks, blockquotes, links, highlights
- Slash commands (`/`) — insert any block without reaching for the toolbar
- Floating selection toolbar — format selected text instantly
- Autosave every 2.5 seconds (debounced)
- Word + character count

### Dashboard
- Grid and list view toggle
- Sort by last edited / created / name / page count
- Live search across notebooks and pages
- Notebook rename with color change
- Per-notebook page management
- Export JSON backup / Import JSON backup
- Storage repair utility
- Sync quota usage bar

### Overlay
- Draggable floating widget on every webpage
- Minimizable, closeable
- Reads and writes the same notes as the side panel
- Auto-hides when notes don't exist for that URL
- Toggle via `Ctrl+Shift+O` or right-click menu

### Security
- Password lock on the dashboard (SHA-256 hash stored, never plain text)
- No external servers — all data stays in Chrome Sync

---

## Storage Design

NotebookOS uses `chrome.storage.sync` exclusively. Data is modular:

```
notebook_index     → string[]         (list of all notebook IDs)
url_index          → { url: pageId }  (O(1) URL lookup)
notebook_<id>      → Notebook object
page_<id>          → Page object
settings           → Settings object
```

Chrome Sync limits: ~8KB per key, ~100KB total. NotebookOS guards against quota overruns before every write.

---

## Project Structure

```
notebookos/
├── manifest.json
├── icons/
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
├── pages/
│   ├── sidepanel.html     # Main note-taking UI
│   ├── dashboard.html     # Notebook manager
│   └── onboarding.html    # First-run welcome page
├── scripts/
│   ├── background.js      # Service worker: badge, menus, tab events
│   ├── content.js         # Injected: floating overlay widget
│   ├── storage.js         # Data layer: all CRUD, URL index, export/import
│   ├── sidepanel.js       # Side panel controller + rich editor
│   └── dashboard.js       # Dashboard controller
└── styles/
    ├── main.css            # Design system: tokens, typography, components
    ├── sidepanel.css       # Side panel specific styles
    ├── dashboard.css       # Dashboard specific styles
    └── overlay.css         # Injected overlay styles (isolated)
```

---

## Build Phases

| Phase | Description |
|---|---|
| 1 | Foundation — manifest, folder structure, background worker, storage layer skeleton, side panel shell, dashboard shell |
| 2 | Storage hardening — URL index (O(1) lookups), quota guard, URL normalization, duplicate detection, repair utility, export/import |
| 3 | Rich editor — slash commands, floating selection toolbar, all formatting commands, keyboard shortcuts, toolbar active states |
| 4 | Dashboard — grid/list toggle, sort, debounced search, notebook shortcuts in sidebar, detail view, storage bar |
| 5 | Overlay + lock — content script floating widget, context menu highlight-to-note, password lock with SHA-256, settings modal |
| 6 | Polish — keyboard command shortcuts, extension badge, proper icons, onboarding page, README |

---

## Privacy

- **No data leaves your browser** except through Chrome's own sync service
- No analytics, no tracking, no external requests
- Notes are stored in your Google account's Chrome Sync storage — subject to Google's privacy policy
- Password hashes are computed locally with the Web Crypto API (SHA-256)

---

## License

MIT — free to use, modify, and distribute.
