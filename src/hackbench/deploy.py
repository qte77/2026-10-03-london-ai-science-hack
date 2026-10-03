"""Modal deployment: one ASGI app owns the whole host, so root files like /llms.txt work.

Deploy with `make deploy`. Pattern per Modal's web-functions guide (checked 2026-10-03).
"""

import modal

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]>=0.115")
    .add_local_python_source("hackbench")
)
app = modal.App("hackbench")


@app.function(image=image)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web():
    from hackbench.api import create_app

    return create_app()
