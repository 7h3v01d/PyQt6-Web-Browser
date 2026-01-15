try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox, QProgressBar, QTextEdit, QCheckBox
    from PyQt6.QtGui import QAction
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
    from PyQt6.QtCore import QUrl
except ImportError as e:
    print(f"Failed to import PyQt6 modules: {str(e)}")
    raise
from interceptors import Plugin
import os
import yt_dlp
from pathlib import Path

class YouTubeDownloaderDialog(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(200, 200, 600, 500)
        self.layout = QVBoxLayout()

        # Embedded browser for YouTube browsing
        self.profile = QWebEngineProfile("YouTubeDownloaderProfile", self)
        if self.plugin.browser.anonymous_mode and self.plugin.browser.tor_enabled:
            self.profile.setProxyConfig(QWebEngineProfile.ProxyConfig(
                QWebEngineProfile.ProxyType.Socks5Proxy, "127.0.0.1", 9050
            ))
        self.browser = QWebEngineView()
        self.page = QWebEnginePage(self.profile, self.browser)
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl("https://www.youtube.com"))
        self.layout.addWidget(self.browser)

        # URL input for videos or playlists
        self.url_label = QLabel("YouTube Video/Playlist URL(s) (one per line):")
        self.layout.addWidget(self.url_label)
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("Enter YouTube video or playlist URL(s), e.g., https://www.youtube.com/watch?... or https://www.youtube.com/playlist?...")
        self.layout.addWidget(self.url_input)

        # Format selection (video or audio)
        self.format_label = QLabel("Download Format:")
        self.layout.addWidget(self.format_label)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Video (MP4)", "Audio (MP3)"])
        self.layout.addWidget(self.format_combo)

        # Quality selection (for video)
        self.quality_label = QLabel("Video Quality:")
        self.layout.addWidget(self.quality_label)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["720p", "1080p", "4K", "Best Available"])
        self.layout.addWidget(self.quality_combo)

        # Subtitle language selection
        self.subtitle_label = QLabel("Subtitle Language:")
        self.layout.addWidget(self.subtitle_label)
        self.subtitle_combo = QComboBox()
        self.subtitle_combo.addItems(["None", "English", "Spanish", "French", "German", "Japanese"])
        self.layout.addWidget(self.subtitle_combo)

        # Download button
        self.download_btn = QPushButton("Download Video(s)")
        self.download_btn.clicked.connect(self.start_download)
        self.layout.addWidget(self.download_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Status: Ready")
        self.layout.addWidget(self.status_label)

        self.setLayout(self.layout)

    def start_download(self):
        """Download single video, playlist, or multiple URLs."""
        urls = self.url_input.toPlainText().strip().split("\n")
        if not urls:
            self.status_label.setText("Status: No URLs provided")
            self.plugin.browser.statusBar.showMessage("No URLs provided", 5000)
            return

        format_type = self.format_combo.currentText()
        quality = self.quality_combo.currentText()
        subtitle_lang = self.subtitle_combo.currentText().lower() if self.subtitle_combo.currentText() != "None" else None

        output_dir = Path("downloads")
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / "%(title)s.%(ext)s")

        ydl_opts = {
            "outtmpl": output_path,
            "quiet": True,
            "progress_hooks": [self.update_progress],
            "noplaylist": False,  # Allow playlists
        }

        if format_type == "Video (MP4)":
            ydl_opts["format"] = "bestvideo[height<=?{}]+bestaudio/best".format(
                quality.replace("p", "") if quality != "Best Available" else "4320"
            )
            ydl_opts["merge_output_format"] = "mp4"
        else:  # Audio (MP3)
            ydl_opts["format"] = "bestaudio"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }]

        if subtitle_lang:
            ydl_opts["sub_lang"] = subtitle_lang
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = False
            ydl_opts["sub_format"] = "srt"

        try:
            self.status_label.setText("Status: Downloading...")
            self.download_btn.setEnabled(False)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for url in urls:
                    if not url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
                        self.status_label.setText(f"Status: Invalid YouTube URL: {url}")
                        self.plugin.browser.statusBar.showMessage(f"Invalid YouTube URL: {url}", 5000)
                        continue
                    ydl.download([url])
            self.status_label.setText("Status: Download completed")
            self.plugin.browser.statusBar.showMessage(f"YouTube video(s) downloaded to {output_dir}", 5000)
        except Exception as e:
            self.status_label.setText(f"Status: Download failed ({str(e)})")
            self.plugin.browser.statusBar.showMessage(f"YouTube download failed: {str(e)}", 5000)
        finally:
            self.download_btn.setEnabled(True)
            self.progress_bar.setValue(0)

    def update_progress(self, d):
        if d["status"] == "downloading":
            percent = d.get("downloaded_bytes", 0) / d.get("total_bytes", 1) * 100
            self.progress_bar.setValue(int(percent))
        elif d["status"] == "finished":
            self.progress_bar.setValue(100)

class Plugin(Plugin):
    def __init__(self, browser, name="YouTube Downloader Plugin", version="1.0"):
        super().__init__(browser, name, version)

    def add_to_menu(self, menu):
        try:
            action = QAction("YouTube Downloader", self.browser)
            action.triggered.connect(self.open_dialog)
            menu.addAction(action)
        except NameError as e:
            self.browser.statusBar.showMessage(f"YouTube Downloader Plugin: QAction not available: {str(e)}", 5000)

    def open_dialog(self):
        dialog = YouTubeDownloaderDialog(plugin=self, parent=self.browser)
        dialog.exec()