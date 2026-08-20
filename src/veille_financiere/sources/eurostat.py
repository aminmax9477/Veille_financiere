"""Eurostat - statistiques europeennes (inflation HICP, chomage...).

Format JSON-stat 2.0: ``value`` est un dict {index_aplati: valeur}. Comme on
ne requete qu'une seule combinaison de dimensions hors temps, l'index se
ramene directement a la position temporelle.
"""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


class EurostatSource(Source):
    name = "eurostat"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        params = {"format": "JSON", "lastTimePeriod": spec.get("limit", 24)}
        params.update(spec.get("params", {}))
        payload = self.fetcher.fetch(f"{BASE}/{spec['native_id']}", params=params)

        values = payload.get("value") or {}
        if not values:
            raise SourceError("reponse Eurostat sans valeurs")

        time_cat = payload["dimension"]["time"]["category"]["index"]
        # index temporel -> libelle de periode
        by_pos = {pos: period for period, pos in time_cat.items()}

        sizes = payload.get("size", [])
        dims = payload.get("id", [])
        time_pos = dims.index("time") if "time" in dims else len(dims) - 1
        # Pas de temps dans l'index aplati (row-major).
        stride = 1
        for s in sizes[time_pos + 1:]:
            stride *= s

        out: list[Observation] = []
        for flat_idx, val in values.items():
            if val is None:
                continue
            t_index = (int(flat_idx) // stride) % sizes[time_pos]
            period = by_pos.get(t_index)
            if period is None:
                continue
            out.append(self._obs(spec, parse_period(period), float(val)))
        return out
