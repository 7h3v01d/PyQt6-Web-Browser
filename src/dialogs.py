from urllib.parse import urlparse
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QTextEdit, QTabWidget, QWidget, QPushButton, QHBoxLayout,
                             QInputDialog, QLineEdit, QMessageBox, QHeaderView)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl

class HistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browsing History")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Date", "Title", "URL"])
        self.history_table.setRowCount(len(history))
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        
        for row, (timestamp, url) in enumerate(history):
            parsed_url = urlparse(url)
            short_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"[:50]
            if len(f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}") > 50:
                short_url += "..."
            
            date_item = QTableWidgetItem(timestamp)
            title_item = QTableWidgetItem(self.get_page_title(url) or "Unknown")
            url_item = QTableWidgetItem(short_url)
            url_item.setData(Qt.ItemDataRole.UserRole, url)
            self.history_table.setItem(row, 0, date_item)
            self.history_table.setItem(row, 1, title_item)
            self.history_table.setItem(row, 2, url_item)
        
        self.history_table.resizeColumnsToContents()
        self.history_table.doubleClicked.connect(self.open_history_url)
        layout.addWidget(self.history_table)
        self.setLayout(layout)
    
    def get_page_title(self, url):
        parsed_url = urlparse(url)
        if "youtube.com" in parsed_url.netloc:
            return parsed_url.path.split("/")[-1] if parsed_url.path != "/" else "YouTube"
        return parsed_url.netloc
    
    def open_history_url(self):
        selected = self.history_table.selectedItems()
        if selected:
            url = selected[0].data(Qt.ItemDataRole.UserRole)
            if url:
                self.parent().add_new_tab(QUrl(url), "History Tab")

class DevToolsDialog(QDialog):
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Developer Tools")
        self.setGeometry(200, 200, 800, 600)
        self.command_history = parent.load_console_history() if hasattr(parent, 'load_console_history') else []
        self.history_index = len(self.command_history)
        layout = QVBoxLayout()
        
        self.inspector = QWebEngineView()
        self.inspector.setPage(browser.page().devToolsPage())
        layout.addWidget(self.inspector, stretch=2)
        
        self.console_input = QTextEdit()
        self.console_input.setPlaceholderText("Enter JavaScript code (Shift+Enter for new line, Enter to execute)...")
        self.console_input.setFixedHeight(100)
        layout.addWidget(self.console_input, stretch=1)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        layout.addWidget(self.console_output, stretch=1)
        
        self.setLayout(layout)
        self.console_input.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if obj == self.console_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.execute_js(self.parent().tabs.currentWidget())
                return True
            elif event.key() == Qt.Key.Key_Up:
                self.navigate_history(-1)
                return True
            elif event.key == Qt.Key.Key_Down:
                self.navigate_history(1)
                return True
        return super().eventFilter(obj, event)
    
    def execute_js(self, browser):
        js_code = self.console_input.toPlainText().strip()
        if js_code:
            self.command_history.append(js_code)
            self.history_index = len(self.command_history)
            if hasattr(self.parent(), 'save_console_history'):
                self.parent().save_console_history(self.command_history)
            browser.page().runJavaScript(js_code, self.handle_js_result)
    
    def handle_js_result(self, result):
        self.console_output.append(str(result))
    
    def navigate_history(self, direction):
        if not self.command_history:
            return
        self.history_index = max(0, min(self.history_index + direction, len(self.command_history)))
        if self.history_index < len(self.command_history):
            self.console_input.setPlainText(self.command_history[self.history_index])
        else:
            self.console_input.clear()

class PasswordManagerDialog(QDialog):
    def __init__(self, vault, parent=None):
        super().__init__(parent)
        self.vault = vault
        self.setWindowTitle("Password Manager")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        
        self.tab_widget = QTabWidget()
        self.logins_tab = QWidget()
        self.api_keys_tab = QWidget()
        
        self.tab_widget.addTab(self.logins_tab, "Logins")
        self.tab_widget.addTab(self.api_keys_tab, "API Keys")
        
        # Logins tab
        logins_layout = QVBoxLayout()
        self.logins_table = QTableWidget()
        self.logins_table.setColumnCount(3)
        self.logins_table.setHorizontalHeaderLabels(["URL", "Username", "Password"])
        self.logins_table.horizontalHeader().setStretchLastSection(True)
        logins_layout.addWidget(self.logins_table)
        
        logins_btn_layout = QHBoxLayout()
        add_login_btn = QPushButton("Add Login")
        add_login_btn.clicked.connect(self.add_login)
        logins_btn_layout.addWidget(add_login_btn)
        
        delete_login_btn = QPushButton("Delete Login")
        delete_login_btn.clicked.connect(self.delete_login)
        logins_btn_layout.addWidget(delete_login_btn)
        
        reveal_login_btn = QPushButton("Reveal Password")
        reveal_login_btn.clicked.connect(self.reveal_login_password)
        logins_btn_layout.addWidget(reveal_login_btn)
        
        hide_login_btn = QPushButton("Hide Password")
        hide_login_btn.clicked.connect(self.hide_logins_password)
        logins_btn_layout.addWidget(hide_login_btn)
        
        logins_layout.addLayout(logins_btn_layout)
        self.logins_tab.setLayout(logins_layout)
        
        # API Keys tab
        api_keys_layout = QVBoxLayout()
        self.api_keys_table = QTableWidget()
        self.api_keys_table.setColumnCount(2)
        self.api_keys_table.setHorizontalHeaderLabels(["Service", "API Key"])
        self.api_keys_table.horizontalHeader().setStretchLastSection(True)
        api_keys_layout.addWidget(self.api_keys_table)
        
        api_keys_btn_layout = QHBoxLayout()
        add_api_key_btn = QPushButton("Add API Key")
        add_api_key_btn.clicked.connect(self.add_api_key)
        api_keys_btn_layout.addWidget(add_api_key_btn)
        
        delete_api_key_btn = QPushButton("Delete API Key")
        delete_api_key_btn.clicked.connect(self.delete_api_key)
        api_keys_btn_layout.addWidget(delete_api_key_btn)
        
        reveal_api_key_btn = QPushButton("Reveal API Key")
        reveal_api_key_btn.clicked.connect(self.reveal_api_key)
        api_keys_btn_layout.addWidget(reveal_api_key_btn)
        
        hide_api_key_btn = QPushButton("Hide API Key")
        hide_api_key_btn.clicked.connect(self.hide_api_key)
        api_keys_btn_layout.addWidget(hide_api_key_btn)
        
        api_keys_layout.addLayout(api_keys_btn_layout)
        self.api_keys_tab.setLayout(api_keys_layout)
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
        self.refresh_logins()
        self.refresh_api_keys()

    def refresh_logins(self):
        logins = self.vault.get_logins()
        self.logins_table.setRowCount(len(logins))
        for row, login in enumerate(logins):
            self.logins_table.setItem(row, 0, QTableWidgetItem(login["url"]))
            self.logins_table.setItem(row, 1, QTableWidgetItem(login["username"]))
            self.logins_table.setItem(row, 2, QTableWidgetItem("*" * 12))

    def refresh_api_keys(self):
        keys = self.vault.get_api_keys()
        self.api_keys_table.setRowCount(len(keys))
        for row, key_info in enumerate(keys):
            self.api_keys_table.setItem(row, 0, QTableWidgetItem(key_info["service"]))
            self.api_keys_table.setItem(row, 1, QTableWidgetItem("*" * 12))

    def add_login(self):
        url, ok1 = QInputDialog.getText(self, "Add Login", "URL:")
        username, ok2 = QInputDialog.getText(self, "Add Login", "Username:")
        password, ok3 = QInputDialog.getText(self, "Add Login", "Password:", QLineEdit.EchoMode.Password)
        if ok1 and ok2 and ok3 and url and username:
            self.vault.data["logins"].append({"url": url, "username": username, "password": password})
            self.vault.create_and_lock_vault(self.vault.data)
            self.refresh_logins()

    def delete_login(self):
        current_row = self.logins_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a login to delete.")
            return
        
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this login?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.vault.data["logins"][current_row]
            self.vault.create_and_lock_vault(self.vault.data)
            self.refresh_logins()

    def add_api_key(self):
        service, ok1 = QInputDialog.getText(self, "Add API Key", "Service Name (e.g., Gemini, xAI):")
        key, ok2 = QInputDialog.getText(self, "Add API Key", "API Key:", QLineEdit.EchoMode.Password)
        if ok1 and ok2 and service and key:
            self.vault.data["api_keys"].append({"service": service, "key": key})
            self.vault.create_and_lock_vault(self.vault.data)
            self.refresh_api_keys()

    def delete_api_key(self):
        current_row = self.api_keys_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an API key to delete.")
            return
        
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this API key?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.vault.data["api_keys"][current_row]
            self.vault.create_and_lock_vault(self.vault.data)
            self.refresh_api_keys()

    def _prompt_for_master_password(self):
        password, ok = QInputDialog.getText(self, "Authentication Required", 
                                            "Enter your master password to reveal:", 
                                            QLineEdit.EchoMode.Password)
        if ok and self.vault.verify_master_password(password):
            return True
        elif ok:
            QMessageBox.critical(self, "Authentication Failed", "Incorrect master password.")
        return False

    def reveal_login_password(self):
        current_row = self.logins_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a login to reveal.")
            return

        if self._prompt_for_master_password():
            password = self.vault.get_logins()[current_row]["password"]
            self.logins_table.item(current_row, 2).setText(password)

    def hide_logins_password(self):
        for row in range(self.logins_table.rowCount()):
            self.logins_table.item(row, 2).setText("*" * 12)

    def reveal_api_key(self):
        current_row = self.api_keys_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an API key to reveal.")
            return
        
        if self._prompt_for_master_password():
            key = self.vault.get_api_keys()[current_row]["key"]
            self.api_keys_table.item(current_row, 1).setText(key)

    def hide_api_key(self):
        for row in range(self.api_keys_table.rowCount()):
            self.api_keys_table.item(row, 1).setText("*" * 12)