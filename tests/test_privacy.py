"""
Private browsing policy.

Private mode fails silently — the tab looks correct while a URL lands in
history.json or tabs.json — so every write path is gated by a pure
predicate and every predicate is pinned here.
"""

import pytest

from privacy import (
    PRIVATE_PREFIX,
    is_internal_url,
    is_private_label,
    privacy_summary,
    should_offer_password_save,
    should_persist_tab,
    should_record_history,
    strip_private_marker,
    tab_label,
)

REAL_URLS = [
    "https://example.com",
    "https://example.com/page?q=1",
    "http://insecure.example.com",
    "https://sub.domain.example.co.uk/deep/path",
]

INTERNAL_URLS = [
    "file:///G:/Projects/blackline-browser/src/new_tab.html",
    "about:blank",
    "chrome://settings",
    "data:text/html,<h1>hi</h1>",
    "blob:https://example.com/1234",
    "javascript:void(0)",
]


# ── internal URL detection ───────────────────────────────────────────────

@pytest.mark.parametrize("url", INTERNAL_URLS)
def test_internal_urls_detected(url):
    assert is_internal_url(url)


@pytest.mark.parametrize("url", REAL_URLS)
def test_real_urls_are_not_internal(url):
    assert not is_internal_url(url)


@pytest.mark.parametrize("url", ["", None, "   "])
def test_empty_url_treated_as_internal(url):
    assert is_internal_url(url)


def test_scheme_check_is_case_insensitive():
    assert is_internal_url("FILE:///C:/x.html")
    assert is_internal_url("About:Blank")


# ── the leak guarantees ──────────────────────────────────────────────────

class TestPrivateTabsWriteNothing:
    """The core promise. If any of these invert, private mode is a lie."""

    @pytest.mark.parametrize("url", REAL_URLS + INTERNAL_URLS)
    def test_never_recorded_in_history(self, url):
        assert should_record_history(url, private=True) is False

    @pytest.mark.parametrize("url", REAL_URLS + INTERNAL_URLS)
    def test_never_persisted_to_session(self, url):
        assert should_persist_tab(url, private=True) is False

    def test_no_password_capture(self):
        assert should_offer_password_save(private=True) is False

    def test_private_flag_dominates_url_shape(self):
        """A perfectly ordinary URL is still excluded when private."""
        url = "https://example.com"
        assert should_record_history(url, private=False) is True
        assert should_record_history(url, private=True) is False


class TestNormalTabsStillWork:
    """Guard against over-correcting and breaking ordinary browsing."""

    @pytest.mark.parametrize("url", REAL_URLS)
    def test_history_recorded(self, url):
        assert should_record_history(url, private=False) is True

    @pytest.mark.parametrize("url", REAL_URLS)
    def test_session_persisted(self, url):
        assert should_persist_tab(url, private=False) is True

    @pytest.mark.parametrize("url", INTERNAL_URLS)
    def test_internal_pages_still_excluded(self, url):
        assert should_record_history(url, private=False) is False
        assert should_persist_tab(url, private=False) is False

    def test_password_capture_allowed(self):
        assert should_offer_password_save(private=False) is True


# ── labelling ────────────────────────────────────────────────────────────

class TestTabLabels:

    def test_private_tabs_are_marked(self):
        assert tab_label("Example", private=True).startswith(PRIVATE_PREFIX)

    def test_normal_tabs_are_not(self):
        assert tab_label("Example", private=False) == "Example"

    def test_empty_title_falls_back(self):
        assert tab_label("", private=False) == "New Tab"
        assert tab_label(None, private=False) == "New Tab"
        assert tab_label("   ", private=False) == "New Tab"

    def test_long_title_truncated(self):
        assert len(tab_label("x" * 200, private=False)) == 30

    def test_marker_survives_truncation(self):
        """A long title must not push the private marker out of view."""
        label = tab_label("x" * 200, private=True)
        assert label.startswith(PRIVATE_PREFIX)
        assert len(label) == 30

    def test_round_trip_marker(self):
        label = tab_label("Example", private=True)
        assert is_private_label(label)
        assert strip_private_marker(label) == "Example"

    def test_strip_is_a_noop_on_normal_labels(self):
        assert strip_private_marker("Example") == "Example"
        assert not is_private_label("Example")

    def test_custom_limit(self):
        assert len(tab_label("x" * 50, private=False, limit=10)) == 10


# ── status text ──────────────────────────────────────────────────────────

def test_private_summary_states_the_guarantees():
    text = privacy_summary(True).lower()
    for promise in ("history", "session", "password", "cookies"):
        assert promise in text


def test_normal_summary_is_the_usual_indicator():
    assert privacy_summary(False) == "CONNECTION SECURE"
