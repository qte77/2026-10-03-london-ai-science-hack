"""ClaudeAgent's manual tool-use loop, driven by a fake client: no network, no key, $0."""

import json
from pathlib import Path
from typing import Any

import pytest
from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

from hackbench.claude_agent import ClaudeAgent, cost_usd
from hackbench.session import Caps, Session, run_session

TOOLS = [{"name": "add", "description": "add", "input_schema": {"type": "object"}}]
VERDICT = {
    "label": "accept",
    "confidence": 0.7,
    "falsifier": {"kpi": "porosity_pct", "threshold": 2.0},
    "cited_entries": [],
}


def _usage(inp: int = 1000, out: int = 100) -> Usage:
    return Usage(input_tokens=inp, output_tokens=out, cache_read_input_tokens=0)


def _message(content: list[Any], stop_reason: str, usage: Usage) -> Message:
    # Reason: model_construct skips the fields this loop never reads (id, model, role, ...).
    return Message.model_construct(content=content, stop_reason=stop_reason, usage=usage)


def _tool_turn(*calls: tuple[str, dict[str, Any]], usage: Usage | None = None) -> Message:
    blocks = [
        ToolUseBlock(type="tool_use", id=f"tu_{i}", name=name, input=args)
        for i, (name, args) in enumerate(calls)
    ]
    return _message(blocks, "tool_use", usage or _usage())


def _end_turn() -> Message:
    return _message([TextBlock(type="text", text="I think it is fine.")], "end_turn", _usage())


class FakeClient:
    """Replays scripted responses and records every request."""

    def __init__(self, responses: list[Message]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> Message:  # noqa: ANN401 - mirrors the Client protocol
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot
        return self.responses.pop(0)


def _session(tmp_path: Path, caps: Caps | None = None) -> Session:
    return Session(
        tmp_path / "s.jsonl",
        tools={"add": lambda a, b: a + b},
        honeypots=[],
        meta={"agent": "test"},
        caps=caps,
    )


def _agent(
    client: FakeClient, model: str = "claude-haiku-4-5", effort: str | None = None
) -> ClaudeAgent:
    return ClaudeAgent("test", model, "system prompt", TOOLS, client, effort=effort)


def _events(tmp_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (tmp_path / "s.jsonl").read_text().splitlines()]


def test_loop_runs_tools_returns_entries_and_journals_every_turns_cost(tmp_path: Path) -> None:
    client = FakeClient(
        [
            _tool_turn(("add", {"a": 1, "b": 2}), ("rm", {})),
            _tool_turn(("submit_verdict", VERDICT), usage=_usage(2000, 50)),
        ]
    )
    run_session(_agent(client), "judge it", _session(tmp_path))

    events = _events(tmp_path)
    kinds = [e["event"] for e in events]
    assert kinds == [
        "session_start", "usage", "tool", "blocked", "usage", "submission", "session_end"
    ]  # fmt: skip
    # Reason: usage is journaled before tools run, so the verdict turn's cost is not lost.
    assert events[-1]["cost_usd"] == pytest.approx(cost_usd("claude-haiku-4-5", 3000, 150))

    second = client.requests[1]["messages"]
    results = second[-1]["content"]
    assert second[-1]["role"] == "user"
    assert [r["tool_use_id"] for r in results] == ["tu_0", "tu_1"]  # all results, one message
    ok = json.loads(results[0]["content"])
    assert ok["result"] == 3
    assert ok["entry"] == events[2]["hash"]  # the agent gets a citable journal hash
    assert results[1]["is_error"] is True


def test_request_shape_follows_the_model_rules(tmp_path: Path) -> None:
    for model, effort in (("claude-haiku-4-5", None), ("claude-sonnet-5-5", "medium")):
        client = FakeClient([_tool_turn(("submit_verdict", VERDICT))])
        run_session(_agent(client, model, effort), "brief", _session(tmp_path / model))
        req = client.requests[0]
        assert req["model"] == model
        assert req["tool_choice"] == {"type": "auto"}  # forced choice is a 400 on Sonnet 5.5
        assert "temperature" not in req  # non-default temperature is a 400 on Sonnet 5.5
        assert req["cache_control"] == {"type": "ephemeral"}
        assert req["messages"][0] == {"role": "user", "content": "brief"}
        if effort:
            assert req["output_config"] == {"effort": "medium"}
        else:
            assert "output_config" not in req  # effort errors on Haiku 4.5


def test_ending_the_turn_without_a_verdict_is_journaled(tmp_path: Path) -> None:
    client = FakeClient([_end_turn()])
    run_session(_agent(client), "brief", _session(tmp_path))
    end = _events(tmp_path)[-1]
    assert end["stop_reason"] == "no_submission"
    assert end["model_stop_reason"] == "end_turn"


def test_budget_stops_the_loop_before_the_next_request(tmp_path: Path) -> None:
    client = FakeClient([_tool_turn(("add", {"a": 1, "b": 1}), usage=_usage(10_000_000, 0))])
    run_session(_agent(client), "brief", _session(tmp_path, Caps(max_cost_usd=1.5)))
    assert len(client.requests) == 1
    assert _events(tmp_path)[-1]["stop_reason"] == "budget"


def test_cost_uses_per_model_prices_and_cache_multipliers() -> None:
    assert cost_usd("claude-haiku-4-5", 1_000_000, 1_000_000) == pytest.approx(6.0)
    assert cost_usd("claude-sonnet-5-5", 1_000_000, 0) == pytest.approx(2.0)
    assert cost_usd(
        "claude-sonnet-5-5", 0, 0, cache_write=1_000_000, cache_read=1_000_000
    ) == pytest.approx(2.0 * 1.25 + 2.0 * 0.1)
