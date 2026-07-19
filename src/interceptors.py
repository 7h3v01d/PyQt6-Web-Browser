import os
import re
import urllib.request
import logging
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import QDateTime

logger = logging.getLogger(__name__)

EASYLIST_MIRRORS = [
    "https://easylist-downloads.adblockplus.org/easylist.txt",
    "https://raw.githubusercontent.com/easylist/easylist/master/easylist.txt",
    "https://easylist.to/easylist/easylist.txt",
]

EASYLIST_FILE = "easylist.txt"
_HOSTNAME_RE = re.compile(r"^[a-z0-9]([a-z0-9\-_.]*[a-z0-9])?$")
EASYLIST_MAX_AGE_DAYS = 7


class Plugin:
    def __init__(self, browser, name="Unnamed Plugin", version="1.0"):
        self.browser = browser
        self.name = name
        self.version = version
        self.initialized = False
        self.shared_requests = []
        self.shared_responses = []

    def init_plugin(self):
        try:
            self.initialized = True
            self.browser.statusBar.showMessage(f"Plugin {self.name} v{self.version} initialized", 5000)
        except Exception as e:
            self.browser.statusBar.showMessage(f"Failed to initialize plugin {self.name}: {str(e)}", 5000)
            self.initialized = False

    def add_to_toolbar(self, toolbar): pass
    def add_to_menu(self, menu): pass
    def get_interceptor(self): return None

    def log_request(self, request_data):
        try:
            self.shared_requests.append(request_data)
        except Exception as e:
            logger.debug(f"Plugin {self.name}: Failed to log request: {str(e)}")

    def log_response(self, response_data):
        try:
            self.shared_responses.append(response_data)
        except Exception as e:
            logger.debug(f"Plugin {self.name}: Failed to log response: {str(e)}")

    def get_shared_requests(self): return self.shared_requests
    def get_shared_responses(self): return self.shared_responses


class ChainedInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, interceptors):
        super().__init__()
        self.interceptors = interceptors

    def interceptRequest(self, info):
        for interceptor in self.interceptors:
            try:
                interceptor.interceptRequest(info)
            except Exception as e:
                logger.debug(f"Interceptor error: {str(e)}")


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    WHITELIST = frozenset([
        'netflix.com', 'licensewidevine.com', 'nflxvideo.net',
        'nflximg.net', 'nflxext.com', 'widevine.com',
    ])

    def __init__(self):
        super().__init__()
        self.ad_filters = set()
        self.enabled = True
        self.load_easylist()

    def _needs_refresh(self):
        if not os.path.exists(EASYLIST_FILE):
            return True
        cutoff = QDateTime.currentDateTime().addDays(-EASYLIST_MAX_AGE_DAYS).toMSecsSinceEpoch() / 1000
        return os.path.getmtime(EASYLIST_FILE) < cutoff

    def _download_easylist(self):
        """Try each mirror in turn; return True on success."""
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AdBlocker/1.0)"}
        for url in EASYLIST_MIRRORS:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = response.read()
                with open(EASYLIST_FILE, "wb") as f:
                    f.write(data)
                logger.info(f"EasyList downloaded from {url}")
                return True
            except Exception as e:
                logger.warning(f"EasyList mirror failed ({url}): {e}")
        return False

    def load_easylist(self):
        if self._needs_refresh():
            ok = self._download_easylist()
            if not ok:
                if not os.path.exists(EASYLIST_FILE):
                    logger.warning("EasyList unavailable — ad blocking will be limited.")
                    return
                logger.warning("Using stale EasyList (all mirrors failed).")
        try:
            filters = set()
            skipped = 0
            with open(EASYLIST_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    domain = self._parse_rule(line.strip())
                    if domain:
                        filters.add(domain)
                    else:
                        skipped += 1
            self.ad_filters = filters
            logger.info(f"EasyList loaded: {len(self.ad_filters):,} domain rules "
                        f"({skipped:,} non-domain rules ignored)")
        except Exception as e:
            logger.error(f"Failed to parse EasyList: {e}")

    @staticmethod
    def _parse_rule(line: str):
        """
        Extract a blockable hostname from an EasyList line, or None.

        Only plain domain anchors are honoured — "||doubleclick.net^$third-party".
        Rules carrying a path, a wildcard, or a $domain= scope are skipped: we
        have no page context here, so applying them globally is what caused
        github.com and youtube.com to be blocked outright.
        """
        if not line or line.startswith(("[", "!", "@@", "#", "/")):
            return None
        if not line.startswith("||"):
            return None
        body = line[2:]
        options = ""
        if "$" in body:
            body, options = body.split("$", 1)
        body = body.split("^")[0].strip().lower()
        if not body or "/" in body or "*" in body or "." not in body:
            return None
        if "domain=" in options:              # site-scoped rule, not global
            return None
        if not _HOSTNAME_RE.match(body):
            return None
        return body

    def _is_blocked(self, host: str) -> bool:
        """Exact host or true subdomain match — never a bare substring."""
        if host in self.ad_filters:
            return True
        parts = host.split(".")
        for i in range(1, len(parts) - 1):
            if ".".join(parts[i:]) in self.ad_filters:
                return True
        return False

    def interceptRequest(self, info):
        if not self.enabled:
            return
        host = info.requestUrl().host().lower()
        if not host:
            return
        if any(host == w or host.endswith("." + w) for w in self.WHITELIST):
            return
        if self._is_blocked(host):
            info.block(True)


class ProxyInterceptor(QWebEngineUrlRequestInterceptor):
    WHITELIST = frozenset([
        'netflix.com', 'licensewidevine.com', 'nflxvideo.net',
        'nflximg.net', 'nflxext.com',
    ])

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.paused = False
        self.pending_request = None

    def interceptRequest(self, info):
        url_str = info.requestUrl().toString()
        if any(w in url_str for w in self.WHITELIST):
            return
        request_data = {
            "url": url_str,
            "method": info.requestMethod().decode(),
            "headers": {k.decode(): v.decode() for k, v in info.requestHeaders().items()},
            "body": info.requestData().decode() if info.requestData() else ""
        }
        self.plugin.log_request(request_data)
        if self.paused:
            self.pending_request = info
            self.plugin.show_pending_request(request_data)
            info.block(True)
