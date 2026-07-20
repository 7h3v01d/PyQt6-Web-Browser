"""
Plugin integrity guard.

Plugins run as ordinary Python in the browser process, so the policy is
deny-first: only a file whose SHA-256 matches a previously approved entry
may be imported. These tests pin that policy down, including the two
weaknesses in the original loader — a CWD-relative search path, and no
integrity check at all.
"""

import json
import os

import pytest

from plugin_guard import (
    LOCK_FILENAME,
    LOCK_VERSION,
    PluginGuard,
    PluginStatus,
    hash_file,
    resolve_plugin_dir,
)

PLUGIN_SRC = "class Plugin:\n    name = 'Test'\n"
EVIL_SRC = "import os\nos.system('calc')\n"


@pytest.fixture
def plugin_dir(tmp_path):
    d = tmp_path / "plugins"
    d.mkdir()
    return d


@pytest.fixture
def a_plugin(plugin_dir):
    path = plugin_dir / "sample_plugin.py"
    path.write_text(PLUGIN_SRC, encoding="utf-8")
    return path


@pytest.fixture
def guard(plugin_dir):
    return PluginGuard(plugin_dir)


# ── hashing ──────────────────────────────────────────────────────────────

def test_hash_is_stable(a_plugin):
    assert hash_file(a_plugin) == hash_file(a_plugin)


def test_hash_changes_with_content(a_plugin):
    before = hash_file(a_plugin)
    a_plugin.write_text(PLUGIN_SRC + "# edited\n", encoding="utf-8")
    assert hash_file(a_plugin) != before


def test_hash_is_sha256_hex(a_plugin):
    digest = hash_file(a_plugin)
    assert len(digest) == 64
    int(digest, 16)


def test_hash_handles_large_file(plugin_dir):
    big = plugin_dir / "big_plugin.py"
    big.write_bytes(b"# padding\n" * 200_000)
    assert len(hash_file(big)) == 64


# ── deny-first policy ────────────────────────────────────────────────────

class TestDenyFirst:

    def test_unknown_plugin_is_new_and_must_not_load(self, guard, a_plugin):
        status = guard.status(a_plugin)
        assert status is PluginStatus.NEW
        assert status.may_load is False

    def test_approved_plugin_may_load(self, guard, a_plugin):
        guard.approve(a_plugin)
        assert guard.status(a_plugin) is PluginStatus.APPROVED
        assert guard.status(a_plugin).may_load is True

    def test_modified_plugin_is_denied(self, guard, a_plugin):
        guard.approve(a_plugin)
        a_plugin.write_text(EVIL_SRC, encoding="utf-8")
        status = guard.status(a_plugin)
        assert status is PluginStatus.CHANGED
        assert status.may_load is False

    def test_revoked_plugin_is_denied(self, guard, a_plugin):
        guard.revoke(a_plugin)
        status = guard.status(a_plugin)
        assert status is PluginStatus.REVOKED
        assert status.may_load is False

    def test_reverting_content_restores_approval(self, guard, a_plugin):
        """Approval pins content, not filename."""
        guard.approve(a_plugin)
        a_plugin.write_text(EVIL_SRC, encoding="utf-8")
        assert guard.status(a_plugin) is PluginStatus.CHANGED
        a_plugin.write_text(PLUGIN_SRC, encoding="utf-8")
        assert guard.status(a_plugin) is PluginStatus.APPROVED

    def test_swapping_a_file_under_a_trusted_name_is_denied(self, guard, plugin_dir):
        """The attack the hash exists to stop."""
        path = plugin_dir / "screenshot_plugin.py"
        path.write_text(PLUGIN_SRC, encoding="utf-8")
        guard.approve(path)
        path.write_text(EVIL_SRC, encoding="utf-8")
        assert guard.status(path).may_load is False

    @pytest.mark.parametrize("status,allowed", [
        (PluginStatus.APPROVED, True),
        (PluginStatus.NEW, False),
        (PluginStatus.CHANGED, False),
        (PluginStatus.REVOKED, False),
    ])
    def test_only_approved_may_load(self, status, allowed):
        assert status.may_load is allowed


# ── lock file ────────────────────────────────────────────────────────────

class TestLockFile:

    def test_approval_persists_across_instances(self, plugin_dir, a_plugin):
        PluginGuard(plugin_dir).approve(a_plugin)
        assert PluginGuard(plugin_dir).status(a_plugin) is PluginStatus.APPROVED

    def test_lock_is_written_beside_the_app_not_inside_plugins(self, plugin_dir, a_plugin):
        guard = PluginGuard(plugin_dir)
        guard.approve(a_plugin)
        assert guard.lock_path.name == LOCK_FILENAME
        assert not (plugin_dir / LOCK_FILENAME).exists()
        assert guard.lock_path.exists()

    def test_lock_contents_are_readable_json(self, plugin_dir, a_plugin):
        guard = PluginGuard(plugin_dir)
        guard.approve(a_plugin)
        raw = json.loads(guard.lock_path.read_text(encoding="utf-8"))
        assert raw["version"] == LOCK_VERSION
        assert raw["plugins"]["sample_plugin.py"]["approved"] is True
        assert len(raw["plugins"]["sample_plugin.py"]["sha256"]) == 64

    def test_missing_lock_trusts_nothing(self, plugin_dir, a_plugin):
        assert PluginGuard(plugin_dir).status(a_plugin) is PluginStatus.NEW

    @pytest.mark.parametrize("content", [
        "not json at all",
        "[]",
        '{"version": 999, "plugins": {}}',
        '{"version": 1}',
        '{"version": 1, "plugins": "nope"}',
        "",
    ])
    def test_corrupt_lock_fails_closed(self, tmp_path, plugin_dir, a_plugin, content):
        """A damaged lock must deny everything, never approve everything."""
        lock = tmp_path / LOCK_FILENAME
        lock.write_text(content, encoding="utf-8")
        guard = PluginGuard(plugin_dir, lock_path=lock)
        assert guard.status(a_plugin) is PluginStatus.NEW

    def test_lock_entries_missing_hash_are_dropped(self, tmp_path, plugin_dir, a_plugin):
        lock = tmp_path / LOCK_FILENAME
        lock.write_text(json.dumps({
            "version": LOCK_VERSION,
            "plugins": {"sample_plugin.py": {"approved": True}},
        }), encoding="utf-8")
        guard = PluginGuard(plugin_dir, lock_path=lock)
        assert guard.status(a_plugin) is PluginStatus.NEW

    def test_save_is_atomic(self, plugin_dir, a_plugin):
        guard = PluginGuard(plugin_dir)
        guard.approve(a_plugin)
        leftovers = [f for f in os.listdir(guard.lock_path.parent) if f.endswith(".tmp")]
        assert leftovers == []


# ── scanning ─────────────────────────────────────────────────────────────

class TestScan:

    def test_scan_classifies_each_file(self, plugin_dir):
        approved = plugin_dir / "a_plugin.py"
        approved.write_text(PLUGIN_SRC, encoding="utf-8")
        fresh = plugin_dir / "b_plugin.py"
        fresh.write_text(PLUGIN_SRC, encoding="utf-8")

        guard = PluginGuard(plugin_dir)
        guard.approve(approved)

        result = dict((p.name, s) for p, s in guard.scan())
        assert result["a_plugin.py"] is PluginStatus.APPROVED
        assert result["b_plugin.py"] is PluginStatus.NEW

    def test_scan_is_sorted(self, plugin_dir):
        for name in ("z_plugin.py", "a_plugin.py", "m_plugin.py"):
            (plugin_dir / name).write_text(PLUGIN_SRC, encoding="utf-8")
        names = [p.name for p, _ in PluginGuard(plugin_dir).scan()]
        assert names == sorted(names)

    def test_scan_skips_dunder_and_hidden(self, plugin_dir):
        (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
        (plugin_dir / "_private.py").write_text("", encoding="utf-8")
        (plugin_dir / ".hidden.py").write_text("", encoding="utf-8")
        (plugin_dir / "real_plugin.py").write_text(PLUGIN_SRC, encoding="utf-8")
        names = [p.name for p, _ in PluginGuard(plugin_dir).scan()]
        assert names == ["real_plugin.py"]

    def test_scan_ignores_non_python(self, plugin_dir):
        (plugin_dir / "notes.txt").write_text("hello", encoding="utf-8")
        (plugin_dir / "real_plugin.py").write_text(PLUGIN_SRC, encoding="utf-8")
        assert len(PluginGuard(plugin_dir).scan()) == 1

    def test_scan_of_missing_directory_is_empty(self, tmp_path):
        assert PluginGuard(tmp_path / "nope").scan() == []


# ── housekeeping ─────────────────────────────────────────────────────────

class TestPruning:

    def test_stale_entries_detected(self, plugin_dir, a_plugin):
        guard = PluginGuard(plugin_dir)
        guard.approve(a_plugin)
        a_plugin.unlink()
        assert guard.stale_entries() == ["sample_plugin.py"]

    def test_prune_removes_them(self, plugin_dir, a_plugin):
        guard = PluginGuard(plugin_dir)
        guard.approve(a_plugin)
        a_plugin.unlink()
        assert guard.prune() == ["sample_plugin.py"]
        assert guard.entries == {}

    def test_deleted_then_restored_plugin_needs_reapproval(self, plugin_dir, a_plugin):
        """Otherwise a name could be reclaimed by different content."""
        guard = PluginGuard(plugin_dir)
        guard.approve(a_plugin)
        a_plugin.unlink()
        guard.prune()
        a_plugin.write_text(EVIL_SRC, encoding="utf-8")
        assert guard.status(a_plugin) is PluginStatus.NEW

    def test_forget_drops_a_single_entry(self, plugin_dir, a_plugin):
        guard = PluginGuard(plugin_dir)
        guard.approve(a_plugin)
        guard.forget("sample_plugin.py")
        assert guard.status(a_plugin) is PluginStatus.NEW


# ── path resolution regression ───────────────────────────────────────────

class TestPluginDirResolution:
    """
    Shipped bug: the loader used Path("plugins"), which resolves against the
    current working directory. Starting Blackline from another folder would
    search a different plugins/ tree — an easy way to get arbitrary code
    into the process.
    """

    def test_resolves_relative_to_the_module(self, tmp_path):
        app = tmp_path / "app" / "browser.py"
        app.parent.mkdir(parents=True)
        app.write_text("", encoding="utf-8")
        assert resolve_plugin_dir(app) == tmp_path / "app" / "plugins"

    def test_is_independent_of_cwd(self, tmp_path, monkeypatch):
        app = tmp_path / "app" / "browser.py"
        app.parent.mkdir(parents=True)
        app.write_text("", encoding="utf-8")
        expected = resolve_plugin_dir(app)

        elsewhere = tmp_path / "elsewhere"
        (elsewhere / "plugins").mkdir(parents=True)
        monkeypatch.chdir(elsewhere)

        assert resolve_plugin_dir(app) == expected
        assert resolve_plugin_dir(app) != (elsewhere / "plugins")

    def test_result_is_absolute(self, tmp_path):
        app = tmp_path / "browser.py"
        app.write_text("", encoding="utf-8")
        assert resolve_plugin_dir(app).is_absolute()
