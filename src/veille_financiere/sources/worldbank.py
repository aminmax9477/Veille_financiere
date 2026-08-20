"""Banque mondiale - indicateurs annuels par pays."""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://api.worldbank.org/v2"


class WorldBankSource(Source):
    name = "worldbank"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        country = spec.get("country", "WLD")
        payload = self.fetcher.fetch(
            f"{BASE}/country/{country}/indicator/{spec['native_id']}",
            params={"format": "json", "per_page": spec.get("limit", 40)},
        )
        # La reponse est [metadata, rows]; rows peut valoir None si pas de donnee.
        if not isinstance(payload, list) or len(payload) < 2:
            raise SourceError("reponse Banque mondiale inattendue")
        rows = payload[1] or []
        out: list[Observation] = []
        for row in rows:
            if row.get("value") is None:
                continue
            out.append(
                self._obs(spec, parse_period(row["date"]), float(row["value"]))
            )
        return out
