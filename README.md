# HackBench: London AI x Science Hackathon (2026-10-03)

[![CI](https://github.com/qte77/2026-10-03-london-ai-science-hack/actions/workflows/ci.yml/badge.svg)](https://github.com/qte77/2026-10-03-london-ai-science-hack/actions/workflows/ci.yml)

Science agents doing Polaron's battery-electrode QC, and the evals that tell you when to trust
them: correctness, reward hacking, calibration, falsification. Built during the
[London AI x Science Hackathon](docs/event.md), 3–4 Oct 2026.

**Status:** the agent-native surface is live. The QC pipeline and the drift suite with known
ground truth run locally (`make qc`, `make qc-suite`; held-out suite 5/9). Honeypots, agents and
the UI are in progress.

**Team:** built together with
[GRAMSINATOR/2026_10_03_hackathon_AI-X-SCIENCE](https://github.com/GRAMSINATOR/2026_10_03_hackathon_AI-X-SCIENCE)
(Track 4 QC core with a Streamlit dashboard). This repo is the evaluation layer. Coordination
happens in that repo's issues.

**Caveat on real-data verdicts:** the fields of view appear to be tiles of fewer, larger
micrographs, some spanning several batch folders. Until the tile-to-micrograph mapping is
applied, real-data verdicts treat tiles as independent and may be overconfident. The synthetic
drift suite is not affected.

## Live

<https://thismay52--hackbench-web.modal.run>

| Path | For | What |
|---|---|---|
| `/` | people + agents | Landing page; `Accept: text/markdown` returns markdown instead |
| `/index.md` | agents | Markdown version of the landing page |
| `/llms.txt` | agents | Project summary and links |
| `/robots.txt` | crawlers | Per-agent allow rules, `Content-Signal: search=yes, ai-input=yes, ai-train=no`, sitemap |
| `/sitemap.xml` | crawlers | Indexable pages with `lastmod` |
| `/.well-known/api-catalog` | agents | RFC 9727 API catalog (`application/linkset+json`) |
| `/.well-known/agent-skills/index.json` | agents | Agent skills index; the `hackbench` `SKILL.md` is pinned by SHA-256 |
| `/.well-known/ard.json` | agents | Agentic Resource Discovery catalog |
| `/.well-known/agent-card.json` | agents (A2A) | Agent card with the `evaluate-qc-verdict` skill |
| `/openapi.json` | agents | REST schema |
| `/v1/health` | anyone | `{"status": "ok", "commit": "<git SHA of the deployed code>"}` |

## Quick start

| Command | What |
|---|---|
| `make install` | `uv sync --all-extras` (app, dev tools, Modal CLI, QC libraries) |
| `make validate` | Lint (incl. security rules), format check, `mypy --strict`, tests; run before pushing |
| `make audit` | Dependency vulnerability scan (`pip-audit`) |
| `make qc` | Reference QC pipeline on `HACKBENCH_DATA_DIR`: KPIs per field of view, bootstrap CIs vs the baseline batch, accept / investigate / reject; writes `results/` (git-ignored) |
| `make qc-suite` | Builds a **training** and a **held-out** synthetic drift suite from the baseline (material vs imaging drift, known truth), chooses the tolerance `k` on training only, scores the held-out suite once; images go to `/tmp/hackbench-scratch` (`--scratch`), results to `results/suite.json` |
| `make e2e` | End-to-end tests against the live deploy (`HACKBENCH_E2E_URL` overrides the target) |
| `make run` | Serve locally at <http://localhost:8000> |
| `make deploy` | Deploy to Modal |

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `HACKBENCH_BASE_URL` | Modal Secret `hackbench`; local `.env` | Public URL the agent card and `llms.txt` advertise (default `http://localhost:8000`) |
| `HACKBENCH_PROFILE` | Modal Secret `hackbench`; local `.env` | Use-case profile in `src/hackbench/profiles/` (default `polaron`) |
| `HACKBENCH_DATA_DIR` | shell / `.env` | Folder of batch subfolders with SEM TIFFs for `make qc` (default `data/polaron`, git-ignored) |
| `HACKBENCH_COMMIT` | set by `make deploy` / CI | Commit reported by `/v1/health` |
| `HACKBENCH_E2E_URL` | shell, when running `make e2e` | Deployment the e2e tests target (default: the live URL above) |
| Sponsor API keys | local `.env` | See [`.env.example`](.env.example) |

One-time Modal setup:

```sh
uv run modal token new                                            # writes ~/.modal.toml
uv run modal secret create hackbench --from-dotenv .env --force   # app config + keys
make deploy
```

## CI/CD

| Workflow | Trigger | What |
|---|---|---|
| `ci.yml` | PR, push to `main` | Lint, strict typecheck, tests, `pip-audit`, gitleaks, tracking guard |
| `deploy.yml` | CI green on a push to `main`; manual | `make deploy`, then `make e2e` against the live URL |
| `preregister.yml` | push of a `prereg-*` tag | GitHub release whose server timestamp proves the pipeline was frozen first |

Deploy needs repo secrets `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` and repo variable
`HACKBENCH_BASE_URL`.

## Docs

- [Architecture](docs/architecture.md): system diagram, both surfaces, how it serves each track
- [Changelog](CHANGELOG.md)
- [Event facts](docs/event.md): format, tracks, prizes, judging
- [Application draft](docs/application-draft.md): Luma application questions and answers
- [AGENTS.md](AGENTS.md): rules for coding agents working here
