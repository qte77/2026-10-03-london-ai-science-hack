# Architecture

Back to [README](../README.md) · See also: [event facts](event.md)

**Status (8 Oct 2026):** live at <https://qte77.github.io/2026-10-03-london-ai-science-hack/>,
a static pre-render of the app on GitHub Pages (hosting moved from Modal on 8 Oct).
Parallax (the teammate's QC) decides on each batch; HackBench checks whether those decisions,
and the agents making them, can be trusted. Both run in one cycle and are served from one URL.
Last recorded run: [runs/2026-10-04-e2e.md](runs/2026-10-04-e2e.md).

```
  Local machine                                  GitHub
  ┌──────────────────────────────────────┐      ┌─────────────────────────────────────────┐
  │ derived inputs, Parallax briefs,     │      │ CI green on main                        │
  │ suite.json (make qc / make qc-suite) │      │   │                                     │
  │            │                         │      │   ▼                                     │
  │            ▼                         │      │ Pages workflow                          │
  │ Cycle (make cycle, 7 stages)         │      │   make site: every app route rendered   │
  │   Parallax briefs (teammate QC)      │      │   through FastAPI into _site/           │
  │   + HackBench evals: reference,      │      │   │                                     │
  │   drift suite, KPI robustness        │      │   ▼                                     │
  │   (precomputed), agents vs honeypots │      │ GitHub Pages                            │
  │   (scripted), paper judge ───────────┼──┐   │   /            Parallax console         │
  │   → results + hash-chained journal   │  │   │   /results/    Parallax + HackBench     │
  │            │                         │  │   │   /v1/results  everything as JSON       │
  │            ▼                         │  │   │   /v1/health   built commit             │
  │ data/results.snapshot.json ──commit──┼──┼──▶│                                         │
  └──────────────────────────────────────┘  │   └─────────────────────────────────────────┘
                                            │
                     ┌──────────────────────┴───────────────┐
                     ▼                                      ▼
           GXL Paperclip (literature)        Cloudflare Workers AI (LLM judge)
```

**Flow:** the cycle runs locally (`make cycle`) on derived inputs and Parallax briefs (no raw
images), calls Paperclip and Workers AI, and writes `results/cycle/results.json` with a
hash-chained journal. The drift suite and KPI robustness are precomputed from the raw images
(`make qc-suite`) and only summarised by the cycle; the scripted agents re-run each cycle (live
Claude configs need `--with-claude`). Publishing a run means copying that file to
`data/results.snapshot.json` and merging to `main`. GitHub CI gates every merge; the Pages
workflow then renders every route of the FastAPI app into static files with the Pages URL as
`HACKBENCH_BASE_URL`, deploys, and runs the e2e tests once `/v1/health` reports the new commit.
During the event (3–4 Oct) the same app ran on Modal and read results from a Modal Volume.

## Code layout: what is generic, what is swappable

| Layer | File | Swap by |
|---|---|---|
| Project identity (name, repo, version) | `src/hackbench/__init__.py` | Editing once; version comes from `pyproject.toml` |
| Runtime settings (`HACKBENCH_*` env vars) | `src/hackbench/settings.py` | Env vars / local `.env` |
| **Use case and sponsor** (copy, event, skill metadata, integrity rules) | `src/hackbench/profiles/<name>.toml` | Adding a profile and setting `HACKBENCH_PROFILE` |
| **Domain plug-in seam** | `src/hackbench/task.py` (`Task` protocol) | Implementing `Task` for the new domain |
| Generic surfaces (API, discovery, landing) | `api.py`, `discovery.py`, `landing.py` | Not needed: they read the profile and settings |
| Generic evaluation core | `journal.py` (hash-chained run log), `stats.py` (bootstrap CI, three-way verdict), `session.py` (`Session`, `Agent` protocol, caps, trip-wires), `claude_agent.py` (Claude tool-use loop, prices) | Not needed: domain-agnostic |
| Polaron domain | `polaron/io.py`, `kpis.py`, `task.py` (`PolaronTask`, `calibrate_k`), `drift.py`, `workspace.py` (agent tools, opaque ids, decoys), `agents.py` (scripted honest and cheating controls), `llm.py` (tool schemas, prompts, the four Claude configs); parameters in the profile's `[domain]` | Replaced by another domain package implementing `Task` |
| Static site (GitHub Pages) | `src/hackbench/static_site.py`, `.github/workflows/pages.yml` | Pointing `HACKBENCH_BASE_URL` at another host; the routes are rendered by the app itself |

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
