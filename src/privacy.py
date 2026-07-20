"""
privacy.py  —  what may be recorded, and what must not.

Private browsing fails quietly: the window looks right, but a URL ends up
in history.json or tabs.json and the guarantee is gone with no visible
symptom. The decisions are therefore pure functions here rather than
inline conditions in browser.py, so they can be tested exhaustively.

Rule: a private tab writes nothing to disk. Not history, not the session,
not cookies (its profile is off-the-record), not the notes sidebar's
current-domain state.
"""

PRIVATE_PREFIX = "◈ "

# Schemes that are internal to the browser and never worth recording.
_INTERNAL_SCHEMES = ("file://", "about:", "chrome://", "data:", "blob:", "javascript:")


def is_internal_url(url) -> bool:
    """True for the new tab page and other browser-internal targets."""
    if not url:
        return True
    text = str(url).strip().lower()
    if not text:                      # whitespace-only counts as no URL
        return True
    return text.startswith(_INTERNAL_SCHEMES)


def should_record_history(url, private: bool) -> bool:
    """
    History is written for ordinary tabs visiting real pages only.

    Private tabs never contribute, regardless of URL.
    """
    if private:
        return False
    return not is_internal_url(url)


def should_persist_tab(url, private: bool) -> bool:
    """
    Session restore must not resurrect a private tab on next launch —
    that would leak the browsing across restarts, which is precisely
    what private mode promises not to do.
    """
    if private:
        return False
    return not is_internal_url(url)


def should_offer_password_save(private: bool) -> bool:
    """Captured credentials are not written to the vault from a private tab."""
    return not private


def tab_label(label: str, private: bool, limit: int = 30) -> str:
    """
    Decorate a tab title so private tabs are unmistakable.

    Truncation happens after the marker, so a long title can never push the
    marker out of view.
    """
    text = (label or "New Tab").strip() or "New Tab"
    if not private:
        return text[:limit]
    room = max(1, limit - len(PRIVATE_PREFIX))
    return PRIVATE_PREFIX + text[:room]


def is_private_label(label: str) -> bool:
    return bool(label) and label.startswith(PRIVATE_PREFIX)


def strip_private_marker(label: str) -> str:
    return label[len(PRIVATE_PREFIX):] if is_private_label(label) else label


def privacy_summary(private: bool) -> str:
    """Status-bar text describing what the current mode does and does not keep."""
    if private:
        return ("PRIVATE — no history, no session restore, no saved passwords. "
                "Cookies are discarded when the last private tab closes.")
    return "CONNECTION SECURE"
