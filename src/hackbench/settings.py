"""Runtime settings: the only place the app reads its own environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    base_url: str = "http://localhost:8000"
    profile: str = "polaron"
    commit: str = "local"
    data_dir: str = "data/polaron"
    # Reason: local dev/tests read the results a `make cycle` run just wrote; Modal overrides
    # this to the volume mount path (`/data/results/results.json`).
    results_path: str = "results/cycle/results.json"
    # Reason: a committed, derived-only fallback so `/v1/results` works even before the first
    # volume write; Modal overrides this to wherever `deploy.py` adds the file in the image.
    snapshot_path: str = "data/results.snapshot.json"

    @classmethod
    def from_env(cls) -> "Settings":
        # Reason: read per request so a redeploy or test monkeypatch takes effect immediately.
        defaults = cls()
        return cls(
            base_url=os.environ.get("HACKBENCH_BASE_URL", defaults.base_url).rstrip("/"),
            profile=os.environ.get("HACKBENCH_PROFILE", defaults.profile),
            commit=os.environ.get("HACKBENCH_COMMIT", defaults.commit),
            data_dir=os.environ.get("HACKBENCH_DATA_DIR", defaults.data_dir),
            results_path=os.environ.get("HACKBENCH_RESULTS_PATH", defaults.results_path),
            snapshot_path=os.environ.get("HACKBENCH_SNAPSHOT_PATH", defaults.snapshot_path),
        )
