"""Controles qualite et reconciliation entre sources.

Collecter beaucoup de donnees ne sert a rien si on ne sait pas lesquelles
sont fiables. Ce module produit, pour chaque serie, un verdict explicite:

* ``freshness``   - la derniere observation est-elle assez recente pour la
  frequence annoncee ?
* ``continuity``  - manque-t-il des points dans l'historique ?
* ``outlier``     - la derniere variation est-elle aberrante au regard de la
  volatilite historique de la serie ?
* ``reconcile``   - les sources qui couvrent la meme serie sont-elles
  d'accord *a date egale* ?

Le point important est la comparaison a date egale: comparer la derniere
valeur FRED (souvent decalee de quelques jours) a la derniere valeur BCE
produirait des divergences fantomes qui n'ont rien a voir avec la qualite
des donnees.
"""
from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import Observation

INFO, WARN, ERROR = "info", "warning", "error"

# Age maximal tolere de la derniere observation, par frequence.
MAX_AGE_DAYS = {
    "daily": 7,        # marge pour week-ends et jours feries
    "monthly": 75,     # les publications macro sortent avec ~1 mois de retard
    "quarterly": 150,
    "annual": 550,
}

# Ecart relatif attendu entre deux sources d'une meme serie, par categorie.
# Les series de marche doivent coller de tres pres; les agregats macro
# tolerent des ecarts de definition et de revision.
CATEGORY_TOLERANCE = {
    # Les parites sont fixees a des heures differentes selon le publicateur
    # (fixing BCE a 14h15 CET, taux "noon buying" de New York pour FRED):
    # un ecart de quelques dixiemes de pourcent est normal, pas une anomalie.
    "change": 0.004,
    "taux": 0.02,
    "actions": 0.005,
    "matieres": 0.02,
    "crypto": 0.01,
    "macro": 0.10,
    "fondamentaux": 0.01,
}

# Ecart absolu en dessous duquel on ne signale rien, meme si l'ecart relatif
# depasse le seuil. Sans ce plancher, deux series proches de zero (croissance
# du PIB a 0,7 % contre 0,86 %) affichent un ecart relatif de 19 % qui ne
# traduit aucune anomalie exploitable.
CATEGORY_ABS_FLOOR = {
    "change": 0.0,      # les parites sont d'ordre 1, le relatif suffit
    "taux": 0.03,       # 3 points de base
    "macro": 0.30,      # 0,3 point de pourcentage
    "actions": 0.0,
    "matieres": 0.0,
    "crypto": 0.0,
    "fondamentaux": 0.0,
}


@dataclass(slots=True)
class Check:
    series_id: str
    name: str
    severity: str
    passed: bool
    detail: str = ""


def _tolerance(category: str, default: float) -> float:
    return CATEGORY_TOLERANCE.get(category, default)


def _abs_floor(category: str) -> float:
    return CATEGORY_ABS_FLOOR.get(category, 0.0)


def check_freshness(series_id: str, obs: Sequence[Observation], frequency: str,
                    today: dt.date | None = None) -> Check:
    today = today or dt.date.today()
    if not obs:
        return Check(series_id, "freshness", ERROR, False, "aucune observation")
    latest = max(o.date for o in obs)
    # Les projections (FMI) sont datees dans le futur: la fraicheur n'a pas
    # de sens, on la considere satisfaite.
    if latest > today:
        return Check(series_id, "freshness", INFO, True,
                     f"serie prospective (horizon {latest})")
    age = (today - latest).days
    limit = MAX_AGE_DAYS.get(frequency, 90)
    if age <= limit:
        return Check(series_id, "freshness", INFO, True,
                     f"derniere valeur au {latest} ({age} j)")
    return Check(series_id, "freshness", WARN, False,
                 f"donnee obsolete: {latest} soit {age} j "
                 f"(seuil {limit} j pour frequence {frequency})")


def check_continuity(series_id: str, obs: Sequence[Observation],
                     frequency: str) -> Check:
    # Dedoublonnage indispensable: quand plusieurs sources couvrent la meme
    # serie, les dates se repetent et le pas median tomberait a zero, ce qui
    # ferait passer chaque intervalle normal pour un trou.
    dates = sorted({o.date for o in obs})
    if len(dates) < 3:
        return Check(series_id, "continuity", INFO, True, "historique trop court")
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    median_gap = statistics.median(gaps)
    # Un trou est un intervalle nettement superieur au pas median observe.
    threshold = max(median_gap * 4, median_gap + 5)
    holes = [(a, b) for a, b in zip(dates, dates[1:]) if (b - a).days > threshold]
    if not holes:
        return Check(series_id, "continuity", INFO, True,
                     f"{len(dates)} points, pas median {median_gap:.0f} j")
    worst = max(holes, key=lambda p: (p[1] - p[0]).days)
    return Check(series_id, "continuity", WARN, False,
                 f"{len(holes)} trou(s), le plus large entre {worst[0]} et "
                 f"{worst[1]} ({(worst[1]-worst[0]).days} j)")


def check_outlier(series_id: str, obs: Sequence[Observation],
                  z_threshold: float = 6.0) -> Check:
    """Compare la derniere variation a la distribution des variations passees."""
    if len(obs) < 12:
        return Check(series_id, "outlier", INFO, True, "historique trop court")
    ordered = sorted(obs, key=lambda o: o.date)
    values = [o.value for o in ordered]
    diffs = [b - a for a, b in zip(values, values[1:])]
    if len(diffs) < 8:
        return Check(series_id, "outlier", INFO, True, "historique trop court")

    body, last = diffs[:-1], diffs[-1]
    mean = statistics.fmean(body)
    stdev = statistics.pstdev(body)
    if stdev == 0:
        # Serie plate (taux directeur par ex.): tout mouvement est notable
        # mais pas anormal, on ne cree pas de faux positif.
        return Check(series_id, "outlier", INFO, True, "serie constante")
    z = abs(last - mean) / stdev
    if z <= z_threshold:
        return Check(series_id, "outlier", INFO, True,
                     f"derniere variation a {z:.1f} ecart-type")
    return Check(series_id, "outlier", WARN, False,
                 f"variation anormale le {ordered[-1].date}: "
                 f"{values[-2]:.4f} -> {values[-1]:.4f} ({z:.1f} ecart-types)")


def reconcile(series_id: str, by_source: dict[str, list[Observation]],
              category: str, default_tolerance: float = 0.005) -> list[Check]:
    """Compare les sources d'une meme serie sur leurs dates communes."""
    sources = [s for s, o in by_source.items() if o]
    if len(sources) < 2:
        return [Check(series_id, "reconcile", INFO, True,
                      "une seule source, pas de recoupement possible")]

    tol = _tolerance(category, default_tolerance)
    floor = _abs_floor(category)
    indexed = {
        src: {o.date: o.value for o in obs} for src, obs in by_source.items() if obs
    }
    checks: list[Check] = []
    reference = max(sources, key=lambda s: len(indexed[s]))

    for src in sources:
        if src == reference:
            continue
        common = sorted(set(indexed[reference]) & set(indexed[src]), reverse=True)
        if not common:
            checks.append(Check(
                series_id, f"reconcile:{reference}~{src}", WARN, False,
                "aucune date commune: sources non comparables "
                f"({reference} s'arrete le {max(indexed[reference])}, "
                f"{src} le {max(indexed[src])})"))
            continue

        # On evalue sur les dates communes les plus recentes.
        sample = common[:10]
        worst_date, worst_rel, worst_abs = None, 0.0, 0.0
        for d in sample:
            a, b = indexed[reference][d], indexed[src][d]
            denom = max(abs(a), abs(b), 1e-9)
            rel = abs(a - b) / denom
            if rel > worst_rel:
                worst_date, worst_rel, worst_abs = d, rel, abs(a - b)

        if worst_rel <= tol or worst_abs <= floor:
            checks.append(Check(
                series_id, f"reconcile:{reference}~{src}", INFO, True,
                f"accord sur {len(sample)} date(s) communes "
                f"(ecart max {worst_rel*100:.3f}%, seuil {tol*100:.2f}% "
                f"/ plancher {floor:g})"))
            continue

        a = indexed[reference][worst_date]
        b = indexed[src][worst_date]
        detail = (f"divergence le {worst_date}: {reference}={a:.4f} vs "
                  f"{src}={b:.4f} ({worst_rel*100:.2f}% > {tol*100:.2f}%)")
        hint = _scale_hint(a, b)
        if hint:
            detail += f" - {hint}"
        checks.append(Check(series_id, f"reconcile:{reference}~{src}",
                            ERROR if worst_rel > 10 * tol else WARN, False, detail))
    return checks


def _scale_hint(a: float, b: float) -> str:
    """Detecte les divergences qui ressemblent a une erreur d'unite."""
    if a == 0 or b == 0:
        return ""
    ratio = a / b
    for factor in (10, 100, 1000, 0.1, 0.01, 0.001):
        if abs(ratio - factor) / factor < 0.02:
            return f"rapport proche de x{factor}, probable probleme d'echelle"
    return ""


def consensus(by_source: dict[str, list[Observation]],
              priority: Sequence[str]) -> Observation | None:
    """Choisit la valeur de reference d'une serie.

    On privilegie la source la plus fraiche; a fraicheur egale, l'ordre de
    priorite (source officielle avant source de marche) tranche.
    """
    latest: list[Observation] = []
    for obs in by_source.values():
        if obs:
            latest.append(max(obs, key=lambda o: o.date))
    if not latest:
        return None
    rank = {s: i for i, s in enumerate(priority)}
    return sorted(latest, key=lambda o: (-o.date.toordinal(),
                                         rank.get(o.source, 99)))[0]


def summarize(checks: Iterable[Check]) -> dict[str, int]:
    out = {"total": 0, "passed": 0, "warning": 0, "error": 0}
    for c in checks:
        out["total"] += 1
        if c.passed:
            out["passed"] += 1
        elif c.severity == ERROR:
            out["error"] += 1
        else:
            out["warning"] += 1
    return out
