"""Agent-native surface: discovery files agents and readiness scanners look for at the host root."""

from fastapi.testclient import TestClient

from hackbench.api import create_app

client = TestClient(create_app())


def test_llms_txt_describes_the_project_and_links_the_api() -> None:
    r = client.get("/llms.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert r.text.startswith("# HackBench")
    assert "/openapi.json" in r.text


def test_robots_txt_carries_a_content_signal() -> None:
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Content-Signal: search=yes, ai-input=yes, ai-train=no" in r.text


def test_agent_card_is_served_from_well_known() -> None:
    r = client.get("/.well-known/agent-card.json")
    assert r.status_code == 200
    card = r.json()
    assert card["name"] == "HackBench"
    assert card["url"].startswith("http")
    assert card["skills"], "agent card must list at least one skill"


def test_openapi_schema_is_published() -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "HackBench"


def test_health_endpoint() -> None:
    assert client.get("/v1/health").json() == {"status": "ok"}
