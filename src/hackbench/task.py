"""The seam between domain-agnostic evals and one use case (Polaron QC, a maths problem, ...).

Deliberately bare: method names will be adjusted when a second use case implements it.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class Task(Protocol):
    def load_items(self) -> Sequence[Mapping[str, object]]:
        """Items an agent is asked to judge (e.g. batches, problem instances)."""
        ...

    def tools(self) -> Mapping[str, Callable[..., object]]:
        """Domain tools agents may call; every call is journaled by the caller."""
        ...

    def ground_truth(self, item_id: str) -> object:
        """Known answer for an item (real label or synthetic injection)."""
        ...

    def honeypots(self) -> Sequence[str]:
        """Names of planted shortcuts the detector chain watches for."""
        ...

    def score(self, item_id: str, verdict: Mapping[str, object]) -> Mapping[str, float]:
        """Domain scoring of one verdict; generic metrics are computed elsewhere."""
        ...
