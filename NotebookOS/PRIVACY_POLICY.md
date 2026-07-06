# Privacy Policy — NotebookOS

**Last updated: 2025**

## Data collection

NotebookOS collects **no data**. The extension does not transmit any information to any server operated by the developers.

## Where your data lives

All notes, notebooks, and settings are stored exclusively in **Chrome Sync** (`chrome.storage.sync`) — Google's built-in storage for extension data. This data is tied to your Google account and subject to [Google's Privacy Policy](https://policies.google.com/privacy).

## What is stored

- Your note content (HTML)
- Page titles and URLs you've taken notes on
- Notebook names and colors
- Settings (dark mode preference, overlay toggle, password hash)

## Passwords

If you enable dashboard password lock, your password is hashed locally using the **Web Crypto API (SHA-256)** before being stored. The plain-text password is never stored or transmitted anywhere.

## Permissions used

| Permission | Reason |
|---|---|
| `storage` | Save notes via Chrome Sync |
| `tabs` | Read the current tab's URL to load matching notes |
| `activeTab` | Access the current tab's URL on icon click |
| `scripting` | Inject the floating overlay widget |
| `contextMenus` | Right-click "Add to NotebookOS" menu |
| `sidePanel` | Open the note editor as a side panel |
| `<all_urls>` | Inject the overlay on any webpage you visit |

## Third-party services

None. NotebookOS makes no external network requests.

## Contact

If you have questions, open an issue on the project repository.
