"""A Claude agent under test: a manual tool-use loop whose only door to the world is a Session.

Model rules this loop follows (claude-api skill, cached 2026-09-25):
- `tool_choice` stays `auto`: Sonnet 5.5 returns a 400 on forced tool choice.
- No `temperature`: Sonnet 5.5 returns a 400 on non-default sampling.
- `effort` goes in `output_config`, never on Haiku 4.5 (it errors there).
- The assistant turn is appended whole (`response.content`), so thinking blocks go back unchanged.
- No server-side refusal fallback: it would silently swap the model under test. A refusal is
  journaled as the model's stop reason instead.
"""

import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol

from hackbench.session import Session

if TYPE_CHECKING:  # the SDK is the optional `agents` extra; only its types are needed here
    from anthropic.types import Message, Usage

# $ per million tokens (input, output). Cache writes cost 1.25x input; cache reads 0.1x.
PRICES: Mapping[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5-5": (2.0, 10.0),
}
CACHE_WRITE, CACHE_READ = 1.25, 0.1


def cost_usd(
    model: str, input_tokens: int, output_tokens: int, cache_write: int = 0, cache_read: int = 0
) -> float:
    price_in, price_out = PRICES[model]
    billed_in = input_tokens + CACHE_WRITE * cache_write + CACHE_READ * cache_read
    return (billed_in * price_in + output_tokens * price_out) / 1_000_000


class _Messages(Protocol):
    # Reason: the SDK's create() has many typed overloads; **Any is the one signature both
    # it and a test fake satisfy.
    def create(self, **kwargs: Any) -> "Message": ...  # noqa: ANN401


class Client(Protocol):
    """The slice of `anthropic.Anthropic` this loop uses; tests pass a fake."""

    @property
    def messages(self) -> _Messages: ...


class ClaudeAgent:
    def __init__(
        self,
        name: str,
        model: str,
        system: str,
        tools: Sequence[Mapping[str, Any]],
        client: Client,
        effort: str | None = None,
        max_tokens: int = 8000,
    ) -> None:
        self.name, self.model, self.system = name, model, system
        self.tools, self.client, self.effort, self.max_tokens = tools, client, effort, max_tokens

    def _request(self, messages: list[dict[str, Any]]) -> "Message":
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system,
            "tools": list(self.tools),
            "tool_choice": {"type": "auto"},
            "cache_control": {"type": "ephemeral"},  # system + tools are the stable prefix
            "messages": messages,
        }
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        return self.client.messages.create(**kwargs)

    def _record_usage(self, session: Session, usage: "Usage") -> None:
        inp, out = usage.input_tokens, usage.output_tokens
        write = usage.cache_creation_input_tokens or 0
        read = usage.cache_read_input_tokens or 0
        session.record_usage(inp + write + read, out, cost_usd(self.model, inp, out, write, read))

    def run(self, brief: str, session: Session) -> None:
        messages: list[dict[str, Any]] = [{"role": "user", "content": brief}]
        while not session.done:
            response = self._request(messages)
            # Reason: record cost BEFORE running tools; submit_verdict ends the session and
            # later usage would be dropped.
            self._record_usage(session, response.usage)
            if session.done:
                return
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                session.end("no_submission", model_stop_reason=str(response.stop_reason))
                return
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                out = session.call(block.name, block.input)
                result: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(out),
                }
                if "error" in out:
                    result["is_error"] = True
                results.append(result)
            messages.append({"role": "user", "content": results})
