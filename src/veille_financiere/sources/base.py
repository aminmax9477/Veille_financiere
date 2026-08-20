"""Contrat commun a tous les adaptateurs de source."""
from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any

from ..http import Fetcher
from ..models import Observation, SeriesResult, SourceError

log = logging.getLogger(__name__)


class Source:
    """Un fournisseur de donnees.

    Les sous-classes implementent ``_fetch_series`` et laissent la classe de
    base gerer le chronometrage et l'encapsulation des erreurs, pour qu'une
    source en panne ne fasse jamais tomber tout le run.
    """

    name: str = "base"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def fetch(self, spec: dict[str, Any]) -> SeriesResult:
        series_id = spec["series_id"]
        started = time.perf_counter()
        try:
            obs = self._fetch_series(spec)
        except Exception as exc:  # noqa: BLE001 - isolation volontaire par source
            log.warning("%s/%s a echoue: %s", self.name, series_id, exc)
            res = SeriesResult.failed(series_id, self.name, str(exc)[:300])
            res.latency_ms = int((time.perf_counter() - started) * 1000)
            return res
        return SeriesResult(
            series_id=series_id,
            source=self.name,
            observations=obs,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        raise NotImplementedError

    # --- utilitaires partages -------------------------------------------------

    def _obs(self, spec: dict[str, Any], date: dt.date, value: float,
             **extra: Any) -> Observation:
        # ``scale`` ramene une source a l'unite canonique de la serie
        # (certaines cotations sont exprimees en centiemes ou en multiples).
        scale = float(spec.get("scale", 1.0))
        return Observation(
            series_id=spec["series_id"],
            source=self.name,
            date=date,
            value=float(value) * scale,
            unit=spec.get("unit", ""),
            frequency=spec.get("frequency", ""),
            native_id=str(spec.get("native_id", "")),
            meta=extra or {},
        )


def parse_period(period: str) -> dt.date:
    """Convertit les formats de periode rencontres en date de fin de periode.

    Gere ``2026-08-20``, ``2026-08``, ``2026``, ``2026-Q2``, ``2026-M08``.
    On normalise sur la *fin* de periode: c'est la convention qui permet de
    comparer une serie trimestrielle et une serie mensuelle sans decalage.
    """
    p = period.strip().upper().replace("M", "-").replace("--", "-")
    if p.endswith("-"):
        p = p[:-1]

    if "Q" in p:
        year, _, q = p.partition("-Q")
        if not q:
            year, _, q = p.partition("Q")
        month = int(q) * 3
        return _end_of_month(int(year), month)

    parts = p.split("-")
    try:
        if len(parts) >= 3:
            return dt.date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            return _end_of_month(int(parts[0]), int(parts[1]))
        if len(parts) == 1 and parts[0]:
            return dt.date(int(parts[0]), 12, 31)
    except ValueError as exc:
        raise SourceError(f"periode illisible: {period!r}") from exc
    raise SourceError(f"periode illisible: {period!r}")


def _end_of_month(year: int, month: int) -> dt.date:
    if month == 12:
        return dt.date(year, 12, 31)
    return dt.date(year, month + 1, 1) - dt.timedelta(days=1)
