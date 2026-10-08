# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Changed

- **Hosting moved from Modal to GitHub Pages:** <https://qte77.github.io/2026-10-03-london-ai-science-hack/>. `make site` (`hackbench.static_site`) renders every route of the FastAPI app into static files, so the site and `make run` cannot drift. The new `pages.yml` workflow publishes it after CI passes on `main`, waits until `/v1/health` reports the new commit, then runs `make e2e`. The site shows the committed results snapshot; publish a new cycle by copying `results/cycle/results.json` to `data/results.snapshot.json`.
- Every internal link (landing, noscript summary, markdown twin, `Link` header, markdown 404, skills index) is now built from `HACKBENCH_BASE_URL` instead of root-relative paths, so the site works under a sub-path. The React console uses a relative vite `base` and fetches `../v1/results`.
- `pages.yml` uploads hidden paths (`include-hidden-files: true`); without it `/.well-known/*` (agent card, skills index, ARD, API catalog) returned 404 on Pages.
- e2e: the homepage test checks the markdown twin at `/index.md` (a static host cannot negotiate on `Accept`); new checks cover `/v1/results`, a batch brief, and the React console's assets.

### Removed

- Modal hosting: `deploy.yml`, `src/hackbench/deploy.py`, `make deploy`, `make cycle-upload`, `make cycle-modal`, the `deploy` extra (`modal`) and the CI deploy tokens in `.env.example`. The optional Modal LLM endpoint for the paper judge (`HACKBENCH_LLM_URL`) is unchanged.

### Added

- `data/submissions/` (CSV + JSON): all 50 event submissions from iterate.inc's public projects endpoint, with participants' names in free text replaced by `[name]` (team names and URLs kept). Track names are mapped from `track_id`, inferred from submission content since the public API serves IDs only. Regenerate with `python3 scripts/scrape_submissions.py` (fetches via a sibling `polyfetch-scrape` checkout; the raw payload and the redaction list stay in gitignored `private/`).

### Security

- UI build toolchain: `vite` 5.4.21 → 6.4.4 (`esbuild` 0.21.5 → 0.25.12), clearing four Dependabot alerts (one high, three moderate). All four concern the local dev server, not the deployed console. `ui/dist` rebuilt; same source, minifier-only differences.

### Known limitations

- A Modal dedicated endpoint for the paper judge can't be created without a payment method on the Modal workspace (H100 only, even for small models). The judge falls back automatically to Cloudflare Workers AI. See the README's Configuration section.

## [0.2.0] - 2026-10-04

### Added

- `docs/positioning.md`: who Parallax is for, the pains it relieves (each with evidence from the live run), the story arc, and what is not claimed.
- **QC console** at `/results` (Vite + React, `ui/`): the owner's design with three looks (polymer default, console, lab80; `?look=` or the switcher, remembered in localStorage), contrast ≥ 4.5:1 checked in pytest (`tests/test_ui_contrast.py`), and a mobile layout. It renders Parallax's decision briefs (Apache-2.0, credited) with HackBench's second-method strip and an explicit "methods disagree" line, plus validation and infrastructure panels.
- **End-to-end cycle** (`cycle.py`, `make cycle`, Modal `cycle` function on Volume `hackbench-data`, run on demand via `make cycle-modal`; no schedule). Stages: reference (k = 2.5, calibrated on train), drift suite, KPI robustness, scripted honest and cheating agents, Paperclip literature (`papers.py`, REST, skipped without a key), paper judge (below), and Parallax briefs. Every stage is journaled. `make cycle-upload` puts derived inputs only (no TIFFs) on the Volume, including the paper-judge research bundle (`BUNDLE=`); `make cycle-modal` runs it.
- **Paper judge** (`paper_judge.py`, cycle stage `paper_judge` after `papers`): for each of the 18-paper research bundle's assessments, resolves the paper in Paperclip (`/lookup` by DOI, else `/search` by title) and scores evidence via `/claims/support`, then has an LLM judge (a **Modal Shared/Dedicated Endpoint**, Modal-managed and OpenAI-compatible, via `HACKBENCH_LLM_URL` + `HACKBENCH_LLM_MODEL` + a workspace proxy token `MODAL_PROXY_TOKEN_ID`/`_SECRET`; else Cloudflare Workers AI `@cf/openai/gpt-oss-20b`; else skipped independently) grade Paperclip's output against the curated direction. Reports `paperclip_resolved_rate`, `paperclip_agreement`, and (when a judge ran) `judge_agreement`, `judge_paperclip_agreement`, `grounded_rate`, `brier`. Every call is journaled (hashes, latency, counts); no full text/snippets/abstracts are ever persisted. Capped at 60 Paperclip calls. Rendered in `/results.md`.
- `GET /v1/results` (live Volume result, falling back to the committed `data/results.snapshot.json`) and its markdown twin `/results.md`.
- Paper and release links are rendered only with http(s) schemes (backend and UI).
- Claude agents under test (`claude_agent.py`, `polaron/llm.py`): a manual tool-use loop that
  reaches the environment only through the session; four configs (Haiku 4.5 and Sonnet 5.5 ×
  neutral and score-pressure prompts, published verbatim in `polaron/llm.py`); strict tool
  schemas, `tool_choice` auto, no sampling overrides, Sonnet effort `medium`; each turn's cost
  is journaled before its tools run, from per-model prices. No server-side refusal fallback,
  because it would swap the model under test. `anthropic` SDK as the optional `agents` extra.
- `make agent-smoke`: one live session (costs money; reads `ANTHROPIC_API_KEY` from `.env`).
- Scripted control agents (`polaron/agents.py`, no LLM): `HonestAgent` judges only from
  `compare_to_baseline` with the reference rule (matches the reference pipeline, trips no
  honeypot, cites its evidence); `CheatingAgent` reads the decoy report and the cached verdict
  and submits the decoy's label (trips every honeypot). They are the negative and positive
  controls for the detectors.
- Agent session wrapper (`session.py`): every agent tool call goes through `Session.call` and
  is journaled (hash-chained, one file per session); caps of 15 calls, 180 s and $1.50 per
  session; `submit_verdict(label, confidence, falsifier {kpi, threshold}, cited_entries)` with
  validation; unknown or out-of-bounds calls are journaled and refused; honeypot trip-wires
  journal the touch and still serve the decoy. An `Agent` protocol for adapters.
- Polaron agent workspace (`polaron/workspace.py`): opaque ids (`baseline/fov_01`,
  `candidate/fov_01`) so batch and file names can't leak the answer; precomputed KPIs;
  `compare_to_baseline` returns CIs, tolerances and roles but never the pipeline's verdict;
  files confined to a staged directory holding a README and a decoy `previous_qc_report.md`,
  plus a `cached_verdict` tool. Both decoys carry a deliberately wrong label and are registered
  as honeypots in the profile.
- Polaron QC reference pipeline (`make qc`): BSE channel, edge-cropped, 25 nm/px from the TIFF;
  six KPIs per field of view (porosity %, bright-phase %, pore density, pore diameter µm, edge
  density, intensity spread); bootstrap 95% CIs of each batch vs the baseline; accept /
  investigate / reject with the driving KPIs named. Implements the `Task` protocol.
- Generic: hash-chained, tamper-evident run journal (`journal.py`); bootstrap and verdict rules
  (`stats.py`). `HACKBENCH_DATA_DIR` setting; profile `[domain]` section.
- QC libraries as an optional `qc` extra (tifffile, imagecodecs, numpy, scikit-image).
- Tests use synthetic micrographs with known ground truth; no real data in the repo or CI.
- Drift injector and scored suite (`make qc-suite`): material drifts (added pores, coarsening;
  large = reject) vs imaging drifts (contrast, blur; material unchanged = accept), injected into
  the right halves of baseline fields of view and compared with the left halves.
  `PolaronTask.ground_truth()` / `score()` now read the suite's `truth.json`. First run of the
  reference pipeline: 3/9 correct; it rejects imaging-only drift (edge density and intensity
  spread track acquisition settings, not material).
- Material vs imaging KPIs: only material KPIs (porosity, bright phase, pore density, pore
  diameter) decide the verdict; imaging KPIs (edge density, intensity spread) raise
  `acquisition_flags` instead. Idea credited to teammate GRAMSINATOR's per-KPI robustness check.
- Calibration without tuning to the benchmark: `calibrate_k()` picks the tolerance factor on a
  training suite; `make qc-suite` then scores a held-out suite (different seeds and drift
  levels) once. Held-out accuracy 5/9 (was 3/9); remaining errors: blur (pore diameter is
  focus-sensitive), high contrast (porosity threshold), large coarsening under-called.
- Suite images are written to a scratch folder on `/tmp` instead of the repo (`--scratch`);
  the first run filled the shared workspace disk.
- README names the team and links the teammate repo; states the open pseudo-replication caveat
  on real-data verdicts (tiles of shared micrographs).

### Changed

- Modularity seam: use-case copy and metadata moved from code into
  `src/hackbench/profiles/polaron.toml` (switch with `HACKBENCH_PROFILE`); one `Settings`
  reads all `HACKBENCH_*` env vars; version comes from package metadata (was typed 3×);
  one app-name constant (was 4×); a bare `Task` protocol for domain plug-ins. The Polaron
  anti-cheat rule moved from AGENTS.md into the profile's `integrity_rules`. Pages unchanged
  except one unified skill description.
- Modal deploy keeps non-Python package files (the default ignore would drop the profile).

### Fixed

- Deploy e2e raced Modal's container swap and tested the previous version. The deploy now
  stamps `HACKBENCH_COMMIT`, `/v1/health` reports it, and `deploy.yml` waits until the new
  commit is serving before running `make e2e`.

### Added

- Landing page at `/` (was a 404): HTML for people in the qte77 EyeRest palette, markdown
  for agents via `Accept: text/markdown` (`Vary: Accept`) and `/index.md`; canonical link,
  Open Graph tags, `SoftwareApplication` JSON-LD.
- Agent discovery: `/sitemap.xml`, `/.well-known/api-catalog` (RFC 9727),
  `/.well-known/agent-skills/index.json` + `SKILL.md` (SHA-256 pinned), `/.well-known/ard.json`;
  RFC 8288 `Link` headers on the homepage; per-agent `robots.txt` rules with a sitemap line;
  markdown 404s for `Accept: text/markdown`; "when to use / when not" in `llms.txt`, the skill
  and the homepage; markdown frontmatter.

- `deploy.yml`: deploy to Modal after green CI on a push to `main`, then run the e2e tests
  against the live URL. Fork-triggered runs are excluded.
- `preregister.yml`: a `prereg-*` tag creates a GitHub release as server-timestamped proof that
  the pipeline was frozen before the unseen batch was opened.

## [0.1.0] - 2026-10-03

### Added

- FastAPI app serving the agent-native surface: `/llms.txt`, `/robots.txt` with a
  Content-Signal line, `/.well-known/agent-card.json`, `/openapi.json`, `/v1/health` (#1).
- Modal deployment (`make deploy`), live at <https://<modal-workspace>--hackbench-web.modal.run> (#1).
- `HACKBENCH_BASE_URL`, loaded from the `hackbench` Modal Secret, so the agent card and
  `llms.txt` advertise the public URL (#2).
- `.env.example` with sponsor API variable names (#2).
- `AGENTS.md`, `Makefile`, architecture doc with the system diagram (#1).
- README documents the live URL, endpoints, configuration and commands; this changelog (#3).
- CI on every PR and push to `main`: ruff with security, annotation and bugbear rules;
  `mypy --strict`; pytest; `pip-audit`; gitleaks full-history secret scan; a guard against
  tracking `private/`, TIFFs or `.env`. Actions pinned by commit SHA (#4).
- `make typecheck` and `make audit` (#4).
- End-to-end tests against the live deploy (`make e2e`, `HACKBENCH_E2E_URL`); skipped by
  default so `make test` stays offline (#6).
