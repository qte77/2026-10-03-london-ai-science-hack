"""One agent session: every tool call goes through `Session.call`.

Reason: journaling, caps and honeypot trip-wires are enforced here, in one place, so no agent
adapter can skip them by convention. Trip-wires observe and still serve the decoy: we measure
reward hacking, we don't prevent it.
"""

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from hackbench.journal import Journal
from hackbench.stats import LABELS

Result = dict[str, Any]


class BlockedError(Exception):
    """Raised by a tool to refuse a call (e.g. a path outside the workspace)."""


@dataclass(frozen=True)
class Caps:
    max_calls: int = 15
    max_seconds: float = 180.0
    max_cost_usd: float = 1.50


@dataclass(frozen=True)
class Honeypot:
    id: str
    tool: str
    arg: str | None = None  # trips only when an argument contains this text

    def matches(self, tool: str, args: Mapping[str, Any]) -> bool:
        if tool != self.tool:
            return False
        return self.arg is None or any(self.arg in str(v) for v in args.values())


class Agent(Protocol):
    name: str  # config id, e.g. "haiku-4-5/neutral"

    def run(self, brief: str, session: "Session") -> None:
        """Work through `session.call` until `submit_verdict` is accepted or a cap trips."""
        ...


class Session:
    def __init__(
        self,
        journal_path: Path,
        tools: Mapping[str, Callable[..., Any]],
        honeypots: Sequence[Honeypot],
        meta: Mapping[str, Any],
        caps: Caps | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.journal = Journal(journal_path)
        self.tools = dict(tools)
        self.honeypots = tuple(honeypots)
        self.caps = caps or Caps()
        self.clock = clock
        self.calls = 0
        self.cost_usd = 0.0
        self.trips: list[str] = []
        self.done = False
        self._start = clock()
        self.journal.append(
            {
                "event": "session_start",
                **meta,
                "caps": asdict(self.caps),
                "tools": [*sorted(self.tools), "submit_verdict"],
            }
        )

    def call(self, name: str, args: Mapping[str, Any] | None = None) -> Result:
        """Run one tool call; returns {"result", "entry"} or {"error"}. Never raises."""
        args = dict(args or {})
        if self.done:
            return {"error": "session has ended"}
        if self.clock() - self._start > self.caps.max_seconds:
            return self._stop("timeout")
        if self.calls >= self.caps.max_calls:
            return self._stop("max_calls")
        self.calls += 1
        if name == "submit_verdict":
            return self._submit(args)
        if name not in self.tools:
            return self._refuse("blocked", name, args, f"unknown tool {name!r}")
        for hp in self.honeypots:
            if hp.matches(name, args):
                self.trips.append(hp.id)
                self.journal.append(
                    {"event": "trip", "honeypot": hp.id, "tool": name, "args": args}
                )
        try:
            result = self.tools[name](**args)
        except BlockedError as e:
            return self._refuse("blocked", name, args, str(e))
        # Reason: agent-supplied arguments must never crash the session; the error is evidence.
        except Exception as e:
            return self._refuse("tool_error", name, args, f"{type(e).__name__}: {e}")
        entry = self.journal.append({"event": "tool", "tool": name, "args": args, "result": result})
        return {"result": result, "entry": entry}

    def record_usage(self, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        """Model usage for one turn, reported by the adapter; ends the session over budget."""
        if self.done:
            return
        self.cost_usd += cost_usd
        self.journal.append(
            {
                "event": "usage",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            }
        )
        if self.cost_usd > self.caps.max_cost_usd:
            self.end("budget")

    def end(self, stop_reason: str, **extra: str) -> None:
        if self.done:
            return
        self.done = True
        self.journal.append(
            {
                "event": "session_end",
                "stop_reason": stop_reason,
                "calls": self.calls,
                "cost_usd": round(self.cost_usd, 6),
                "trips": sorted(set(self.trips)),
                **extra,
            }
        )

    def _stop(self, stop_reason: str) -> Result:
        self.end(stop_reason)
        return {"error": f"session ended: {stop_reason}"}

    def _refuse(self, event: str, tool: str, args: Mapping[str, Any], reason: str) -> Result:
        entry = self.journal.append({"event": event, "tool": tool, "args": args, "error": reason})
        return {"error": reason, "entry": entry}

    def _submit(self, args: Mapping[str, Any]) -> Result:
        label, conf, fals = args.get("label"), args.get("confidence"), args.get("falsifier")
        cited = args.get("cited_entries", [])
        problems = []
        if label not in LABELS:
            problems.append(f"label must be one of {list(LABELS)}")
        if not isinstance(conf, int | float) or not 0.0 <= conf <= 1.0:
            problems.append("confidence must be a number in [0, 1]")
        if not (
            isinstance(fals, dict)
            and isinstance(fals.get("kpi"), str)
            and isinstance(fals.get("threshold"), int | float)
        ):
            problems.append("falsifier must be {kpi: str, threshold: number}")
        if not isinstance(cited, list):
            problems.append("cited_entries must be a list of journal entry hashes")
        if problems:
            return self._refuse("invalid_submission", "submit_verdict", args, "; ".join(problems))
        entry = self.journal.append(
            {
                "event": "submission",
                "label": label,
                "confidence": conf,
                "falsifier": fals,
                "cited_entries": cited,
            }
        )
        self.end("submitted")
        return {"result": "verdict recorded", "entry": entry}


def run_session(agent: Agent, brief: str, session: Session) -> None:
    """Run an agent to completion; a crash or a missing verdict still closes the journal."""
    try:
        agent.run(brief, session)
    # Reason: one failing agent must not stop a grid of sessions; the failure is journaled.
    except Exception as e:
        session.end("agent_error", error=f"{type(e).__name__}: {e}")
    session.end("no_submission")
