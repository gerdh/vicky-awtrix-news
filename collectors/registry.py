#!/usr/bin/env python3

"""Collector registry for the Vicky information engine.

The registry runs independent collectors, isolates failures, validates returned
items, and combines all successful results into one list for the news pool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable


LogFunction = Callable[[str], None]


@dataclass
class CollectorResult:
    name: str
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    started_at: str = ""
    finished_at: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None


class CollectorRegistry:
    """Register and execute collectors without sharing failure state."""

    def __init__(self, log: LogFunction | None = None) -> None:
        self._collectors: list[Any] = []
        self._log = log or (lambda message: None)

    def register(self, collector: Any) -> None:
        name = self._collector_name(collector)
        if any(self._collector_name(item) == name for item in self._collectors):
            raise ValueError(f"collector already registered: {name}")
        self._collectors.append(collector)

    def run_all(self) -> tuple[list[dict[str, Any]], list[CollectorResult]]:
        combined: list[dict[str, Any]] = []
        results: list[CollectorResult] = []

        for collector in self._collectors:
            result = self._run_one(collector)
            results.append(result)
            combined.extend(result.items)

        return combined, results

    def _run_one(self, collector: Any) -> CollectorResult:
        name = self._collector_name(collector)
        started = datetime.now().isoformat(timespec="seconds")
        self._log(f"collector {name}: start")

        try:
            raw_items = collector.collect()
            items = self._validate_items(raw_items, name)
            finished = datetime.now().isoformat(timespec="seconds")
            self._log(f"collector {name}: {len(items)} items")
            return CollectorResult(
                name=name,
                items=items,
                started_at=started,
                finished_at=finished,
            )
        except Exception as error:
            finished = datetime.now().isoformat(timespec="seconds")
            message = f"{type(error).__name__}: {error}"
            self._log(f"collector {name}: ERROR {message}")
            return CollectorResult(
                name=name,
                error=message,
                started_at=started,
                finished_at=finished,
            )

    @staticmethod
    def _collector_name(collector: Any) -> str:
        name = getattr(collector, "name", None)
        if name:
            return str(name)
        return collector.__class__.__name__

    @staticmethod
    def _validate_items(
        raw_items: Iterable[dict[str, Any]] | None,
        collector_name: str,
    ) -> list[dict[str, Any]]:
        if raw_items is None:
            return []

        if isinstance(raw_items, (str, bytes, dict)):
            raise TypeError(
                f"collector {collector_name} must return an iterable of dictionaries"
            )

        valid: list[dict[str, Any]] = []

        for index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise TypeError(
                    f"collector {collector_name} returned non-dict item at index {index}"
                )

            title = str(item.get("title", "")).strip()
            source = str(item.get("source", "")).strip()

            if not title or not source:
                raise ValueError(
                    f"collector {collector_name} returned invalid item at index {index}"
                )

            valid.append(item)

        return valid
