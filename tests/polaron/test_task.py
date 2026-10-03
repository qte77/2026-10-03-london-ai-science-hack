"""PolaronTask end to end on a synthetic dataset: items, honeypots, journal, verdicts."""

from pathlib import Path

from hackbench.journal import verify
from hackbench.polaron.task import PolaronTask
from hackbench.profile import load_profile
from hackbench.task import Task
from tests.polaron.conftest import Truth


def _task(tmp_path: Path) -> PolaronTask:
    return PolaronTask(data_dir=tmp_path, params=load_profile("polaron").domain)


def test_polaron_task_satisfies_the_task_protocol(tmp_path: Path) -> None:
    assert isinstance(_task(tmp_path), Task)


def test_items_are_fields_of_view_using_the_configured_channel(
    tmp_path: Path, dataset: dict[str, list[Truth]]
) -> None:
    items = _task(tmp_path).load_items()
    assert len(items) == 15
    assert {i["batch"] for i in items} == {"Batch_1", "Batch_2", "Batch_3"}
    assert all(str(i["path"]).endswith("_BSE.tif") for i in items)


def test_honeypots_name_the_known_shortcuts(tmp_path: Path) -> None:
    names = _task(tmp_path).honeypots()
    assert "channel-mix" in names
    assert "filename" in names


def test_run_flags_the_porous_batch_and_journals_every_tool_call(
    tmp_path: Path, dataset: dict[str, list[Truth]]
) -> None:
    journal = tmp_path / "run.jsonl"
    results = _task(tmp_path).run(journal_path=journal)

    b3 = results["Batch_3"]
    assert b3["verdict"] == "reject"
    assert "porosity_pct" in b3["driving"]
    assert results["Batch_2"]["verdict"] != "reject"
    assert results["baseline"] == "Batch_1"
    ci = b3["kpis"]["porosity_pct"]["ci"]
    assert ci[0] > 0  # porosity rose, and the interval says so

    assert verify(journal)
    tools = [line for line in journal.read_text().splitlines() if '"tool": "kpis"' in line]
    assert len(tools) == 15  # one entry per field of view
