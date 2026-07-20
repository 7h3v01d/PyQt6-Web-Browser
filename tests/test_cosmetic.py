"""
Element-hiding rules.

These selectors arrive from a file downloaded over the network, so the
injection-safety tests matter as much as the parsing ones: an unescaped
brace or quote would let a filter-list author — or anyone able to MITM the
download — style or script every page you visit.
"""

import json
import shutil
import subprocess

import pytest

from cosmetic import (
    HIDE_DECLARATION,
    STYLE_ELEMENT_ID,
    CosmeticFilterSet,
    build_injection_js,
    build_removal_js,
    is_safe_selector,
    parse_cosmetic_rule,
)


# ── selector validation ──────────────────────────────────────────────────

@pytest.mark.parametrize("selector", [
    ".ad-banner",
    "#sidebar-ad",
    "div.promo",
    "a[href^='http://ads']",
    ".sponsored, .promoted",
    "div > .ad",
    "div ~ .ad",
    "#ad_1234",
    ".a-very-long-but-legitimate-class-name-here",
])
def test_accepts_real_selectors(selector):
    assert is_safe_selector(selector)


@pytest.mark.parametrize("selector", [
    ".ad}body{display:none",          # escapes the rule
    ".ad{color:red}",
    "</style><script>alert(1)</script>",
    ".ad/*comment*/",
    "@import url(evil.css)",
    "@media print",
    ".ad\\",
    "",
    "   ",
    "x" * 500,                        # absurd length
])
def test_rejects_dangerous_selectors(selector):
    assert not is_safe_selector(selector)


# ── rule parsing ─────────────────────────────────────────────────────────

class TestParsing:

    def test_generic_rule(self):
        assert parse_cosmetic_rule("##.ad-banner") == ((), ".ad-banner", False)

    def test_domain_scoped_rule(self):
        assert parse_cosmetic_rule("example.com##.sponsored") == \
            (("example.com",), ".sponsored", False)

    def test_multiple_domains(self):
        domains, selector, exception = parse_cosmetic_rule("a.com,b.com##.promo")
        assert set(domains) == {"a.com", "b.com"}
        assert selector == ".promo"
        assert exception is False

    def test_exception_rule(self):
        assert parse_cosmetic_rule("example.com#@#.ad-banner") == \
            (("example.com",), ".ad-banner", True)

    def test_domains_lowercased(self):
        domains, _, _ = parse_cosmetic_rule("EXAMPLE.COM##.ad")
        assert domains == ("example.com",)

    @pytest.mark.parametrize("line", [
        "",
        "! a comment",
        "[Adblock Plus 2.0]",
        "||doubleclick.net^",              # network rule, not cosmetic
        "example.com#?#div:has(.ad)",      # procedural
        "example.com#$#body{}",            # style injection
        "##.ad}body{display:none",         # unsafe selector
    ])
    def test_rejects_non_cosmetic_or_unsafe(self, line):
        assert parse_cosmetic_rule(line) is None

    def test_negated_domain_becomes_generic_plus_exception(self):
        result = parse_cosmetic_rule("~safe.com##.ad")
        base, negations = result
        assert base == ((), ".ad", False)
        assert negations == (("safe.com", ".ad", True),)


# ── set construction and lookup ──────────────────────────────────────────

@pytest.fixture
def filters():
    return CosmeticFilterSet.from_lines([
        "##.generic-ad",
        "##.banner",
        "example.com##.site-specific",
        "example.com##.another",
        "other.com##.elsewhere",
        "example.com#@#.banner",           # exception on this host
        "! comment",
        "||network.rule^",
    ])


class TestLookup:

    def test_generic_applies_everywhere(self, filters):
        for host in ("example.com", "other.com", "unrelated.net"):
            assert ".generic-ad" in filters.selectors_for(host)

    def test_scoped_rules_only_on_their_host(self, filters):
        assert ".site-specific" in filters.selectors_for("example.com")
        assert ".site-specific" not in filters.selectors_for("other.com")

    def test_subdomains_inherit(self, filters):
        assert ".site-specific" in filters.selectors_for("www.example.com")
        assert ".site-specific" in filters.selectors_for("a.b.example.com")

    def test_exception_removes_a_generic_rule(self, filters):
        assert ".banner" not in filters.selectors_for("example.com")
        assert ".banner" in filters.selectors_for("other.com")

    def test_exception_applies_to_subdomains(self, filters):
        assert ".banner" not in filters.selectors_for("www.example.com")

    def test_unknown_host_gets_generic_only(self, filters):
        assert filters.selectors_for("nowhere.net") == {".generic-ad", ".banner"}

    @pytest.mark.parametrize("host", ["", None, "   ", "localhost"])
    def test_degenerate_hosts_are_safe(self, filters, host):
        assert isinstance(filters.selectors_for(host), set)

    def test_specific_only_excludes_generic(self, filters):
        assert filters.specific_selectors_for("example.com") == \
            {".site-specific", ".another"}


# ── CSS generation ───────────────────────────────────────────────────────

class TestCssGeneration:

    def test_css_hides_selectors(self, filters):
        css = filters.css_for("example.com")
        assert css.endswith(HIDE_DECLARATION)
        assert ".site-specific" in css

    def test_css_is_a_single_rule(self, filters):
        assert filters.css_for("example.com").count("{") == 1

    def test_empty_selectors_yield_empty_css(self):
        assert CosmeticFilterSet().css_for("example.com") == ""

    def test_css_is_deterministic(self, filters):
        assert filters.css_for("example.com") == filters.css_for("example.com")

    def test_unsafe_selectors_cannot_reach_css(self):
        """Defence in depth: even if one were stored, build_css drops it."""
        css = CosmeticFilterSet.build_css({".ad}body{x:y", ".ok"})
        assert ".ok" in css
        assert "body{x:y" not in css
        assert css.count("{") == 1        # exactly the one we opened


# ── injection safety ─────────────────────────────────────────────────────

class TestInjectionSafety:
    """
    The CSS comes from a downloaded list. Concatenating it into a JS string
    would hand script execution to whoever wrote — or intercepted — that list.
    """

    def test_css_is_json_encoded(self):
        js = build_injection_js('.ad{display:none}')
        assert json.dumps('.ad{display:none}') in js

    @pytest.mark.parametrize("css", [
        '.ad[title="x"]' + HIDE_DECLARATION,
        ".ad'x'" + HIDE_DECLARATION,
        '.ad\n.b' + HIDE_DECLARATION,
        '";alert(1);"' + HIDE_DECLARATION,
    ])
    def test_generated_js_is_always_valid_syntax(self, css, tmp_path):
        """The strongest form of the guarantee: node must accept it."""
        node = shutil.which("node")
        if not node:
            pytest.skip("node not available")
        path = tmp_path / "inject.js"
        path.write_text(build_injection_js(css), encoding="utf-8")
        result = subprocess.run([node, "--check", str(path)],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("payload", [
        '";alert(1);var x="',
        "';alert(1);//",
        ".ad\n</script><script>alert(1)</script>",
        ".ad\\u0022",
    ])
    def test_payloads_are_neutralised(self, payload):
        js = build_injection_js(payload)
        # The payload survives only inside the JSON literal, never as code.
        assert js.count(json.dumps(payload)) == 1

    def test_element_id_is_encoded_too(self):
        js = build_injection_js(".ad{}", element_id='x";alert(1);"')
        assert json.dumps('x";alert(1);"') in js

    def test_empty_css_produces_no_script(self):
        assert build_injection_js("") == ""

    def test_injection_replaces_previous_stylesheet(self):
        js = build_injection_js(".ad{}")
        assert "prev.remove()" in js.replace(" ", "")

    def test_removal_script_targets_the_right_element(self):
        assert json.dumps(STYLE_ELEMENT_ID) in build_removal_js()


# ── realistic volume ─────────────────────────────────────────────────────

def test_handles_a_realistic_rule_mix():
    lines = ["##.ad-%d" % i for i in range(500)]
    lines += ["site%d.com##.promo" % i for i in range(500)]
    filters = CosmeticFilterSet.from_lines(lines)
    assert len(filters.generic) == 500
    assert len(filters.specific) == 500
    css = filters.css_for("site1.com")
    assert css.count("{") == 1
    assert ".promo" in css
