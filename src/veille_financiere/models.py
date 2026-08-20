"""Modeles normalises partages par toutes les sources.

Tout ce que le pipeline collecte finit sous la forme d'``Observation``:
une valeur numerique, datee, rattachee a une serie et a une source. C'est
ce denominateur commun qui rend possible la reconciliation entre sources.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Any


class SourceError(RuntimeError):
    """Erreur recuperable levee par un adaptateur de source."""


@dataclass(frozen=True, slots=True)
class Observation:
    """Une valeur unique, datee, pour une serie donnee."""

    series_id: str          # identifiant canonique interne, ex. "fx.eurusd"
    source: str             # nom de l'adaptateur, ex. "ecb"
    date: dt.date           # date de reference de l'observation
    value: float
    unit: str = ""          # ex. "EUR/USD", "percent", "USD"
    frequency: str = ""     # daily | monthly | quarterly | annual
    native_id: str = ""     # identifiant chez la source, ex. "DGS10"
    retrieved_at: dt.datetime = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    meta: dict[str, Any] = field(default_factory=dict)

    def as_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["retrieved_at"] = self.retrieved_at.isoformat()
        d["meta"] = d["meta"] or {}
        return d


@dataclass(slots=True)
class SeriesResult:
    """Ce que retourne un adaptateur: des observations + le contexte de l'appel."""

    series_id: str
    source: str
    observations: list[Observation] = field(default_factory=list)
    ok: bool = True
    error: str = ""
    latency_ms: int = 0

    @property
    def latest(self) -> Observation | None:
        if not self.observations:
            return None
        return max(self.observations, key=lambda o: o.date)

    @classmethod
    def failed(cls, series_id: str, source: str, error: str) -> "SeriesResult":
        return cls(series_id=series_id, source=source, ok=False, error=error)
