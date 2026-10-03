"""Run the reference QC pipeline: `python -m hackbench.polaron [--out DIR]` (or `make qc`)."""

import argparse
import json
from pathlib import Path

from hackbench.journal import verify
from hackbench.polaron.task import PolaronTask
from hackbench.profile import load_profile
from hackbench.settings import Settings


def main() -> None:
    s = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(s.data_dir))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    task = PolaronTask(args.data_dir, load_profile(s.profile).domain)
    if not task.load_items():
        raise SystemExit(f"no fields of view found under {args.data_dir}")
    journal = args.out / "journal.jsonl"
    results = task.run(journal_path=journal)
    results["commit"] = s.commit
    results["journal_verified"] = verify(journal)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    for batch, r in results.items():
        if isinstance(r, dict):
            print(f"{batch}: {r['verdict']:<11} driving={r['driving']} (n={r['n_fov']})")
    print(f"journal: {journal} (verified={results['journal_verified']})")


if __name__ == "__main__":
    main()
