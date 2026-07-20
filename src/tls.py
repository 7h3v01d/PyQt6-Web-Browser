"""
tls.py  —  transport security policy.

Two things live here, both as pure functions so the decisions can be tested
without a network or a running engine.

HTTPS-only: decide whether a navigation should be silently upgraded to
https, allowed as-is, or blocked pending user consent.

Certificate errors: the previous handler was a plain Yes/No message box.
One click past a certificate warning is how interception succeeds in
practice, which is why every mainstream browser makes it deliberately
awkward and refuses to let you bypass some errors at all. This module
classifies an error and says how much friction the interstitial should
apply.
"""

from enum import Enum
from urllib.parse import urlsplit, urlunsplit

# Hosts where plain http is normal and upgrading only breaks things.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})
LOCAL_SUFFIXES = ("localhost", ".local", ".localhost", ".internal", ".test")

# Schemes we never touch.
NON_WEB_SCHEMES = frozenset({"file", "about", "data", "blob", "chrome",
                             "javascript", "qrc", "view-source"})


class HttpsDecision(Enum):
    ALLOW = "allow"        # already secure, or a scheme/host we leave alone
    UPGRADE = "upgrade"    # rewrite to https and continue
    BLOCK = "block"        # http, upgrade refused before — needs consent


class CertSeverity(Enum):
    """
    How dangerous proceeding would be.

    OVERRIDABLE     — plausibly benign (self-signed lab box, expired cert)
    DANGEROUS       — likely interception; allow only with typed confirmation
    FATAL           — never offer a bypass
    """
    OVERRIDABLE = "overridable"
    DANGEROUS = "dangerous"
    FATAL = "fatal"

    @property
    def may_override(self) -> bool:
        return self is not CertSeverity.FATAL

    @property
    def requires_typed_confirmation(self) -> bool:
        return self is CertSeverity.DANGEROUS


# Matched against QWebEngineCertificateError.description(), lowercased.
# Qt's enum names differ across versions, so text matching is the portable
# option — hence the deliberately broad fragments.
_FATAL_MARKERS = (
    "revoked",
    "known interception",
    "pinned key",
    "certificate transparency",
)

_DANGEROUS_MARKERS = (
    "common name invalid",
    "name mismatch",
    "does not match",
    "authority invalid",
    "issuer",
    "untrusted",
    "self signed",
    "self-signed",
    "weak",
    "sha-1",
    "malformed",
)


def _split(url):
    parts = urlsplit(str(url or "").strip())
    return parts


def is_local_host(host: str) -> bool:
    """Loopback and LAN-style names, where plain http is expected."""
    if not host:
        return False
    host = host.strip().lower().rstrip(".")
    # IPv6 arrives either bare ("::1") or bracketed with a port ("[::1]:80").
    # A naive split(":")[0] turns "::1" into an empty string.
    if host.startswith("["):
        host = host[1:].split("]")[0]
    elif host.count(":") == 1:
        host = host.split(":")[0]
    if host in LOCAL_HOSTS:
        return True
    if host.endswith(LOCAL_SUFFIXES):
        return True
    # RFC1918 ranges — a home lab or a local Ollama box
    if host.startswith(("10.", "192.168.")):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) == 4 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    return False


def upgrade_url(url) -> str:
    """Return the https form of an http URL, preserving everything else."""
    parts = _split(url)
    if parts.scheme.lower() != "http":
        return str(url)
    return urlunsplit(("https",) + tuple(parts)[1:])


def https_decision(url, https_only_enabled: bool, exempt_hosts=()) -> HttpsDecision:
    """
    Decide what to do with a navigation.

    exempt_hosts holds hosts the user has already chosen to load over http
    this session, so they are not asked twice.
    """
    parts = _split(url)
    scheme = parts.scheme.lower()

    if not scheme or scheme in NON_WEB_SCHEMES:
        return HttpsDecision.ALLOW
    if scheme != "http":
        return HttpsDecision.ALLOW
    if not https_only_enabled:
        return HttpsDecision.ALLOW

    host = parts.hostname or ""
    if is_local_host(host):
        return HttpsDecision.ALLOW
    if host.lower() in {h.lower() for h in exempt_hosts}:
        return HttpsDecision.ALLOW

    return HttpsDecision.UPGRADE


def classify_certificate_error(description, url=None) -> CertSeverity:
    """
    Grade a certificate error from its description.

    Unknown wording is treated as DANGEROUS rather than OVERRIDABLE: an
    error we do not recognise is not an error we should wave through.
    """
    text = str(description or "").strip().lower()
    if not text:
        return CertSeverity.DANGEROUS

    for marker in _FATAL_MARKERS:
        if marker in text:
            return CertSeverity.FATAL

    # Expiry is the classic benign case — a lapsed cert on a site you know.
    if "expired" in text or "not yet valid" in text or "date invalid" in text:
        return CertSeverity.OVERRIDABLE

    for marker in _DANGEROUS_MARKERS:
        if marker in text:
            return CertSeverity.DANGEROUS

    return CertSeverity.DANGEROUS


def confirmation_phrase(host: str) -> str:
    """
    What the user must type to bypass a DANGEROUS error.

    Typing the hostname forces them to look at which host they are actually
    trusting, which is the detail an interception attack depends on them
    ignoring.
    """
    return (host or "").strip().lower()


def interstitial_text(host, description, severity: CertSeverity) -> tuple:
    """(headline, body) for the certificate interstitial."""
    host = host or "this site"
    if severity is CertSeverity.FATAL:
        return (
            f"Blackline blocked the connection to {host}",
            f"{description}\n\nThis error cannot be bypassed. The certificate "
            "indicates the connection is being intercepted or the certificate "
            "has been revoked.",
        )
    if severity is CertSeverity.DANGEROUS:
        return (
            f"Your connection to {host} is not private",
            f"{description}\n\nSomeone may be impersonating {host} to steal "
            "passwords, messages, or card details. Continue only if you "
            "understand exactly why this certificate is wrong.",
        )
    return (
        f"The certificate for {host} is out of date",
        f"{description}\n\nThis often means the site's certificate expired or "
        "the clock on this machine is wrong. Check the date before continuing.",
    )


class CertExceptionStore:
    """
    Session-scoped certificate overrides.

    Deliberately in-memory only. A persisted exception silently downgrades
    that host's security forever, and the user would have no reminder they
    ever granted it. Exceptions are keyed by host *and* error text, so a
    different failure on the same host asks again.
    """

    __slots__ = ("_granted",)

    def __init__(self):
        self._granted = set()

    @staticmethod
    def _key(host, description):
        return ((host or "").strip().lower(), str(description or "").strip().lower())

    def allow(self, host, description):
        self._granted.add(self._key(host, description))

    def is_allowed(self, host, description) -> bool:
        return self._key(host, description) in self._granted

    def clear(self):
        self._granted.clear()

    def __len__(self):
        return len(self._granted)
