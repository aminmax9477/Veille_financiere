"""CoinGecko - prix crypto (API publique, fortement limitee en debit).

On interroge l'historique plutot que le seul prix courant: sans profondeur,
aucune date ne coincide avec celles de FRED/Coinbase et le recoupement
entre les deux sources est impossible.

``market_chart`` renvoie des points infra-journaliers; on retient le dernier
releve de chaque journee UTC pour obtenir une cloture quotidienne comparable
a celle publiee par Coinbase via FRED.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from ..models import Observation, SourceError
from .base import Source

BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoSource(Source):
    name = "coingecko"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        vs = spec.get("vs_currency", "usd")
        payload = self.fetcher.fetch(
            f"{BASE}/coins/{spec['native_id']}/market_chart",
            params={"vs_currency": vs, "days": spec.get("lookback_days", 30)},
        )
        prices = payload.get("prices")
        if not prices:
            raise SourceError(
                f"aucun historique pour {spec['native_id']}: "
                f"{str(payload)[:120]}"
            )

        # Dernier releve de chaque journee UTC.
        daily: dict[dt.date, tuple[int, float]] = {}
        for ts_ms, value in prices:
            if value is None:
                continue
            day = dt.datetime.fromtimestamp(ts_ms / 1000, dt.timezone.utc).date()
            known = daily.get(day)
            if known is None or ts_ms > known[0]:
                daily[day] = (ts_ms, float(value))

        if not daily:
            raise SourceError(f"historique vide pour {spec['native_id']}")

        out = [self._obs(spec, day, value) for day, (_, value) in daily.items()]
        out.sort(key=lambda o: o.date, reverse=True)
        return out
