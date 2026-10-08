"""End-to-end checks against a deployed instance. Set HACKBENCH_E2E_URL to run (`make e2e`)."""

import os

import httpx
import pytest

BASE_URL = os.environ.get("HACKBENCH_E2E_URL", "").rstrip("/")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="HACKBENCH_E2E_URL not set")


@pytest.fixture(scope="module")
def http() -> httpx.Client:
    # Reason: generous timeout so a slow first CDN fetch doesn't fail the run.
    return httpx.Client(base_url=BASE_URL, timeout=60.0, follow_redirects=False)


def test_health(http: httpx.Client) -> None:
    r = http.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["commit"]


def test_llms_txt_advertises_the_public_url(http: httpx.Client) -> None:
    r = http.get("/llms.txt")
    assert r.status_code == 200
    assert r.text.startswith("# Parallax")
    assert f"{BASE_URL}/openapi.json" in r.text
    assert "localhost" not in r.text


def test_robots_txt_content_signal(http: httpx.Client) -> None:
    r = http.get("/robots.txt")
    assert r.status_code == 200
    assert "Content-Signal: search=yes, ai-input=yes, ai-train=no" in r.text


def test_agent_card_points_at_the_deployment(http: httpx.Client) -> None:
    r = http.get("/.well-known/agent-card.json")
    assert r.status_code == 200
    card = r.json()
    assert card["name"] == "Parallax"
    assert card["url"] == BASE_URL
    assert any(s["id"] == "evaluate-qc-verdict" for s in card["skills"])


def test_openapi_lists_the_health_route(http: httpx.Client) -> None:
    r = http.get("/openapi.json")
    assert r.status_code == 200
    assert "/v1/health" in r.json()["paths"]


def test_homepage_serves_html_and_its_markdown_twin(http: httpx.Client) -> None:
    page = http.get("/", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert '<div id="root"></div>' in page.text  # the designed console
    assert "<noscript><h1>Parallax</h1>" in page.text
    assert f'href="{BASE_URL}/index.md"' in page.text
    # Reason: a static host cannot negotiate on Accept, so agents use the twin URL.
    md = http.get("/index.md")
    assert md.status_code == 200
    assert "\n# Parallax\n" in md.text


def test_results_and_a_batch_brief_are_published(http: httpx.Client) -> None:
    results = http.get("/v1/results").json()
    assert results["schema"] == "hackbench-results/1"
    batch = next(b for b, d in results["batches"].items() if d.get("parallax_brief"))
    brief = results["batches"][batch]["parallax_brief"]
    assert http.get(f"/data/{batch}/brief.json").json() == brief


def test_react_console_loads_its_assets(http: httpx.Client) -> None:
    page = http.get("/results/")
    assert page.status_code == 200
    src = page.text.split('src="', 1)[1].split('"', 1)[0]
    assert src.startswith("./assets/")  # relative, so it resolves under any sub-path
    assert http.get(f"/results/{src.removeprefix('./')}").status_code == 200


def test_served_over_https(http: httpx.Client) -> None:
    assert http.get("/v1/health").url.scheme == "https"
