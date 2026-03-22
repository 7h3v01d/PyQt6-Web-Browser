# Browser Upgrade — What Changed & How To Use It

## Files to replace / add

| File | Action |
|---|---|
| `browser.py` | **Replace** your existing one |
| `dialogs.py` | **Replace** your existing one |
| `new_tab.html` | **Add** (new file, place next to `browser.py`) |
| `bookmarks_v2.json` | Auto-created on first run (migrates your old bookmarks) |

---

## New Features

### 🌙 Dark Mode
- Applied to the whole Qt UI (toolbar, menus, tabs, panels) — not just web pages.
- Toggle: **Ctrl+Shift+D** or the 🌙 button in the toolbar.
- Preference saved in `settings.json`.

### ⚡ Speed Dial New Tab Page
- Every new tab opens `new_tab.html` — a dark page with a live clock, greeting, and your speed dial grid.
- Click any card to open the site.
- **+** card or "+ Add site" button to add a new tile (name + URL).
- Hover a card → × appears to remove it.
- The search bar on the page searches DuckDuckGo (or navigates directly if you type a URL).
- Speed dial data is stored in browser `localStorage` (persists across restarts).

### 📚 Smarter Bookmarks (Ctrl+Shift+O)
- Full manager with a **folder tree** on the left, **bookmark table** on the right.
- **Search bar** at the top — instant filter across titles and URLs.
- Right-click any bookmark for a context menu (Open / Edit / Delete).
- Adding a bookmark (**Ctrl+D**) now prompts for a folder.
- Data saved to `bookmarks_v2.json` (your old bookmarks are migrated automatically).

### 🔍 Better History (Ctrl+H)
- Live search bar — type to filter by site or URL instantly.
- Shows newest entries first.
- "Open in New Tab" button for the selected entry.
- "Clear All History" button.

### 📝 Note-Taking Sidebar (Ctrl+Shift+N)
- Dockable panel on the right side.
- **This Page** tab: notes are saved per-domain (e.g., separate note for `reddit.com`, `github.com`).
- **Global** tab: one persistent scratch pad not tied to any page.
- Notes auto-save as you type to `notes.json`.
- Quick list at the bottom shows all pages that have notes.

### 🗂 Session Restore
- Tabs are saved automatically when you close the browser.
- Restored on next launch (previous session loads on top of the new-tab page).
- **Ctrl+S** → File → "Save Session" to snapshot manually at any time.

### 📖 Reading Mode (Ctrl+Shift+R)
- Strips a page down to its article body in a clean dark serif layout.
- Font size A− / A+ controls in the injected reading bar.
- "Exit Reader" button goes back. Or just navigate away.

### 🔎 Find In Page (Ctrl+F)
- Shows a quick dialog; uses Qt's built-in `findText`.

### 🔍 Zoom (Ctrl+= / Ctrl+- / Ctrl+0)
- Per-tab zoom, resets with Ctrl+0.

---

## Keyboard Shortcuts Reference

### Navigation
| Shortcut | Action |
|---|---|
| `Alt+←` | Back |
| `Alt+→` | Forward |
| `F5` or `Ctrl+R` | Reload |
| `Ctrl+L` | Focus URL bar (select all) |
| `Alt+Home` | New tab (home page) |
| `Escape` | Stop loading |

### Tabs
| Shortcut | Action |
|---|---|
| `Ctrl+T` | New Tab |
| `Ctrl+W` | Close current tab |
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+Tab` | Previous tab |
| `Ctrl+1` – `Ctrl+8` | Jump to tab 1–8 |
| `Ctrl+9` | Jump to last tab |

### Page
| Shortcut | Action |
|---|---|
| `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Reset zoom |
| `Ctrl+F` | Find in page |
| `Ctrl+P` | Print |

### Browser Features
| Shortcut | Action |
|---|---|
| `Ctrl+D` | Bookmark this page |
| `Ctrl+Shift+O` | Open Bookmarks manager |
| `Ctrl+H` | Open History |
| `Ctrl+J` | Toggle Downloads panel |
| `Ctrl+Shift+N` | Toggle Notes sidebar |
| `Ctrl+Shift+R` | Reading Mode |
| `Ctrl+Shift+D` | Toggle Dark/Light Mode |
| `Ctrl+Shift+I` | Developer Tools |
| `F11` | Toggle fullscreen |
