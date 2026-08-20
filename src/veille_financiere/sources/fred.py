"""FRED (Federal Reserve Bank of St. Louis) - macro US et taux."""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://api.stlouisfed.org/fred/series/observations"


class FredSource(Source):
    name = "fred"

    def __init__(self, fetcher, api_key: str) -> None:
        super().__init__(fetcher)
        if not api_key:
            raise SourceError("FRED_API_KEY absente")
        self.api_key = api_key

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        payload = self.fetcher.fetch(
            BASE,
            params={
                "series_id": spec["native_id"],
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": spec.get("limit", 120),
                # units=pc1 delegue le glissement annuel a FRED plutot que de
                # le recalculer nous-memes sur une serie tronquee.
                "units": spec.get("fred_units", "lin"),
            },
        )
        out: list[Observation] = []
        for row in payload.get("observations", []):
            # FRED encode les valeurs manquantes par ".".
            if row.get("value") in (".", "", None):
                continue
            out.append(self._obs(spec, parse_period(row["date"]), float(row["value"])))
        return out
