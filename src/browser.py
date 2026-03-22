"""
browser.py  —  upgraded personal browser
New features vs original:
  • Dark mode  (system-aware + manual toggle, Ctrl+Shift+D)
  • Keyboard shortcuts  (full set, see SHORTCUTS section)
  • Session restore  (saves & restores tab URLs across restarts)
  • Reading mode  (Ctrl+Shift+R  — strips page to readable article)
  • Custom new-tab page  (speed dial + clock + search)
  • Note-taking sidebar  (Ctrl+Shift+N)
  • Smarter bookmarks via BookmarksDialog with folders & search
  • Improved history (search, clear)
  • Better download panel integration
"""

import sys
import json
import os
import urllib.request
from urllib.parse import urlparse, urlunparse
from importlib import import_module
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QLineEdit, QPushButton,
    QTabWidget, QMenu, QStatusBar, QListWidget,
    QDockWidget, QFileDialog, QInputDialog, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QVBoxLayout,
    QApplication, QWidget, QHBoxLayout
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest,
    QWebEngineScript, QWebEngineSettings
)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, Qt, QDateTime, QObject, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPalette, QColor, QFont

from interceptors import Plugin, ChainedInterceptor, AdBlockInterceptor
from dialogs import HistoryDialog, DevToolsDialog, PasswordManagerDialog, BookmarksDialog, NoteSidebar
from vault import Vault
from main_gui import DownloadPanel


# ─────────────────────────────────────────────────────────────────────────────
# Reading mode JS  — strips a page down to its article text
# ─────────────────────────────────────────────────────────────────────────────

READER_JS = r"""
(function() {
    // Find the largest block of text content
    const candidates = Array.from(document.querySelectorAll('article, main, [role="main"], .post-content, .article-body, .entry-content, #content, #main'));
    let best = null;
    let bestLen = 0;
    candidates.forEach(el => {
        const len = el.innerText.length;
        if (len > bestLen) { bestLen = len; best = el; }
    });
    if (!best && document.body.innerText.length > 100) best = document.body;
    if (!best) return;

    const title = document.title || '';
    const html = best.innerHTML;

    document.open();
    document.write(`<!DOCTYPE html><html><head>
    <meta charset="utf-8">
    <title>${title}</title>
    <style>
        body {
            font-family: Georgia, 'Times New Roman', serif;
            background: #1a1a2e;
            color: #e2e0d8;
            max-width: 720px;
            margin: 60px auto;
            padding: 0 24px 80px;
            font-size: 19px;
            line-height: 1.8;
        }
        h1,h2,h3,h4 { font-family: system-ui, sans-serif; color: #f1f0ea; }
        h1 { font-size: 2em; margin-bottom: 0.3em; }
        a { color: #818cf8; }
        img { max-width: 100%; border-radius: 8px; }
        pre, code { background: #2d2d44; border-radius: 6px; padding: 2px 6px; font-size: 0.85em; }
        blockquote { border-left: 3px solid #6366f1; margin-left: 0; padding-left: 20px; color: #94a3b8; }
        #reader-bar { position: fixed; top: 0; left: 0; right: 0; padding: 10px 24px;
                      background: rgba(15,17,23,0.9); backdrop-filter: blur(10px);
                      display: flex; align-items: center; gap: 16px; z-index: 9999;
                      border-bottom: 1px solid rgba(255,255,255,0.1); }
        #reader-bar span { font-family: system-ui; font-size: 13px; color: #64748b; flex: 1; }
        #exit-reader { font-family: system-ui; font-size: 12px; padding: 5px 14px;
                       background: #6366f1; color: white; border: none; border-radius: 8px; cursor: pointer; }
        #font-dec, #font-inc { font-family: system-ui; font-size: 14px; padding: 4px 10px;
                               background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
                               color: #e2e8f0; border-radius: 6px; cursor: pointer; }
    </style>
    </head><body>
    <div id="reader-bar">
        <span>📖 Reading Mode — ${title}</span>
        <button id="font-dec" onclick="document.body.style.fontSize=Math.max(14,parseInt(getComputedStyle(document.body).fontSize)-2)+'px'">A−</button>
        <button id="font-inc" onclick="document.body.style.fontSize=Math.min(28,parseInt(getComputedStyle(document.body).fontSize)+2)+'px'">A+</button>
        <button id="exit-reader" onclick="history.back()">Exit Reader</button>
    </div>
    <div style="margin-top:60px">
    <h1>${title}</h1>
    ${html}
    </div>
    </body></html>`);
    document.close();
})();
"""

# ─────────────────────────────────────────────────────────────────────────────
# Dark mode stylesheet  (applied to the Qt chrome, not the web content)
# ─────────────────────────────────────────────────────────────────────────────

DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
}
QMenuBar {
    background-color: #0f1117;
    color: #e2e8f0;
    border-bottom: 1px solid #1e2130;
}
QMenuBar::item:selected { background: #1e2130; }
QMenu { background-color: #1a1d28; color: #e2e8f0; border: 1px solid #2d3148; }
QMenu::item:selected { background-color: #6366f1; }
QToolBar {
    background-color: #0f1117;
    border-bottom: 1px solid #1e2130;
    spacing: 4px;
    padding: 4px 6px;
}
QPushButton {
    background-color: #1e2130;
    color: #e2e8f0;
    border: 1px solid #2d3148;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 13px;
    min-width: 28px;
}
QPushButton:hover { background-color: #2d3148; border-color: #6366f1; }
QPushButton:pressed { background-color: #6366f1; color: white; }
QPushButton:checked { background-color: #6366f1; color: white; border-color: #4f46e5; }
QLineEdit {
    background-color: #1a1d28;
    color: #f1f5f9;
    border: 1px solid #2d3148;
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 13px;
    selection-background-color: #6366f1;
}
QLineEdit:focus { border-color: #6366f1; }
QTabWidget::pane { border-top: 2px solid #6366f1; background: #0f1117; }
QTabBar::tab {
    background: #1a1d28;
    color: #94a3b8;
    padding: 6px 16px;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
    font-size: 12px;
    max-width: 200px;
}
QTabBar::tab:selected { background: #6366f1; color: white; }
QTabBar::tab:hover:!selected { background: #2d3148; color: #e2e8f0; }
QStatusBar {
    background-color: #0a0c12;
    color: #64748b;
    font-size: 11px;
    border-top: 1px solid #1e2130;
}
QDockWidget { color: #e2e8f0; font-weight: bold; }
QDockWidget::title { background: #1a1d28; padding: 4px 8px; }
QTableWidget, QListWidget, QTreeWidget {
    background-color: #13151f;
    color: #e2e8f0;
    border: 1px solid #2d3148;
    gridline-color: #1e2130;
    alternate-background-color: #181b27;
}
QHeaderView::section {
    background-color: #1e2130;
    color: #94a3b8;
    border: 1px solid #2d3148;
    padding: 4px 8px;
    font-size: 12px;
}
QScrollBar:vertical {
    background: #13151f; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2d3148; border-radius: 4px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #6366f1; }
QTextEdit {
    background-color: #13151f;
    color: #e2e8f0;
    border: 1px solid #2d3148;
    border-radius: 6px;
    selection-background-color: #6366f1;
}
QProgressBar {
    background-color: #1e2130;
    border: 1px solid #2d3148;
    border-radius: 4px;
    text-align: center;
    color: #e2e8f0;
}
QProgressBar::chunk { background-color: #6366f1; border-radius: 4px; }
QSplitter::handle { background: #2d3148; }
"""

LIGHT_QSS = ""   # Use Qt default light palette


# ─────────────────────────────────────────────────────────────────────────────
# JS Bridge
# ─────────────────────────────────────────────────────────────────────────────

class JsBridge(QObject):
    credentials_captured = pyqtSignal(str, str)

    @pyqtSlot(str, str)
    def capture_credentials(self, username, password):
        self.credentials_captured.emit(username, password)


QWEBCHANNEL_JS_CODE = """
"use strict";
class QWebChannel {
    constructor(transport, initCallback) {
        if (typeof transport === "undefined") { console.error("QWebChannel: transport required!"); return; }
        this.transport = transport;
        this.send = this.send.bind(this);
        this.execCallbacks = {};
        this.execId = 0;
        this.objects = {};
        this.transport.onmessage = this.onmessage.bind(this);
        this.send("QWebChannel.initialize");
        if (initCallback) { initCallback(this); }
    }
    send(data) {
        if (typeof this.transport.send !== "function") { console.error("QWebChannel: transport.send is not a function!"); return; }
        this.transport.send(data);
    }
    exec(data, callback) {
        if (!callback) { this.send(data); return; }
        if (this.execId === Number.MAX_SAFE_INTEGER) { this.execId = 0; }
        const id = ++this.execId;
        self.execCallbacks[id] = callback;
        this.send(JSON.stringify({ id: id, data: data }));
    }
    onmessage(message) {
        const data = JSON.parse(message.data);
        if (data.id && this.execCallbacks[data.id]) {
            const cb = self.execCallbacks[data.id];
            delete self.execCallbacks[data.id];
            cb(data.data);
        } else if (data.object && data.data) {
            if (this.objects[data.object]) { this.objects[data.object].emit(data.data); }
        }
    }
    registerObject(name, object) { self.objects[name] = object; }
}
if (typeof module !== 'undefined' && module.exports) { module.exports = QWebChannel; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# Main Browser Window
# ─────────────────────────────────────────────────────────────────────────────

NEW_TAB_HTML = os.path.join(os.path.dirname(__file__), "new_tab.html")
HISTORY_FILE  = "history.json"
TABS_FILE     = "tabs.json"
SETTINGS_FILE = "settings.json"
CONSOLE_HIST  = "console_history.json"


class WebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Browser")
        self.setGeometry(100, 100, 1280, 820)

        # ── State ──────────────────────────────────────────────────────────
        self.bookmarks   = BookmarksDialog.load_bookmarks()
        self.history     = []
        self.homepage    = "newtab"
        self.plugins     = []
        self.tor_enabled = False
        self.vault       = None
        self.autofill_enabled = True
        self.dark_mode   = True    # default dark
        self.reading_mode_active = False

        # ── Profile ────────────────────────────────────────────────────────
        self.profile = QWebEngineProfile.defaultProfile()
        self.USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ]
        self.profile.setHttpUserAgent(self.USER_AGENTS[0])
        self.profile.setPersistentStoragePath("webengine_profile")
        s = self.profile.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        self.profile.downloadRequested.connect(self.handle_download)

        # ── Status bar ─────────────────────────────────────────────────────
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # ── Ad blocker ─────────────────────────────────────────────────────
        self.ad_blocker = AdBlockInterceptor()
        self.dev_tools   = None
        self.download_panel = None

        # ── Toolbar ────────────────────────────────────────────────────────
        self._build_toolbar()

        # ── Tabs ───────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_by_index)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.setCentralWidget(self.tabs)

        # ── Menus ──────────────────────────────────────────────────────────
        self._build_menus()

        # ── Keyboard shortcuts ─────────────────────────────────────────────
        self._build_shortcuts()

        # ── Plugins ────────────────────────────────────────────────────────
        self.load_plugins()

        # ── WebChannel ─────────────────────────────────────────────────────
        self.channel  = QWebChannel()
        self.js_bridge = JsBridge()
        self.js_bridge.credentials_captured.connect(self.handle_credentials)
        self.channel.registerObject("bridge", self.js_bridge)

        # ── Download panel ─────────────────────────────────────────────────
        self.download_panel = DownloadPanel(self)
        self.download_dock  = QDockWidget("Downloads", self)
        self.download_dock.setWidget(self.download_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.download_dock)
        self.download_dock.hide()

        # ── Notes sidebar ──────────────────────────────────────────────────
        self.note_sidebar = NoteSidebar(self)
        self.note_dock = QDockWidget("Notes", self)
        self.note_dock.setWidget(self.note_sidebar)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.note_dock)
        self.note_dock.hide()

        # ── Vault (password manager) ────────────────────────────────────────
        password, ok = QInputDialog.getText(
            self, "Vault Password", "Enter master password (or cancel to skip):",
            QLineEdit.EchoMode.Password
        )
        if ok and password:
            self.vault = Vault(password)
            if not self.vault.unlock_vault():
                self.vault.create_and_lock_vault({"logins": [], "api_keys": []})
        else:
            self.statusBar.showMessage("Vault not initialized. Password manager disabled.", 5000)

        # ── Apply dark mode ────────────────────────────────────────────────
        self.apply_theme()

        # ── Load settings & session ────────────────────────────────────────
        self.load_settings()
        self.load_history()

        # ── Open initial tab ───────────────────────────────────────────────
        self.add_new_tab(self._newtab_url(), "New Tab")
        self.load_tabs()   # restore previous session on top

        # ── Interceptors ───────────────────────────────────────────────────
        interceptors = [self.ad_blocker]
        for plugin in self.plugins:
            interceptor = plugin.get_interceptor()
            if interceptor:
                interceptors.append(interceptor)
        self.profile.setUrlRequestInterceptor(ChainedInterceptor(interceptors))

    # ─────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────

    def apply_theme(self):
        if self.dark_mode:
            QApplication.instance().setStyleSheet(DARK_QSS)
        else:
            QApplication.instance().setStyleSheet(LIGHT_QSS)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.save_settings()
        label = "Dark" if self.dark_mode else "Light"
        self.statusBar.showMessage(f"Switched to {label} mode", 3000)

    # ─────────────────────────────────────────────────────────────────────
    # Toolbar
    # ─────────────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        self.toolbar = QToolBar("Navigation")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.back_btn = QPushButton("◄")
        self.back_btn.setToolTip("Back  (Alt+←)")
        self.back_btn.clicked.connect(self.navigate_back)
        self.toolbar.addWidget(self.back_btn)

        self.forward_btn = QPushButton("►")
        self.forward_btn.setToolTip("Forward  (Alt+→)")
        self.forward_btn.clicked.connect(self.navigate_forward)
        self.toolbar.addWidget(self.forward_btn)

        self.reload_btn = QPushButton("↻")
        self.reload_btn.setToolTip("Reload  (F5 / Ctrl+R)")
        self.reload_btn.clicked.connect(self.reload_page)
        self.toolbar.addWidget(self.reload_btn)

        self.home_btn = QPushButton("⌂")
        self.home_btn.setToolTip("Home  (Alt+Home)")
        self.home_btn.clicked.connect(self.go_home)
        self.toolbar.addWidget(self.home_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter URL…")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setMinimumWidth(300)
        self.toolbar.addWidget(self.url_bar)

        self.ssl_label = QLabel("🔒")
        self.ssl_label.setToolTip("Connection security")
        self.toolbar.addWidget(self.ssl_label)

        # Reading mode toggle button
        self.reader_btn = QPushButton("📖")
        self.reader_btn.setToolTip("Reading Mode  (Ctrl+Shift+R)")
        self.reader_btn.setCheckable(True)
        self.reader_btn.clicked.connect(self.toggle_reading_mode)
        self.toolbar.addWidget(self.reader_btn)

        # Dark mode quick-toggle
        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setToolTip("Toggle Dark/Light Mode  (Ctrl+Shift+D)")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(True)
        self.theme_btn.clicked.connect(self.toggle_dark_mode)
        self.toolbar.addWidget(self.theme_btn)

    # ─────────────────────────────────────────────────────────────────────
    # Menus
    # ─────────────────────────────────────────────────────────────────────

    def _build_menus(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("File")
        self._add_action(file_menu, "New Tab", self._new_tab_action, "Ctrl+T")
        self._add_action(file_menu, "Close Tab", self.close_current_tab, "Ctrl+W")
        file_menu.addSeparator()
        self._add_action(file_menu, "Set Homepage", self.set_homepage)
        self._add_action(file_menu, "Save Session", self.save_tabs)

        # View
        view_menu = mb.addMenu("View")
        self._add_action(view_menu, "Developer Tools", self.toggle_dev_tools, "Ctrl+Shift+I")
        self._add_action(view_menu, "Show Downloads", self.show_download_manager, "Ctrl+J")
        self._add_action(view_menu, "Show Notes", self.toggle_notes, "Ctrl+Shift+N")
        view_menu.addSeparator()
        self._add_action(view_menu, "Reading Mode", self.toggle_reading_mode, "Ctrl+Shift+R")
        self._add_action(view_menu, "Toggle Dark Mode", self.toggle_dark_mode, "Ctrl+Shift+D")
        view_menu.addSeparator()
        self._add_action(view_menu, "Zoom In", self.zoom_in, "Ctrl+=")
        self._add_action(view_menu, "Zoom Out", self.zoom_out, "Ctrl+-")
        self._add_action(view_menu, "Reset Zoom", self.zoom_reset, "Ctrl+0")

        # History
        history_menu = mb.addMenu("History")
        self._add_action(history_menu, "Show History", self.show_history, "Ctrl+H")

        # Bookmarks
        bm_menu = mb.addMenu("Bookmarks")
        self._add_action(bm_menu, "Show Bookmarks", self.show_bookmarks, "Ctrl+Shift+O")
        self._add_action(bm_menu, "Bookmark This Page", self.add_bookmark, "Ctrl+D")

        # Tools
        tools_menu = mb.addMenu("Tools")
        self.toggle_ad_blocker_action = QAction("Enable Ad Blocker", self, checkable=True)
        self.toggle_ad_blocker_action.triggered.connect(self.toggle_ad_blocker)
        tools_menu.addAction(self.toggle_ad_blocker_action)

        self.toggle_autofill_action = QAction("Enable Autofill", self, checkable=True)
        self.toggle_autofill_action.triggered.connect(self.toggle_autofill)
        tools_menu.addAction(self.toggle_autofill_action)

        tools_menu.addSeparator()
        self._add_action(tools_menu, "Password Manager", self.show_password_manager)

    def _add_action(self, menu, label, slot, shortcut=None):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    # ─────────────────────────────────────────────────────────────────────
    # Keyboard shortcuts  (beyond what's in menus)
    # ─────────────────────────────────────────────────────────────────────

    def _build_shortcuts(self):
        shortcuts = [
            ("Alt+Left",    self.navigate_back),
            ("Alt+Right",   self.navigate_forward),
            ("F5",          self.reload_page),
            ("Ctrl+R",      self.reload_page),
            ("Ctrl+L",      self._focus_url_bar),
            ("Alt+Home",    self.go_home),
            ("Ctrl+Tab",    self.next_tab),
            ("Ctrl+Shift+Tab", self.prev_tab),
            ("Ctrl+1",      lambda: self._switch_tab(0)),
            ("Ctrl+2",      lambda: self._switch_tab(1)),
            ("Ctrl+3",      lambda: self._switch_tab(2)),
            ("Ctrl+4",      lambda: self._switch_tab(3)),
            ("Ctrl+5",      lambda: self._switch_tab(4)),
            ("Ctrl+6",      lambda: self._switch_tab(5)),
            ("Ctrl+7",      lambda: self._switch_tab(6)),
            ("Ctrl+8",      lambda: self._switch_tab(7)),
            ("Ctrl+9",      lambda: self._switch_tab(self.tabs.count() - 1)),
            ("Escape",      self._cancel_load),
            ("F11",         self.toggle_fullscreen),
            ("Ctrl+P",      self.print_page),
            ("Ctrl+F",      self.focus_find),
        ]
        for seq, slot in shortcuts:
            action = QAction(self)
            action.setShortcut(seq)
            action.triggered.connect(slot)
            self.addAction(action)

    # ─────────────────────────────────────────────────────────────────────
    # New Tab URL helper
    # ─────────────────────────────────────────────────────────────────────

    def _newtab_url(self):
        if os.path.exists(NEW_TAB_HTML):
            return QUrl.fromLocalFile(os.path.abspath(NEW_TAB_HTML))
        return QUrl(self.homepage if self.homepage != "newtab" else "https://duckduckgo.com")

    def _new_tab_action(self):
        self.add_new_tab(self._newtab_url(), "New Tab")

    # ─────────────────────────────────────────────────────────────────────
    # Tab management
    # ─────────────────────────────────────────────────────────────────────

    def add_new_tab(self, url, label="New Tab"):
        browser = QWebEngineView()
        page = QWebEnginePage(self.profile, browser)
        browser.setPage(page)
        page.setWebChannel(self.channel)
        page.runJavaScript(QWEBCHANNEL_JS_CODE)
        page.loadFinished.connect(lambda ok: self.on_load_finished(ok, browser))
        page.certificateError.connect(lambda error: self.handle_certificate_error(error, browser))
        # Handle "open in new tab / new window" from right-click menus
        page.createWindow = lambda _win_type: self._create_window()
        browser.urlChanged.connect(self.update_urlbar)
        browser.titleChanged.connect(lambda title: self.tabs.setTabText(self.tabs.indexOf(browser), title[:30] or "New Tab"))
        browser.loadProgress.connect(lambda p: self._update_load_progress(p, browser))
        browser.load(url)
        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)
        return browser

    def _create_window(self):
        """Called by QWebEnginePage.createWindow — opens a blank new tab and returns its page."""
        browser = self.add_new_tab(self._newtab_url(), "New Tab")
        return browser.page()

    def close_tab_by_index(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            widget.deleteLater()
        else:
            # Last tab — just navigate home instead of closing
            self.tabs.currentWidget().load(self._newtab_url())

    def on_load_finished(self, ok, browser):
        self.update_ssl_indicator(ok, browser)
        if browser == self.tabs.currentWidget():
            url_str = browser.url().toString()
            # Record history
            if url_str and not url_str.startswith("file://"):
                ts = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")
                self.history.append((ts, url_str))
                self.save_history()
            # Update notes sidebar domain
            if hasattr(self, 'note_sidebar'):
                self.note_sidebar.set_current_url(url_str)

    def _update_load_progress(self, percent, browser):
        if browser == self.tabs.currentWidget():
            if percent < 100:
                self.statusBar.showMessage(f"Loading… {percent}%")
            else:
                self.statusBar.clearMessage()

    def navigate_to_url(self):
        url = self.url_bar.text().strip()
        if not url:
            return
        # Smart URL detection
        if url.startswith("http://") or url.startswith("https://") or url.startswith("file://"):
            qurl = QUrl(url)
        elif "." in url and " " not in url:
            qurl = QUrl("https://" + url)
        else:
            qurl = QUrl("https://duckduckgo.com/?q=" + url.replace(" ", "+"))
        if self.tabs.count() == 0:
            self.add_new_tab(qurl, "Loading…")
        else:
            self.tabs.currentWidget().load(qurl)

    def navigate_back(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().back()

    def navigate_forward(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().forward()

    def reload_page(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().reload()

    def go_home(self):
        self.add_new_tab(self._newtab_url(), "New Tab")

    def update_urlbar(self, url):
        self.url_bar.setText(url.toString())

    def tab_open_doubleclick(self, index):
        if index == -1:
            self._new_tab_action()

    def current_tab_changed(self, index):
        if index != -1 and self.tabs.currentWidget():
            self.update_urlbar(self.tabs.currentWidget().url())
            if hasattr(self, 'note_sidebar'):
                self.note_sidebar.set_current_url(self.tabs.currentWidget().url().toString())

    def close_current_tab(self):
        self.close_tab_by_index(self.tabs.currentIndex())

    def next_tab(self):
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count())

    def prev_tab(self):
        self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % self.tabs.count())

    def _switch_tab(self, index):
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def _cancel_load(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().stop()

    # ─────────────────────────────────────────────────────────────────────
    # Zoom
    # ─────────────────────────────────────────────────────────────────────

    def zoom_in(self):
        if self.tabs.count() > 0:
            w = self.tabs.currentWidget()
            w.setZoomFactor(min(w.zoomFactor() + 0.1, 3.0))

    def zoom_out(self):
        if self.tabs.count() > 0:
            w = self.tabs.currentWidget()
            w.setZoomFactor(max(w.zoomFactor() - 0.1, 0.3))

    def zoom_reset(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().setZoomFactor(1.0)

    # ─────────────────────────────────────────────────────────────────────
    # Reading mode
    # ─────────────────────────────────────────────────────────────────────

    def toggle_reading_mode(self):
        if self.tabs.count() == 0:
            return
        self.tabs.currentWidget().page().runJavaScript(READER_JS)
        self.reader_btn.setChecked(not self.reader_btn.isChecked())
        self.statusBar.showMessage("Reading mode activated", 3000)

    # ─────────────────────────────────────────────────────────────────────
    # Notes sidebar
    # ─────────────────────────────────────────────────────────────────────

    def toggle_notes(self):
        if self.note_dock.isHidden():
            self.note_dock.show()
        else:
            self.note_dock.hide()

    # ─────────────────────────────────────────────────────────────────────
    # URL bar / misc shortcuts
    # ─────────────────────────────────────────────────────────────────────

    def _focus_url_bar(self):
        self.url_bar.setFocus()
        self.url_bar.selectAll()

    def focus_find(self):
        """Activates in-page search (browser built-in)."""
        if self.tabs.count() > 0:
            # Show simple find text dialog
            text, ok = QInputDialog.getText(self, "Find in Page", "Search:")
            if ok and text:
                self.tabs.currentWidget().findText(text)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def print_page(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().page().print(None)

    # ─────────────────────────────────────────────────────────────────────
    # Downloads
    # ─────────────────────────────────────────────────────────────────────

    def handle_download(self, download):
        suggested_path = download.suggestedFileName()
        path, _ = QFileDialog.getSaveFileName(self, "Save File", suggested_path)
        if path:
            download.accept()
            self.download_panel.add_download(
                url=download.url().toString(),
                save_path=path,
                num_threads=1,
                start_immediately=True
            )
            self.download_dock.show()
        else:
            download.cancel()

    def show_download_manager(self):
        if self.download_dock.isHidden():
            self.download_dock.show()
        else:
            self.download_dock.hide()

    # ─────────────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────────────

    def show_history(self):
        dialog = HistoryDialog(self.history, self)
        dialog.exec()

    def save_history(self):
        try:
            # Keep last 2000 entries
            with open(HISTORY_FILE, "w") as f:
                json.dump(self.history[-2000:], f)
        except Exception:
            pass

    def load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE) as f:
                    data = json.load(f)
                    # Support both old string format and new [ts, url] tuple format
                    self.history = []
                    for item in data:
                        if isinstance(item, (list, tuple)) and len(item) == 2:
                            self.history.append(tuple(item))
                        elif isinstance(item, str):
                            self.history.append(("Unknown", item))
        except Exception:
            self.history = []

    # ─────────────────────────────────────────────────────────────────────
    # Bookmarks
    # ─────────────────────────────────────────────────────────────────────

    def show_bookmarks(self):
        dialog = BookmarksDialog(self.bookmarks, self)
        dialog.exec()
        self.bookmarks = dialog.bookmarks   # sync back

    def add_bookmark(self):
        if self.tabs.count() == 0:
            return
        url = self.tabs.currentWidget().url().toString()
        title = self.tabs.currentWidget().title() or url
        if not url or url.startswith("file://"):
            return
        # Quick-add with default folder
        existing_urls = [b.get("url") if isinstance(b, dict) else b for b in self.bookmarks]
        if url not in existing_urls:
            folder, ok = QInputDialog.getItem(
                self, "Add Bookmark", "Folder:",
                list({b.get("folder", "Bookmarks") for b in self.bookmarks if isinstance(b, dict)} or ["Bookmarks"]),
                0, True
            )
            if not ok:
                folder = "Bookmarks"
            self.bookmarks.append({"title": title, "url": url, "folder": folder})
            # persist
            try:
                with open("bookmarks_v2.json", "w") as f:
                    json.dump(self.bookmarks, f, indent=2)
            except Exception:
                pass
            self.statusBar.showMessage(f"Bookmarked: {title[:50]}", 3000)
        else:
            self.statusBar.showMessage("Already bookmarked", 2000)

    # ─────────────────────────────────────────────────────────────────────
    # Password manager
    # ─────────────────────────────────────────────────────────────────────

    def show_password_manager(self):
        if self.vault:
            dialog = PasswordManagerDialog(self.vault, self)
            dialog.exec()
        else:
            self.statusBar.showMessage("Vault not initialized", 3000)

    # ─────────────────────────────────────────────────────────────────────
    # Developer tools
    # ─────────────────────────────────────────────────────────────────────

    def toggle_dev_tools(self):
        if not self.dev_tools:
            from dialogs import DevToolsDialog
            dev_tools_dialog = DevToolsDialog(self.tabs.currentWidget(), self)
            self.dev_tools = QDockWidget("Developer Tools", self)
            self.dev_tools.setWidget(dev_tools_dialog)
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dev_tools)
        if self.dev_tools.isHidden():
            self.dev_tools.show()
        else:
            self.dev_tools.hide()

    # ─────────────────────────────────────────────────────────────────────
    # Credentials / vault
    # ─────────────────────────────────────────────────────────────────────

    def handle_credentials(self, username, password):
        if self.vault and self.autofill_enabled:
            url = self.tabs.currentWidget().url().toString()
            self.vault.data["logins"].append({"url": url, "username": username, "password": password})
            self.vault.create_and_lock_vault(self.vault.data)

    # ─────────────────────────────────────────────────────────────────────
    # Plugins
    # ─────────────────────────────────────────────────────────────────────

    def load_plugins(self):
        plugin_dir = Path("plugins")
        if plugin_dir.exists():
            sys.path.append(str(plugin_dir))
            for plugin_path in plugin_dir.glob("*.py"):
                module_name = plugin_path.stem
                try:
                    module = import_module(module_name)
                    plugin_class = getattr(module, "Plugin", None)
                    if plugin_class:
                        plugin = plugin_class(self)
                        plugin.init_plugin()
                        plugin.add_to_menu(self.menuBar().addMenu(plugin.name))
                        self.plugins.append(plugin)
                except Exception as e:
                    self.statusBar.showMessage(f"Failed to load plugin {module_name}: {str(e)}", 5000)

    # ─────────────────────────────────────────────────────────────────────
    # Session save / restore
    # ─────────────────────────────────────────────────────────────────────

    def save_tabs(self):
        try:
            urls = []
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                url = widget.url().toString()
                if url and not url.startswith("file://"):
                    urls.append(url)
            with open(TABS_FILE, "w") as f:
                json.dump(urls, f)
            self.statusBar.showMessage(f"Session saved ({len(urls)} tabs)", 3000)
        except Exception as e:
            self.statusBar.showMessage(f"Failed to save session: {str(e)}", 5000)

    def load_tabs(self):
        try:
            if os.path.exists(TABS_FILE):
                with open(TABS_FILE) as f:
                    tabs = json.load(f)
                for url in tabs:
                    if url:
                        self.add_new_tab(QUrl(url), url[:40])
        except Exception as e:
            self.statusBar.showMessage(f"Failed to restore session: {str(e)}", 5000)

    def closeEvent(self, event):
        """Auto-save session on close."""
        self.save_tabs()
        super().closeEvent(event)

    # ─────────────────────────────────────────────────────────────────────
    # Settings
    # ─────────────────────────────────────────────────────────────────────

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump({
                    "homepage": self.homepage,
                    "ad_blocker_enabled": self.ad_blocker.enabled,
                    "tor_enabled": self.tor_enabled,
                    "autofill_enabled": self.autofill_enabled,
                    "dark_mode": self.dark_mode,
                }, f, indent=2)
        except Exception as e:
            self.statusBar.showMessage(f"Failed to save settings: {str(e)}", 5000)

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE) as f:
                    s = json.load(f)
                self.homepage          = s.get("homepage", "newtab")
                self.ad_blocker.enabled = s.get("ad_blocker_enabled", True)
                self.tor_enabled       = s.get("tor_enabled", False)
                self.autofill_enabled  = s.get("autofill_enabled", True)
                self.dark_mode         = s.get("dark_mode", True)
                self.toggle_ad_blocker_action.setChecked(self.ad_blocker.enabled)
                self.toggle_autofill_action.setChecked(self.autofill_enabled)
                self.theme_btn.setChecked(self.dark_mode)
                self.apply_theme()
        except Exception as e:
            self.statusBar.showMessage(f"Failed to load settings: {str(e)}", 5000)

    def toggle_ad_blocker(self):
        self.ad_blocker.enabled = self.toggle_ad_blocker_action.isChecked()
        self.save_settings()

    def toggle_autofill(self):
        self.autofill_enabled = self.toggle_autofill_action.isChecked()
        self.save_settings()

    def set_homepage(self):
        url, ok = QInputDialog.getText(self, "Set Homepage", "Enter URL (or 'newtab'):", text=self.homepage)
        if ok and url:
            if url != "newtab" and not url.startswith("http"):
                url = "https://" + url
            self.homepage = url
            self.save_settings()

    # ─────────────────────────────────────────────────────────────────────
    # SSL / certificate
    # ─────────────────────────────────────────────────────────────────────

    def handle_certificate_error(self, error, browser):
        reply = QMessageBox.warning(
            self, "Certificate Error",
            f"Invalid certificate for {error.url().toString()}: {error.description()}\n\nProceed anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            error.acceptCertificate()
            self.ssl_label.setText("⚠️")
        else:
            error.rejectCertificate()
            self.ssl_label.setText("🔒")

    def update_ssl_indicator(self, ok, browser):
        if browser == self.tabs.currentWidget():
            url = browser.url()
            if ok and url.scheme() == "https":
                self.ssl_label.setText("🔐")
            else:
                self.ssl_label.setText("🔒")

    # ─────────────────────────────────────────────────────────────────────
    # Console history  (used by DevToolsDialog)
    # ─────────────────────────────────────────────────────────────────────

    def load_console_history(self):
        try:
            if os.path.exists(CONSOLE_HIST):
                with open(CONSOLE_HIST) as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def save_console_history(self, history):
        try:
            with open(CONSOLE_HIST, "w") as f:
                json.dump(history[-200:], f)
        except Exception:
            pass
