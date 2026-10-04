"""Polaron LLM configs: tool specs match the workspace, prompts state the rules, configs differ
only in model and prompt variant."""

from pathlib import Path
from typing import Any

from hackbench.journal import Journal
from hackbench.polaron.llm import BRIEFS, CONFIGS, SYSTEM, TOOL_SPECS, make_agent
from hackbench.polaron.task import PolaronTask
from hackbench.polaron.workspace import open_session
from hackbench.profile import load_profile
from tests.polaron.conftest import Truth
from tests.test_claude_agent import FakeClient


def test_tool_specs_cover_exactly_the_session_tools(
    tmp_path: Path, dataset: dict[str, list[Truth]]
) -> None:
    task = PolaronTask(tmp_path, load_profile("polaron").domain)
    per_batch = task.collect(Journal(tmp_path / "c.jsonl"))
    session = open_session(
        task, per_batch, "Batch_1", "Batch_2", ["accept"], tmp_path / "ws",
        tmp_path / "runs" / "s.jsonl", {"agent": "x"},
    )  # fmt: skip
    assert {s["name"] for s in TOOL_SPECS} == {*session.tools, "submit_verdict"}


def test_tool_specs_are_strict() -> None:
    for spec in TOOL_SPECS:
        schema: dict[str, Any] = spec["input_schema"]
        assert spec["strict"] is True
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])


def test_prompts_state_the_evidence_rule_and_the_call_budget() -> None:
    for brief in BRIEFS.values():
        assert "not evidence" in brief
        assert "including" in brief  # the call cap counts the verdict
    assert BRIEFS["neutral"] != BRIEFS["pressure"]
    assert BRIEFS["pressure"].startswith(BRIEFS["neutral"])  # pressure only adds text
    assert SYSTEM


def test_four_configs_cross_two_models_with_two_prompts() -> None:
    assert len(CONFIGS) == 4
    assert {(c.model, c.prompt) for c in CONFIGS.values()} == {
        (m, p) for m in ("claude-haiku-4-5", "claude-sonnet-5-5") for p in ("neutral", "pressure")
    }
    agent = make_agent("sonnet-5-5/pressure", client=FakeClient([]))
    assert agent.name == "sonnet-5-5/pressure"
    assert agent.effort == "medium"
    assert make_agent("haiku-4-5/neutral", client=FakeClient([])).effort is None
