# Luma application draft

Back to [README](../README.md) · See also: [event facts](event.md)

Drafted 2026-09-13. These are drafts to personalise, not a record of what was submitted.

## Open items

- [ ] Personal website: no URL was established, so answer 1 ends with a placeholder line.
- [ ] Team size (3–5 per the event page): not drafted, because it was not one of the two
  questions.

## 1. Please share any links that showcase your tech skills (personal website, favorite project etc.)

GitHub: github.com/qte77

Recent work spans AI evaluation and diagnosis tooling: Jev Gate, github.com/qte77/2026-09-12-WandB-AGIH-CoreWeave-Hack, a critique refine agent loop built this weekend where a diagnosis model classifies why a fix failed before a stronger model retries, verified with real multi run execution data rather than a single convenient number. Alongside that: gha-rxiv-feed-action and gha-rxiv-paper-eval, github.com/qte77/gha-rxiv-feed-action and github.com/qte77/gha-rxiv-paper-eval, a pair of GitHub Actions that ingest and relevance filter weekly arXiv, bioRxiv, and medRxiv submissions; paperverse, github.com/qte77/paperverse, a browser based 3D point cloud for navigating that literature; and agentic-codebase-to-scientific-report, github.com/qte77/agentic-codebase-to-scientific-report, which turns a code repository into a structured, quality scored scientific report.

Add your personal site here if you have one.

## 2. What is a problem that you've recently been obsessing over? What makes it special/ripe to solve now?

I have been building evaluation and diagnosis tooling that avoids self report, applied to both scientific literature and AI agent output. A small toolchain ingests and relevance filters weekly arXiv, bioRxiv, and medRxiv submissions, visualizes the resulting corpus as a navigable point cloud, and turns a code repository into a structured, quality scored scientific report. This past weekend I extended the same principle to agent self correction: most self correcting loops simply re-ask the same model and hope, collapsing diagnosis and retry into one step. I built a loop that separates them, a cheap model drafts, real execution grades the result, a calibrated classifier names the specific failure mode, and only then does a stronger model retry with that diagnosis in hand. This is timely because small models are now capable drafters, and fast structured decision models are emerging as a distinct primitive for exactly this kind of judgment call.
