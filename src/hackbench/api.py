"""One FastAPI app serving both surfaces: UI for people, REST/discovery files for agents."""

import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from hackbench import discovery
from hackbench.landing import TAGLINE, render_html, render_markdown

MARKDOWN = "text/markdown; charset=utf-8"

# Reason: name the major AI agents/crawlers explicitly so per-bot policy is unambiguous.
AI_AGENTS = (
    "ChatGPT-User",
    "GPTBot",
    "ClaudeBot",
    "Claude-User",
    "PerplexityBot",
    "Google-Extended",
    "ora-agent",
    "DeepSeekBot",
)


def _base_url() -> str:
    # Reason: absolute URLs in discovery files; the deploy sets it, tests fall back.
    return os.environ.get("HACKBENCH_BASE_URL", "http://localhost:8000")


def _robots_txt() -> str:
    per_agent = "".join(f"User-agent: {ua}\nAllow: /\n\n" for ua in AI_AGENTS)
    return (
        f"{per_agent}User-agent: *\n"
        "Content-Signal: search=yes, ai-input=yes, ai-train=no\nAllow: /\n\n"
        f"Sitemap: {_base_url()}/sitemap.xml\n"
    )


def _agent_card() -> dict[str, object]:
    return {
        "name": "HackBench",
        "description": TAGLINE,
        "url": _base_url(),
        "version": "0.1.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "evaluate-qc-verdict",
                "name": "Evaluate a QC verdict",
                "description": (
                    "Score an agent's accept/investigate/reject verdict on a Polaron electrode "
                    "batch for correctness, reward hacking, calibration and falsification."
                ),
                "tags": ["evals", "reward-hacking", "materials", "qc"],
            }
        ],
    }


def _wants_markdown(request: Request) -> bool:
    return "text/markdown" in request.headers.get("accept", "")


def create_app() -> FastAPI:
    app = FastAPI(title="HackBench", version="0.1.0", description=TAGLINE)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        # Reason: agents asking for markdown get a readable 404 with a way back in.
        if exc.status_code == 404 and _wants_markdown(request):
            return Response(discovery.markdown_404(), status_code=404, media_type=MARKDOWN)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> Response:
        # Reason: one URL, two audiences; Vary tells caches the body depends on Accept.
        headers = {"Vary": "Accept", "Link": discovery.link_header()}
        if _wants_markdown(request):
            return Response(render_markdown(_base_url()), media_type=MARKDOWN, headers=headers)
        return HTMLResponse(render_html(_base_url()), headers=headers)

    @app.get("/index.md", include_in_schema=False)
    def index_md() -> Response:
        return Response(
            render_markdown(_base_url()),
            media_type=MARKDOWN,
            headers={"Link": discovery.link_header()},
        )

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
    def llms_txt() -> str:
        return discovery.llms_txt(_base_url())

    @app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
    def robots_txt() -> str:
        return _robots_txt()

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap() -> Response:
        return Response(discovery.sitemap_xml(_base_url()), media_type="application/xml")

    @app.get("/.well-known/agent-card.json", include_in_schema=False)
    def agent_card() -> dict[str, object]:
        return _agent_card()

    @app.get("/.well-known/agent-skills/index.json", include_in_schema=False)
    def skills_index() -> dict[str, object]:
        return discovery.skills_index(_base_url())

    @app.get(discovery.SKILL_PATH, include_in_schema=False)
    def skill_md() -> Response:
        return Response(discovery.skill_md(_base_url()), media_type=MARKDOWN)

    @app.get("/.well-known/ard.json", include_in_schema=False)
    def ard() -> dict[str, object]:
        return discovery.ard(_base_url())

    @app.get("/.well-known/api-catalog", include_in_schema=False)
    def api_catalog() -> JSONResponse:
        return JSONResponse(discovery.api_catalog(_base_url()), media_type=discovery.LINKSET)

    return app
