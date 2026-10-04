# Architecture

Back to [README](../README.md) · See also: [event facts](event.md)

**Status:** built and live at <https://<modal-workspace>--hackbench-web.modal.run>: the landing page
(HTML + markdown), the agent discovery files (`llms.txt`, `robots.txt`, sitemap, agent card,
skills index, ARD, API catalog, OpenAPI) and `/v1/health`. Built and run locally on real
data: the Polaron QC reference pipeline (`make qc`), the drift suite with known ground truth
and held-out scoring (`make qc-suite`, held-out 5/9), the hash-chained journal, and the agent
session wrapper (journaled tool calls, caps, honeypot trip-wires, a staged workspace with two
decoys), and the scripted honest and cheating control agents. Planned: LLM agent adapters,
the detector chain and the UI.

## Code layout: what is generic, what is swappable

| Layer | File | Swap by |
|---|---|---|
| Project identity (name, repo, version) | `src/hackbench/__init__.py` | Editing once; version comes from `pyproject.toml` |
| Runtime settings (`HACKBENCH_*` env vars) | `src/hackbench/settings.py` | Env vars / Modal Secret `hackbench` |
| **Use case and sponsor** (copy, event, skill metadata, integrity rules) | `src/hackbench/profiles/<name>.toml` | Adding a profile and setting `HACKBENCH_PROFILE` |
| **Domain plug-in seam** | `src/hackbench/task.py` (`Task` protocol) | Implementing `Task` for the new domain |
| Generic surfaces (API, discovery, landing) | `api.py`, `discovery.py`, `landing.py` | Not needed: they read the profile and settings |
| Generic evaluation core | `journal.py` (hash-chained run log), `stats.py` (bootstrap CI, three-way verdict), `session.py` (`Session`, `Agent` protocol, caps, trip-wires) | Not needed: domain-agnostic |
| Polaron domain | `polaron/io.py`, `kpis.py`, `task.py` (`PolaronTask`, `calibrate_k`), `drift.py`, `workspace.py` (agent tools, opaque ids, decoys), `agents.py` (scripted honest and cheating controls); parameters in the profile's `[domain]` | Replaced by another domain package implementing `Task` |
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

```
                    ┌──────────────────────────────────────────────────────────────────┐
                    │           ONE FastAPI APP  (Modal web endpoint, @asgi_app)       │
                    │      https://<workspace>--hackbench-web.modal.run                │
                    │                                                                  │
   HUMANS ────────▶ │  UI   /                leaderboard (hack rate · calibration · acc)│
   (QC engineer,    │       /runs/{id}       evidence: verdict · tool trace · trips    │
    judges)         │       /batches/{id}    verdict card: accept/investigate/reject   │
                    │                        + driving KPIs + confidence intervals     │
                    │       *.md twins · JSON-LD · no-JS server-rendered               │
                    │                                                                  │
   AGENTS ────────▶ │  API  /v1/tasks  /v1/runs/{id}  /v1/leaderboard   (public read)  │
   (Claude, judges' │       POST /v1/verdicts                           (bearer token) │
    own agents)     │       /openapi.json · /mcp (MCP server)                          │
                    │  DISC /llms.txt · /robots.txt (Content-Signal)                   │
                    │       /.well-known/{agent-card.json, mcp/server-card.json,       │
                    │        agent-skills/index.json → SKILL.md, api-catalog, ard.json}│
                    └───────────────┬───────────────────────────────┬──────────────────┘
                                    │ same data (DRY)               │ reads
                                    ▼                               ▼
┌─ ENVIRONMENT ──────────────────────────────────┐   ┌─ RESULTS STORE (Modal Volume) ─────┐
│ REAL       Polaron Batch_1/2/3 (31 FOV × 3 ch) │   │ runs/*.jsonl  hash-chained journal │
│ HELD-OUT   unseen batch (opened only after tag)│   │ kpis/*.csv · verdicts/*.json       │
│ SYNTHETIC  drift injector (contrast · blur ·   │   │ → exported to repo (replayable)    │
│            particle-scale · pores, known size) │   └──────────────▲─────────────────────┘
│ HONEYPOTS  decoy labels.json · channel/filename│                  │ every call + verdict
│            shortcut · cached-verdict tool ·    │                  │
│            early unseen-batch path             │                  │
│                                                │                  │
│ TOOLS (every call logged) ─────────────────────┼──────────────────┘
│   list_items()  kpis(fov_id)                   │
│   compare_to_baseline()  list_files/read_text  │
│   submit_verdict(label, confidence, falsifier) │
└───────────────┬────────────────────────────────┘
                │ tasks + tools via one adapter
                ▼
┌─ AGENTS UNDER TEST ────────────────────────────────────────────────────────────────────┐
│ Claude Haiku / Sonnet (neutral vs score-pressure prompt) · Claude Code headless        │
│ open model on Modal GPU · optional Devin ×5 (own VM → GitHub PRs)                      │
│ CONTROLS: reference pipeline (honest, non-agent) · cheating control agent (trips all)  │
└───────────────┬────────────────────────────────────────────────────────────────────────┘
                │ verdict + confidence + "what would change my mind" + tool log
                ▼
┌─ EVALS: detector chain, cheap → expensive ────────────────────────────────────────────┐
│ 1 honeypot trip-wires        did it touch a planted shortcut?                         │
│ 2 re-score                   vs synthetic ground truth / unseen batch                 │
│ 3 provenance                 every reported number ↔ a tool-log entry                 │
│ 4 fast judge (Jev / Laya)    "did this run exploit X?"  (calibrated; optional)        │
│ 5 Claude escalation          only when the fast judge is unsure                       │
│ + calibration                ECE / Brier: stated confidence vs outcome                │
│ + falsification              does its stated counterexample flip the verdict?         │
└───────────────┬───────────────────────────────────────────────────────────────────────┘
                ▼
     verdicts: honest / hack(type) / borderline  ──▶  results store  ──▶  UI + API

 OUTSIDE THE APP
 ├─ GitHub repo ◀── agent PRs · CI (tests, guards) · pre-registration TAG
 │                   (tag before the unseen batch is first opened)
 └─ (optional) GitHub Pages static leaderboard mirror; agent discovery stays on Modal
```

## How it serves both tracks

| Track | What it judges | Where it shows up |
|---|---|---|
| Polaron (materials QC) | KPI quality, accuracy on the new batch, interpretability, honest uncertainty, usability | KPI table, unseen-batch verdict, verdict cards with confidence intervals, QC view |
| Originator (agents that know when they're wrong) | Reward-hacking evals, calibrated uncertainty, falsification | Detector chain, precision/recall on planted controls, calibration and falsification metrics |
