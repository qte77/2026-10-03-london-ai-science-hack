"""Agent discovery files: skills index, ARD, API catalog, sitemap, Link headers, markdown 404s."""

import hashlib

from fastapi.testclient import TestClient

from hackbench.api import create_app

client = TestClient(create_app())


def test_llms_txt_says_when_to_use_and_when_not() -> None:
    text = client.get("/llms.txt").text
    assert "## When to use HackBench" in text
    assert "## When not to use it" in text


def test_skill_md_is_served_with_frontmatter() -> None:
    r = client.get("/.well-known/agent-skills/hackbench/SKILL.md")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text.startswith("---\nname: hackbench\n")


def test_agent_skills_index_pins_the_skill_by_digest() -> None:
    index = client.get("/.well-known/agent-skills/index.json").json()
    assert index["$schema"].startswith("https://schemas.agentskills.io/discovery/")
    (skill,) = index["skills"]
    assert skill["name"] == "hackbench"
    assert skill["description"]
    body = client.get(skill["url"]).content
    assert skill["digest"] == "sha256:" + hashlib.sha256(body).hexdigest()


def test_ard_lists_the_skill() -> None:
    ard = client.get("/.well-known/ard.json").json()
    assert ard["specVersion"] == "1.0"
    (entry,) = ard["entries"]
    assert entry["url"].endswith("/.well-known/agent-skills/hackbench/SKILL.md")
    assert entry["representativeQueries"]


def test_api_catalog_is_an_rfc9727_linkset() -> None:
    r = client.get("/.well-known/api-catalog")
    assert r.headers["content-type"].startswith("application/linkset+json")
    assert "rfc9727" in r.headers["content-type"]
    (entry,) = r.json()["linkset"]
    assert entry["service-desc"][0]["href"].endswith("/openapi.json")


def test_sitemap_lists_the_indexable_pages() -> None:
    r = client.get("/sitemap.xml")
    assert r.headers["content-type"].startswith("application/xml")
    for path in ("/", "/index.md", "/llms.txt"):
        assert f"{path}</loc>" in r.text
    assert "<lastmod>" in r.text


def test_homepage_advertises_discovery_via_link_header() -> None:
    link = client.get("/").headers["link"]
    assert 'rel="sitemap"' in link
    assert 'rel="alternate"; type="text/markdown"' in link
    assert 'rel="api-catalog"' in link
    assert 'rel="service-desc"' in link


def test_missing_page_returns_markdown_404_when_asked() -> None:
    r = client.get("/no-such-page", headers={"Accept": "text/markdown"})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/markdown")
    assert "/llms.txt" in r.text


def test_missing_page_keeps_json_404_by_default() -> None:
    r = client.get("/no-such-page")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}
