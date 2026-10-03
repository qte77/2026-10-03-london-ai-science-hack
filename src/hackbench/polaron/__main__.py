"""Run the reference QC pipeline (`make qc`) or the scored drift suite (`make qc-suite`).

python -m hackbench.polaron [--out DIR]           real batches vs the profile baseline
python -m hackbench.polaron --suite [--out DIR]   synthetic drift suite with known truth
"""

import argparse
import json
from pathlib import Path
from typing import Any

from hackbench.journal import verify
from hackbench.polaron.drift import build_suite
from hackbench.polaron.task import PolaronTask
from hackbench.profile import load_profile
from hackbench.settings import Settings


def _print_batches(results: dict[str, Any]) -> None:
    for batch, r in results.items():
        if isinstance(r, dict) and "verdict" in r:
            line = f"{batch:<20} {r['verdict']:<11} driving={r['driving']}"
            if "correct" in r:
                line += f"  expected={r['expected']}  {'OK' if r['correct'] else 'WRONG'}"
            print(line)


def _run(task: PolaronTask, out: Path) -> dict[str, Any]:
    journal = out / "journal.jsonl"
    results = task.run(journal_path=journal)
    results["journal_verified"] = verify(journal)
    return results


def main() -> None:
    s = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(s.data_dir))
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--suite", action="store_true", help="build and score the drift suite")
    args = parser.parse_args()
    params = load_profile(s.profile).domain

    if args.suite:
        suite_dir = args.out / "suite"
        build_suite(
            args.data_dir,
            str(params["baseline_batch"]),
            str(params["channel"]),
            suite_dir,
            seed=int(params["seed"]),
            crop_px=int(params["crop_px"]),
        )
        task = PolaronTask(suite_dir, {**params, "baseline_batch": "S_base", "crop_px": 0})
        results = _run(task, args.out / "suite-run")
        for batch, r in results.items():
            truth = task.ground_truth(batch)
            if isinstance(r, dict) and isinstance(truth, dict):
                r.update(expected=truth["expected"], kind=truth["kind"])
                r["correct"] = bool(task.score(batch, r)["correct"])
        name = "suite.json"
    else:
        task = PolaronTask(args.data_dir, params)
        if not task.load_items():
            raise SystemExit(f"no fields of view found under {args.data_dir}")
        results = _run(task, args.out)
        name = "results.json"

    results["commit"] = s.commit
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / name).write_text(json.dumps(results, indent=2) + "\n")
    _print_batches(results)
    scored = [r for r in results.values() if isinstance(r, dict) and "correct" in r]
    if scored:
        right = sum(r["correct"] for r in scored)
        print(f"accuracy: {right}/{len(scored)}")
    print(f"journal verified: {results['journal_verified']}")


if __name__ == "__main__":
    main()
