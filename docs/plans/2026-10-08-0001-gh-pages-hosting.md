# Plan 0001: host on GitHub Pages, drop Modal, scrub the Modal workspace name from history

**Status (8 Oct 2026):** Phase A (agent) is in PR `feat/gh-pages`. Phase B (owner) and Phase C
(agent) are open; see [Remaining work](#remaining-work), the only list of open items.

## Where things stand

- **Shipped in `feat/gh-pages`:**
  - `hackbench.static_site` and `make site` pre-render every app route into `_site/`.
  - `pages.yml` publishes to <https://qte77.github.io/2026-10-03-london-ai-science-hack/>.
  - Links follow `HACKBENCH_BASE_URL`, so the site works under a sub-path.
  - The React console is relative.
  - Modal hosting is removed.
  - The workspace name is gone from the tree.
- **Verified before merge:**
  - `make validate` passes.
  - e2e passes 8/9 against a local static server under a sub-path; `test_served_over_https` can only pass on the real host.
  - Both consoles render on desktop and mobile with no console errors or failed requests.
- **Not yet verified:** the live Pages site (row A2).
- **The loop:** merge → `pages.yml` builds, deploys, waits for `/v1/health` to report the commit,
  then runs `make e2e` → check the live site in a browser.

## Decisions (defaults applied; the owner may override)

| Decision | Default taken | Why |
|---|---|---|
| Link style | Absolute, from `HACKBENCH_BASE_URL` | That setting already drove the canonical, agent-card and llms.txt URLs; one rule, no new setting |
| Results on Pages | Committed snapshot (`data/results.snapshot.json`) | A static host has no Volume; publishing a run means committing it |
| Cycle on Modal | Removed (`make cycle` runs locally) | Its only consumer was the Modal web app |
| Paper-judge Modal LLM endpoint | Kept | It is an LLM provider option, not hosting, and carries no workspace name |
| `reload` hook in `create_app` | Kept | Generic and tested; harmless without Modal |
| Replacement text in the rewrite | `<modal-workspace>` | Already used in the historical records in the tree |

## Remaining work

| # | Item | Gate | Done when |
|---|---|---|---|
| A1 | Merge `feat/gh-pages` | owner | PR merged; `pages.yml` run green, including the e2e job |
| A2 | Browser check of the live Pages site: `/` and `/results/`, desktop and mobile, looks, batch switch | agent | No console errors or failed requests; screenshots taken |
| B1 | Stop the Modal app and delete its secret: `modal app stop hackbench`, `modal secret delete hackbench`, and the Volume `hackbench-data` if unwanted | owner | The old URL no longer answers |
| B2 | After A1: delete repo secrets `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, and repo variable `HACKBENCH_BASE_URL` (its value is the old Modal URL). `deploy.yml` reads it until A1 merges | owner | `gh secret list` and `gh variable list` don't show them |
| B2b | After A1: delete the logs of the 33 runs of the removed "Deploy" workflow. Each step's log prints the old URL from that variable | owner | `gh run list --workflow Deploy` is empty |
| B3 | Run the rewrite (`private/rewrite/rewrite.sh`, after A1), review the report, then force-push `main` and all tags from the rewritten mirror | owner | 0 occurrences in blobs and messages; remote refs match `refs-after.txt` |
| B4 | Re-point the 3 releases to the rewritten tags; add the rewrite note to `prereg-2026-10-04-unseen` | owner | Each release shows the new tag; the prereg note lists old → new commit |
| B5 | GitHub Support: purge cached views and `refs/pull/*` that still hold the old commits | owner | Support confirms |
| ~~C1~~ | ~~Edit PR, issue and release text on GitHub that still names the workspace~~: **done 8 Oct**. PR #2 and #6 descriptions and the v0.1.0 and v0.2.0 notes now use `<modal-workspace>`; no issue, PR or review comment had it (`private/rewrite/scrub_github_text.sh`) | agent | Searching the repo's issues and PRs finds 0 |
| C2 | Reset local clones to the rewritten history | agent | `git log --all` in each clone has 0 occurrences |
| C3 | Ask the teammate (GRAMSINATOR) to drop the old URL from their repo, if it appears there | owner | Their README no longer has it |

## Source map

- **Static export:** `src/hackbench/static_site.py`
  - `ROUTES` maps each route to a file; `/` → `index.html`, `/about` → `about/index.html`.
  - The console's `assets/` and `data/` and `ui/dist` → `results/` are copied first.
  - Per-batch `data/<batch>/brief.json` comes from the results.
  - Writes `.nojekyll`.
  - Tests: `tests/test_static_site.py`.
- **Link rule:**
  - `src/hackbench/landing.py`: `AGENT_LINKS`, `CONSOLE_PATH`, `render_*`, `head_meta`.
  - `src/hackbench/discovery.py`: `link_header(base)`, `markdown_404(base)`, the skills-index `url`.
  - `src/hackbench/api.py` passes `s.base_url`.
- **React console:** `ui/vite.config.js` `base: "./"`; `ui/src/lib/fetchResults.js` `RESULTS_URL = "../v1/results"`. Rebuild with `npm run build` in `ui/` and commit `ui/dist`.
- **Workflow:** `.github/workflows/pages.yml`.
  - Jobs: build (`configure-pages` gives the base URL), deploy, e2e.
  - Actions are pinned by SHA: configure-pages v6.0.0, upload-pages-artifact v5.0.0, deploy-pages v5.0.1.
  - Pages is already enabled with build type "workflow".
- **e2e:** `tests/e2e/test_live.py`; `Makefile` `e2e` defaults to the Pages URL.
- **History rewrite (gitignored, never commit):** `private/rewrite/`.
  - `replacements.txt` holds the literal name.
  - `rewrite.sh` mirror-clones, drops `refs/pull/*`, runs `git filter-repo --replace-text --replace-message`, and writes `commit-map.txt` and `refs-before/after.txt`.
  - Dry run on 8 Oct: 43 commits, 3 annotated tags rewritten, 0 occurrences left.

## Watch-outs

- **The pre-registration proof weakens.** After B3, `prereg-2026-10-04-unseen` points at a commit
  pushed on rewrite day. The B4 note must state the old and new commit and that only the
  workspace name changed.
- **Pages limits:** there is no `Accept` negotiation at `/` (agents use `/index.md`).
  Extensionless files (`/v1/results`, `/v1/health`) may not be served as `application/json`
  (UNVERIFIED until A2). `/robots.txt` and `/.well-known/` sit under the sub-path, not at the host root.
- **Push from the rewritten mirror only** with `env -u GH_TOKEN -u GITHUB_TOKEN`. Any clone made
  before B3 still holds the name; re-clone or reset it (C2).
- `ui/console/engine/instrument.html` was referenced by the console before this arc and is still
  missing; out of scope here.
