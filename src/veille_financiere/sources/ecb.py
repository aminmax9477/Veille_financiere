"""BCE - portail de donnees officiel (taux de change, taux directeurs).

Format SDMX-JSON: les observations sont indexees par position, il faut les
recroiser avec la dimension temps declaree dans ``structure``.
"""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://data-api.ecb.europa.eu/service/data"


class EcbSource(Source):
    name = "ecb"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        payload = self.fetcher.fetch(
            f"{BASE}/{spec['native_id']}",
            params={
                "lastNObservations": spec.get("limit", 60),
                "format": "jsondata",
            },
        )
        datasets = payload.get("dataSets") or []
        if not datasets:
            raise SourceError("reponse BCE sans dataSets")

        time_dim = None
        for dim in payload["structure"]["dimensions"].get("observation", []):
            if dim.get("role") == "time" or dim.get("id") == "TIME_PERIOD":
                time_dim = dim
                break
        if time_dim is None:
            raise SourceError("dimension temps absente de la reponse BCE")
        periods = [v["id"] for v in time_dim["values"]]

        out: list[Observation] = []
        for series in datasets[0].get("series", {}).values():
            for idx_str, cell in series.get("observations", {}).items():
                idx = int(idx_str)
                if idx >= len(periods) or not cell or cell[0] is None:
                    continue
                out.append(
                    self._obs(spec, parse_period(periods[idx]), float(cell[0]))
                )
        return out
