"""Paper judge: Paperclip resolves + scores evidence for each bundle claim, then an LLM judge
(OpenAI-compatible chat-completions endpoint - the Modal vLLM judge, else Cloudflare Workers AI)
scores Paperclip's output against the curated direction.

Pipeline: bundle papers -> Paperclip `/lookup` or `/search` (resolve) -> Paperclip
`/claims/support` (evidence for/against) -> LLM judge -> scores. Reads only
`papers[].{id,title,doi}` and `assessments[].{target, claim, direction}` from a
`marker-research/1` bundle. Every Paperclip and judge call is journaled (hashes, latency,
counts/parsed result) - never full text, snippets or abstracts.
"""

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx

from hackbench.journal import Journal

PAPERCLIP_BASE_URL = "https://paperclip.gxl.ai/api/v1"
MAX_CALLS = 60
JUDGE_MAX_TOKENS = 400
# Reason: @cf/meta/llama-3.1-8b-instruct returns HTTP 410 (deprecated 2026-05-30, checked live
# 2026-10-04); gpt-oss-20b answered the same OpenAI-compatible request with clean JSON.
CF_MODEL = "@cf/openai/gpt-oss-20b"
DIRECTIONS = ("SUPPORTIVE", "CONTRADICTORY", "NEUTRAL")
# Reason: retry schedule tolerating a cold-starting Modal vLLM container (scale-to-zero); tests
# pass `backoff=()` so MockTransport cases never sleep. Sum = 465s, under the ~8min cap.
DEFAULT_BACKOFF: Sequence[float] = (15.0, 30.0, 60.0, 120.0, 240.0)

_JUDGE_SYSTEM = (
    "You are a strict research-evidence judge. You are given a scientific claim about a "
    "target marker, a curated direction, and evidence a literature-search API (Paperclip) "
    "returned for that claim (titles/DOIs/short snippets only). Decide: does the evidence "
    "actually address the claim (grounded)? What direction does it support "
    "(SUPPORTIVE/CONTRADICTORY/NEUTRAL)? Does that match the curated direction? Is the "
    "evidence relevant at all? Reply with ONLY compact JSON, no prose: "
    '{"direction": "SUPPORTIVE|CONTRADICTORY|NEUTRAL", "paperclip_relevant": true|false, '
    '"paperclip_direction_correct": true|false, "grounded": true|false, '
    '"confidence": 0.0-1.0, "reason": "<one sentence>"}.'
)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _hits_in(body: Mapping[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        value = body.get(key)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
    return []


def _post_with_retry(
    http: httpx.Client,
    url: str,
    payload: Mapping[str, Any],
    backoff: Sequence[float],
    headers: Mapping[str, str] | None = None,
) -> httpx.Response | None:
    """Try once, then retry on transport errors or 5xx per `backoff`'s delays (seconds)."""
    last: httpx.Response | None = None
    for delay in (0.0, *backoff):
        if delay:
            time.sleep(delay)
        try:
            last = http.post(url, json=payload, headers=headers)
        except httpx.HTTPError:
            last = None
            continue
        if last.status_code < 500:
            return last
    return last


# ---- Paperclip: resolve + claim support -----------------------------------------------------


def _paperclip_headers(api_key: str) -> dict[str, str]:
    # Reason: paperclip.gxl.ai/install documents an `X-API-Key` header; its openapi.json also
    # shows a Bearer scheme. Sending both costs nothing and covers either enforcement.
    return {"X-API-Key": api_key, "Authorization": f"Bearer {api_key}"}


def _post_paperclip(
    http: httpx.Client, journal: Journal, tool: str, path: str, payload: Mapping[str, Any]
) -> dict[str, Any] | None:
    """POST one Paperclip call, journaled; `None` means the call failed (transport/non-200)."""
    try:
        r = http.post(path, json=payload)
    except httpx.HTTPError as exc:
        journal.append({"tool": tool, "error": str(exc)})
        return None
    journal.append({"tool": tool, "status_code": r.status_code})
    if r.status_code != 200:
        return None
    try:
        body = r.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    # Reason: `/claims/support`'s response schema is unspecified in Paperclip's own
    # openapi.json; journal the top-level keys so a live run reveals the real shape even when
    # the parsed counts come out zero.
    journal.append({"tool": f"{tool}.keys", "keys": sorted(body.keys())})
    return body


def _resolve_paper(
    http: httpx.Client, journal: Journal, paper: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve one bundle paper in Paperclip: `/lookup` by DOI, else `/search` by title."""
    doi = paper.get("doi")
    if doi:
        body = _post_paperclip(
            http, journal, "paperclip.lookup", "/lookup", {"doi": doi, "num_results": 3}
        )
    else:
        body = _post_paperclip(
            http,
            journal,
            "paperclip.search",
            "/search",
            {"query": str(paper.get("title") or ""), "num_results": 3},
        )
    hits = _hits_in(body or {}, "papers", "results")
    if body is None or not hits:
        return {"resolved": False, "paperclip_id": None, "source": None, "ok": body is not None}
    hit = hits[0]
    return {
        "resolved": True,
        "paperclip_id": hit.get("id"),
        "source": hit.get("source"),
        "ok": True,
    }


def _support_counts(body: Mapping[str, Any]) -> tuple[int, int, list[dict[str, Any]]]:
    support = _hits_in(body, "support", "supporting", "evidence_for", "for")
    against = _hits_in(body, "against", "refuting", "evidence_against")
    if support or against:
        return len(support), len(against), support + against
    # Reason: fall back to a flat passage list with a per-item label, since the response
    # schema for `/claims/support` is unspecified in Paperclip's own openapi.json.
    flat = _hits_in(body, "evidence", "passages", "results")
    sup = [p for p in flat if str(p.get("label", "")).lower() in ("supports", "support")]
    con = [
        p
        for p in flat
        if str(p.get("label", "")).lower() in ("refutes", "refute", "contradicts", "against")
    ]
    return len(sup), len(con), flat


def _direction_from_counts(n_support: int, n_against: int) -> str:
    if n_support > n_against:
        return "SUPPORTIVE"
    if n_against > n_support:
        return "CONTRADICTORY"
    return "NEUTRAL"


def _paper_found(
    paper: Mapping[str, Any], paperclip_id: object, evidence: Sequence[Mapping[str, Any]]
) -> bool:
    doi = str(paper.get("doi") or "").lower()
    title = str(paper.get("title") or "").lower()
    for item in evidence:
        if doi and str(item.get("doi") or "").lower() == doi:
            return True
        if paperclip_id and item.get("id") == paperclip_id:
            return True
        if title and str(item.get("title") or "").lower() == title:
            return True
    return False


# ---- LLM judge: OpenAI-compatible, Modal vLLM else Cloudflare Workers AI --------------------


def _judge_target(
    llm_url: str, cf_account_id: str, cf_api_token: str
) -> tuple[str, str, dict[str, str], str | None]:
    """(base_url, provider, headers, fixed_model). Modal vLLM first, else Cloudflare Workers AI.

    Reason: provider is picked by config PRESENCE, not a reachability probe - the judge call's
    own retry/backoff already tolerates a cold Modal container, so a failed call after retries
    is counted as a judge error, not a silent fallback to the other provider.
    """
    if llm_url:
        return f"{llm_url}/v1", "modal-vllm", {}, None
    if cf_account_id and cf_api_token:
        base = f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/v1"
        return base, "cloudflare-workers-ai", {"Authorization": f"Bearer {cf_api_token}"}, CF_MODEL
    return "", "", {}, None


def _discover_model(http: httpx.Client, base_url: str, headers: Mapping[str, str]) -> str:
    """Best-effort `GET {base_url}/models`; falls back to the `llm` alias."""
    try:
        r = http.get(f"{base_url}/models", headers=headers)
    except httpx.HTTPError:
        return "llm"
    if r.status_code != 200:
        return "llm"
    try:
        data = r.json().get("data", [])
    except ValueError:
        return "llm"
    if data and isinstance(data[0], dict) and isinstance(data[0].get("id"), str):
        return str(data[0]["id"])
    return "llm"


def _parse_judgment(text: str) -> dict[str, Any] | None:
    """Defensive parse of the judge's reply. Malformed/garbage output returns None (an error)."""
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        obj = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    direction = obj.get("direction")
    confidence = obj.get("confidence")
    if direction not in DIRECTIONS or not isinstance(confidence, int | float):
        return None
    return {
        "direction": direction,
        "paperclip_relevant": bool(obj.get("paperclip_relevant", True)),
        "paperclip_direction_correct": bool(obj.get("paperclip_direction_correct", False)),
        "grounded": bool(obj.get("grounded", False)),
        "confidence": max(0.0, min(1.0, float(confidence))),
    }


def _call_judge(
    http: httpx.Client,
    base_url: str,
    headers: Mapping[str, str],
    model: str,
    target: object,
    claim: str,
    curated: object,
    evidence: Sequence[Mapping[str, Any]],
    backoff: Sequence[float],
) -> tuple[dict[str, Any] | None, float, int | None]:
    ev_lines = [
        f"- {e.get('title')} (doi={e.get('doi')}): {str(e.get('snippet') or '')[:200]}"
        for e in list(evidence)[:5]
    ]
    user = (
        f"Target marker: {target}\nCurated direction: {curated}\nClaim: {claim}\n"
        f"Evidence:\n{chr(10).join(ev_lines) if ev_lines else '(none returned)'}"
    )
    payload = {
        "model": model,
        "max_tokens": JUDGE_MAX_TOKENS,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user", "content": user},
        ],
    }
    t0 = time.monotonic()
    r = _post_with_retry(http, f"{base_url}/chat/completions", payload, backoff, headers=headers)
    seconds = round(time.monotonic() - t0, 3)
    # Reason: return the HTTP status so failures (e.g. a 410 deprecated model) are journaled.
    status = r.status_code if r is not None else None
    if r is None or r.status_code != 200:
        return None, seconds, status
    try:
        body = r.json()
        text = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return None, seconds, status
    return _parse_judgment(str(text)), seconds, status


def run_paper_judge(
    bundle_path: Path,
    journal: Journal,
    *,
    api_key: str,
    llm_url: str = "",
    cf_account_id: str = "",
    cf_api_token: str = "",
    client: httpx.Client | None = None,
    judge_client: httpx.Client | None = None,
    max_calls: int = MAX_CALLS,
    backoff: Sequence[float] = DEFAULT_BACKOFF,
) -> dict[str, Any]:
    """Resolve + score each bundle assessment via Paperclip, then judge Paperclip's output with
    an LLM. `n`/`errors` are over Paperclip calls; `judge.n`/`judge.errors` are over judge calls.
    `judge` degrades independently of Paperclip (Paperclip success + judge unreachable still
    returns Paperclip's scores, with `judge: {"status": "skipped"|"ok", ...}`)."""
    if not api_key:
        return {"status": "skipped", "reason": "PAPERCLIP_API_KEY unset"}

    bundle = json.loads(bundle_path.read_text())
    papers = [p for p in bundle.get("papers", []) if isinstance(p, dict)]

    own_client = client is None
    http = client or httpx.Client(
        base_url=PAPERCLIP_BASE_URL, headers=_paperclip_headers(api_key), timeout=30.0
    )

    calls = 0
    errors = 0
    resolved_cache: dict[Any, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    try:
        for paper in papers:
            paper_id = paper.get("id")
            assessments = [a for a in paper.get("assessments", []) if isinstance(a, dict)]
            if not assessments:
                continue
            if paper_id not in resolved_cache:
                if calls >= max_calls:
                    resolved_cache[paper_id] = {
                        "resolved": False,
                        "paperclip_id": None,
                        "source": None,
                        "ok": False,
                    }
                    errors += 1
                else:
                    calls += 1
                    resolved_cache[paper_id] = _resolve_paper(http, journal, paper)
                    if not resolved_cache[paper_id]["ok"]:
                        errors += 1
            resolved = resolved_cache[paper_id]

            for a in assessments:
                claim = str(a.get("claim") or "")[:590]
                target, curated = a.get("target"), a.get("direction")
                if calls >= max_calls:
                    errors += 1
                    rows.append(
                        {
                            "paper_id": paper_id,
                            "target": target,
                            "curated": curated,
                            "paperclip": None,
                            "n_support": 0,
                            "n_against": 0,
                            "our_paper_found": False,
                            "paperclip_id": resolved.get("paperclip_id"),
                            "resolved": resolved.get("resolved"),
                            "source": resolved.get("source"),
                            "judge": None,
                        }
                    )
                    continue
                calls += 1
                body = _post_paperclip(
                    http,
                    journal,
                    "paperclip.claims_support",
                    "/claims/support",
                    {"claim": claim, "top_n": 20},
                )
                if body is None:
                    errors += 1
                n_support, n_against, evidence = _support_counts(body or {})
                rows.append(
                    {
                        "paper_id": paper_id,
                        "target": target,
                        "curated": curated,
                        "paperclip": _direction_from_counts(n_support, n_against),
                        "n_support": n_support,
                        "n_against": n_against,
                        "our_paper_found": _paper_found(
                            paper, resolved.get("paperclip_id"), evidence
                        ),
                        "paperclip_id": resolved.get("paperclip_id"),
                        "resolved": resolved.get("resolved"),
                        "source": resolved.get("source"),
                        "judge": None,
                        "_evidence": evidence,
                        "_claim": claim,
                    }
                )
    finally:
        if own_client:
            http.close()

    n_papers = len(resolved_cache)
    n_resolved = sum(1 for v in resolved_cache.values() if v.get("resolved"))
    paperclip_resolved_rate = (n_resolved / n_papers) if n_papers else 0.0
    n_rows = len(rows)
    paperclip_agreement = (
        sum(1 for r in rows if r["paperclip"] == r["curated"]) / n_rows if n_rows else 0.0
    )

    judge = _run_judge(rows, journal, llm_url, cf_account_id, cf_api_token, judge_client, backoff)
    for row in rows:
        row.pop("_evidence", None)
        row.pop("_claim", None)

    return {
        "status": "ok",
        "n": calls,
        "errors": errors,
        "paperclip_resolved_rate": paperclip_resolved_rate,
        "paperclip_agreement": paperclip_agreement,
        "rows": rows,
        "judge": judge,
    }


def _run_judge(
    rows: list[dict[str, Any]],
    journal: Journal,
    llm_url: str,
    cf_account_id: str,
    cf_api_token: str,
    judge_client: httpx.Client | None,
    backoff: Sequence[float],
) -> dict[str, Any]:
    base_url, provider, headers, fixed_model = _judge_target(llm_url, cf_account_id, cf_api_token)
    if not provider:
        return {
            "status": "skipped",
            "reason": "HACKBENCH_LLM_URL unset; CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN unset",
        }

    own_client = judge_client is None
    jhttp = judge_client or httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0))
    judge_errors = 0
    scored: list[dict[str, Any]] = []
    model = fixed_model or "llm"
    try:
        if fixed_model is None:
            model = _discover_model(jhttp, base_url, headers)
        for row in rows:
            evidence = row.pop("_evidence", [])
            claim = row.pop("_claim", "")
            parsed, seconds, status = _call_judge(
                jhttp,
                base_url,
                headers,
                model,
                row["target"],
                claim,
                row["curated"],
                evidence,
                backoff,
            )
            journal.append(
                {
                    "tool": "judge",
                    "paper_id": row["paper_id"],
                    "target": row["target"],
                    "provider": provider,
                    "prompt_hash": _hash(f"{row['target']}\n{claim}"),
                    "model": model,
                    "latency_s": seconds,
                    "status_code": status,
                    "parsed": parsed,
                }
            )
            if parsed is None:
                judge_errors += 1
                row["judge"] = None
                continue
            correct = parsed["direction"] == row["curated"]
            row["judge"] = {
                "direction": parsed["direction"],
                "confidence": parsed["confidence"],
                "grounded": parsed["grounded"],
                "paperclip_relevant": parsed["paperclip_relevant"],
                "paperclip_direction_correct": parsed["paperclip_direction_correct"],
            }
            scored.append({**row, "correct": correct})
    finally:
        if own_client:
            jhttp.close()

    n_scored = len(scored)
    judge_agreement = (sum(1 for r in scored if r["correct"]) / n_scored) if n_scored else 0.0
    judge_paperclip_agreement = (
        sum(1 for r in scored if r["judge"]["direction"] == r["paperclip"]) / n_scored
        if n_scored
        else 0.0
    )
    grounded_rate = (
        (sum(1 for r in scored if r["judge"]["grounded"]) / n_scored) if n_scored else 0.0
    )
    brier = (
        sum((r["judge"]["confidence"] - (1.0 if r["correct"] else 0.0)) ** 2 for r in scored)
        / n_scored
        if n_scored
        else 0.0
    )
    return {
        "status": "ok",
        "provider": provider,
        "model": model,
        "n": len(rows),
        "errors": judge_errors,
        "judge_agreement": judge_agreement,
        "judge_paperclip_agreement": judge_paperclip_agreement,
        "grounded_rate": grounded_rate,
        "brier": brier,
    }
