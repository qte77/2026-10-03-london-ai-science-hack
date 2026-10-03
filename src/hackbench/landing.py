"""Landing page: one source of content (the profile), rendered as markdown and HTML."""

import html
import json

from hackbench import DISPLAY_NAME, REPO_URL
from hackbench.profile import Profile

# (path, label) pairs shown to both audiences.
AGENT_LINKS: tuple[tuple[str, str], ...] = (
    ("/llms.txt", "llms.txt: project summary for agents"),
    ("/.well-known/agent-card.json", "Agent card (A2A discovery)"),
    ("/openapi.json", "OpenAPI schema (REST API)"),
    ("/v1/health", "Health check"),
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


def render_markdown(p: Profile, base_url: str) -> str:
    links = "\n".join(f"- [{label}]({path})" for path, label in AGENT_LINKS)
    use = "\n".join(f"- {item}" for item in p.when_to_use)
    avoid = "\n".join(f"- {item}" for item in p.when_not_to_use)
    return (
        f"---\ntitle: {DISPLAY_NAME}\ndescription: {p.tagline}\ncanonical: {base_url}/\n"
        f"last-updated: {p.updated.isoformat()}\n---\n\n"
        f"# {DISPLAY_NAME}\n\n> {p.tagline}\n\n{p.status}\n\n"
        f"## When to use {DISPLAY_NAME}\n\n{use}\n\n## When not to use it\n\n{avoid}\n\n"
        f"## For agents\n\n{links}\n\n## Source\n\n- [GitHub repository]({REPO_URL})\n"
    )


def _li(items: tuple[str, ...]) -> str:
    return "\n".join(f"<li>{html.escape(item)}</li>" for item in items)


def _json_ld(p: Profile, base_url: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": DISPLAY_NAME,
        "description": p.tagline,
        "url": base_url,
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web",
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
        "codeRepository": REPO_URL,
        "sameAs": [REPO_URL],
    }
    # Reason: "</" must not appear inside a <script> block; escape it for safety.
    return json.dumps(data, indent=2).replace("</", "<\\/")


def render_html(p: Profile, base_url: str) -> str:
    links = "\n".join(
        f'<li><a href="{html.escape(path)}">{html.escape(label)}</a></li>'
        for path, label in AGENT_LINKS
    )
    tagline = html.escape(p.tagline)
    base = html.escape(base_url)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{DISPLAY_NAME}</title>
<meta name="description" content="{tagline}">
<link rel="canonical" href="{base}/">
<link rel="alternate" type="text/markdown" href="/index.md">
<meta property="og:type" content="website">
<meta property="og:title" content="{DISPLAY_NAME}">
<meta property="og:description" content="{tagline}">
<meta property="og:url" content="{base}/">
<script type="application/ld+json">
{_json_ld(p, base_url)}
</script>
<style>{CSS}</style>
</head>
<body>
<main>
<p class="eyebrow">{html.escape(p.event.name)} · {html.escape(p.event.dates)}</p>
<h1>{DISPLAY_NAME}</h1>
<div class="rule" aria-hidden="true"></div>
<p>{tagline}</p>
<p class="muted">{html.escape(p.status)}</p>
<h2>When to use {DISPLAY_NAME}</h2>
<ul>
{_li(p.when_to_use)}
</ul>
<h2>When not to use it</h2>
<ul>
{_li(p.when_not_to_use)}
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
