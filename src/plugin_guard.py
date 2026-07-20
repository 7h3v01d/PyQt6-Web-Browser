"""
plugin_guard.py  —  deny-first integrity gate for the plugin directory.

Plugins are ordinary Python modules imported into the browser process with
full privileges. Before this module existed, any .py file dropped into a
`plugins/` folder *relative to the current working directory* was imported
and executed with no manifest, no signature, and no prompt — so launching
Blackline from a different directory could load an entirely different,
attacker-supplied plugin tree.

The model here is the same one used in UCI Protocol: hash-pin on first
sight (TOFU), then deny anything whose hash changes until a human approves
it. No Qt dependency, so the policy can be tested directly.

Approval state lives in plugins.lock beside the application, not the CWD:

    {
      "version": 1,
      "plugins": { "screenshot_plugin.py": {"sha256": "...", "approved": true} }
    }
"""

import hashlib
import json
import os
import tempfile
from enum import Enum
from pathlib import Path

LOCK_FILENAME = "plugins.lock"
LOCK_VERSION = 1
CHUNK = 65536


class PluginStatus(Enum):
    """Outcome of checking one plugin file against the lock."""

    APPROVED = "approved"        # known hash, previously approved
    NEW = "new"                  # never seen before
    CHANGED = "changed"          # known name, different hash
    REVOKED = "revoked"          # known hash, explicitly denied

    @property
    def may_load(self) -> bool:
        """Deny-first: only an explicit prior approval permits execution."""
        return self is PluginStatus.APPROVED


def hash_file(path) -> str:
    """SHA-256 of a file, read in chunks so large plugins do not blow memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


class PluginGuard:
    """
    Tracks which plugin files have been approved, by content hash.

    Nothing here imports or executes a plugin — it only answers "may this
    file be loaded?" so the decision is auditable and testable in isolation.
    """

    def __init__(self, plugin_dir, lock_path=None):
        self.plugin_dir = Path(plugin_dir)
        self.lock_path = Path(lock_path) if lock_path else self.plugin_dir.parent / LOCK_FILENAME
        self.entries = {}
        self.load()

    # ── lock file ────────────────────────────────────────────────────────

    def load(self):
        """Read the lock file. A missing or unreadable lock means trust nothing."""
        self.entries = {}
        if not self.lock_path.exists():
            return
        try:
            with open(self.lock_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict) or raw.get("version") != LOCK_VERSION:
            return
        plugins = raw.get("plugins")
        if not isinstance(plugins, dict):
            return
        for name, meta in plugins.items():
            if isinstance(meta, dict) and isinstance(meta.get("sha256"), str):
                self.entries[name] = {
                    "sha256": meta["sha256"],
                    "approved": bool(meta.get("approved", False)),
                }

    def save(self):
        """Persist the lock atomically — a truncated lock would deny everything."""
        payload = {"version": LOCK_VERSION, "plugins": self.entries}
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.lock_path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.lock_path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # ── policy ───────────────────────────────────────────────────────────

    def status(self, path) -> PluginStatus:
        """Classify one plugin file against the lock."""
        path = Path(path)
        name = path.name
        digest = hash_file(path)
        entry = self.entries.get(name)

        if entry is None:
            return PluginStatus.NEW
        if entry["sha256"] != digest:
            return PluginStatus.CHANGED
        return PluginStatus.APPROVED if entry["approved"] else PluginStatus.REVOKED

    def scan(self):
        """
        Classify every .py file in the plugin directory.

        Returns a list of (path, status) sorted by filename so the approval
        prompt order is deterministic. Dotfiles and __init__.py are ignored.
        """
        if not self.plugin_dir.is_dir():
            return []
        found = []
        for path in sorted(self.plugin_dir.glob("*.py")):
            if path.name.startswith((".", "_")):
                continue
            try:
                found.append((path, self.status(path)))
            except OSError:
                continue
        return found

    def stale_entries(self):
        """Names in the lock whose file no longer exists."""
        present = {p.name for p in self.plugin_dir.glob("*.py")} \
            if self.plugin_dir.is_dir() else set()
        return sorted(set(self.entries) - present)

    # ── decisions ────────────────────────────────────────────────────────

    def approve(self, path, save: bool = True):
        """Pin the current contents of this file as approved."""
        path = Path(path)
        self.entries[path.name] = {"sha256": hash_file(path), "approved": True}
        if save:
            self.save()

    def revoke(self, path, save: bool = True):
        """Pin the current contents as explicitly denied."""
        path = Path(path)
        self.entries[path.name] = {"sha256": hash_file(path), "approved": False}
        if save:
            self.save()

    def forget(self, name, save: bool = True):
        """Drop an entry entirely — the file becomes NEW again if it returns."""
        if self.entries.pop(name, None) is not None and save:
            self.save()

    def prune(self, save: bool = True):
        """Remove lock entries for files that no longer exist."""
        removed = self.stale_entries()
        for name in removed:
            self.entries.pop(name, None)
        if removed and save:
            self.save()
        return removed


def resolve_plugin_dir(app_file) -> Path:
    """
    Locate plugins/ relative to the application, never the CWD.

    The old loader used Path("plugins"), so the directory searched depended
    on where the process happened to be started from.
    """
    return Path(app_file).resolve().parent / "plugins"
