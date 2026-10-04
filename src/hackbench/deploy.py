"""Modal deployment: one ASGI app owns the whole host, so root files like /llms.txt work.

Deploy with `make deploy`. Pattern per Modal's web-functions guide (checked 2026-10-03).
"""

import os
from pathlib import Path
from typing import Any

import modal
from fastapi import FastAPI

from hackbench import APP_NAME, __version__

# Reason: bake the deployed commit and version into the image; in the container the package
# is copied as source (not installed), so package metadata is unavailable there.
COMMIT = os.environ.get("HACKBENCH_COMMIT", "local")

# Reason: one Volume carries `cycle`'s derived, pre-registered inputs in (an owner's prior
# local `make qc`/`make qc-suite` output, uploaded with `modal volume put` - never raw TIFFs)
# and its `results.json` out, so `cycle` and `web` agree on where results live with neither
# redeployed. `web` calls `.reload()` before reading so a fresh `cycle` write is visible
# without restarting the always-on web container.
DATA_MOUNT = "/data"
QC_INPUTS_DIR = f"{DATA_MOUNT}/qc"
RESULTS_DIR = f"{DATA_MOUNT}/results"
RESULTS_PATH = f"{RESULTS_DIR}/results.json"
SNAPSHOT_PATH = "/opt/hackbench/results.snapshot.json"
data_volume = modal.Volume.from_name(f"{APP_NAME}-data", create_if_missing=True)

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]>=0.115")
    .env(
        {
            "HACKBENCH_COMMIT": COMMIT,
            "HACKBENCH_VERSION": __version__,
            "HACKBENCH_RESULTS_PATH": RESULTS_PATH,
            "HACKBENCH_SNAPSHOT_PATH": SNAPSHOT_PATH,
        }
    )
    # Reason: the default ignore drops non-Python files, which would lose profiles/*.toml.
    .add_local_python_source(APP_NAME, ignore=["**/__pycache__/**"])
    # Reason: a committed, derived-only fallback so `/v1/results` works before the first
    # `cycle` run (or Volume) exists.
    .add_local_file("data/results.snapshot.json", SNAPSHOT_PATH)
)
app = modal.App(APP_NAME)


# Reason: the Modal Secret carries HACKBENCH_BASE_URL (and later the API keys).
@app.function(
    image=image,
    secrets=[modal.Secret.from_name(APP_NAME)],
    volumes={DATA_MOUNT: data_volume},
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web() -> FastAPI:
    from hackbench.api import create_app

    return create_app(reload=data_volume.reload)


# Reason: only `cycle` needs the QC/agents stack (numpy, scikit-image, tifffile, anthropic);
# keeping `web`'s image light keeps its cold start fast.
cycle_image = image.pip_install(
    "imagecodecs>=2026.8.16",
    "numpy>=2.5.3",
    "scikit-image>=0.26.0",
    "tifffile>=2026.9.20",
    "anthropic>=1.11.0",
)


@app.function(
    image=cycle_image,
    secrets=[modal.Secret.from_name(APP_NAME)],
    volumes={DATA_MOUNT: data_volume},
    timeout=3600,
)
def cycle(with_claude: bool = False) -> dict[str, Any]:
    """Run the end-to-end cycle against the derived, pre-registered inputs an owner has
    already placed on the `hackbench-data` Volume at `/data/qc` (`modal volume put`, from a
    prior local `make qc`/`make qc-suite` run - never raw TIFFs). Writes `results.json`
    straight onto the Volume so `web` serves it live on its next request, no redeploy.
    """
    from hackbench.cycle import run_cycle

    result = run_cycle(Path(QC_INPUTS_DIR), Path(RESULTS_DIR), with_claude=with_claude)
    data_volume.commit()
    return result
