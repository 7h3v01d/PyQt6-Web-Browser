"""
cosmetic.py  —  element-hiding rules, the half of EasyList we were throwing away.

A request interceptor can stop an ad loading but cannot remove the space it
occupied, which is why blocked ads leave holes. EasyList carries ~23,700
element-hiding rules for exactly this; none of them were being used.

Supported syntax:
    ##.ad-banner                    generic, applies everywhere
    example.com##.sponsored         scoped to a domain (and its subdomains)
    a.com,b.com##.promo             several domains
    ~sub.example.com##.x            negated domain, treated as an exception
    example.com#@#.ad-banner        exception: do not hide here

Deliberately unsupported: procedural cosmetics (#?#, #$#) using :has(),
:matches-css() and friends. Those need a filtering engine at DOM level;
faking them with plain CSS produces wrong results silently.

Security note: these selectors come from a file downloaded over the
network. Every one is validated before it can reach a stylesheet — an
unchecked "}" would let a list author break out of the rule and style, or
hide, anything on the page.
"""

import json
import re

# Selectors must look like selectors. Anything containing CSS or HTML
# structural characters is dropped rather than escaped: a rule we cannot
# parse confidently is not a rule worth applying.
_FORBIDDEN = ("{", "}", "</", "<script", "*/", "/*", "\\", "@import", "@media")

# "/" is allowed because attribute selectors carry URLs, e.g.
# a[href^='http://ads']. The _FORBIDDEN check above still rejects the
# comment sequences "/*" and "*/" before this pattern is consulted.
_SELECTOR_RE = re.compile(r"^[A-Za-z0-9\s\.\#\[\]\(\)\=\"'\-_:,>+~^$|*/]+$")

MAX_SELECTOR_LENGTH = 300
HIDE_DECLARATION = "{display:none!important}"

# Splitting on the separators, longest first so #@# is not seen as #.
_SEPARATORS = ("#@#", "#?#", "#$#", "##")


def is_safe_selector(selector: str) -> bool:
    """Reject anything that could escape the CSS rule it will be placed in."""
    if not selector:
        return False
    s = selector.strip()
    if not s or len(s) > MAX_SELECTOR_LENGTH:
        return False
    lowered = s.lower()
    if any(bad in lowered for bad in _FORBIDDEN):
        return False
    return bool(_SELECTOR_RE.match(s))


def parse_cosmetic_rule(line: str):
    """
    Parse one element-hiding rule.

    Returns (domains, selector, is_exception) or None. `domains` is a tuple,
    empty for a generic rule. Negated domains (~x.com) are returned as
    exceptions for that domain.
    """
    if not line:
        return None
    line = line.strip()
    if not line or line.startswith(("!", "[")):
        return None

    separator = None
    for sep in _SEPARATORS:
        index = line.find(sep)
        if index != -1:
            # #?# and #$# are procedural — not representable as plain CSS.
            if sep in ("#?#", "#$#"):
                return None
            separator = (sep, index)
            break
    if separator is None:
        return None

    sep, index = separator
    domain_part = line[:index]
    selector = line[index + len(sep):].strip()

    if not is_safe_selector(selector):
        return None

    is_exception = sep == "#@#"

    if not domain_part:
        return ((), selector, is_exception)

    domains, negated = [], []
    for raw in domain_part.split(","):
        raw = raw.strip().lower()
        if not raw:
            continue
        if raw.startswith("~"):
            negated.append(raw[1:])
        else:
            domains.append(raw)

    if negated and not domains:
        # "~a.com##.x" hides everywhere except a.com. Represent as a generic
        # rule plus an exception on the negated domain.
        return ((), selector, False), tuple((d, selector, True) for d in negated)

    return (tuple(domains), selector, is_exception)


class CosmeticFilterSet:
    """Element-hiding rules, indexed for per-host lookup."""

    __slots__ = ("generic", "specific", "exceptions", "skipped")

    def __init__(self):
        self.generic = set()
        self.specific = {}        # host -> set of selectors
        self.exceptions = {}      # host -> set of selectors
        self.skipped = 0

    # ── building ─────────────────────────────────────────────────────────

    def _add(self, domains, selector, is_exception):
        if not domains:
            if is_exception:
                return
            self.generic.add(selector)
            return
        target = self.exceptions if is_exception else self.specific
        for domain in domains:
            target.setdefault(domain, set()).add(selector)

    @classmethod
    def from_lines(cls, lines) -> "CosmeticFilterSet":
        out = cls()
        for line in lines:
            parsed = parse_cosmetic_rule(line)
            if parsed is None:
                out.skipped += 1
                continue
            # A negated rule expands to a generic rule plus exceptions.
            if isinstance(parsed[0], tuple) and len(parsed) == 2 \
                    and isinstance(parsed[1], tuple) and parsed[1] \
                    and isinstance(parsed[1][0], tuple):
                base, negations = parsed
                out._add(*base)
                for domain, selector, _ in negations:
                    out.exceptions.setdefault(domain, set()).add(selector)
                continue
            out._add(*parsed)
        return out

    @classmethod
    def from_file(cls, path, encoding="utf-8") -> "CosmeticFilterSet":
        with open(path, "r", encoding=encoding, errors="ignore") as fh:
            return cls.from_lines(fh)

    # ── lookup ───────────────────────────────────────────────────────────

    @staticmethod
    def _host_chain(host):
        """example.com and its parents, so a rule for example.com covers www."""
        host = (host or "").strip().lower().rstrip(".")
        if not host:
            return []
        parts = host.split(".")
        return [".".join(parts[i:]) for i in range(len(parts) - 1)]

    def selectors_for(self, host) -> set:
        """Every selector that should be hidden on this host."""
        chain = self._host_chain(host)
        selectors = set(self.generic)
        for domain in chain:
            selectors |= self.specific.get(domain, set())
        for domain in chain:
            selectors -= self.exceptions.get(domain, set())
        return selectors

    def specific_selectors_for(self, host) -> set:
        """Host-scoped selectors only, minus exceptions."""
        chain = self._host_chain(host)
        selectors = set()
        for domain in chain:
            selectors |= self.specific.get(domain, set())
        for domain in chain:
            selectors -= self.exceptions.get(domain, set())
        return selectors

    # ── output ───────────────────────────────────────────────────────────

    @staticmethod
    def build_css(selectors) -> str:
        """One rule joining every selector. Empty input yields empty output."""
        clean = sorted(s for s in selectors if is_safe_selector(s))
        if not clean:
            return ""
        return ",".join(clean) + HIDE_DECLARATION

    def generic_css(self) -> str:
        return self.build_css(self.generic)

    def css_for(self, host) -> str:
        return self.build_css(self.selectors_for(host))

    def specific_css_for(self, host) -> str:
        return self.build_css(self.specific_selectors_for(host))

    def __len__(self):
        return (len(self.generic)
                + sum(len(v) for v in self.specific.values()))


STYLE_ELEMENT_ID = "blackline-cosmetic"


def build_injection_js(css: str, element_id: str = STYLE_ELEMENT_ID) -> str:
    """
    JavaScript that installs `css` as a stylesheet.

    The CSS is embedded with json.dumps rather than string concatenation.
    These rules arrive from a downloaded filter list, so a quote or a
    newline spliced straight into a JS literal would be a script injection
    with a remote author — the list maintainer, or anyone who can MITM the
    download.
    """
    if not css:
        return ""
    payload = json.dumps(css)
    ident = json.dumps(str(element_id))
    return (
        "(function(){"
        f"var id={ident};"
        "var prev=document.getElementById(id);"
        "if(prev){prev.remove();}"
        "var s=document.createElement('style');"
        "s.id=id;s.type='text/css';"
        f"s.textContent={payload};"
        "(document.head||document.documentElement).appendChild(s);"
        "})();"
    )


def build_removal_js(element_id: str = STYLE_ELEMENT_ID) -> str:
    """JavaScript that removes a previously injected stylesheet."""
    ident = json.dumps(str(element_id))
    return (
        "(function(){"
        f"var e=document.getElementById({ident});"
        "if(e){e.remove();}"
        "})();"
    )
