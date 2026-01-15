import os
import urllib.request
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import QDateTime

class Plugin:
    def __init__(self, browser, name="Unnamed Plugin", version="1.0"):
        self.browser = browser
        self.name = name
        self.version = version
        self.initialized = False
        self.shared_requests = []  # Shared storage for requests
        self.shared_responses = []  # Shared storage for responses
    
    def init_plugin(self):
        """Initialize the plugin with error handling."""
        try:
            self.initialized = True
            self.browser.statusBar.showMessage(f"Plugin {self.name} v{self.version} initialized", 5000)
        except Exception as e:
            self.browser.statusBar.showMessage(f"Failed to initialize plugin {self.name}: {str(e)}", 5000)
            self.initialized = False
    
    def add_to_toolbar(self, toolbar):
        """Add actions or widgets to the toolbar."""
        pass
    
    def add_to_menu(self, menu):
        """Add actions to a specified menu."""
        pass
    
    def get_interceptor(self):
        """Return a request interceptor if any."""
        return None
    
    def log_request(self, request_data):
        """Store request data in shared storage."""
        try:
            self.shared_requests.append(request_data)
            self.browser.statusBar.showMessage(f"Plugin {self.name}: Logged request to {request_data['url']}", 5000)
        except Exception as e:
            self.browser.statusBar.showMessage(f"Plugin {self.name}: Failed to log request: {str(e)}", 5000)
    
    def log_response(self, response_data):
        """Store response data in shared storage."""
        try:
            self.shared_responses.append(response_data)
            self.browser.statusBar.showMessage(f"Plugin {self.name}: Logged response from {response_data['url']}", 5000)
        except Exception as e:
            self.browser.statusBar.showMessage(f"Plugin {self.name}: Failed to log response: {str(e)}", 5000)
    
    def get_shared_requests(self):
        """Return shared requests for other plugins."""
        return self.shared_requests
    
    def get_shared_responses(self):
        """Return shared responses for other plugins."""
        return self.shared_responses

class ChainedInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, interceptors):
        super().__init__()
        self.interceptors = interceptors
    
    def interceptRequest(self, info):
        for interceptor in self.interceptors:
            try:
                interceptor.interceptRequest(info)
            except Exception as e:
                print(f"Interceptor error: {str(e)}")

class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self):
        super().__init__()
        self.ad_filters = []
        self.enabled = True
        self.load_easylist()
    
    def load_easylist(self):
        try:
            easylist_file = "easylist.txt"
            if not os.path.exists(easylist_file) or os.path.getmtime(easylist_file) < QDateTime.currentDateTime().addDays(-7).toMSecsSinceEpoch() / 1000:
                urllib.request.urlretrieve("https://easylist.to/easylist/easylist.txt", easylist_file)
            with open(easylist_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(("[", "!")) and "||" in line:
                        domain = line.split("||")[1].split("^")[0]
                        self.ad_filters.append(domain.lower())
        except Exception as e:
            print(f"Failed to load EasyList: {str(e)}")
    
    def interceptRequest(self, info):
        if not self.enabled:
            return
        url = info.requestUrl().host().lower()
        print(f"AdBlockInterceptor: Checking URL: {url}")  # Debug log
        # Whitelist Netflix-related domains
        if any(domain in url for domain in ['netflix.com', 'licensewidevine.com', 'nflxvideo.net', 'nflximg.net', 'nflxext.com']):
            return
        if any(ad_filter in url for ad_filter in self.ad_filters):
            print(f"AdBlockInterceptor: Blocking URL: {url}")  # Debug log
            info.block(True)

class ProxyInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
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