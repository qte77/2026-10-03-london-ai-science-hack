# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added

- Landing page at `/` (was a 404): HTML for people in the qte77 EyeRest palette, markdown
  for agents via `Accept: text/markdown` (`Vary: Accept`) and `/index.md`; canonical link,
  Open Graph tags, `SoftwareApplication` JSON-LD.

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
