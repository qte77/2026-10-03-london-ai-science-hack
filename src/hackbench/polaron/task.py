"""PolaronTask: batch-vs-baseline QC on SEM fields of view, implementing the `Task` protocol."""

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from hackbench.journal import Journal
from hackbench.polaron.io import load_channel, pixel_size_nm
from hackbench.polaron.kpis import compute_kpis
from hackbench.stats import bootstrap_diff_ci, verdict


class PolaronTask:
    def __init__(self, data_dir: Path, params: Mapping[str, Any]) -> None:
        self.data_dir = data_dir
        self.baseline = str(params["baseline_batch"])
        self.channel = str(params["channel"])
        self.crop_px = int(params["crop_px"])
        self.k = float(params["tolerance_k"])
        self.n = int(params["bootstrap_n"])
        self.seed = int(params["seed"])
        self._honeypots = tuple(params["honeypots"])

    # --- Task protocol -------------------------------------------------------------------

    def load_items(self) -> Sequence[Mapping[str, object]]:
        """One item per field of view: the configured channel's file in each batch folder."""
        items = []
        for path in sorted(self.data_dir.glob(f"*/*_{self.channel}.tif")):
            fov = path.name.removesuffix(f"_{self.channel}.tif")
            items.append(
                {"id": f"{path.parent.name}/{fov}", "batch": path.parent.name, "path": path}
            )
        return items

    def tools(self) -> Mapping[str, Callable[..., object]]:
        return {"kpis": self.kpis, "compare_to_baseline": self.compare}

    def ground_truth(self, item_id: str) -> object:
        # Reason: the real batches carry no labels; ground truth comes from synthetic drift
        # injection (plan item 9), not from this data.
        return None

    def honeypots(self) -> Sequence[str]:
        return self._honeypots

    def score(self, item_id: str, verdict: Mapping[str, object]) -> Mapping[str, float]:
        # Reason: scoring needs ground truth, which arrives with the drift injector (item 9).
        return {}

    # --- Tools ---------------------------------------------------------------------------

    def kpis(self, path: Path) -> dict[str, float]:
        return compute_kpis(load_channel(path, self.crop_px), pixel_size_nm(path))

    def compare(
        self, per_batch: Mapping[str, list[dict[str, float]]], batch: str
    ) -> dict[str, Any]:
        base, other = per_batch[self.baseline], per_batch[batch]
        kpis, cis, tol = {}, {}, {}
        for name in base[0]:
            b_vals = np.array([row[name] for row in base])
            o_vals = np.array([row[name] for row in other])
            diff, lo, hi = bootstrap_diff_ci(b_vals, o_vals, n=self.n, seed=self.seed)
            tol[name] = self.k * float(b_vals.std(ddof=1)) if b_vals.size > 1 else 0.0
            cis[name] = (lo, hi)
            kpis[name] = {
                "base_mean": float(b_vals.mean()),
                "batch_mean": float(o_vals.mean()),
                "diff": diff,
                "ci": [lo, hi],
                "tolerance": tol[name],
            }
        v = verdict(cis, tol)
        for name in kpis:
            kpis[name]["driving"] = name in v.driving
        return {"verdict": v.label, "driving": list(v.driving), "n_fov": len(other), "kpis": kpis}

    # --- Reference pipeline --------------------------------------------------------------

    def run(self, journal_path: Path) -> dict[str, Any]:
        """Reference (non-agent) pipeline: KPIs per FOV, then every batch vs the baseline."""
        journal = Journal(journal_path)
        per_batch: dict[str, list[dict[str, float]]] = defaultdict(list)
        for item in self.load_items():
            values = self.kpis(Path(str(item["path"])))
            journal.append({"tool": "kpis", "item": item["id"], "result": values})
            per_batch[str(item["batch"])].append(values)

        results: dict[str, Any] = {"baseline": self.baseline}
        for batch in sorted(per_batch):
            if batch == self.baseline:
                continue
            outcome = self.compare(per_batch, batch)
            journal.append(
                {
                    "tool": "verdict",
                    "batch": batch,
                    "result": outcome["verdict"],
                    "driving": outcome["driving"],
                }
            )
            results[batch] = outcome
        return results
