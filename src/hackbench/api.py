"""One FastAPI app serving both surfaces: UI for people, REST/discovery files for agents."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from hackbench import DISPLAY_NAME, __version__, discovery
from hackbench.landing import render_html, render_markdown
from hackbench.profile import Profile, load_profile
from hackbench.settings import Settings

MARKDOWN = "text/markdown; charset=utf-8"

# Reason: name the major AI agents/crawlers explicitly so per-bot policy is unambiguous.
# Infra policy, not use-case data, so it stays in code rather than the profile.
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


def _ctx() -> tuple[Settings, Profile]:
    s = Settings.from_env()
    return s, load_profile(s.profile)


def _robots_txt(base_url: str) -> str:
    per_agent = "".join(f"User-agent: {ua}\nAllow: /\n\n" for ua in AI_AGENTS)
    return (
        f"{per_agent}User-agent: *\n"
        "Content-Signal: search=yes, ai-input=yes, ai-train=no\nAllow: /\n\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )


def _agent_card(p: Profile, base_url: str) -> dict[str, object]:
    return {
        "name": DISPLAY_NAME,
        "description": p.tagline,
        "url": base_url,
        "version": __version__,
        "capabilities": {"streaming": False},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": p.skill.id,
                "name": p.skill.name,
                "description": p.skill.description,
                "tags": list(p.skill.tags),
            }
        ],
    }


def _wants_markdown(request: Request) -> bool:
    return "text/markdown" in request.headers.get("accept", "")


def create_app() -> FastAPI:
    _, profile = _ctx()
    app = FastAPI(title=DISPLAY_NAME, version=__version__, description=profile.tagline)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        # Reason: agents asking for markdown get a readable 404 with a way back in.
        if exc.status_code == 404 and _wants_markdown(request):
            return Response(discovery.markdown_404(), status_code=404, media_type=MARKDOWN)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> Response:
        s, p = _ctx()
        # Reason: one URL, two audiences; Vary tells caches the body depends on Accept.
        headers = {"Vary": "Accept", "Link": discovery.link_header()}
        if _wants_markdown(request):
            return Response(render_markdown(p, s.base_url), media_type=MARKDOWN, headers=headers)
        return HTMLResponse(render_html(p, s.base_url), headers=headers)

    @app.get("/index.md", include_in_schema=False)
    def index_md() -> Response:
        s, p = _ctx()
        return Response(
            render_markdown(p, s.base_url),
            media_type=MARKDOWN,
            headers={"Link": discovery.link_header()},
        )

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        # Reason: lets the deploy pipeline wait until the new commit is the one serving.
        return {"status": "ok", "commit": Settings.from_env().commit}

    @app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
    def llms_txt() -> str:
        s, p = _ctx()
        return discovery.llms_txt(p, s.base_url)

    @app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
    def robots_txt() -> str:
        return _robots_txt(Settings.from_env().base_url)

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap() -> Response:
        s, p = _ctx()
        return Response(discovery.sitemap_xml(p, s.base_url), media_type="application/xml")

    @app.get("/.well-known/agent-card.json", include_in_schema=False)
    def agent_card() -> dict[str, object]:
        s, p = _ctx()
        return _agent_card(p, s.base_url)

    @app.get("/.well-known/agent-skills/index.json", include_in_schema=False)
    def skills_index() -> dict[str, object]:
        s, p = _ctx()
        return discovery.skills_index(p, s.base_url)

    @app.get(discovery.SKILL_PATH, include_in_schema=False)
    def skill_md() -> Response:
        s, p = _ctx()
        return Response(discovery.skill_md(p, s.base_url), media_type=MARKDOWN)

    @app.get("/.well-known/ard.json", include_in_schema=False)
    def ard() -> dict[str, object]:
        s, p = _ctx()
        return discovery.ard(p, s.base_url)

    @app.get("/.well-known/api-catalog", include_in_schema=False)
    def api_catalog() -> JSONResponse:
        return JSONResponse(
            discovery.api_catalog(Settings.from_env().base_url), media_type=discovery.LINKSET
        )

    return app
