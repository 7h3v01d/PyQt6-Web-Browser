import os
import urllib.request
import logging
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import QDateTime, QUrl

from adblock import FilterSet, host_matches_any
from tls import HttpsDecision, https_decision, upgrade_url
from cosmetic import CosmeticFilterSet

logger = logging.getLogger(__name__)

EASYLIST_MIRRORS = [
    "https://easylist-downloads.adblockplus.org/easylist.txt",
    "https://raw.githubusercontent.com/easylist/easylist/master/easylist.txt",
    "https://easylist.to/easylist/easylist.txt",
]

EASYPRIVACY_MIRRORS = [
    "https://easylist-downloads.adblockplus.org/easyprivacy.txt",
    "https://raw.githubusercontent.com/easylist/easylist/master/easyprivacy.txt",
    "https://easylist.to/easylist/easyprivacy.txt",
]

EASYLIST_FILE = "easylist.txt"
EASYPRIVACY_FILE = "easyprivacy.txt"
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


class HttpsOnlyInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Rewrites http:// navigations to https://.

    Local and RFC1918 hosts are left alone — upgrading them would break
    the local tooling that has no TLS at all. Hosts the user has chosen to
    load over http are exempt for the session only.
    """

    def __init__(self):
        super().__init__()
        self.enabled = False
        self.exempt_hosts = set()
        self.upgrades = 0

    def exempt(self, host):
        if host:
            self.exempt_hosts.add(str(host).strip().lower())

    def interceptRequest(self, info):
        if not self.enabled:
            return
        url = info.requestUrl()
        decision = https_decision(url.toString(), True, self.exempt_hosts)
        if decision is HttpsDecision.UPGRADE:
            secure = upgrade_url(url.toString())
            self.upgrades += 1
            logger.debug(f"HTTPS-only upgrade: {url.toString()} -> {secure}")
            info.redirect(QUrl(secure))


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    WHITELIST = frozenset([
        'netflix.com', 'licensewidevine.com', 'nflxvideo.net',
        'nflximg.net', 'nflxext.com', 'widevine.com',
    ])

    def __init__(self):
        super().__init__()
        self.filters = FilterSet()
        self.cosmetics = CosmeticFilterSet()
        self.enabled = True
        self.load_easylist()

    def _needs_refresh(self):
        if not os.path.exists(EASYLIST_FILE):
            return True
        cutoff = QDateTime.currentDateTime().addDays(-EASYLIST_MAX_AGE_DAYS).toMSecsSinceEpoch() / 1000
        return os.path.getmtime(EASYLIST_FILE) < cutoff

    def _download_list(self, mirrors, target):
        """Try each mirror in turn; return True on success."""
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AdBlocker/1.0)"}
        for url in mirrors:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = response.read()
                with open(target, "wb") as f:
                    f.write(data)
                logger.info(f"{target} downloaded from {url}")
                return True
            except Exception as e:
                logger.warning(f"Mirror failed ({url}): {e}")
        return False

    def _download_easylist(self):
        return self._download_list(EASYLIST_MIRRORS, EASYLIST_FILE)

    def load_easylist(self):
        if self._needs_refresh():
            ok = self._download_easylist()
            if not ok:
                if not os.path.exists(EASYLIST_FILE):
                    logger.warning("EasyList unavailable — ad blocking will be limited.")
                    return
                logger.warning("Using stale EasyList (all mirrors failed).")
        # EasyPrivacy is a separate list covering trackers and analytics,
        # which EasyList deliberately leaves alone.
        if not os.path.exists(EASYPRIVACY_FILE):
            self._download_list(EASYPRIVACY_MIRRORS, EASYPRIVACY_FILE)

        try:
            self.filters = FilterSet.from_file(EASYLIST_FILE)
            base_rules = len(self.filters)

            if os.path.exists(EASYPRIVACY_FILE):
                privacy = FilterSet.from_file(EASYPRIVACY_FILE)
                self.filters.domains |= privacy.domains
                logger.info(f"EasyPrivacy loaded: {len(privacy):,} tracker rules")

            # Element hiding — the half of the list previously discarded, and
            # the reason blocked ads still left holes in the layout.
            self.cosmetics = CosmeticFilterSet.from_file(EASYLIST_FILE)
            logger.info(f"EasyList loaded: {base_rules:,} domain rules, "
                        f"{len(self.cosmetics):,} cosmetic rules "
                        f"({len(self.filters):,} blocked hosts total)")
        except Exception as e:
            logger.error(f"Failed to parse filter lists: {e}")

    def interceptRequest(self, info):
        if not self.enabled:
            return
        host = info.requestUrl().host().lower()
        if not host:
            return
        if host_matches_any(host, self.WHITELIST):
            return
        if self.filters.is_blocked(host):
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
