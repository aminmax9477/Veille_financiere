"""FMI - DataMapper (projections World Economic Outlook)."""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://www.imf.org/external/datamapper/api/v1"


class ImfSource(Source):
    name = "imf"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        country = spec.get("country", "FRA")
        payload = self.fetcher.fetch(f"{BASE}/{spec['native_id']}/{country}")
        values = (payload.get("values") or {}).get(spec["native_id"], {})
        rows = values.get(country)
        if not rows:
            raise SourceError(f"aucune donnee FMI pour {spec['native_id']}/{country}")
        out: list[Observation] = []
        for year, val in rows.items():
            if val is None:
                continue
            out.append(self._obs(spec, parse_period(year), float(val),
                                 projection=True))
        out.sort(key=lambda o: o.date, reverse=True)
        return out[: spec.get("limit", 40)]
