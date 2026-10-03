"""Agent discovery documents: llms.txt, SKILL.md + skills index, ARD, API catalog, sitemap."""

import hashlib
from datetime import date

from hackbench.landing import REPO_URL, TAGLINE, WHEN_NOT_TO_USE, WHEN_TO_USE

SKILL_NAME = "hackbench"
SKILL_PATH = f"/.well-known/agent-skills/{SKILL_NAME}/SKILL.md"
LINKSET = 'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"'
LAST_UPDATED = date(2026, 10, 3)


def _bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items)


def llms_txt(base: str) -> str:
    return f"""# HackBench

> {TAGLINE}

## When to use HackBench

{_bullets(WHEN_TO_USE)}

## When not to use it

{_bullets(WHEN_NOT_TO_USE)}

## For agents

- [Markdown homepage]({base}/index.md)
- [OpenAPI schema]({base}/openapi.json): REST endpoints under /v1
- [API catalog]({base}/.well-known/api-catalog) (RFC 9727)
- [Agent skill]({base}{SKILL_PATH})
- [Agent card]({base}/.well-known/agent-card.json)
- [Health]({base}/v1/health)

## Source

- [GitHub repository]({REPO_URL})
"""


def skill_md(base: str) -> str:
    return f"""---
name: {SKILL_NAME}
description: Use HackBench to check whether a science agent's QC verdict on battery-electrode
  micrographs is correct, honest (no reward hacking) and calibrated.
---

# HackBench

{TAGLINE}

## When to use

{_bullets(WHEN_TO_USE)}

## When not to use

{_bullets(WHEN_NOT_TO_USE)}

## How to call it

- API schema: {base}/openapi.json
- Health check: `GET {base}/v1/health` returns `{{"status": "ok"}}`
- Status: the evaluation endpoints are being built; this skill is updated as they ship.
"""


def skills_index(base: str) -> dict[str, object]:
    digest = hashlib.sha256(skill_md(base).encode()).hexdigest()
    return {
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [
            {
                "name": SKILL_NAME,
                "type": "skill-md",
                "description": (
                    "Check whether a science agent's QC verdict on battery-electrode "
                    "micrographs is correct, honest and calibrated."
                ),
                "url": SKILL_PATH,
                "digest": f"sha256:{digest}",
            }
        ],
    }


def ard(base: str) -> dict[str, object]:
    return {
        "specVersion": "1.0",
        "entries": [
            {
                "identifier": f"urn:air:{base.removeprefix('https://')}:skill:{SKILL_NAME}",
                "displayName": "HackBench",
                "type": "application/ai-skill+md",
                "url": f"{base}{SKILL_PATH}",
                "description": TAGLINE,
                "representativeQueries": [
                    "evaluate a science agent's verdict for reward hacking",
                    "calibration of an AI agent's materials QC decision",
                    "battery electrode micrograph batch drift QC benchmark",
                ],
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
            }
        ]
    }


def sitemap_xml(base: str) -> str:
    urls = "".join(
        f"<url><loc>{base}{path}</loc><lastmod>{LAST_UPDATED.isoformat()}</lastmod></url>"
        for path in ("/", "/index.md", "/llms.txt", SKILL_PATH)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    )


def link_header() -> str:
    return ", ".join(
        (
            '</sitemap.xml>; rel="sitemap"',
            '</index.md>; rel="alternate"; type="text/markdown"',
            '</.well-known/api-catalog>; rel="api-catalog"',
            '</openapi.json>; rel="service-desc"',
            '</llms.txt>; rel="describedby"',
        )
    )


def markdown_404() -> str:
    return (
        "# Not found\n\nThis page does not exist on HackBench. Start from "
        "[/llms.txt](/llms.txt), the [markdown homepage](/index.md) or the "
        "[sitemap](/sitemap.xml).\n"
    )
