"""SEC EDGAR - fondamentaux XBRL des societes cotees aux Etats-Unis.

La SEC impose un User-Agent nominatif; sans contact declare on s'abstient
plutot que de risquer un blocage cote SEC.
"""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://data.sec.gov/api/xbrl/companyconcept"


class SecEdgarSource(Source):
    name = "sec_edgar"

    def __init__(self, fetcher, contact: str = "") -> None:
        super().__init__(fetcher)
        self.contact = contact.strip()

    def _headers(self) -> dict[str, str]:
        who = self.contact or "veille-financiere contact-non-declare"
        return {"User-Agent": f"veille-financiere {who}",
                "Accept-Encoding": "gzip, deflate"}

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        cik = str(spec["cik"]).zfill(10)
        taxonomy = spec.get("taxonomy", "us-gaap")
        payload = self.fetcher.fetch(
            f"{BASE}/CIK{cik}/{taxonomy}/{spec['native_id']}.json",
            headers=self._headers(),
        )
        unit_key = spec.get("xbrl_unit", "USD")
        rows = (payload.get("units") or {}).get(unit_key)
        if not rows:
            available = list((payload.get("units") or {}).keys())
            raise SourceError(f"unite {unit_key} absente (dispo: {available[:4]})")

        # Deux natures de concepts cohabitent dans XBRL:
        #  - les concepts de stock (Assets, StockholdersEquity) sont dates a
        #    un instant et n'ont pas de champ "start";
        #  - les concepts de flux (NetIncomeLoss, Revenues) couvrent une
        #    duree, et la meme balise apparait aussi bien dans un 10-Q
        #    (3 mois) que dans un 10-K (12 mois).
        # Melanger les deux dans une seule serie produirait des variations
        # absurdes: on filtre donc les flux sur la duree demandee.
        want_days = spec.get("duration_days")
        best: dict[str, dict] = {}
        for row in rows:
            end = row.get("end")
            if end is None or row.get("val") is None:
                continue
            start = row.get("start")
            if start is not None:
                span = (parse_period(end) - parse_period(start)).days
                if want_days is not None and abs(span - want_days) > 20:
                    continue
            # A periode egale, on retient la publication la plus recente
            # (les chiffres sont revises d'un depot a l'autre).
            key = f"{row.get('start', '')}:{end}"
            prev = best.get(key)
            if prev is None or (row.get("filed", "") > prev.get("filed", "")):
                best[key] = row

        out: list[Observation] = []
        for row in best.values():
            out.append(
                self._obs(
                    spec, parse_period(row["end"]), float(row["val"]),
                    form=row.get("form", ""), fy=row.get("fy"),
                    fp=row.get("fp", ""), filed=row.get("filed", ""),
                )
            )
        out.sort(key=lambda o: o.date, reverse=True)
        return out[: spec.get("limit", 24)]
