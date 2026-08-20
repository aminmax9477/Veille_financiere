"""Frankfurter - taux de change derives des references quotidiennes BCE.

On recupere une plage de dates plutot que le seul dernier point: sans
historique, aucune date ne coincide avec celles de FRED (publiees avec
quelques jours de retard) et la reconciliation n'a rien a comparer.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://api.frankfurter.dev/v1"


class FrankfurterSource(Source):
    name = "frankfurter"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        try:
            base_ccy, quote = spec["native_id"].split("/")
        except ValueError as exc:
            raise SourceError(
                f"paire mal formee: {spec['native_id']!r} (attendu 'EUR/USD')"
            ) from exc

        days = int(spec.get("lookback_days", 60))
        end = dt.date.today()
        start = end - dt.timedelta(days=days)
        payload = self.fetcher.fetch(
            f"{BASE}/{start.isoformat()}..{end.isoformat()}",
            params={"base": base_ccy, "symbols": quote},
        )

        rates = payload.get("rates") or {}
        if not rates:
            raise SourceError(f"aucun taux renvoye pour {spec['native_id']}")

        out: list[Observation] = []
        for day, row in rates.items():
            val = row.get(quote)
            if val is None:
                continue
            out.append(self._obs(spec, parse_period(day), float(val)))
        if not out:
            raise SourceError(f"devise {quote} absente de la reponse")
        out.sort(key=lambda o: o.date, reverse=True)
        return out
