"""One FastAPI app serving both surfaces: UI for people, REST/discovery files for agents."""

import os

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

DESCRIPTION = (
    "Science agents doing Polaron's battery-electrode QC, and the evals that tell you when "
    "to trust them: correctness, reward hacking, calibration, falsification."
)

ROBOTS_TXT = """User-agent: *
Content-Signal: search=yes, ai-input=yes, ai-train=no
Allow: /
"""


def _base_url() -> str:
    # Reason: the agent card must carry an absolute URL; the deploy sets it, tests fall back.
    return os.environ.get("HACKBENCH_BASE_URL", "http://localhost:8000")


def _llms_txt() -> str:
    base = _base_url()
    return f"""# HackBench

> {DESCRIPTION}

## API

- [OpenAPI schema]({base}/openapi.json): REST endpoints under /v1
- [Agent card]({base}/.well-known/agent-card.json): A2A discovery
- [Health]({base}/v1/health)
"""


def _agent_card() -> dict:
    return {
        "name": "HackBench",
        "description": DESCRIPTION,
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


def create_app() -> FastAPI:
    app = FastAPI(title="HackBench", version="0.1.0", description=DESCRIPTION)

    @app.get("/v1/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
    def llms_txt() -> str:
        return _llms_txt()

    @app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
    def robots_txt() -> str:
        return ROBOTS_TXT

    @app.get("/.well-known/agent-card.json", include_in_schema=False)
    def agent_card() -> dict:
        return _agent_card()

    return app
