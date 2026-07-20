"""
Durable JSON storage.

Covers the two shipped defects: data files resolved against the current
working directory, and non-atomic writes whose failures were swallowed by
a bare `except: pass`.
"""

import json
import os
from pathlib import Path

import pytest

import storage
from storage import (
    APP_ROOT,
    BACKUP_SUFFIX,
    data_path,
    migrate_legacy_file,
    read_json,
    read_json_with_recovery,
    write_json,
)

SAMPLE = {"homepage": "newtab", "dark_mode": True, "tabs": ["https://example.com"]}


# ── path anchoring ───────────────────────────────────────────────────────

class TestPathAnchoring:
    """
    Shipped bug: open("history.json") resolves against the CWD, so starting
    Blackline from another folder began with an empty history and no
    settings — the same class of defect that left plugins/ unreachable.
    """

    def test_data_path_is_absolute(self):
        assert data_path("history.json").is_absolute()

    def test_data_path_is_independent_of_cwd(self, tmp_path, monkeypatch):
        before = data_path("history.json")
        monkeypatch.chdir(tmp_path)
        assert data_path("history.json") == before

    def test_anchored_at_app_root_not_src(self):
        assert data_path("history.json").parent == APP_ROOT
        assert APP_ROOT.name != "src"

    def test_all_data_files_share_a_directory(self):
        parents = {data_path(n).parent for n in
                   ("history.json", "tabs.json", "settings.json", "notes.json")}
        assert len(parents) == 1


# ── round trip ───────────────────────────────────────────────────────────

def test_write_then_read(tmp_path):
    p = tmp_path / "settings.json"
    assert write_json(p, SAMPLE) is True
    assert read_json(p) == SAMPLE


def test_write_creates_missing_directories(tmp_path):
    p = tmp_path / "nested" / "deeper" / "settings.json"
    assert write_json(p, SAMPLE) is True
    assert read_json(p) == SAMPLE


def test_unicode_survives_round_trip(tmp_path):
    p = tmp_path / "notes.json"
    data = {"global": "café — 日本語 — ünïcode"}
    write_json(p, data)
    assert read_json(p) == data


def test_write_reports_failure_rather_than_swallowing(tmp_path):
    """A set is not JSON-serialisable; the caller must be told."""
    assert write_json(tmp_path / "bad.json", {"x": {1, 2, 3}}) is False


def test_failed_write_leaves_no_temp_files(tmp_path):
    write_json(tmp_path / "bad.json", {"x": {1, 2, 3}})
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []


def test_successful_write_leaves_no_temp_files(tmp_path):
    write_json(tmp_path / "ok.json", SAMPLE)
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []


# ── reading tolerates damage ─────────────────────────────────────────────

@pytest.mark.parametrize("content", ["", "   ", "{ broken", "not json", "\x00\x01"])
def test_corrupt_file_returns_default(tmp_path, content):
    p = tmp_path / "settings.json"
    p.write_text(content, encoding="utf-8", errors="ignore")
    assert read_json(p, default={"fallback": True}) == {"fallback": True}


def test_missing_file_returns_default(tmp_path):
    assert read_json(tmp_path / "nope.json", default=[]) == []


def test_read_never_raises_on_a_directory(tmp_path):
    d = tmp_path / "adir.json"
    d.mkdir()
    assert read_json(d, default="safe") == "safe"


# ── backup and recovery ──────────────────────────────────────────────────

class TestBackupRecovery:

    def test_backup_written_on_overwrite(self, tmp_path):
        p = tmp_path / "history.json"
        write_json(p, ["first"])
        write_json(p, ["second"])
        assert read_json(Path(str(p) + BACKUP_SUFFIX)) == ["first"]
        assert read_json(p) == ["second"]

    def test_no_backup_on_first_write(self, tmp_path):
        p = tmp_path / "history.json"
        write_json(p, ["first"])
        assert not Path(str(p) + BACKUP_SUFFIX).exists()

    def test_recovery_uses_backup_when_primary_is_corrupt(self, tmp_path):
        p = tmp_path / "history.json"
        write_json(p, ["good"])
        write_json(p, ["newer"])
        p.write_text("{ truncated", encoding="utf-8")

        data, recovered = read_json_with_recovery(p, default=[])
        assert data == ["good"]
        assert recovered is True

    def test_recovery_flag_false_when_primary_is_fine(self, tmp_path):
        p = tmp_path / "history.json"
        write_json(p, ["good"])
        data, recovered = read_json_with_recovery(p, default=[])
        assert data == ["good"]
        assert recovered is False

    def test_default_when_both_are_gone(self, tmp_path):
        data, recovered = read_json_with_recovery(tmp_path / "nope.json", default=[])
        assert data == []
        assert recovered is False

    def test_falsey_stored_value_is_not_mistaken_for_missing(self, tmp_path):
        """An empty list is real data, not a failed read."""
        p = tmp_path / "tabs.json"
        write_json(p, [])
        data, recovered = read_json_with_recovery(p, default=["fallback"])
        assert data == []
        assert recovered is False

    def test_keep_backup_can_be_disabled(self, tmp_path):
        p = tmp_path / "x.json"
        write_json(p, ["a"])
        write_json(p, ["b"], keep_backup=False)
        assert not Path(str(p) + BACKUP_SUFFIX).exists()


# ── atomicity ────────────────────────────────────────────────────────────

class TestAtomicity:

    def test_original_survives_a_failed_write(self, tmp_path):
        """
        The point of the temp-file dance: a write that dies part-way must
        not truncate what was already there.
        """
        p = tmp_path / "history.json"
        write_json(p, ["original"])
        assert write_json(p, {"bad": {1, 2}}) is False
        assert read_json(p) == ["original"]

    def test_interrupted_write_leaves_file_intact(self, tmp_path, monkeypatch):
        p = tmp_path / "history.json"
        write_json(p, ["original"])

        real_replace = os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 1:          # fail the backup rotation
                raise OSError("simulated")
            return real_replace(src, dst)

        monkeypatch.setattr(storage.os, "replace", flaky)
        write_json(p, ["second"])
        assert read_json(p) in (["original"], ["second"])
        assert read_json(p) is not None


# ── migration ────────────────────────────────────────────────────────────

class TestLegacyMigration:

    def test_moves_a_file_from_the_old_cwd(self, tmp_path, monkeypatch):
        target_root = tmp_path / "approot"
        target_root.mkdir()
        monkeypatch.setattr(storage, "APP_ROOT", target_root)

        legacy_dir = tmp_path / "oldcwd"
        legacy_dir.mkdir()
        (legacy_dir / "history.json").write_text('["old"]', encoding="utf-8")

        assert migrate_legacy_file("history.json", cwd=legacy_dir) is True
        assert read_json(target_root / "history.json") == ["old"]
        assert not (legacy_dir / "history.json").exists()

    def test_never_clobbers_existing_data(self, tmp_path, monkeypatch):
        target_root = tmp_path / "approot"
        target_root.mkdir()
        monkeypatch.setattr(storage, "APP_ROOT", target_root)
        (target_root / "history.json").write_text('["current"]', encoding="utf-8")

        legacy_dir = tmp_path / "oldcwd"
        legacy_dir.mkdir()
        (legacy_dir / "history.json").write_text('["stale"]', encoding="utf-8")

        assert migrate_legacy_file("history.json", cwd=legacy_dir) is False
        assert read_json(target_root / "history.json") == ["current"]

    def test_noop_when_nothing_to_move(self, tmp_path):
        assert migrate_legacy_file("history.json", cwd=tmp_path) is False

    def test_noop_when_cwd_is_the_app_root(self, monkeypatch, tmp_path):
        monkeypatch.setattr(storage, "APP_ROOT", tmp_path)
        (tmp_path / "history.json").write_text("[]", encoding="utf-8")
        assert migrate_legacy_file("history.json", cwd=tmp_path) is False
        assert (tmp_path / "history.json").exists()
