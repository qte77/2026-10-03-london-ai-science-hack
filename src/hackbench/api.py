"""One FastAPI app serving both surfaces: UI for people, REST/discovery files for agents."""

import contextlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from hackbench import DISPLAY_NAME, __version__, discovery
from hackbench.landing import render_console, render_html, render_markdown
from hackbench.profile import Profile, load_profile
from hackbench.settings import Settings

MARKDOWN = "text/markdown; charset=utf-8"
LABELS = ("accept", "investigate", "reject")

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


def _load_results(reload: Callable[[], None] | None) -> tuple[dict[str, Any] | None, str]:
    """Live results (Modal volume), else a committed snapshot, else `(None, "none")`."""
    if reload is not None:
        # Reason: a stale/unmounted volume must not break the endpoint; fall through to snapshot.
        with contextlib.suppress(Exception):
            reload()
    s = Settings.from_env()
    for path, source in ((Path(s.results_path), "live"), (Path(s.snapshot_path), "snapshot")):
        if path.exists():
            try:
                return json.loads(path.read_text()), source
            except (OSError, json.JSONDecodeError):
                continue
    return None, "none"


def _parallax_label(brief: Mapping[str, Any]) -> str | None:
    # Reason: duplicated (not imported) from `cycle.py` so the web image never pulls in
    # the QC stack (numpy/scipy/scikit-image) that `cycle.py` transitively imports.
    claims = brief.get("claims") or []
    claim = next(
        (c for c in claims if isinstance(c, dict) and c.get("id") == "decision.verdict"), None
    )
    label = (claim or {}).get("label")
    if not isinstance(label, str):
        label = brief.get("hero", {}).get("decision", {}).get("state")
    if isinstance(label, str) and label.lower() in LABELS:
        return label.lower()
    return None


def _render_results_md(d: Mapping[str, Any]) -> str:
    lines = [
        "# HackBench results",
        "",
        f"Commit `{d.get('commit')}` · generated {d.get('generated_at')}",
        "",
        "## Batches",
        "",
    ]
    for batch, b in (d.get("batches") or {}).items():
        hb = b.get("hackbench")
        brief = b.get("parallax_brief")
        px = _parallax_label(brief) if brief else None
        lines.append(
            f"- **{batch}**: hackbench=`{hb['verdict'] if hb else '—'}` "
            f"parallax=`{px or '—'}` agree=`{b.get('agree')}`"
        )
    suite = d.get("suite") or {}
    lines += [
        "",
        "## Suite",
        "",
        f"Held-out accuracy: {suite.get('heldout_accuracy')} (k={suite.get('chosen_k')})",
        "",
        "## KPI robustness (top by material shift)",
        "",
    ]
    rob = sorted(
        (d.get("kpi_robustness") or {}).items(),
        key=lambda kv: kv[1].get("material_shift", 0),
        reverse=True,
    )
    for name, r in rob[:3]:
        lines.append(
            f"- **{name}** ({r.get('role')}): imaging={r.get('imaging_shift')} "
            f"material={r.get('material_shift')}"
        )
    pj = d.get("paper_judge") or {}
    lines += ["", "## Paper judge", ""]
    if pj.get("status") == "ok":
        lines.append(
            f"- paperclip: n={pj.get('n')} errors={pj.get('errors')} "
            f"resolved_rate={pj.get('paperclip_resolved_rate')} "
            f"agreement={pj.get('paperclip_agreement')}"
        )
        judge = pj.get("judge") or {}
        if judge.get("status") == "ok":
            lines.append(
                f"- judge ({judge.get('provider')}/{judge.get('model')}): "
                f"agreement={judge.get('judge_agreement')} brier={judge.get('brier')} "
                f"grounded_rate={judge.get('grounded_rate')} errors={judge.get('errors')}"
            )
        else:
            lines.append(f"- judge: {judge.get('status', 'skipped')} ({judge.get('reason', '—')})")
    else:
        lines.append(f"- {pj.get('status', 'skipped')}: {pj.get('reason', '—')}")

    lines += ["", "## Cycle stages", ""]
    for stg in (d.get("cycle") or {}).get("stages", []):
        lines.append(f"- {stg.get('name')}: {stg.get('status')} ({stg.get('seconds')}s)")
    return "\n".join(lines) + "\n"


def create_app(reload: Callable[[], None] | None = None) -> FastAPI:
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
        # Reason: people get the owner's designed QC console at /; its assets resolve under
        # /results/ (Vite base). Agents keep the markdown twin; the plain landing is at /about.
        console = Path(s.ui_dir) / "index.html"
        if console.exists():
            page = render_console(console.read_text(), p, s.base_url)
            return HTMLResponse(page, headers=headers)
        return HTMLResponse(render_html(p, s.base_url), headers=headers)

    @app.get("/about", include_in_schema=False)
    def about() -> Response:
        s, p = _ctx()
        return HTMLResponse(render_html(p, s.base_url), headers={"Link": discovery.link_header()})

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

    @app.get("/v1/results")
    def results() -> Response:
        data, source = _load_results(reload)
        if data is None:
            return JSONResponse({"detail": "no results available yet"}, status_code=503)
        return JSONResponse(data, headers={"X-Results-Source": source})

    @app.get("/results.md", include_in_schema=False)
    def results_md() -> Response:
        data, _source = _load_results(reload)
        if data is None:
            return Response(
                "# HackBench results\n\nNo results yet.\n", media_type=MARKDOWN, status_code=503
            )
        return Response(_render_results_md(data), media_type=MARKDOWN)

    # Reason: mount the built console only if present, so the API still works without it.
    ui_dist = Path(Settings.from_env().ui_dir)
    if (ui_dist / "index.html").exists():
        app.mount("/results", StaticFiles(directory=str(ui_dist), html=True), name="results-ui")

    return app
