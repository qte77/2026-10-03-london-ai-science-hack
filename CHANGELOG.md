# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added

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
- Modal deployment (`make deploy`), live at <https://thismay52--hackbench-web.modal.run> (#1).
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
