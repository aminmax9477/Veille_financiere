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


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """Une publication macroeconomique attendue ou deja parue.

    Contrairement a ``Observation``, un evenement n'est pas une serie: il
    porte une heure de publication, un consensus et, une fois paru, une
    valeur constatee. C'est ce triptyque attendu/consensus/constate qui fait
    l'interet d'un agenda dans une veille du matin.
    """

    source: str
    date: dt.date
    region: str
    event: str
    time: str = ""                  # heure locale de publication, ex. "08:30 AM"
    period: str = ""                # periode couverte, ex. "JUL"
    actual: str | None = None       # valeur constatee, None si non encore parue
    previous: str | None = None
    consensus: str | None = None
    forecast: str | None = None

    @property
    def released(self) -> bool:
        return self.actual not in (None, "")

    def surprise(self) -> float | None:
        """Ecart entre la valeur constatee et le consensus, en points.

        Renvoie None si l'un des deux manque ou n'est pas comparable
        numeriquement: ces champs arrivent sous forme de texte ("209K",
        "3.2%", "-3.28") et toutes les unites ne se soustraient pas.
        """
        a, c = _to_number(self.actual), _to_number(self.consensus)
        if a is None or c is None:
            return None
        return a - c


def _to_number(raw: str | None) -> float | None:
    """Convertit '209K', '3.2%', '-3.28' en nombre; None si illisible."""
    if raw is None:
        return None
    text = str(raw).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    multiplier = 1.0
    if text and text[-1] in "KMBT":
        multiplier = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[text[-1]]
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None
