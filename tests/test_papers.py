"""hackbench.papers: Paperclip literature lookups via httpx.MockTransport (no network, no keys)."""

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from hackbench.journal import Journal
from hackbench.papers import BASE_URL, CLAIMS, QUERIES, run_papers


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        headers={"X-API-Key": "test-key"},
        transport=httpx.MockTransport(handler),
    )


def _journal(tmp_path: Path) -> Journal:
    return Journal(tmp_path / "papers.jsonl")


def test_skips_without_a_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PAPERCLIP_API_KEY", raising=False)
    monkeypatch.delenv("GXL_API_KEY", raising=False)
    out = run_papers(_journal(tmp_path))
    assert out == {"status": "skipped", "reason": "PAPERCLIP_API_KEY/GXL_API_KEY unset"}


def _handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["x-api-key"] == "test-key"
    if request.url.path == "/api/v1/search":
        body = json.loads(request.content)
        assert body["num_results"] == 5
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "P1",
                        "title": "A paper",
                        "doi": "10.1/x",
                        "url": "https://example.test/p1",
                        "abstract": "full text that must never be stored",
                    }
                ]
            },
        )
    if request.url.path == "/api/v1/claims/support":
        return httpx.Response(
            200, json={"support": [{"id": "P2", "title": "supports it"}], "against": []}
        )
    return httpx.Response(404)


def test_search_and_claims_are_projected_to_minimal_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPERCLIP_API_KEY", "test-key")
    journal = _journal(tmp_path)
    client = _client(_handler)

    out = run_papers(journal, client=client)

    assert out["status"] == "ok"
    assert out["queries"] == QUERIES
    # Reason: the fake handler returns the same hit for every query (one call each);
    # a real search would differ per query.
    assert out["hits"] == [
        {
            "id": "P1",
            "title": "A paper",
            "doi": "10.1/x",
            "url": "https://example.test/p1",
            "citation_url": "https://example.test/p1",
        }
    ] * len(QUERIES)
    text = json.dumps(out)
    assert "full text" not in text  # never store abstracts/full text
    assert len(out["claims"]) == len(CLAIMS)
    assert out["claims"][0]["claim"] == CLAIMS[0]
    assert out["claims"][0]["support"] == [
        {"id": "P2", "title": "supports it", "doi": None, "url": None, "citation_url": None}
    ]
    assert out["claims"][0]["against"] == []

    calls = [json.loads(line) for line in (tmp_path / "papers.jsonl").read_text().splitlines()]
    assert len(calls) == len(QUERIES) + len(CLAIMS)
    assert all(c["tool"].startswith("paperclip.") for c in calls)


def test_caps_at_max_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPERCLIP_API_KEY", "test-key")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"results": []})

    client = _client(handler)
    run_papers(_journal(tmp_path), client=client, max_calls=2)
    assert len(seen) == 2


def test_errors_are_journaled_not_raised(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPERCLIP_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _client(handler)
    out = run_papers(_journal(tmp_path), client=client)
    assert out["status"] == "ok"
    assert out["hits"] == []
    assert out["claims"][0]["support"] == []
