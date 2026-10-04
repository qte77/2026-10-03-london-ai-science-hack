"""hackbench.paper_judge: Paperclip resolve/score + LLM judge, via httpx.MockTransport.

No network, no keys. Covers: skipped-without-key, Paperclip agreement/resolution/found-rate
math, judge scoring + malformed-response errors, and the modal-endpoint/cloudflare/skipped
provider-selection order.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from hackbench.journal import Journal
from hackbench.paper_judge import PAPERCLIP_BASE_URL, _judge_target, run_paper_judge


def test_modal_endpoint_is_first_with_proxy_token_and_model() -> None:
    base, provider, headers, model = _judge_target(
        "https://ws--ep.modal.run", "acct", "cf-token", "gpt-oss-20b", "wk-1.ws-2"
    )
    assert provider == "modal-endpoint"
    assert base == "https://ws--ep.modal.run/v1"
    assert headers == {"Authorization": "Bearer wk-1.ws-2"}  # proxy token id.secret
    assert model == "gpt-oss-20b"


BUNDLE = {
    "papers": [
        {
            "id": "paper:a",
            "title": "Title A",
            "doi": "10.1/a",
            "assessments": [
                {"target": "m1", "claim": "claim one", "direction": "SUPPORTIVE"},
                {"target": "m2", "claim": "claim two", "direction": "CONTRADICTORY"},
            ],
        },
        {
            "id": "paper:b",
            "title": "Title B",
            "doi": None,
            "assessments": [
                {"target": "m3", "claim": "claim three", "direction": "NEUTRAL"},
            ],
        },
    ]
}


def _bundle_path(tmp_path: Path) -> Path:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(BUNDLE))
    return path


def _journal(tmp_path: Path) -> Journal:
    return Journal(tmp_path / "pj.jsonl")


def _paperclip_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        base_url=PAPERCLIP_BASE_URL,
        headers={"X-API-Key": "test-key"},
        transport=httpx.MockTransport(handler),
    )


def test_skipped_without_a_key(tmp_path: Path) -> None:
    out = run_paper_judge(_bundle_path(tmp_path), _journal(tmp_path), api_key="")
    assert out == {"status": "skipped", "reason": "PAPERCLIP_API_KEY unset"}


def _paperclip_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/v1/lookup":
        return httpx.Response(
            200, json={"papers": [{"id": "PC_A", "title": "Title A", "doi": "10.1/a"}]}
        )
    if path == "/api/v1/search":
        return httpx.Response(200, json={"results": [{"id": "PC_B", "title": "Title B"}]})
    if path == "/api/v1/claims/support":
        body = json.loads(request.content)
        claim = body["claim"]
        if claim == "claim one":  # matches paper A's doi -> our_paper_found True
            return httpx.Response(
                200,
                json={
                    "support": [{"id": "PC_A", "doi": "10.1/a", "title": "Title A"}],
                    "against": [],
                },
            )
        if claim == "claim two":  # contradictory, evidence is someone else -> found False
            return httpx.Response(200, json={"support": [], "against": [{"id": "X"}]})
        if claim == "claim three":  # paper B curated NEUTRAL, Paperclip says SUPPORTIVE: mismatch
            return httpx.Response(200, json={"support": [{"id": "Y"}], "against": []})
    return httpx.Response(404)


def test_paperclip_agreement_resolution_and_found_rate(tmp_path: Path) -> None:
    out = run_paper_judge(
        _bundle_path(tmp_path),
        _journal(tmp_path),
        api_key="test-key",
        client=_paperclip_client(_paperclip_handler),
    )
    assert out["status"] == "ok"
    assert out["paperclip_resolved_rate"] == 1.0  # both papers resolved
    assert out["paperclip_agreement"] == pytest.approx(2 / 3)  # claim three mismatches
    rows = {r["target"]: r for r in out["rows"]}
    assert rows["m1"]["paperclip"] == "SUPPORTIVE"
    assert rows["m1"]["our_paper_found"] is True
    assert rows["m2"]["paperclip"] == "CONTRADICTORY"
    assert rows["m2"]["our_paper_found"] is False
    assert rows["m3"]["paperclip"] == "SUPPORTIVE"
    assert out["judge"] == {
        "status": "skipped",
        "reason": "HACKBENCH_LLM_URL unset; CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN unset",
    }
    # Reason: evidence/claim text must never reach the returned result.
    text = json.dumps(out)
    assert "claim one" not in text


def _judge_handler_good_then_malformed(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/models"):
        return httpx.Response(200, json={"data": [{"id": "judge-model"}]})
    if request.method != "POST":
        return httpx.Response(404)
    body = json.loads(request.content)
    user = body["messages"][1]["content"]
    if "Target marker: m1" in user:
        return httpx.Response(
            200,
            json={
                "model": "judge-model",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "direction": "SUPPORTIVE",
                                    "paperclip_relevant": True,
                                    "paperclip_direction_correct": True,
                                    "grounded": True,
                                    "confidence": 0.9,
                                }
                            )
                        }
                    }
                ],
            },
        )
    return httpx.Response(200, json={"choices": [{"message": {"content": "not json at all"}}]})


def test_judge_scores_and_malformed_response_counts_as_error(tmp_path: Path) -> None:
    out = run_paper_judge(
        _bundle_path(tmp_path),
        _journal(tmp_path),
        api_key="test-key",
        llm_url="http://judge.test",
        client=_paperclip_client(_paperclip_handler),
        judge_client=httpx.Client(
            transport=httpx.MockTransport(_judge_handler_good_then_malformed)
        ),
        backoff=(),
    )
    judge = out["judge"]
    assert judge["status"] == "ok"
    assert judge["provider"] == "modal-endpoint"
    assert judge["model"] == "judge-model"
    assert judge["n"] == 3
    assert judge["errors"] == 2  # m2 and m3 return unparsable content
    assert judge["judge_agreement"] == 1.0  # the one scored row (m1) matches curated
    assert judge["brier"] == pytest.approx((0.9 - 1.0) ** 2)


def test_provider_selection_order(tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("authorization")
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "m"}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "bad"}}]})

    judge_client = httpx.Client(transport=httpx.MockTransport(handler))

    out = run_paper_judge(
        _bundle_path(tmp_path),
        _journal(tmp_path),
        api_key="test-key",
        llm_url="http://judge.test",
        client=_paperclip_client(_paperclip_handler),
        judge_client=judge_client,
        backoff=(),
    )
    assert out["judge"]["provider"] == "modal-endpoint"
    assert seen["host"] == "judge.test"
    assert seen["auth"] is None

    out = run_paper_judge(
        _bundle_path(tmp_path),
        _journal(tmp_path),
        api_key="test-key",
        llm_url="",
        cf_account_id="acct123",
        cf_api_token="tok456",  # noqa: S106 - fake token, test fixture only
        client=_paperclip_client(_paperclip_handler),
        judge_client=httpx.Client(transport=httpx.MockTransport(handler)),
        backoff=(),
    )
    assert out["judge"]["provider"] == "cloudflare-workers-ai"
    assert out["judge"]["model"] == "@cf/openai/gpt-oss-20b"
    assert seen["host"] == "api.cloudflare.com"
    assert "acct123" in seen["path"]
    assert seen["auth"] == "Bearer tok456"

    out = run_paper_judge(
        _bundle_path(tmp_path),
        _journal(tmp_path),
        api_key="test-key",
        client=_paperclip_client(_paperclip_handler),
    )
    assert out["judge"]["status"] == "skipped"
