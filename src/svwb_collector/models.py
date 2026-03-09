from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Item:
    source_key: str
    source_name: str
    item_type: str
    external_id: str
    title: str
    url: str
    published_at: str | None = None
    is_official: bool = True
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConnectorResult:
    source_key: str
    source_name: str
    is_official: bool
    items: list[Item] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked_reason: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunContext:
    run_id: int
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
