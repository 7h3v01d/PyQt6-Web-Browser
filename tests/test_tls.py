"""
Transport security policy.

The certificate tests encode a deliberate stance: an unrecognised error is
never treated as benign, revocation and interception cannot be bypassed at
all, and overrides live only for the session.
"""

import pytest

from tls import (
    CertExceptionStore,
    CertSeverity,
    HttpsDecision,
    classify_certificate_error,
    confirmation_phrase,
    https_decision,
    interstitial_text,
    is_local_host,
    upgrade_url,
)


# ── local host detection ─────────────────────────────────────────────────

@pytest.mark.parametrize("host", [
    "localhost", "127.0.0.1", "::1",
    "dev.local", "box.internal", "app.test", "thing.localhost",
    "192.168.0.163",          # the Ollama rig
    "10.0.0.5",
    "172.16.4.4", "172.31.255.1",
])
def test_local_hosts_recognised(host):
    assert is_local_host(host)


@pytest.mark.parametrize("host", [
    "example.com", "github.com",
    "172.15.0.1", "172.32.0.1",      # just outside RFC1918
    "11.0.0.1", "193.168.0.1",
    "", None,
])
def test_public_hosts_not_local(host):
    assert not is_local_host(host)


def test_local_check_ignores_port_and_case():
    assert is_local_host("LOCALHOST:8080")
    assert is_local_host("192.168.0.163:11434")


# ── URL upgrading ────────────────────────────────────────────────────────

@pytest.mark.parametrize("given,expected", [
    ("http://example.com", "https://example.com"),
    ("http://example.com/path?q=1#frag", "https://example.com/path?q=1#frag"),
    ("http://user@example.com:8080/x", "https://user@example.com:8080/x"),
])
def test_upgrade_rewrites_scheme_only(given, expected):
    assert upgrade_url(given) == expected


@pytest.mark.parametrize("url", [
    "https://example.com", "file:///C:/x.html", "about:blank", "",
])
def test_upgrade_leaves_other_schemes_alone(url):
    assert upgrade_url(url) == url


# ── HTTPS-only decisions ─────────────────────────────────────────────────

class TestHttpsOnly:

    def test_http_is_upgraded_when_enabled(self):
        assert https_decision("http://example.com", True) is HttpsDecision.UPGRADE

    def test_http_untouched_when_disabled(self):
        assert https_decision("http://example.com", False) is HttpsDecision.ALLOW

    def test_https_always_allowed(self):
        assert https_decision("https://example.com", True) is HttpsDecision.ALLOW

    @pytest.mark.parametrize("url", [
        "file:///C:/new_tab.html", "about:blank", "data:text/html,x",
        "blob:https://example.com/1", "chrome://settings",
    ])
    def test_internal_schemes_untouched(self, url):
        assert https_decision(url, True) is HttpsDecision.ALLOW

    @pytest.mark.parametrize("url", [
        "http://localhost:8899",              # What's On My Face
        "http://192.168.0.163:11434",         # local Ollama
        "http://127.0.0.1:8050",              # voice gateway
    ])
    def test_local_services_not_upgraded(self, url):
        """Upgrading these would break local tooling that has no TLS."""
        assert https_decision(url, True) is HttpsDecision.ALLOW

    def test_user_exemption_respected(self):
        assert https_decision("http://legacy.example.com", True,
                              exempt_hosts=["legacy.example.com"]) is HttpsDecision.ALLOW

    def test_exemption_is_case_insensitive(self):
        assert https_decision("http://Legacy.Example.COM", True,
                              exempt_hosts=["legacy.example.com"]) is HttpsDecision.ALLOW

    def test_exemption_does_not_leak_to_other_hosts(self):
        assert https_decision("http://other.example.com", True,
                              exempt_hosts=["legacy.example.com"]) is HttpsDecision.UPGRADE


# ── certificate classification ───────────────────────────────────────────

class TestCertificateSeverity:

    @pytest.mark.parametrize("description", [
        "The certificate has expired",
        "Certificate date invalid",
        "The certificate is not yet valid",
    ])
    def test_expiry_is_overridable(self, description):
        assert classify_certificate_error(description) is CertSeverity.OVERRIDABLE

    @pytest.mark.parametrize("description", [
        "The certificate has been revoked",
        "Certificate transparency required",
        "Certificate uses a pinned key that does not match",
        "Known interception detected",
    ])
    def test_interception_markers_are_fatal(self, description):
        assert classify_certificate_error(description) is CertSeverity.FATAL

    @pytest.mark.parametrize("description", [
        "The certificate's common name is invalid",
        "Certificate authority invalid",
        "Self signed certificate",
        "The certificate name does not match the host",
        "Weak signature algorithm (SHA-1)",
        "Certificate is malformed",
    ])
    def test_trust_failures_are_dangerous(self, description):
        assert classify_certificate_error(description) is CertSeverity.DANGEROUS

    @pytest.mark.parametrize("description", [
        "", None, "   ", "some error nobody has ever seen",
    ])
    def test_unknown_errors_default_to_dangerous(self, description):
        """Fail closed: an unrecognised error is not a safe error."""
        assert classify_certificate_error(description) is CertSeverity.DANGEROUS

    def test_classification_is_case_insensitive(self):
        assert classify_certificate_error("THE CERTIFICATE HAS BEEN REVOKED") is CertSeverity.FATAL

    def test_fatal_beats_dangerous_when_both_present(self):
        both = "Self signed certificate that has also been revoked"
        assert classify_certificate_error(both) is CertSeverity.FATAL


class TestOverridePermissions:

    def test_fatal_cannot_be_bypassed(self):
        assert CertSeverity.FATAL.may_override is False

    def test_dangerous_needs_typed_confirmation(self):
        assert CertSeverity.DANGEROUS.may_override is True
        assert CertSeverity.DANGEROUS.requires_typed_confirmation is True

    def test_overridable_needs_only_a_click(self):
        assert CertSeverity.OVERRIDABLE.may_override is True
        assert CertSeverity.OVERRIDABLE.requires_typed_confirmation is False

    def test_confirmation_phrase_is_the_host(self):
        assert confirmation_phrase("Example.COM ") == "example.com"


# ── interstitial copy ────────────────────────────────────────────────────

class TestInterstitialText:

    def test_names_the_host(self):
        headline, _ = interstitial_text("bank.example.com", "expired",
                                        CertSeverity.OVERRIDABLE)
        assert "bank.example.com" in headline

    def test_fatal_says_it_cannot_be_bypassed(self):
        _, body = interstitial_text("x.com", "revoked", CertSeverity.FATAL)
        assert "cannot be bypassed" in body.lower()

    def test_dangerous_warns_about_impersonation(self):
        _, body = interstitial_text("x.com", "authority invalid",
                                    CertSeverity.DANGEROUS)
        assert "impersonating" in body.lower()

    def test_description_always_included(self):
        for severity in CertSeverity:
            _, body = interstitial_text("x.com", "UNIQUE-MARKER", severity)
            assert "UNIQUE-MARKER" in body


# ── exception store ──────────────────────────────────────────────────────

class TestCertExceptionStore:

    def test_nothing_allowed_initially(self):
        assert not CertExceptionStore().is_allowed("example.com", "expired")

    def test_grant_is_remembered(self):
        store = CertExceptionStore()
        store.allow("example.com", "expired")
        assert store.is_allowed("example.com", "expired")

    def test_grant_does_not_cover_other_hosts(self):
        store = CertExceptionStore()
        store.allow("example.com", "expired")
        assert not store.is_allowed("other.com", "expired")

    def test_grant_does_not_cover_other_errors(self):
        """A new failure mode on a trusted host must ask again."""
        store = CertExceptionStore()
        store.allow("example.com", "expired")
        assert not store.is_allowed("example.com", "authority invalid")

    def test_matching_ignores_case_and_padding(self):
        store = CertExceptionStore()
        store.allow("Example.COM", "Expired")
        assert store.is_allowed(" example.com ", " expired ")

    def test_clear_revokes_everything(self):
        store = CertExceptionStore()
        store.allow("a.com", "e")
        store.allow("b.com", "e")
        assert len(store) == 2
        store.clear()
        assert len(store) == 0

    def test_store_has_no_persistence_api(self):
        """
        Session-only by design: a saved exception downgrades that host
        forever with no reminder it was ever granted.
        """
        store = CertExceptionStore()
        for forbidden in ("save", "load", "path", "write", "dump"):
            assert not hasattr(store, forbidden)
