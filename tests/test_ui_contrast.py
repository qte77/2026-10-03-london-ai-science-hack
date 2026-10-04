"""WCAG AA contrast check for ui/src/looks.css, so a theme token can't regress below
4.5:1 without failing CI. Parses the plain `--name: #hex;` declarations per
`[data-look="..."]` block (ignoring 8-digit "wash" colours, which are backgrounds, not
text) and checks every text-like token against every surface token within its own look.
No Node/browser needed: the WCAG relative-luminance formula is pure arithmetic.
"""

import re
from pathlib import Path

LOOKS_CSS = Path(__file__).resolve().parents[1] / "ui" / "src" / "looks.css"

TEXT_TOKENS = ("text", "text-2", "text-3", "muted", "faint", "crit", "warn", "ok", "ref", "link")
SURFACE_TOKENS = ("bg", "surface-0", "surface-1", "surface-2")

BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]+)\}")
TOKEN_RE = re.compile(r"--([\w-]+):\s*#([0-9a-fA-F]{6,8});")
LOOK_ATTR_RE = re.compile(r'\[data-look="(\w+)"\]')


def parse_looks(css_text: str) -> dict[str, dict[str, str]]:
    """Map look name -> {token name: "#rrggbb"}, skipping 8-digit wash colours."""
    looks: dict[str, dict[str, str]] = {}
    for selector, body in BLOCK_RE.findall(css_text):
        names = set(LOOK_ATTR_RE.findall(selector))
        if ":root" in selector:
            names.add("console")
        if not names:
            continue
        tokens = {name: f"#{hexval}" for name, hexval in TOKEN_RE.findall(body) if len(hexval) == 6}
        for name in names:
            looks.setdefault(name, {}).update(tokens)
    return looks


def _linear(channel: float) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    la, lb = relative_luminance(hex_a), relative_luminance(hex_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def test_looks_css_exists() -> None:
    assert LOOKS_CSS.is_file(), f"expected {LOOKS_CSS} to exist"


def test_every_look_defines_the_full_token_set() -> None:
    looks = parse_looks(LOOKS_CSS.read_text())
    assert set(looks) == {"console", "lab80", "polymer"}
    for name, tokens in looks.items():
        missing = [t for t in (*TEXT_TOKENS, *SURFACE_TOKENS) if t not in tokens]
        assert not missing, f"{name} is missing tokens: {missing}"


def test_text_tokens_meet_wcag_aa_against_every_surface() -> None:
    looks = parse_looks(LOOKS_CSS.read_text())
    failures = []
    for look_name, tokens in looks.items():
        for text_name in TEXT_TOKENS:
            for surface_name in SURFACE_TOKENS:
                ratio = contrast_ratio(tokens[text_name], tokens[surface_name])
                if ratio < 4.5:
                    failures.append(
                        f"{look_name}: {text_name} ({tokens[text_name]}) on "
                        f"{surface_name} ({tokens[surface_name]}) = {ratio:.2f}:1"
                    )
    assert not failures, "WCAG AA (4.5:1) failures:\n" + "\n".join(failures)
