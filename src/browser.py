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
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QVBoxLayout
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest, QWebEngineScript, QWebEngineSettings
)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, Qt, QDateTime, QObject, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
import PyQt6
from random import choice
from interceptors import Plugin, ChainedInterceptor, AdBlockInterceptor
from dialogs import HistoryDialog, DevToolsDialog, PasswordManagerDialog
from vault import Vault
from main_gui import DownloadPanel

# JsBridge class for Python-JS communication
class JsBridge(QObject):
    credentials_captured = pyqtSignal(str, str)

    @pyqtSlot(str, str)
    def capture_credentials(self, username, password):
        """This slot is called from JavaScript to send credentials to Python."""
        self.credentials_captured.emit(username, password)

# Embedded qwebchannel.js source code (unchanged)
QWEBCHANNEL_JS_CODE = """
/* Truncated for brevity - assumed to be the same as your original */
"use strict";

class QWebChannel {
    constructor(transport, initCallback) {
        if (typeof transport === "undefined") {
            console.error("QWebChannel: transport required!");
            return;
        }
        this.transport = transport;
        this.send = this.send.bind(this);
        this.execCallbacks = {};
        this.execId = 0;
        this.objects = {};
        this.transport.onmessage = this.onmessage.bind(this);
        this.send("QWebChannel.initialize");
        if (initCallback) {
            initCallback(this);
        }
    }
    send(data) {
        if (typeof this.transport.send !== "function") {
            console.error("QWebChannel: transport.send is not a function!");
            return;
        }
        this.transport.send(data);
    }
    exec(data, callback) {
        if (!callback) {
            this.send(data);
            return;
        }
        if (this.execId === Number.MAX_SAFE_INTEGER) {
            this.execId = 0;
        }
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
            if (this.objects[data.object]) {
                this.objects[data.object].emit(data.data);
            }
        }
    }
    registerObject(name, object) {
        self.objects[name] = object;
    }
}
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QWebChannel;
}
"""

class WebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Web Browser")
        self.setGeometry(100, 100, 1200, 800)
        
        self.bookmarks = []
        self.history = []
        self.homepage = "https://www.google.com"
        self.plugins = []
        self.tor_enabled = False
        self.vault = None
        self.autofill_enabled = True
        self.profile = QWebEngineProfile.defaultProfile()
        
        # Set user agent and enable settings for Netflix DRM
        self.USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ]
        self.profile.setHttpUserAgent(self.USER_AGENTS[0])
        self.profile.setPersistentStoragePath("webengine_profile")
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        
        # Connect download signal
        self.profile.downloadRequested.connect(self.handle_download)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.ad_blocker = AdBlockInterceptor()
        self.dev_tools = None
        self.download_panel = None
        
        # Setup toolbar
        self.toolbar = QToolBar("Navigation")
        self.addToolBar(self.toolbar)
        
        self.back_btn = QPushButton("◄")
        self.back_btn.clicked.connect(self.navigate_back)
        self.toolbar.addWidget(self.back_btn)
        
        self.forward_btn = QPushButton("►")
        self.forward_btn.clicked.connect(self.navigate_forward)
        self.toolbar.addWidget(self.forward_btn)
        
        self.reload_btn = QPushButton("↻")
        self.reload_btn.clicked.connect(self.reload_page)
        self.toolbar.addWidget(self.reload_btn)
        
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)
        
        self.ssl_label = QLabel("🔒")
        self.toolbar.addWidget(self.ssl_label)
        
        # Setup tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.setCentralWidget(self.tabs)
        
        # Setup menus
        self.menuBar = self.menuBar()
        file_menu = self.menuBar.addMenu("File")
        view_menu = self.menuBar.addMenu("View")
        history_menu = self.menuBar.addMenu("History")
        bookmarks_menu = self.menuBar.addMenu("Bookmarks")
        tools_menu = self.menuBar.addMenu("Tools")
        
        new_tab_action = QAction("New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(lambda: self.add_new_tab(QUrl(self.homepage), "New Tab"))
        file_menu.addAction(new_tab_action)
        
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(self.close_current_tab)
        file_menu.addAction(close_tab_action)
        
        self.toggle_ad_blocker_action = QAction("Enable Ad Blocker", self, checkable=True)
        self.toggle_ad_blocker_action.triggered.connect(self.toggle_ad_blocker)
        tools_menu.addAction(self.toggle_ad_blocker_action)
        
        self.toggle_autofill_action = QAction("Enable Autofill", self, checkable=True)
        self.toggle_autofill_action.triggered.connect(self.toggle_autofill)
        tools_menu.addAction(self.toggle_autofill_action)
        
        set_homepage_action = QAction("Set Homepage", self)
        set_homepage_action.triggered.connect(self.set_homepage)
        file_menu.addAction(set_homepage_action)
        
        show_history_action = QAction("Show History", self)
        show_history_action.triggered.connect(self.show_history)
        history_menu.addAction(show_history_action)
        
        show_bookmarks_action = QAction("Show Bookmarks", self)
        show_bookmarks_action.triggered.connect(self.show_bookmarks)
        bookmarks_menu.addAction(show_bookmarks_action)
        
        add_bookmark_action = QAction("Add Bookmark", self)
        add_bookmark_action.triggered.connect(self.add_bookmark)
        bookmarks_menu.addAction(add_bookmark_action)
        
        password_manager_action = QAction("Password Manager", self)
        password_manager_action.triggered.connect(self.show_password_manager)
        tools_menu.addAction(password_manager_action)
        
        dev_tools_action = QAction("Developer Tools", self)
        dev_tools_action.setShortcut("Ctrl+Shift+I")
        dev_tools_action.triggered.connect(self.toggle_dev_tools)
        view_menu.addAction(dev_tools_action)
        
        download_manager_action = QAction("Show Downloads", self)
        download_manager_action.triggered.connect(self.show_download_manager)
        view_menu.addAction(download_manager_action)
        
        # Load plugins
        self.load_plugins()
        
        # Setup WebChannel
        self.channel = QWebChannel()
        self.js_bridge = JsBridge()
        self.js_bridge.credentials_captured.connect(self.handle_credentials)
        self.channel.registerObject("bridge", self.js_bridge)
        
        # Setup download panel
        self.download_panel = DownloadPanel(self)
        self.download_dock = QDockWidget("Downloads", self)
        self.download_dock.setWidget(self.download_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.download_dock)
        
        # Setup vault
        password, ok = QInputDialog.getText(self, "Vault Password", "Enter master password:", QLineEdit.EchoMode.Password)
        if ok and password:
            self.vault = Vault(password)
            if not self.vault.unlock_vault():
                self.vault.create_and_lock_vault({"logins": [], "api_keys": []})
        else:
            self.statusBar.showMessage("Vault not initialized. Password manager disabled.", 5000)
        
        # Initialize with a default tab
        self.add_new_tab(QUrl(self.homepage), "Homepage")
        
        # Load settings and saved tabs
        self.load_settings()
        self.load_tabs()
        
        # Setup interceptors
        interceptors = [self.ad_blocker]
        for plugin in self.plugins:
            interceptor = plugin.get_interceptor()
            if interceptor:
                interceptors.append(interceptor)
        self.profile.setUrlRequestInterceptor(ChainedInterceptor(interceptors))
        
    def handle_download(self, download):
        """Handle download requests."""
        suggested_path = download.suggestedFileName()
        path, _ = QFileDialog.getSaveFileName(self, "Save File", suggested_path)
        if path:
            download.accept()
            self.download_panel.add_download(
                url=download.url().toString(),
                save_path=path,
                num_threads=1,  # Single thread for compatibility
                start_immediately=True
            )
        else:
            download.cancel()
        
    def show_download_manager(self):
        """Show or hide the download panel."""
        if self.download_dock.isHidden():
            self.download_dock.show()
        else:
            self.download_dock.hide()
        
    def add_new_tab(self, url, label):
        browser = QWebEngineView()
        browser.setPage(QWebEnginePage(self.profile, browser))
        browser.page().setWebChannel(self.channel)
        browser.page().runJavaScript(QWEBCHANNEL_JS_CODE)
        browser.page().loadFinished.connect(lambda ok: self.update_ssl_indicator(ok, browser))
        browser.page().certificateError.connect(lambda error: self.handle_certificate_error(error, browser))
        browser.urlChanged.connect(self.update_urlbar)
        browser.titleChanged.connect(lambda title: self.tabs.setTabText(self.tabs.indexOf(browser), title))
        browser.load(url)
        self.tabs.addTab(browser, label)
        self.tabs.setCurrentWidget(browser)
        
    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith("http"):
            url = "https://" + url
        if self.tabs.count() == 0:
            self.add_new_tab(QUrl(url), "New Tab")
        else:
            self.tabs.currentWidget().load(QUrl(url))
        
    def navigate_back(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().back()
        
    def navigate_forward(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().forward()
        
    def reload_page(self):
        if self.tabs.count() > 0:
            self.tabs.currentWidget().reload()
        
    def update_urlbar(self, url):
        self.url_bar.setText(url.toString())
        
    def tab_open_doubleclick(self, index):
        if index == -1:
            self.add_new_tab(QUrl(self.homepage), "New Tab")
        
    def current_tab_changed(self, index):
        if index != -1:
            self.update_urlbar(self.tabs.currentWidget().url())
        
    def close_current_tab(self):
        if self.tabs.count() > 1:
            self.tabs.removeTab(self.tabs.currentIndex())
        
    def toggle_ad_blocker(self):
        self.ad_blocker.enabled = self.toggle_ad_blocker_action.isChecked()
        self.save_settings()
        
    def toggle_autofill(self):
        self.autofill_enabled = self.toggle_autofill_action.isChecked()
        self.save_settings()
        
    def show_history(self):
        dialog = HistoryDialog(self.history, self)
        dialog.exec()
        
    def show_bookmarks(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Bookmarks")
        layout = QVBoxLayout()
        list_widget = QListWidget()
        for bookmark in self.bookmarks:
            list_widget.addItem(bookmark)
        list_widget.itemDoubleClicked.connect(lambda item: self.add_new_tab(QUrl(item.text()), item.text()))
        layout.addWidget(list_widget)
        dialog.setLayout(layout)
        dialog.exec()
        
    def add_bookmark(self):
        url = self.tabs.currentWidget().url().toString()
        if url and url not in self.bookmarks:
            self.bookmarks.append(url)
            self.save_settings()
        
    def show_password_manager(self):
        if self.vault:
            dialog = PasswordManagerDialog(self.vault, self)
            dialog.exec()
        
    def toggle_dev_tools(self):
        if not self.dev_tools:
            dev_tools_dialog = DevToolsDialog(self.tabs.currentWidget(), self)
            self.dev_tools = QDockWidget("Developer Tools", self)
            self.dev_tools.setWidget(dev_tools_dialog)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dev_tools)
        if self.dev_tools.isHidden():
            self.dev_tools.show()
        else:
            self.dev_tools.hide()
        
    def handle_credentials(self, username, password):
        if self.vault and self.autofill_enabled:
            url = self.tabs.currentWidget().url().toString()
            self.vault.data["logins"].append({"url": url, "username": username, "password": password})
            self.vault.create_and_lock_vault(self.vault.data)
        
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
                        plugin.add_to_menu(self.menuBar.addMenu(plugin.name))
                        self.plugins.append(plugin)
                except Exception as e:
                    self.statusBar.showMessage(f"Failed to load plugin {module_name}: {str(e)}", 5000)
        
    def load_tabs(self):
        try:
            if os.path.exists("tabs.json"):
                with open("tabs.json", "r") as f:
                    tabs = json.load(f)
                    for url in tabs:
                        self.add_new_tab(QUrl(url), url)
        except Exception as e:
            self.statusBar.showMessage(f"Failed to load tabs: {str(e)}", 5000)
        
    def save_settings(self):
        try:
            with open("settings.json", "w") as f:
                json.dump({
                    "homepage": self.homepage,
                    "ad_blocker_enabled": self.ad_blocker.enabled,
                    "tor_enabled": self.tor_enabled,
                    "autofill_enabled": self.autofill_enabled
                }, f)
            self.statusBar.showMessage("Settings saved successfully", 5000)
        except Exception as e:
            self.statusBar.showMessage(f"Failed to save settings: {str(e)}", 5000)
        
    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    settings = json.load(f)
                    self.homepage = settings.get("homepage", "https://www.google.com")
                    self.ad_blocker.enabled = settings.get("ad_blocker_enabled", True)
                    self.tor_enabled = settings.get("tor_enabled", False)
                    self.autofill_enabled = settings.get("autofill_enabled", True)
                    self.toggle_ad_blocker_action.setChecked(self.ad_blocker.enabled)
                    self.toggle_autofill_action.setChecked(self.autofill_enabled)
            else:
                self.toggle_ad_blocker_action.setChecked(True)
                self.toggle_autofill_action.setChecked(True)
            self.statusBar.showMessage("Settings loaded successfully", 5000)
        except Exception as e:
            self.statusBar.showMessage(f"Failed to load settings: {str(e)}", 5000)
        
    def set_homepage(self):
        url, ok = QInputDialog.getText(self, "Set Homepage", "Enter homepage URL:", text=self.homepage)
        if ok and url:
            if not url.startswith("http"):
                url = "https://" + url
            self.homepage = url
            self.save_settings()
        
    def handle_certificate_error(self, error, browser):
        reply = QMessageBox.warning(
            self, "Certificate Error",
            f"The website {error.url().toString()} has an invalid certificate: {error.description()}\n\nDo you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            error.acceptCertificate()
            self.ssl_label.setText("🔐")
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