"""Landing page: one source of content, rendered as markdown (agents) and HTML (people)."""

import html
import json

TAGLINE = (
    "Science agents doing Polaron's battery-electrode QC, and the evals that tell you when "
    "to trust them: correctness, reward hacking, calibration, falsification."
)
REPO_URL = "https://github.com/qte77/2026-10-03-london-ai-science-hack"

# (path, label) pairs shown to both audiences.
AGENT_LINKS: tuple[tuple[str, str], ...] = (
    ("/llms.txt", "llms.txt: project summary for agents"),
    ("/.well-known/agent-card.json", "Agent card (A2A discovery)"),
    ("/openapi.json", "OpenAPI schema (REST API)"),
    ("/v1/health", "Health check"),
)

STATUS = "Status: the agent-native surface is live; the QC tools and evals are in progress."

WHEN_TO_USE: tuple[str, ...] = (
    "To check whether a science agent's accept / investigate / reject verdict on a "
    "battery-electrode micrograph batch is correct against known ground truth.",
    "To detect reward hacking: an agent using shortcuts such as filenames, detector-channel "
    "metadata or leaked labels instead of the microstructure.",
    "To measure calibration: whether an agent's stated confidence matches how often it is right.",
)

WHEN_NOT_TO_USE: tuple[str, ...] = (
    "Not a production QC system or a certified materials test; it is a hackathon research "
    "prototype (London AI x Science Hackathon, October 2026).",
    "Not a source of Polaron's data; their micrographs are not redistributed here.",
)

# Colour values are the qte77 EyeRest design tokens (DESIGN.md); the CSS is written here.
CSS = """
:root { color-scheme: light dark;
  --bg:#ece8d8; --surface:#e2dec8; --border:#c8c4b0; --text:#2c2818;
  --text-muted:#686040; --primary:#7a6010; --link:#755c0f; }
@media (prefers-color-scheme: dark) { :root {
  --bg:#1c1a14; --surface:#242018; --border:#383428; --text:#d8d0b8;
  --text-muted:#a89878; --primary:#c8a858; --link:#c8a858; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text);
  font:16px/1.6 Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; }
main { max-width:768px; margin:0 auto; padding:64px 24px; }
.eyebrow { font-size:12px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase;
  color:var(--text-muted); margin:0 0 8px; }
h1 { font-size:40px; font-weight:600; letter-spacing:-0.01em; line-height:1.2; margin:0; }
.rule { width:48px; height:3px; border-radius:9999px; background:var(--primary);
  margin:16px 0 24px; }
h2 { font-size:20px; font-weight:600; margin:48px 0 12px; }
a { color:var(--link); }
ul { padding-left:20px; } li { margin:4px 0; }
code { font:13px/1.5 'JetBrains Mono', ui-monospace, 'SF Mono', monospace; }
.muted, footer { color:var(--text-muted); font-size:14px; }
footer { border-top:1px solid var(--border); margin-top:64px; padding-top:16px; }
"""


def render_markdown(base_url: str) -> str:
    links = "\n".join(f"- [{label}]({path})" for path, label in AGENT_LINKS)
    use = "\n".join(f"- {item}" for item in WHEN_TO_USE)
    avoid = "\n".join(f"- {item}" for item in WHEN_NOT_TO_USE)
    return (
        f"---\ntitle: HackBench\ndescription: {TAGLINE}\ncanonical: {base_url}/\n"
        f"last-updated: 2026-10-03\n---\n\n"
        f"# HackBench\n\n> {TAGLINE}\n\n{STATUS}\n\n"
        f"## When to use HackBench\n\n{use}\n\n## When not to use it\n\n{avoid}\n\n"
        f"## For agents\n\n{links}\n\n## Source\n\n- [GitHub repository]({REPO_URL})\n"
    )


def _li(items: tuple[str, ...]) -> str:
    return "\n".join(f"<li>{html.escape(item)}</li>" for item in items)


def _json_ld(base_url: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "HackBench",
        "description": TAGLINE,
        "url": base_url,
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web",
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
        "codeRepository": REPO_URL,
        "sameAs": [REPO_URL],
    }
    # Reason: "</" must not appear inside a <script> block; escape it for safety.
    return json.dumps(data, indent=2).replace("</", "<\\/")


def render_html(base_url: str) -> str:
    links = "\n".join(
        f'<li><a href="{html.escape(path)}">{html.escape(label)}</a></li>'
        for path, label in AGENT_LINKS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HackBench</title>
<meta name="description" content="{html.escape(TAGLINE)}">
<link rel="canonical" href="{html.escape(base_url)}/">
<link rel="alternate" type="text/markdown" href="/index.md">
<meta property="og:type" content="website">
<meta property="og:title" content="HackBench">
<meta property="og:description" content="{html.escape(TAGLINE)}">
<meta property="og:url" content="{html.escape(base_url)}/">
<script type="application/ld+json">
{_json_ld(base_url)}
</script>
<style>{CSS}</style>
</head>
<body>
<main>
<p class="eyebrow">London AI x Science Hackathon · 3&ndash;4 Oct 2026</p>
<h1>HackBench</h1>
<div class="rule" aria-hidden="true"></div>
<p>{html.escape(TAGLINE)}</p>
<p class="muted">{html.escape(STATUS)}</p>
<h2>When to use HackBench</h2>
<ul>
{_li(WHEN_TO_USE)}
</ul>
<h2>When not to use it</h2>
<ul>
{_li(WHEN_NOT_TO_USE)}
</ul>
<h2>For agents</h2>
<ul>
{links}
</ul>
<p class="muted">Agents can request this page as markdown: <code>Accept: text/markdown</code>
or <a href="/index.md">/index.md</a>.</p>
<footer>Source: <a href="{REPO_URL}">GitHub</a> · Apache-2.0</footer>
</main>
</body>
</html>
"""
