"""Modal deployment: one ASGI app owns the whole host, so root files like /llms.txt work.

Deploy with `make deploy`. Pattern per Modal's web-functions guide (checked 2026-10-03).
"""

import modal
from fastapi import FastAPI

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]>=0.115")
    .add_local_python_source("hackbench")
)
app = modal.App("hackbench")


# Reason: the "hackbench" Modal Secret carries HACKBENCH_BASE_URL (and later the API keys).
@app.function(image=image, secrets=[modal.Secret.from_name("hackbench")])
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web() -> FastAPI:
    from hackbench.api import create_app

    return create_app()
