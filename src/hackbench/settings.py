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
    # Reason: the built React console; Modal overrides this to where `deploy.py` copies it.
    ui_dir: str = "ui/dist"
    # Reason: base URL of an OpenAI-compatible LLM judge endpoint for the paper_judge cycle
    # stage; empty means unset, so the judge sub-stage self-reports skipped rather than failing.
    llm_url: str = ""
    # Reason: a Modal Shared/Dedicated Endpoint (Modal-managed, OpenAI-compatible) needs the
    # model name and a workspace proxy token, sent as `Bearer <id>.<secret>`.
    llm_model: str = ""
    modal_proxy_token_id: str = ""
    modal_proxy_token_secret: str = ""
    # Reason: Paperclip API key for paper_judge's resolve/claims-support calls; empty means
    # unset, so the whole paper_judge stage self-reports skipped rather than failing.
    paperclip_api_key: str = ""
    # Reason: Cloudflare Workers AI is the judge fallback when the Modal vLLM endpoint is
    # unset; empty means unset, so that fallback self-reports skipped rather than failing.
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""

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
            ui_dir=os.environ.get("HACKBENCH_UI_DIR", defaults.ui_dir),
            llm_url=os.environ.get("HACKBENCH_LLM_URL", defaults.llm_url).rstrip("/"),
            llm_model=os.environ.get("HACKBENCH_LLM_MODEL", defaults.llm_model),
            modal_proxy_token_id=os.environ.get("MODAL_PROXY_TOKEN_ID", ""),
            modal_proxy_token_secret=os.environ.get("MODAL_PROXY_TOKEN_SECRET", ""),
            paperclip_api_key=(
                os.environ.get("PAPERCLIP_API_KEY") or os.environ.get("GXL_API_KEY") or ""
            ),
            cloudflare_account_id=os.environ.get(
                "CLOUDFLARE_ACCOUNT_ID", defaults.cloudflare_account_id
            ),
            cloudflare_api_token=os.environ.get(
                "CLOUDFLARE_API_TOKEN", defaults.cloudflare_api_token
            ),
        )
