try:
    from PyQt6.QtWidgets import QDockWidget, QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, QWidget, QTextEdit
    from PyQt6.QtGui import QAction
except ImportError as e:
    print(f"Failed to import PyQt6.QtWidgets: {str(e)}")
    raise
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import Qt
from interceptors import Plugin
import json

class ProxyInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.widget = QWidget()
        self.paused = False
        self.pending_request = None
    
    def interceptRequest(self, info):
        request_data = {
            "url": info.requestUrl().toString(),
            "method": info.requestMethod().decode(),
            "headers": {k.decode(): v.decode() for k, v in info.requestHeaders().items()},
            "body": info.requestData().decode() if info.requestData() else ""
        }
        # Skip interception for Netflix-related URLs
        if any(domain in request_data["url"] for domain in ['netflix.com', 'licensewidevine.com', 'nflxvideo.net', 'nflximg.net', 'nflxext.com']):
            return
        self.plugin.log_request(request_data)
        if self.paused:
            self.pending_request = info
            self.plugin.show_pending_request(request_data)
            info.block(True)

class ProxyWidget(QDockWidget):
    def __init__(self, plugin, parent=None):
        super().__init__("Proxy", parent)
        self.plugin = plugin
        self.widget = QWidget()
        self.layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["URL", "Method", "Headers", "Body"])
        self.table.setRowCount(0)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.edit_request)
        self.layout.addWidget(self.table)
        
        self.pause_btn = QPushButton("Pause Proxy")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.layout.addWidget(self.pause_btn)
        
        self.forward_btn = QPushButton("Forward Request")
        self.forward_btn.setEnabled(False)
        self.forward_btn.clicked.connect(self.forward_request)
        self.layout.addWidget(self.forward_btn)
        
        self.request_edit = QTextEdit()
        self.request_edit.setPlaceholderText("Edit request here (JSON format)")
        self.request_edit.setFixedHeight(100)
        self.request_edit.hide()
        self.layout.addWidget(self.request_edit)
        
        self.widget.setLayout(self.layout)
        self.setWidget(self.widget)
        self.current_request = None
    
    def log_request(self, request_data):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(request_data["url"]))
        self.table.setItem(row, 1, QTableWidgetItem(request_data["method"]))
        self.table.setItem(row, 2, QTableWidgetItem(str(request_data["headers"])))
        self.table.setItem(row, 3, QTableWidgetItem(request_data["body"]))
    
    def show_pending_request(self, request_data):
        self.current_request = request_data
        self.request_edit.setText(json.dumps(request_data, indent=2))
        self.request_edit.show()
        self.forward_btn.setEnabled(True)
    
    def toggle_pause(self):
        self.plugin.interceptor.paused = self.pause_btn.isChecked()
        self.pause_btn.setText("Resume Proxy" if self.pause_btn.isChecked() else "Pause Proxy")
        self.forward_btn.setEnabled(self.plugin.interceptor.paused and self.current_request is not None)
        if not self.plugin.interceptor.paused:
            self.request_edit.hide()
    
    def forward_request(self):
        if self.current_request:
            try:
                modified_request = json.loads(self.request_edit.toPlainText())
                self.current_request = None
                self.request_edit.hide()
                self.forward_btn.setEnabled(False)
                self.plugin.interceptor.pending_request = None
                self.plugin.browser.statusBar.showMessage("Request forwarded", 5000)
            except json.JSONDecodeError:
                self.plugin.browser.statusBar.showMessage("Invalid JSON in request edit", 5000)
    
    def edit_request(self, index):
        row = index.row()
        request_data = self.plugin.shared_requests[row]
        self.request_edit.setText(json.dumps(request_data, indent=2))
        self.request_edit.show()
        self.current_request = request_data
        self.forward_btn.setEnabled(True)

class Plugin(Plugin):
    def __init__(self, browser, name="Proxy Plugin", version="1.0"):
        super().__init__(browser, name, version)
        self.interceptor = ProxyInterceptor(self)
        self.proxy_widget = None
    
    def init_plugin(self):
        super().init_plugin()
        self.proxy_widget = ProxyWidget(plugin=self, parent=self.browser)
        self.browser.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.proxy_widget)
    
    def add_to_menu(self, menu):
        try:
            action = QAction("Show Proxy", self.browser)
            action.triggered.connect(self.proxy_widget.show)
            menu.addAction(action)
        except NameError as e:
            self.browser.statusBar.showMessage(f"Proxy Plugin: QAction not available: {str(e)}", 5000)
    
    def get_interceptor(self):
        return self.interceptor
    
    def show_pending_request(self, request_data):
        self.proxy_widget.show_pending_request(request_data)