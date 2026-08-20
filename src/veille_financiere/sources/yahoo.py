"""Yahoo Finance - cours actions, indices, FX, matieres premieres.

API non documentee et agressivement limitee en debit: on passe par
l'endpoint ``chart`` (le plus tolerant) et on s'appuie sur le backoff de
``Fetcher``. Les 429 sont frequents, d'ou un cache plus long cote appelant.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from ..models import Observation, SourceError
from .base import Source

BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


class YahooSource(Source):
    name = "yahoo"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        payload = self.fetcher.fetch(
            f"{BASE}/{spec['native_id']}",
            params={
                "range": spec.get("range", "1mo"),
                "interval": spec.get("interval", "1d"),
            },
            headers=BROWSER_HEADERS,
        )
        chart = payload.get("chart") or {}
        if chart.get("error"):
            raise SourceError(str(chart["error"])[:200])
        results = chart.get("result") or []
        if not results:
            raise SourceError("reponse Yahoo vide")

        result = results[0]
        meta = result.get("meta", {})
        stamps = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        # Yahoo prefere adjclose quand il existe (dividendes/splits corriges).
        adj = (result.get("indicators", {}).get("adjclose") or [{}])
        adjclose = adj[0].get("adjclose") if adj else None

        out: list[Observation] = []
        for i, ts in enumerate(stamps):
            val = None
            if adjclose and i < len(adjclose) and adjclose[i] is not None:
                val = adjclose[i]
            elif i < len(closes) and closes[i] is not None:
                val = closes[i]
            if val is None:
                continue
            date = dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()
            out.append(
                self._obs(spec, date, float(val),
                          currency=meta.get("currency", ""))
            )
        if not out:
            raise SourceError("aucune cloture exploitable")
        return out
