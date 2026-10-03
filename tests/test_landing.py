"""Landing page: HTML for people at /, markdown for agents (content negotiation + /index.md)."""

from fastapi.testclient import TestClient

from hackbench.api import create_app

client = TestClient(create_app())


def test_root_serves_html_for_browsers() -> None:
    r = client.get("/", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "<h1>HackBench</h1>" in r.text
    for path in ("/llms.txt", "/openapi.json", "/.well-known/agent-card.json"):
        assert f'href="{path}"' in r.text


def test_root_advertises_its_markdown_twin() -> None:
    r = client.get("/")
    assert '<link rel="alternate" type="text/markdown" href="/index.md">' in r.text


def test_root_serves_markdown_when_asked() -> None:
    r = client.get("/", headers={"Accept": "text/markdown"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text.startswith("---\ntitle: HackBench\n")
    assert "\n# HackBench\n" in r.text


def test_root_varies_on_accept_so_caches_keep_both_forms() -> None:
    for accept in ("text/html", "text/markdown"):
        assert "Accept" in client.get("/", headers={"Accept": accept}).headers["vary"]


def test_root_html_carries_identity_metadata() -> None:
    page = client.get("/", headers={"Accept": "text/html"}).text
    assert '<html lang="en">' in page
    assert '<link rel="canonical"' in page
    assert '<meta property="og:type" content="website">' in page
    assert '<script type="application/ld+json">' in page
    assert '"@type": "SoftwareApplication"' in page


def test_index_md_is_the_markdown_twin() -> None:
    r = client.get("/index.md")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text == client.get("/", headers={"Accept": "text/markdown"}).text
