"""Modal deployment: one ASGI app owns the whole host, so root files like /llms.txt work.

Deploy with `make deploy`. Pattern per Modal's web-functions guide (checked 2026-10-03).
"""

import os

import modal
from fastapi import FastAPI

from hackbench import APP_NAME, __version__

# Reason: bake the deployed commit and version into the image; in the container the package
# is copied as source (not installed), so package metadata is unavailable there.
COMMIT = os.environ.get("HACKBENCH_COMMIT", "local")

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]>=0.115")
    .env({"HACKBENCH_COMMIT": COMMIT, "HACKBENCH_VERSION": __version__})
    # Reason: the default ignore drops non-Python files, which would lose profiles/*.toml.
    .add_local_python_source(APP_NAME, ignore=["**/__pycache__/**"])
)
app = modal.App(APP_NAME)


# Reason: the Modal Secret carries HACKBENCH_BASE_URL (and later the API keys).
@app.function(image=image, secrets=[modal.Secret.from_name(APP_NAME)])
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web() -> FastAPI:
    from hackbench.api import create_app

    return create_app()
