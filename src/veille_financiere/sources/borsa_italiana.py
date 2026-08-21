"""Borsa Italiana - FTSE MIB, lu sur la page publique de l'operateur.

C'est la seule source du projet qui lise une page HTML au lieu d'une API,
et c'est un choix par defaut : le niveau du FTSE MIB n'est servi par aucune
des interfaces cablees ici. EODHD ne l'expose pas, Twelve Data le catalogue
mais le reserve a ses offres payantes, le flux equivalent de London
Strategic Edge est fige et mal echelonne.

Lire une page prevue pour des yeux humains est fragile d'une facon
particuliere : ce n'est pas qu'elle casse, c'est qu'elle peut renvoyer un
autre nombre sans rien signaler. La page affiche cote a cote le cours du
jour, ses plus haut et plus bas, l'ouverture, et les extremes de l'annee
precedente — sept valeurs de meme forme, dont une seule est le cours.

D'ou la verification retenue : la page publie aussi sa propre variation, et
celle-ci doit se retrouver a partir du cours et de la cloture precedente. Si
l'extraction glisse d'un champ, l'egalite tombe et l'on leve une erreur
plutot que de renvoyer un chiffre plausible mais faux.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from ..models import Observation, SourceError
from .base import Source

URL = ("https://www.borsaitaliana.it/borsa/indici/indici-in-continua"
       "/dettaglio.html")

NAVIGATEUR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

# Le cours et sa variation, dans le bandeau de tete.
_COURS = re.compile(r'-formatPrice[^>]*>\s*<strong>\s*([\d.,]+)\s*</strong>')
_VARIATION = re.compile(r'-percPrice[^>]*>\s*<strong>\s*([+-]?[\d.,]+)\s*%')
# La cloture precedente, dans le tableau des donnees de marche.
_CLOTURE_VEILLE = re.compile(
    r'Chiusura\s+precedente.*?([\d]{1,3}(?:\.[\d]{3})*,[\d]+)', re.S | re.I)
_HORODATAGE = re.compile(r'Ultimo\s+Valore:\s*<strong>\s*'
                         r'(\d{2})/(\d{2})/(\d{2})', re.S | re.I)

# Ecart tolere entre la variation recalculee et celle affichee, en points.
# La page arrondit au centieme, d'ou une marge un peu superieure a l'arrondi.
TOLERANCE_POINTS = 0.02


class BorsaItalianaSource(Source):
    name = "borsa_italiana"

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        page = self.fetcher.fetch(
            URL,
            params={"indexCode": spec.get("native_id", "FTSEMIB"), "lang": "it"},
            headers=NAVIGATEUR,
            as_json=False,
        )
        if not isinstance(page, str) or len(page) < 5_000:
            raise SourceError("page trop courte pour etre celle attendue")

        attendu = spec.get("expect_title", "FTSE MIB")
        if attendu.upper() not in page.upper():
            raise SourceError(f"la page ne mentionne pas {attendu!r}")

        cours = _nombre(_extraire(_COURS, page, "cours"))
        veille = _nombre(_extraire(_CLOTURE_VEILLE, page, "cloture precedente"))
        variation_affichee = _nombre(_extraire(_VARIATION, page, "variation"))

        if veille <= 0:
            raise SourceError("cloture precedente nulle ou negative")

        # Le controle qui donne sa valeur a cette source : la page publie a la
        # fois le cours, la cloture precedente et la variation. Les trois
        # doivent se refermer sur eux-memes.
        recalculee = (cours - veille) / veille * 100
        ecart = abs(recalculee - variation_affichee)
        if ecart > TOLERANCE_POINTS:
            raise SourceError(
                f"lecture incoherente: {cours} contre {veille} donne "
                f"{recalculee:+.2f} %, la page affiche "
                f"{variation_affichee:+.2f} % (ecart {ecart:.2f} point)")

        return [self._obs(spec, _date(page), cours,
                          cloture_precedente=veille,
                          variation_pct=variation_affichee)]


def _extraire(motif: re.Pattern, page: str, quoi: str) -> str:
    trouve = motif.search(page)
    if not trouve:
        raise SourceError(f"{quoi} introuvable: la page a probablement change")
    return trouve.group(1)


def _nombre(brut: str) -> float:
    """Convertit la notation italienne « 52.665,82 » en nombre."""
    texte = brut.strip().replace(".", "").replace(",", ".")
    try:
        return float(texte)
    except ValueError as exc:
        raise SourceError(f"nombre illisible: {brut!r}") from exc


def _date(page: str) -> dt.date:
    trouve = _HORODATAGE.search(page)
    if not trouve:
        raise SourceError("horodatage introuvable")
    jour, mois, annee = (int(x) for x in trouve.groups())
    return dt.date(2000 + annee, mois, jour)
