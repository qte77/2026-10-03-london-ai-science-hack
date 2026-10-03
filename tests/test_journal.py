"""Run journal: append-only, hash-chained, tamper-evident."""

import json
from pathlib import Path

from hackbench.journal import Journal, verify


def test_entries_are_chained_and_verify(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    j = Journal(path)
    j.append({"tool": "kpis", "fov": "a"})
    j.append({"tool": "verdict", "batch": "Batch_2"})
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [e["seq"] for e in lines] == [0, 1]
    assert lines[1]["prev_hash"] == lines[0]["hash"]
    assert verify(path)


def test_editing_an_entry_breaks_verification(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    j = Journal(path)
    j.append({"tool": "kpis", "porosity_pct": 12.0})
    j.append({"tool": "kpis", "porosity_pct": 13.0})
    path.write_text(path.read_text().replace("12.0", "99.0"))
    assert not verify(path)


def test_reopening_continues_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    Journal(path).append({"n": 1})
    Journal(path).append({"n": 2})
    assert verify(path)
    assert len(path.read_text().splitlines()) == 2
