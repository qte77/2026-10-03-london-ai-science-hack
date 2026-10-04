"""Parallax: find what to measure next. HackBench (this package) is its trust and evaluation layer.

Project identity lives here; use-case copy lives in `profiles/<name>.toml`.
"""

import os
from importlib.metadata import PackageNotFoundError, version

APP_NAME = "hackbench"
DISPLAY_NAME = "Parallax"
REPO_URL = "https://github.com/qte77/2026-10-03-london-ai-science-hack"

try:
    __version__ = version(APP_NAME)
except PackageNotFoundError:
    # Reason: in the Modal container the package is copied as source; deploy.py bakes this in.
    __version__ = os.environ.get("HACKBENCH_VERSION", "unknown")
