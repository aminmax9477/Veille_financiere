"""CoinGecko - prix crypto (API publique, fortement limitee en debit)."""
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
            f"{BASE}/simple/price",
            params={
                "ids": spec["native_id"],
                "vs_currencies": vs,
                "include_last_updated_at": "true",
            },
        )
        row = payload.get(spec["native_id"])
        if not row or row.get(vs) is None:
            raise SourceError(f"prix absent pour {spec['native_id']}")
        ts = row.get("last_updated_at")
        date = (
            dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()
            if ts else dt.datetime.now(dt.timezone.utc).date()
        )
        return [self._obs(spec, date, float(row[vs]))]
