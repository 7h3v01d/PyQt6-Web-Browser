"""
storage.py  —  durable, app-anchored JSON persistence.

Two problems this fixes.

Location: history.json, settings.json, tabs.json and console_history.json
were all opened by bare filename, so they resolved against the current
working directory. Launch Blackline from a different folder and it silently
starts a fresh, empty history — the same defect that left plugins/ pointing
at a directory that did not exist.

Durability: each file was written with open(..., "w") followed by
json.dump(). A crash, a full disk, or a power loss part-way through leaves
a truncated file, and the loader then treats it as corrupt and discards it.
save_history() swallowed the failure with a bare `except: pass`, so the
loss was invisible until the next launch.

Writes here go to a temp file, are flushed and fsynced, then moved into
place with os.replace() — atomic on both Windows and POSIX. The previous
contents are kept as <name>.bak.
"""

import json
import os
import tempfile
from pathlib import Path

BACKUP_SUFFIX = ".bak"

# Anchored on the package root (the parent of src/), which is where these
# files already live for anyone launching via run.bat. Nothing moves; it
# just stops depending on where the process happened to start.
APP_ROOT = Path(__file__).resolve().parent.parent


def data_path(name) -> Path:
    """Absolute path for an application data file."""
    return APP_ROOT / str(name)


def read_json(path, default=None):
    """
    Load JSON, falling back to `default` for anything unreadable.

    Never raises: a corrupt settings file must not stop the browser from
    starting. Callers get the default and carry on.
    """
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return default


def read_json_with_recovery(path, default=None):
    """
    As read_json, but falls back to the .bak copy before giving up.

    Returns (data, recovered) so the caller can tell the user their most
    recent session was rolled back rather than silently losing it.
    """
    path = Path(path)
    sentinel = object()
    primary = read_json(path, sentinel)
    if primary is not sentinel:
        return primary, False

    backup = read_json(Path(str(path) + BACKUP_SUFFIX), sentinel)
    if backup is not sentinel:
        return backup, True

    return default, False


def write_json(path, data, keep_backup: bool = True) -> bool:
    """
    Write JSON atomically. Returns True on success, False on failure.

    A False return is the caller's cue to surface something — the previous
    implementation discarded the exception entirely.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    tmp_name = None
    try:
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())

        if keep_backup and path.exists():
            try:
                os.replace(path, str(path) + BACKUP_SUFFIX)
            except OSError:
                pass                      # a missing backup is not fatal

        os.replace(tmp_name, path)
        tmp_name = None
        return True
    except (OSError, TypeError, ValueError):
        return False
    finally:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def migrate_legacy_file(name, cwd=None) -> bool:
    """
    Move a data file left in the working directory into the app root.

    Only acts when the legacy file exists and the anchored one does not, so
    it can never clobber current data. Returns True if a file was moved.
    """
    source = Path(cwd or os.getcwd()) / str(name)
    target = data_path(name)
    try:
        if source.resolve() == target.resolve():
            return False
    except OSError:
        return False
    if not source.is_file() or target.exists():
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        return True
    except OSError:
        return False
