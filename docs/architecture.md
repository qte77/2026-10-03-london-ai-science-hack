# Architecture

Back to [README](../README.md) · See also: [event facts](event.md)

**Status (4 Oct 2026, `main` @ `e9fc4c7`):** live at <https://<modal-workspace>--hackbench-web.modal.run>.
Parallax (the teammate's QC) decides on each batch; HackBench checks whether those decisions,
and the agents making them, can be trusted. Both run in one Modal cycle and are served from one
URL. Last recorded run: [runs/2026-10-04-e2e.md](runs/2026-10-04-e2e.md).

```
   GitHub ── CI green ──▶ auto-deploy
                              │
                              ▼
  ┌───────────────────────── Modal: app "hackbench" ─────────────────────────┐
  │                                                                          │
  │   Volume                     Cycle (on demand, 7 stages)                 │
  │   ┌──────────────────┐      ┌──────────────────────────────────────┐     │
  │   │ derived inputs   │─────▶│ Parallax briefs  (teammate QC)       │     │
  │   │ Parallax briefs  │      │        +                             │     │
  │   │ suite.json       │      │ HackBench evals:                     │     │
  │   │  (precomputed by │      │   reference verdict                  │     │
  │   │  make qc-suite)  │      │   drift suite     (precomputed)      │     │
  │   │                  │      │   KPI robustness  (precomputed)      │     │
  │   │                  │      │   agents vs honeypots (scripted)     │     │
  │   │                  │      │   paper judge ───────────────────────┼──┐  │
  │   │ results.json     │◀─────│ → results + hash-chained journal     │  │  │
  │   └────────┬─────────┘      └──────────────────────────────────────┘  │  │
  │            │                                                          │  │
  │            ▼                                                          │  │
  │   Web (FastAPI)  https://<modal-workspace>--hackbench-web.modal.run           │  │
  │     /            Parallax console                                     │  │
  │     /results/    Parallax + HackBench side by side                    │  │
  │     /v1/results  everything as JSON (agents)                          │  │
  └───────────────────────────────────────────────────────────────────────┼──┘
                                                                          │
                                    ┌─────────────────────────────────────┴──┐
                                    ▼                                        ▼
                          GXL Paperclip (literature)        Cloudflare Workers AI (LLM judge)
```

**Flow:** derived inputs and Parallax briefs sit on the Modal Volume (no raw images). The cycle
runs on demand (`make cycle-modal`), calls Paperclip and Workers AI, and writes `results.json`
with a hash-chained journal. The drift suite and KPI robustness are precomputed locally from the
raw images (`make qc-suite`) and only summarised by the cycle; the scripted agents re-run each
cycle (live Claude configs need `--with-claude`). The web function reads it per request (falling back to a committed
snapshot) and serves people and agents from one URL. GitHub CI gates every merge, then
auto-deploys to Modal; `/v1/health` reports the live commit.

## Code layout: what is generic, what is swappable

| Layer | File | Swap by |
|---|---|---|
| Project identity (name, repo, version) | `src/hackbench/__init__.py` | Editing once; version comes from `pyproject.toml` |
| Runtime settings (`HACKBENCH_*` env vars) | `src/hackbench/settings.py` | Env vars / Modal Secret `hackbench` |
| **Use case and sponsor** (copy, event, skill metadata, integrity rules) | `src/hackbench/profiles/<name>.toml` | Adding a profile and setting `HACKBENCH_PROFILE` |
| **Domain plug-in seam** | `src/hackbench/task.py` (`Task` protocol) | Implementing `Task` for the new domain |
| Generic surfaces (API, discovery, landing) | `api.py`, `discovery.py`, `landing.py` | Not needed: they read the profile and settings |
| Generic evaluation core | `journal.py` (hash-chained run log), `stats.py` (bootstrap CI, three-way verdict), `session.py` (`Session`, `Agent` protocol, caps, trip-wires), `claude_agent.py` (Claude tool-use loop, prices) | Not needed: domain-agnostic |
| Polaron domain | `polaron/io.py`, `kpis.py`, `task.py` (`PolaronTask`, `calibrate_k`), `drift.py`, `workspace.py` (agent tools, opaque ids, decoys), `agents.py` (scripted honest and cheating controls), `llm.py` (tool schemas, prompts, the four Claude configs); parameters in the profile's `[domain]` | Replaced by another domain package implementing `Task` |
| Deployment | `src/hackbench/deploy.py` | Commit and version are baked into the image |

Planned components split the same way. The detector chain, calibration and falsification
evals, agent adapters, sessions, router and UI are generic and call `Task`. Honeypots are
Polaron-specific and live behind `Task`, like the KPIs and the drift injector.

**Evaluation discipline:** tolerances are calibrated on a training drift suite and reported only
on a held-out suite (different seeds and drift levels), so the benchmark is never tuned to the
numbers it reports.

**Known limitation:** real fields of view are treated as independent samples. They appear to be
tiles of fewer parent micrographs, some spanning batch folders, so real-data confidence intervals
may be too narrow until the teammate repo's tile-to-micrograph mapping becomes the statistical
unit.

## How it serves both tracks

| Track | What it judges | Where it shows up |
|---|---|---|
| Polaron (materials QC) | KPI quality, accuracy on the new batch, interpretability, honest uncertainty, usability | KPI table, unseen-batch verdict, verdict cards with confidence intervals, QC view |
| Originator (agents that know when they're wrong) | Reward-hacking evals, calibrated uncertainty, falsification | Detector chain, precision/recall on planted controls, calibration and falsification metrics |
