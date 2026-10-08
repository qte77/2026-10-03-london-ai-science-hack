"""Static export for GitHub Pages: every route pre-rendered, all links under the base URL."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from hackbench.discovery import SKILL_PATH
from hackbench.static_site import export

BASE = "https://example.test/sub"
SNAPSHOT = Path("data/results.snapshot.json")


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("HACKBENCH_BASE_URL", BASE)
        mp.setenv("HACKBENCH_COMMIT", "abc1234")
        # Reason: publish the committed snapshot, never a stray local cycle run.
        mp.setenv("HACKBENCH_RESULTS_PATH", str(out / "no-live-results.json"))
        export(out)
    return out


def test_every_route_becomes_a_file(site: Path) -> None:
    for rel in (
        "index.html",
        "about/index.html",
        "index.md",
        "llms.txt",
        "robots.txt",
        "sitemap.xml",
        "openapi.json",
        "results.md",
        "v1/health",
        "v1/results",
        ".well-known/agent-card.json",
        ".well-known/agent-skills/index.json",
        SKILL_PATH.lstrip("/"),
        ".well-known/ard.json",
        ".well-known/api-catalog",
        ".nojekyll",
    ):
        assert (site / rel).is_file(), rel


def test_homepage_is_the_console_with_its_no_js_summary(site: Path) -> None:
    page = (site / "index.html").read_text()
    assert '<div id="root"></div>' in page
    assert "<noscript><h1>Parallax</h1>" in page


def test_health_reports_the_built_commit(site: Path) -> None:
    assert json.loads((site / "v1/health").read_text()) == {"status": "ok", "commit": "abc1234"}


def test_results_and_briefs_come_from_the_snapshot(site: Path) -> None:
    snapshot = json.loads(SNAPSHOT.read_text())
    assert json.loads((site / "v1/results").read_text()) == snapshot
    briefs = {b: d["parallax_brief"] for b, d in snapshot["batches"].items() if d["parallax_brief"]}
    assert briefs
    for batch, brief in briefs.items():
        assert json.loads((site / f"data/{batch}/brief.json").read_text()) == brief


def test_console_files_and_react_ui_are_included(site: Path) -> None:
    assert (site / "assets/app.js").is_file()
    assert (site / "data/index.json").is_file()
    assert (site / "results/index.html").is_file()


def test_skill_digest_matches_the_published_file(site: Path) -> None:
    index = json.loads((site / ".well-known/agent-skills/index.json").read_text())
    (skill,) = index["skills"]
    assert skill["url"] == f"{BASE}{SKILL_PATH}"
    body = (site / SKILL_PATH.lstrip("/")).read_bytes()
    assert skill["digest"] == "sha256:" + hashlib.sha256(body).hexdigest()


def test_no_internal_link_escapes_the_sub_path(site: Path) -> None:
    # Reason: on a project page, "/x" points at the host root, outside the site.
    root_relative = re.compile(r'(?:href|src)="/(?!/)|\]\(/(?!/)')
    for rel in ("index.html", "about/index.html", "index.md", "results/index.html"):
        assert not root_relative.search((site / rel).read_text()), rel
    assert f"{BASE}/llms.txt" in (site / "about/index.html").read_text()
