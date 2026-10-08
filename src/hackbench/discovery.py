"""Agent discovery documents: llms.txt, SKILL.md + skills index, ARD, API catalog, sitemap."""

import hashlib

from hackbench import APP_NAME, DISPLAY_NAME, REPO_URL
from hackbench.profile import Profile

SKILL_PATH = f"/.well-known/agent-skills/{APP_NAME}/SKILL.md"
LINKSET = 'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"'


def _bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items)


def llms_txt(p: Profile, base: str) -> str:
    return f"""# {DISPLAY_NAME}

> {p.tagline}

## When to use {DISPLAY_NAME}

{_bullets(p.when_to_use)}

## When not to use it

{_bullets(p.when_not_to_use)}

## For agents

- [Markdown homepage]({base}/index.md)
- [OpenAPI schema]({base}/openapi.json): REST endpoints under /v1
- [API catalog]({base}/.well-known/api-catalog) (RFC 9727)
- [Agent skill]({base}{SKILL_PATH})
- [Agent card]({base}/.well-known/agent-card.json)
- [Health]({base}/v1/health)
- [Results]({base}/v1/results) ([markdown twin]({base}/results.md))

## Source

- [GitHub repository]({REPO_URL})
"""


def skill_md(p: Profile, base: str) -> str:
    return f"""---
name: {APP_NAME}
description: {p.skill.summary}
---

# {DISPLAY_NAME}

{p.tagline}

## When to use

{_bullets(p.when_to_use)}

## When not to use

{_bullets(p.when_not_to_use)}

## How to call it

- API schema: {base}/openapi.json
- Health check: `GET {base}/v1/health` returns `status` and the deployed `commit`
- Status: the evaluation endpoints are being built; this skill is updated as they ship.
"""


def skills_index(p: Profile, base: str) -> dict[str, object]:
    digest = hashlib.sha256(skill_md(p, base).encode()).hexdigest()
    return {
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [
            {
                "name": APP_NAME,
                "type": "skill-md",
                "description": p.skill.summary,
                "url": f"{base}{SKILL_PATH}",
                "digest": f"sha256:{digest}",
            }
        ],
    }


def ard(p: Profile, base: str) -> dict[str, object]:
    return {
        "specVersion": "1.0",
        "entries": [
            {
                "identifier": f"urn:air:{base.removeprefix('https://')}:skill:{APP_NAME}",
                "displayName": DISPLAY_NAME,
                "type": "application/ai-skill+md",
                "url": f"{base}{SKILL_PATH}",
                "description": p.tagline,
                "representativeQueries": list(p.skill.representative_queries),
            }
        ],
    }


def api_catalog(base: str) -> dict[str, object]:
    return {
        "linkset": [
            {
                "anchor": f"{base}/v1",
                "service-desc": [{"href": f"{base}/openapi.json", "type": "application/json"}],
                "service-doc": [{"href": f"{base}/llms.txt", "type": "text/plain"}],
                "status": [{"href": f"{base}/v1/health", "type": "application/json"}],
                "item": [{"href": f"{base}/v1/results", "type": "application/json"}],
            }
        ]
    }


def sitemap_xml(p: Profile, base: str) -> str:
    lastmod = p.updated.isoformat()
    urls = "".join(
        f"<url><loc>{base}{path}</loc><lastmod>{lastmod}</lastmod></url>"
        for path in ("/", "/index.md", "/llms.txt", SKILL_PATH)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    )


def link_header(base: str) -> str:
    return ", ".join(
        (
            f'<{base}/sitemap.xml>; rel="sitemap"',
            f'<{base}/index.md>; rel="alternate"; type="text/markdown"',
            f'<{base}/.well-known/api-catalog>; rel="api-catalog"',
            f'<{base}/openapi.json>; rel="service-desc"',
            f'<{base}/llms.txt>; rel="describedby"',
        )
    )


def markdown_404(base: str) -> str:
    return (
        f"# Not found\n\nThis page does not exist on {DISPLAY_NAME}. Start from "
        f"[/llms.txt]({base}/llms.txt), the [markdown homepage]({base}/index.md) or the "
        f"[sitemap]({base}/sitemap.xml).\n"
    )
