"""Pre-render the web app into static files for GitHub Pages.

Each route is requested through the app itself, so the static site and `make run` can never
drift apart. Set HACKBENCH_BASE_URL to the public URL first: every link is built from it.

    uv run python -m hackbench.static_site --out _site
"""

import argparse
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from hackbench.api import create_app
from hackbench.discovery import SKILL_PATH
from hackbench.settings import Settings

# (route, file). Reason: a static host serves files as-is, so each route becomes the file at its
# own path; "/" and "/about" become index.html so the plain URLs keep working.
ROUTES: tuple[tuple[str, str], ...] = (
    ("/", "index.html"),
    ("/about", "about/index.html"),
    ("/index.md", "index.md"),
    ("/llms.txt", "llms.txt"),
    ("/robots.txt", "robots.txt"),
    ("/sitemap.xml", "sitemap.xml"),
    ("/openapi.json", "openapi.json"),
    ("/results.md", "results.md"),
    ("/v1/health", "v1/health"),
    ("/v1/results", "v1/results"),
    ("/.well-known/agent-card.json", ".well-known/agent-card.json"),
    ("/.well-known/agent-skills/index.json", ".well-known/agent-skills/index.json"),
    (SKILL_PATH, SKILL_PATH.lstrip("/")),
    ("/.well-known/ard.json", ".well-known/ard.json"),
    ("/.well-known/api-catalog", ".well-known/api-catalog"),
)


def _write(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def export(out: Path) -> None:
    """Write the whole site under `out`; raise if any route does not answer 200."""
    s = Settings.from_env()
    client = TestClient(create_app())
    # Reason: copy the console's files first; the routes below overwrite what the app serves live.
    console = Path(s.console_dir)
    for sub in ("assets", "data"):
        if (console / sub).is_dir():
            shutil.copytree(console / sub, out / sub, dirs_exist_ok=True)
    ui = Path(s.ui_dir)
    if (ui / "index.html").exists():
        shutil.copytree(ui, out / "results", dirs_exist_ok=True)

    for route, rel in ROUTES:
        r = client.get(route, headers={"Accept": "text/html"})
        if r.status_code != 200:
            raise RuntimeError(f"{route} answered HTTP {r.status_code}")
        _write(out / rel, r.content)

    batches = client.get("/v1/results").json().get("batches") or {}
    for batch in batches:
        r = client.get(f"/data/{batch}/brief.json")
        if r.status_code == 200:
            _write(out / "data" / batch / "brief.json", r.content)

    # Reason: Jekyll would drop dot-directories such as .well-known/.
    _write(out / ".nojekyll", b"")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("_site"))
    out = parser.parse_args().out
    if out.exists():
        shutil.rmtree(out)
    export(out)
    print(f"static site written to {out}")


if __name__ == "__main__":
    main()
