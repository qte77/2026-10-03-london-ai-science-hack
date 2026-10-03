"""Load a use-case profile (domain copy + metadata) from `hackbench/profiles/<name>.toml`."""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from importlib.resources import files
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    summary: str
    description: str
    tags: tuple[str, ...]
    representative_queries: tuple[str, ...]


@dataclass(frozen=True)
class Event:
    name: str
    dates: str


@dataclass(frozen=True)
class Profile:
    tagline: str
    status: str
    updated: date
    when_to_use: tuple[str, ...]
    when_not_to_use: tuple[str, ...]
    integrity_rules: tuple[str, ...]
    event: Event
    skill: Skill
    # Reason: domain-specific parameters stay opaque here; the domain Task interprets them.
    domain: Mapping[str, Any] = field(default_factory=dict)


@cache
def load_profile(name: str) -> Profile:
    resource = files("hackbench.profiles").joinpath(f"{name}.toml")
    if not resource.is_file():
        raise FileNotFoundError(f"no profile named {name!r} in hackbench/profiles/")
    raw = tomllib.loads(resource.read_text(encoding="utf-8"))
    skill = raw["skill"]
    return Profile(
        tagline=raw["tagline"],
        status=raw["status"],
        updated=raw["updated"],
        when_to_use=tuple(raw["when_to_use"]),
        when_not_to_use=tuple(raw["when_not_to_use"]),
        integrity_rules=tuple(raw["integrity_rules"]),
        event=Event(**raw["event"]),
        skill=Skill(
            id=skill["id"],
            name=skill["name"],
            summary=skill["summary"],
            description=skill["description"],
            tags=tuple(skill["tags"]),
            representative_queries=tuple(skill["representative_queries"]),
        ),
        domain=MappingProxyType(raw.get("domain", {})),
    )
