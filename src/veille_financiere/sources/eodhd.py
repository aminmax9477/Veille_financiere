"""EODHD - rendements souverains quotidiens et indices boursiers.

Deux bourses virtuelles sont exploitees, choisies par la cle ``market`` de
la specification :

* ``GBOND`` - 240 tenors souverains publies au jour le jour. C'est la seule
  source cablee ici qui serve les dix ans allemand, francais, italien,
  espagnol, britannique et chinois sans decalage : la BCE n'en publie qu'une
  moyenne mensuelle par pays, FRED s'en tient aux Etats-Unis, et les series
  souveraines de LSE accusent une dizaine de jours de retard.
* ``INDX`` - indices boursiers, utile la ou LSE se fige (l'IBEX 35 s'y
  arrete a juin 2026).
"""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://eodhd.com/api"


class EodhdSource(Source):
    name = "eodhd"

    def __init__(self, fetcher, api_key: str) -> None:
        super().__init__(fetcher)
        if not api_key:
            raise SourceError("EODHD_API_KEY absente")
        self.api_key = api_key

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        market = spec.get("market", "GBOND")
        ticker = spec["native_id"]
        if market:
            ticker = f"{ticker}.{market}"

        payload = self.fetcher.fetch(
            f"{BASE}/eod/{ticker}",
            params={
                "api_token": self.api_key,
                "fmt": "json",
                "order": "d",
                "limit": spec.get("limit", 90),
            },
        )
        if isinstance(payload, dict):
            # Les erreurs arrivent sous forme d'objet plutot que de liste.
            raise SourceError(str(payload)[:200])
        if not payload:
            raise SourceError(f"aucune donnee pour {ticker}")

        field = spec.get("field", "close")
        out: list[Observation] = []
        for row in payload:
            value = row.get(field, row.get("adjusted_close"))
            day = row.get("date")
            if value is None or not day:
                continue
            out.append(self._obs(spec, parse_period(str(day)), float(value)))
        if not out:
            raise SourceError(f"aucune valeur exploitable pour {ticker}")
        return out
