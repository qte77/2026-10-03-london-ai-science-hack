# AGENTS.md

Instructions for coding agents (Claude Code, Devin, others) working in this repo. Humans: start
with [README.md](README.md).

## What this is

HackBench: science agents doing Polaron's battery-electrode QC, and the evals that tell you when
to trust them. Architecture: [docs/architecture.md](docs/architecture.md).

## Commands

`make help` lists everything. Before pushing, run `make validate` (lint + tests). `make run`
serves locally; `make deploy` deploys to Modal.

## Rules

- **Hackathon rule:** build everything during the event. Never copy code from other repos; only
  use credited open-source libraries.
- **Test first:** write the failing test, then the code. Non-trivial modules only.
- **Never commit** raw TIFFs, `.env`, keys, or anything under `private/`.
- **Never use detector-channel presence or filenames as features.** The channel mix differs by
  batch; that is a planted shortcut, not microstructure.
- **The unseen batch stays closed until the pre-registration git tag exists.**
- Every agent tool call and verdict is logged to the run journal; never report a number that
  isn't in it.
- Work on a branch and open a PR; never push to `main` directly from an agent session.
