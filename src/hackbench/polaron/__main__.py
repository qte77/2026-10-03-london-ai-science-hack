"""Run the reference QC pipeline (`make qc`) or the scored drift suite (`make qc-suite`).

python -m hackbench.polaron [--out DIR]           real batches vs the profile baseline
python -m hackbench.polaron --suite [--out DIR]   calibrate k on a training drift suite,
                                                  then score once on a held-out suite
"""

import argparse
import json
from pathlib import Path
from typing import Any

from hackbench.journal import Journal, verify
from hackbench.polaron.drift import DEFAULT_LEVELS, HELDOUT_LEVELS, build_suite
from hackbench.polaron.task import PolaronTask, calibrate_k
from hackbench.profile import load_profile
from hackbench.settings import Settings

HELDOUT_SEED_OFFSET = 1000


def _print_batches(results: dict[str, Any]) -> None:
    for batch, r in results.items():
        if isinstance(r, dict) and "verdict" in r:
            line = f"{batch:<20} {r['verdict']:<11} driving={r['driving']}"
            if r.get("acquisition_flags"):
                line += f" acq_flags={r['acquisition_flags']}"
            if "correct" in r:
                line += f"  expected={r['expected']}  {'OK' if r['correct'] else 'WRONG'}"
            print(line)


def _suite(args: argparse.Namespace, params: dict[str, Any]) -> dict[str, Any]:
    seed, crop = int(params["seed"]), int(params["crop_px"])
    base, channel = str(params["baseline_batch"]), str(params["channel"])
    suite_params = {**params, "baseline_batch": "S_base", "crop_px": 0}

    # Reason: suite images are bulky and regenerable; keep them off the shared repo disk.
    train_dir, held_dir = args.scratch / "suite-train", args.scratch / "suite-heldout"
    train_truth = build_suite(args.data_dir, base, channel, train_dir, DEFAULT_LEVELS, seed, crop)
    held_truth = build_suite(
        args.data_dir, base, channel, held_dir, HELDOUT_LEVELS, seed + HELDOUT_SEED_OFFSET, crop
    )

    journal_path = args.out / "suite-journal.jsonl"
    journal = Journal(journal_path)
    train_task = PolaronTask(train_dir, suite_params)
    held_task = PolaronTask(held_dir, suite_params)
    train_kpis, held_kpis = train_task.collect(journal), held_task.collect(journal)

    best_k, table = calibrate_k(train_task, train_kpis, "S_base", train_truth)
    journal.append({"tool": "calibrate_k", "chosen_k": best_k, "train_accuracy": table})

    results: dict[str, Any] = {"calibration": {"chosen_k": best_k, "train_accuracy_by_k": table}}
    for batch in sorted(held_kpis):
        if batch == "S_base":
            continue
        r = held_task.compare(held_kpis, batch, k=best_k)
        truth = held_truth[batch]
        expected = (
            [str(v) for v in truth["expected"]] if isinstance(truth["expected"], list) else []
        )
        r |= {"expected": expected, "kind": truth["kind"]}
        r["correct"] = r["verdict"] in expected
        journal.append({"tool": "verdict", "batch": batch, "result": r["verdict"], "k": best_k})
        results[batch] = r
    results["journal_verified"] = verify(journal_path)
    return results


def main() -> None:
    s = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(s.data_dir))
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--suite", action="store_true", help="calibrate and score the drift suite")
    parser.add_argument(
        "--scratch",
        type=Path,
        default=Path("/tmp/hackbench-scratch"),  # noqa: S108 - regenerable images only
        help="where suite images are written (large, regenerable)",
    )
    args = parser.parse_args()
    params = dict(load_profile(s.profile).domain)

    if args.suite:
        results = _suite(args, params)
        name = "suite.json"
    else:
        task = PolaronTask(args.data_dir, params)
        if not task.load_items():
            raise SystemExit(f"no fields of view found under {args.data_dir}")
        journal = args.out / "journal.jsonl"
        results = task.run(journal_path=journal)
        results["journal_verified"] = verify(journal)
        name = "results.json"

    results["commit"] = s.commit
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / name).write_text(json.dumps(results, indent=2, default=str) + "\n")
    if "calibration" in results:
        cal = results["calibration"]
        print(f"k chosen on TRAIN suite: {cal['chosen_k']}")
        print(f"train accuracy by k: {cal['train_accuracy_by_k']}")
        print("HELD-OUT suite:")
    _print_batches(results)
    scored = [r for r in results.values() if isinstance(r, dict) and "correct" in r]
    if scored:
        print(f"held-out accuracy: {sum(r['correct'] for r in scored)}/{len(scored)}")
    print(f"journal verified: {results['journal_verified']}")


if __name__ == "__main__":
    main()
