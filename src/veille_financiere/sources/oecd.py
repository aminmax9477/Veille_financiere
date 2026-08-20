"""OCDE - indicateurs courts terme (SDMX-JSON 2.0).

Utile ici pour couvrir les indices boursiers europeens quand Yahoo Finance
est indisponible: l'OCDE publie des indices de cours (base 100) par pays,
mensuels, avec une disponibilite bien plus stable.

Le format ressemble a celui de la BCE mais l'enveloppe differe: les
metadonnees sont sous ``data.structures[0]`` et non ``structure``, et les
periodes ne sont pas renvoyees dans l'ordre chronologique.
"""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://sdmx.oecd.org/public/rest/data"
HEADERS = {"Accept": "application/vnd.sdmx.data+json"}


class OecdSource(Source):
    name = "oecd"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        params = {"format": "jsondata"}
        params.update(spec.get("params", {}))
        payload = self.fetcher.fetch(
            f"{BASE}/{spec['native_id']}", params=params, headers=HEADERS
        )

        data = payload.get("data", payload)
        datasets = data.get("dataSets") or []
        if not datasets:
            raise SourceError("reponse OCDE sans dataSets")

        structures = data.get("structures")
        structure = structures[0] if structures else data.get("structure")
        if not structure:
            raise SourceError("reponse OCDE sans structure")

        obs_dims = structure.get("dimensions", {}).get("observation") or []
        if not obs_dims:
            raise SourceError("dimension temps absente de la reponse OCDE")
        periods = [v["id"] for v in obs_dims[0]["values"]]

        out: list[Observation] = []
        for series in datasets[0].get("series", {}).values():
            for idx_str, cell in series.get("observations", {}).items():
                idx = int(idx_str)
                if idx >= len(periods) or not cell or cell[0] is None:
                    continue
                out.append(self._obs(spec, parse_period(periods[idx]),
                                     float(cell[0])))
        if not out:
            raise SourceError("aucune observation exploitable")
        out.sort(key=lambda o: o.date, reverse=True)
        return out[: spec.get("limit", 60)]
