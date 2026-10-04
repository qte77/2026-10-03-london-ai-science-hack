"""Landing page: HTML for people at /, markdown for agents (content negotiation + /index.md)."""

from fastapi.testclient import TestClient

from hackbench.api import create_app

client = TestClient(create_app())


def test_root_serves_the_designed_console_for_browsers() -> None:
    r = client.get("/", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert '<div id="root"></div>' in r.text  # the owner's design artifact
    assert 'src="assets/app.js"' in r.text
    assert "<noscript><h1>Parallax</h1>" in r.text  # readable without JS


def test_about_keeps_the_plain_landing_page() -> None:
    r = client.get("/about")
    assert r.status_code == 200
    assert "<h1>Parallax</h1>" in r.text
    for path in ("/llms.txt", "/openapi.json", "/.well-known/agent-card.json", "/results/"):
        assert f'href="{path}"' in r.text


def test_markdown_twin_links_to_the_qc_console() -> None:
    assert "](/results/)" in client.get("/index.md").text


def test_root_advertises_its_markdown_twin() -> None:
    r = client.get("/")
    assert '<link rel="alternate" type="text/markdown" href="/index.md">' in r.text


def test_root_serves_markdown_when_asked() -> None:
    r = client.get("/", headers={"Accept": "text/markdown"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text.startswith("---\ntitle: Parallax\n")
    assert "\n# Parallax\n" in r.text


def test_root_varies_on_accept_so_caches_keep_both_forms() -> None:
    for accept in ("text/html", "text/markdown"):
        assert "Accept" in client.get("/", headers={"Accept": accept}).headers["vary"]


def test_root_html_carries_identity_metadata() -> None:
    page = client.get("/", headers={"Accept": "text/html"}).text
    assert '<html lang="en"' in page
    assert '<link rel="canonical"' in page
    assert '<meta property="og:type" content="website">' in page
    assert '<script type="application/ld+json">' in page
    assert '"@type": "SoftwareApplication"' in page


def test_index_md_is_the_markdown_twin() -> None:
    r = client.get("/index.md")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text == client.get("/", headers={"Accept": "text/markdown"}).text


def test_console_assets_and_data_are_served_with_image_files() -> None:
    assert client.get("/assets/app.js").status_code == 200
    batch = client.get("/data/index.json").json()["batches"][0]["id"]
    field = client.get(f"/data/{batch}/field.json")
    assert field.status_code == 200
    assert "data:image" not in field.text
    image = next(iter(field.json()["assets"].values()))["image"]
    assert client.get(f"/data/{batch}/{image}").headers["content-type"] == "image/jpeg"
