"""London Strategic Edge - donnees de marche et macro (cle requise).

Trois familles d'endpoints sont exploitees, choisies par la cle ``mode``
de la specification :

* ``candles``  - chandeliers OHLCV pour tout instrument non optionnel
  (actions, indices, change, crypto, matieres premieres) ;
* ``series``   - series (date, valeur) : macroeconomie et rendements
  souverains ;
* ``bond_yields`` - historique OHLC quotidien par tenor obligataire.

C'est la seule source cablee ici qui couvre a la fois le CAC 40, l'Euro
Stoxx 50 en quotidien et l'or, pour lesquels aucune alternative publique
gratuite fiable n'a ete trouvee.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://api.londonstrategicedge.com/vault"


class LseSource(Source):
    name = "lse"

    def __init__(self, fetcher, api_key: str) -> None:
        super().__init__(fetcher)
        if not api_key:
            raise SourceError("LSE_API_KEY absente")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key}

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        mode = spec.get("mode", "candles")
        if mode == "candles":
            return self._candles(spec)
        if mode == "series":
            return self._series(spec)
        if mode == "bond_yields":
            return self._bond_yields(spec)
        raise SourceError(f"mode LSE inconnu: {mode!r}")

    # ------------------------------------------------------------------

    def _rows(self, path: str, params: dict[str, Any]) -> list[dict]:
        payload = self.fetcher.fetch(f"{BASE}{path}", params=params,
                                     headers=self._headers())
        if isinstance(payload, dict):
            # L'API encapsule ses erreurs dans un champ "detail".
            raise SourceError(str(payload.get("detail", payload))[:200])
        if not payload:
            raise SourceError("aucune ligne renvoyee")
        return payload

    def _candles(self, spec: dict[str, Any]) -> list[Observation]:
        rows = self._rows("/candles", {
            "symbol": spec["native_id"],
            "timeframe": spec.get("timeframe", "1d"),
            "order": "desc",
            "limit": spec.get("limit", 90),
        })
        field = spec.get("field", "close")
        out: list[Observation] = []
        for row in rows:
            value = row.get(field)
            stamp = row.get("timestamp") or row.get("ts")
            if value is None or stamp is None:
                continue
            out.append(self._obs(spec, _to_date(stamp), float(value),
                                 open=row.get("open"), high=row.get("high"),
                                 low=row.get("low")))
        if not out:
            raise SourceError(f"aucune bougie exploitable ({field} absent)")
        return out

    def _series(self, spec: dict[str, Any]) -> list[Observation]:
        rows = self._rows("/series", {
            "symbol": spec["native_id"],
            "dataset": spec.get("dataset"),
            "order": "desc",
            "limit": spec.get("limit", 60),
        })
        out: list[Observation] = []
        for row in rows:
            value, day = row.get("value"), row.get("date")
            if value is None or day is None:
                continue
            out.append(self._obs(spec, _to_date(day), float(value)))
        if not out:
            raise SourceError("aucune observation exploitable")
        return out

    def _bond_yields(self, spec: dict[str, Any]) -> list[Observation]:
        rows = self._rows("/ref/bond_yields", {
            "symbol": spec["native_id"],
            "order": "desc",
            "limit": spec.get("limit", 90),
        })
        field = spec.get("field", "close")
        out: list[Observation] = []
        for row in rows:
            value = row.get(field, row.get("value"))
            day = row.get("date") or row.get("timestamp") or row.get("ts")
            if value is None or day is None:
                continue
            out.append(self._obs(spec, _to_date(day), float(value)))
        if not out:
            raise SourceError("aucun rendement exploitable")
        return out


def _to_date(stamp: str) -> dt.date:
    """Accepte '2026-08-20', '2026-08-20 00:00:00.000000' et l'ISO complet."""
    text = str(stamp).strip()
    if not text:
        raise SourceError("horodatage vide")
    head = text.replace("T", " ").split(" ")[0]
    return parse_period(head)
