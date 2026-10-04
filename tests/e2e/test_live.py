"""End-to-end checks against a deployed instance. Set HACKBENCH_E2E_URL to run (`make e2e`)."""

import os

import httpx
import pytest

BASE_URL = os.environ.get("HACKBENCH_E2E_URL", "").rstrip("/")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="HACKBENCH_E2E_URL not set")


@pytest.fixture(scope="module")
def http() -> httpx.Client:
    # Reason: generous timeout so a Modal cold start doesn't fail the first request.
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


def test_homepage_serves_html_and_markdown(http: httpx.Client) -> None:
    page = http.get("/", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "<h1>Parallax</h1>" in page.text
    md = http.get("/", headers={"Accept": "text/markdown"})
    assert md.headers["content-type"].startswith("text/markdown")
    assert "\n# Parallax\n" in md.text
    assert "Accept" in md.headers["vary"]


def test_served_over_https(http: httpx.Client) -> None:
    assert http.get("/v1/health").url.scheme == "https"
