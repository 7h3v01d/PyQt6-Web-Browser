try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QTextEdit, QLineEdit, QFileDialog, QHBoxLayout, QMessageBox
    from PyQt6.QtGui import QAction
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
    from PyQt6.QtCore import QUrl, Qt
except ImportError as e:
    print(f"Failed to import PyQt6 modules: {str(e)}")
    raise
from interceptors import Plugin
import requests
import json
import os
from pathlib import Path
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
from base64 import b64encode

class GeminiChatDialog(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.browser = self.plugin.browser.tabs.currentWidget()
        self.setWindowTitle("Gemini Chat")
        self.setGeometry(200, 200, 800, 600)
        self.layout = QVBoxLayout()

        self.preview_label = QLabel("Current Page Preview:")
        self.layout.addWidget(self.preview_label)
        self.preview_browser = QWebEngineView()
        self.preview_browser.setFixedHeight(150)
        if self.browser:
            self.preview_browser.setUrl(self.browser.url())
        self.layout.addWidget(self.preview_browser)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Gemini chat history will appear here...")
        self.layout.addWidget(self.chat_history)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Enter your query or command...")
        self.chat_input.returnPressed.connect(self.send_message)
        self.layout.addWidget(self.chat_input)

        self.button_layout = QHBoxLayout()
        self.send_btn = QPushButton("Send Message")
        self.send_btn.clicked.connect(self.send_message)
        self.button_layout.addWidget(self.send_btn)
        self.upload_btn = QPushButton("Upload File")
        self.upload_btn.clicked.connect(self.upload_file)
        self.button_layout.addWidget(self.upload_btn)
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.clicked.connect(self.clear_history)
        self.button_layout.addWidget(self.clear_btn)
        self.layout.addLayout(self.button_layout)

        self.status_label = QLabel("Status: Ready")
        self.layout.addWidget(self.status_label)

        self.setLayout(self.layout)
        self.api_key = self.plugin.browser.vault.get_api_key("Gemini") if self.plugin.browser.vault else None
        self.conversation = self.load_conversation()
        self.update_chat_history()

    def load_conversation(self):
        try:
            if os.path.exists("gemini_chat_history.json"):
                with open("gemini_chat_history.json", "r") as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.status_label.setText(f"Status: Failed to load chat history ({str(e)})")
            return []

    def save_conversation(self):
        try:
            with open("gemini_chat_history.json", "w") as f:
                json.dump(self.conversation, f)
            self.status_label.setText("Status: Chat history saved")
        except Exception as e:
            self.status_label.setText(f"Status: Failed to save chat history ({str(e)})")

    def update_chat_history(self):
        self.chat_history.clear()
        for entry in self.conversation:
            role = "User" if entry["role"] == "user" else "Gemini"
            self.chat_history.append(f"{role}: {entry['content']}\n")

    def send_message(self):
        if not self.api_key:
            QMessageBox.warning(self, "API Key Missing", 
                                "Gemini API key not found in the vault. Please add it via the Password Manager in the Settings menu.")
            return

        query = self.chat_input.text().strip()
        if not query:
            return

        if self.browser:
            self.browser.page().toHtml(lambda html: self.process_page_context(html, query))

    def process_page_context(self, html, query):
        context = html[:1000]
        self.conversation.append({"role": "user", "content": f"Context: {context}\nQuery: {query}"})
        self.send_api_request(query)

    def send_api_request(self, query):
        try:
            self.status_label.setText("Status: Sending request...")
            self.send_btn.setEnabled(False)
            headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
            proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"} if self.plugin.browser.anonymous_mode and self.plugin.browser.tor_enabled else {}
            
            is_code_query = any(keyword in query.lower() for keyword in ["code", "script", "program"])
            
            payload = {
                "contents": [{"parts": [{"text": self.conversation[-1]["content"]}]}]
            }
            
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                json=payload, headers=headers, proxies=proxies
            )
            response.raise_for_status()
            result = response.json()
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            
            if is_code_query:
                content = f"```python\n{content}\n```"
            
            self.conversation.append({"role": "assistant", "content": content})
            self.update_chat_history()
            self.save_conversation()
            self.status_label.setText("Status: Response received")
            self.chat_input.clear()
        except Exception as e:
            self.status_label.setText(f"Status: API request failed ({str(e)})")
        finally:
            self.send_btn.setEnabled(True)

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Upload File", "", "Images (*.png *.jpg *.jpeg);;PDFs (*.pdf);;All Files (*)"
        )
        if not file_path:
            return

        try:
            if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                with open(file_path, "rb") as f:
                    file_data = b64encode(f.read()).decode("utf-8")
                self.conversation.append({"role": "user", "content": f"Analyze this image: [data:image/{Path(file_path).suffix[1:]};base64,{file_data}]"})
            elif file_path.lower().endswith(".pdf") and PyPDF2:
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = "".join(page.extract_text() for page in pdf_reader.pages)
                self.conversation.append({"role": "user", "content": f"Analyze this PDF content: {text[:1000]}"})
            else:
                self.status_label.setText("Status: Unsupported file type")
                return

            self.update_chat_history()
            self.send_api_request("Analyze the uploaded file")
        except Exception as e:
            self.status_label.setText(f"Status: File analysis failed ({str(e)})")

    def clear_history(self):
        self.conversation = []
        self.update_chat_history()
        self.save_conversation()
        self.status_label.setText("Status: History cleared")

class Plugin(Plugin):
    def __init__(self, browser, name="Gemini Chat Plugin", version="1.0"):
        super().__init__(browser, name, version)

    def add_to_menu(self, menu):
        try:
            action = QAction("Gemini Chat", self.browser)
            action.triggered.connect(self.open_dialog)
            menu.addAction(action)
        except NameError as e:
            self.browser.statusBar.showMessage(f"Gemini Chat Plugin: QAction not available: {str(e)}", 5000)

    def open_dialog(self):
        if not self.browser.vault:
            QMessageBox.warning(self.browser, "Vault Locked", "You must unlock the vault to use the Gemini Chat plugin.")
            return
        dialog = GeminiChatDialog(plugin=self, parent=self.browser)
        dialog.exec()