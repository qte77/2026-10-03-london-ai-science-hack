# AGENTS.md

Instructions for coding agents (Claude Code, Devin, others) working in this repo. Humans: start
with [README.md](README.md).

## What this is

HackBench: science agents doing Polaron's battery-electrode QC, and the evals that tell you when
to trust them. Architecture: [docs/architecture.md](docs/architecture.md).

## Commands

`make help` lists everything. Before pushing, run `make validate` (lint + tests). `make run`
serves locally; `make site` pre-renders the static site that the Pages workflow publishes.

## Rules

- **Hackathon rule:** build everything during the event. Never copy code from other repos; only
  use credited open-source libraries.
- **Test first:** write the failing test, then the code. Non-trivial modules only.
- **Never commit** raw TIFFs, `.env`, keys, or anything under `private/`.
- **Follow the active use case's `integrity_rules`** in `src/hackbench/profiles/<name>.toml`
  (default `polaron`). They name the domain shortcuts that count as cheating.
- **Pre-registration:** before opening any held-out data, push a `prereg-*` tag;
  `preregister.yml` turns it into a server-timestamped release.

## Where things live

- Project identity (name, repo, version): `src/hackbench/__init__.py`
- Runtime settings (`HACKBENCH_*` env vars): `src/hackbench/settings.py`, the only reader
- Use-case copy and metadata: `src/hackbench/profiles/<name>.toml`; swap with `HACKBENCH_PROFILE`
- Domain plug-in seam: the `Task` protocol in `src/hackbench/task.py`
- Domain-agnostic code (API, discovery, landing) must not hard-code use-case text.
- Every agent tool call and verdict is logged to the run journal; never report a number that
  isn't in it.
- Work on a branch and open a PR; never push to `main` directly from an agent session.
