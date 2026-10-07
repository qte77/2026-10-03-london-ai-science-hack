"""Fetch the event's public submissions from iterate.inc and write an anonymised copy.

No login needed: the public "Projects" endpoint serves all submissions. Fetches via the
polyfetch CLI from a sibling checkout (env-borrow, no install; see polyfetch-scrape/USING.md):

    python3 scripts/scrape_submissions.py

Writes:
    private/submissions.raw.json      full payload as served (gitignored)
    data/submissions/submissions.json anonymised: people's names listed in
    data/submissions/submissions.csv  private/redact-names.txt replaced with "[name]"
"""

import csv
import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

URL = (
    "https://iterate.inc/api/global-hackathons/68eb0369-50b5-4be1-950b-52e2723a954d"
    "/submissions?limit=100&offset=0&sortBy=ranked"
)
ROOT = Path(__file__).resolve().parent.parent
POLYFETCH = ROOT.parent / "polyfetch-scrape"
RAW = ROOT / "private" / "submissions.raw.json"
NAMES = ROOT / "private" / "redact-names.txt"  # one name per line; gitignored, never committed
OUT = ROOT / "data" / "submissions"
# Reason: the public API serves only track_id, and its tracks endpoint is login-only. Names are from
# the logged-in tracks list (2026-10-04); the id->name match is inferred from submission content
# (sponsor/topic words, explicit "Track 4"/"Serova track" mentions; our PARALLAX is in Polaron's).
TRACKS = {
    "62f1e4b5-1a92-436a-82fa-c1bc3704b44d": "Track 1: Open Maths Problems Track by C3",
    "1e3c89ca-d431-4e6b-a5b8-f14200f37806": (
        "Track 2: Originator Agents that do science & know when they're wrong/reward hacking"
    ),
    "628ba2ed-907b-4c8d-84a2-a88b250c5b45": "Track 3: Protein Engineering by Serova",
    "77356dad-ded9-4896-979a-6264379c26f5": "Track 4: Materials Manufacturing by Polaron",
}
TEXT_FIELDS = ("title", "description", "team_name", "github_url", "demo_url", "screenshot_url")
COLS = [
    "rank",
    "vote_count",
    "title",
    "team_name",
    "track",
    "track_id",
    "description",
    "tech_stack",
    "github_url",
    "demo_url",
    "screenshot_url",
    "created_at",
    "id",
    "team_id",
]


def fetch() -> dict:
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv not found on PATH")
    # Reason: fixed argv (constant URL, repo-relative path), no shell; S603 is a false positive.
    body = subprocess.run(  # noqa: S603
        [uv, "run", "--directory", str(POLYFETCH), "polyfetch", "fetch", URL, "--show-body"],
        check=True,
        capture_output=True,
    ).stdout
    data = json.loads(body)
    # Reason: limit=100 is meant to return everything in one page; fail loudly if it ever doesn't.
    if len(data["submissions"]) != data["total"]:
        raise SystemExit(f"got {len(data['submissions'])} of {data['total']} submissions")
    return data


def redactor(names: list[str]) -> Callable[[object], object]:
    if not names:
        return lambda text: text
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b", re.IGNORECASE)
    return lambda text: pattern.sub("[name]", text) if isinstance(text, str) else text


def main() -> None:
    RAW.parent.mkdir(exist_ok=True)
    if RAW.exists():
        data = json.loads(RAW.read_text())
    else:
        data = fetch()
        RAW.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    lines = NAMES.read_text().splitlines() if NAMES.exists() else []
    names = [n.strip() for n in lines if n.strip()]
    redact = redactor(names)
    subs = []
    for sub in data["submissions"]:
        sub = {
            **sub,
            **{f: redact(sub.get(f)) for f in TEXT_FIELDS},
            "track": TRACKS.get(sub.get("track_id"), ""),
        }
        ts = sub.get("tech_stack")
        sub["tech_stack"] = [redact(t) for t in ts] if isinstance(ts, list) else redact(ts)
        subs.append(sub)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "submissions.json").write_text(
        json.dumps(
            {"source": URL, "total": data["total"], "tracks": TRACKS, "submissions": subs},
            indent=2,
            ensure_ascii=False,
        )
    )
    with (OUT / "submissions.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for sub in subs:
            ts = sub.get("tech_stack")
            w.writerow({**sub, "tech_stack": ", ".join(ts) if isinstance(ts, list) else ts})
    print(f"submissions: {len(subs)} / total {data['total']} | names redacted: {len(names)}")


if __name__ == "__main__":
    main()
