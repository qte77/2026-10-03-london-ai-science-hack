# HackBench: London AI x Science Hackathon (2026-10-03)

Science agents doing Polaron's battery-electrode QC, and the evals that tell you when to trust
them: correctness, reward hacking, calibration, falsification. Built during the
[London AI x Science Hackathon](docs/event.md), 3–4 Oct 2026.

**Status:** skeleton. The agent-native surface is live locally; the QC tools and evals are in
progress.

## Quick start

```sh
make install   # uv sync
make test      # pytest
make run       # http://localhost:8000/llms.txt
make deploy    # Modal (run `uv run modal token new` once)
```

Copy [`.env.example`](.env.example) to `.env` for sponsor API keys.

## Docs

- [Architecture](docs/architecture.md): system diagram, both surfaces, how it serves each track
- [Event facts](docs/event.md): format, tracks, prizes, judging
- [Application draft](docs/application-draft.md): Luma application questions and answers
- [AGENTS.md](AGENTS.md): rules for coding agents working here
