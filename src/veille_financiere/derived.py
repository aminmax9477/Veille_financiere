"""Series calculees a partir des series collectees.

Un ecart de taux entre deux pays, ou la pente d'une courbe, n'est publie
nulle part tel quel : c'est une soustraction. La calculer ici plutot que de
la chercher chez un fournisseur a deux avantages. Elle est disponible des
que ses deux composantes le sont, sans appel reseau supplementaire. Et
surtout, elle est coherente avec le reste du rapport : le spread affiche est
exactement la difference des deux rendements affiches au-dessus, ce qui ne
serait pas garanti en le prenant chez un tiers qui l'aurait calcule a une
autre heure ou sur une autre cotation.

Chaque calcul n'est effectue que sur les dates ou *toutes* les composantes
existent, pour la meme raison qui gouverne la reconciliation : melanger des
dates fabriquerait un chiffre qui ne correspond a aucun jour reel.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .models import Observation


@dataclass(frozen=True, slots=True)
class DerivedSpec:
    series_id: str
    label: str
    unit: str
    category: str
    frequency: str
    inputs: tuple[str, ...]
    combine: Callable[[Sequence[float]], float]
    explanation: str = ""


def _difference(valeurs: Sequence[float]) -> float:
    return valeurs[0] - valeurs[1]


def _residu_fisher(valeurs: Sequence[float]) -> float:
    """Taux reel + point mort d'inflation - taux nominal.

    L'identite de Fisher veut que ce residu soit proche de zero. Les trois
    series viennent de la meme source mais de trois mesures independantes :
    un ecart qui se creuse signale qu'une des trois a decroche.
    """
    reel, point_mort, nominal = valeurs
    return reel + point_mort - nominal


CATALOGUE: tuple[DerivedSpec, ...] = (
    DerivedSpec(
        series_id="spread.oat_bund",
        label="Spread OAT-Bund 10 ans",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.fr10y", "rate.de10y"), combine=_difference,
        explanation="prime de risque francaise face a l'Allemagne",
    ),
    DerivedSpec(
        series_id="spread.btp_bund",
        label="Spread BTP-Bund 10 ans",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.it10y", "rate.de10y"), combine=_difference,
        explanation="prime de risque italienne face a l'Allemagne",
    ),
    DerivedSpec(
        series_id="spread.bonos_bund",
        label="Spread Bonos-Bund 10 ans",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.es10y", "rate.de10y"), combine=_difference,
        explanation="prime de risque espagnole face a l'Allemagne",
    ),
    DerivedSpec(
        series_id="spread.gilt_bund",
        label="Spread Gilt-Bund 10 ans",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.gb10y", "rate.de10y"), combine=_difference,
        explanation="ecart britannique face a l'Allemagne",
    ),
    DerivedSpec(
        series_id="spread.us_de_10y",
        label="Ecart de taux 10 ans Etats-Unis - Allemagne",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.us10y", "rate.de10y"), combine=_difference,
        explanation="differentiel transatlantique, moteur de l'euro-dollar",
    ),
    DerivedSpec(
        series_id="spread.us_curve_30_10",
        label="Pente de la courbe US (30 ans - 10 ans)",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.us30y", "rate.us10y"), combine=_difference,
        explanation="pentification du long terme",
    ),
    DerivedSpec(
        series_id="control.fisher_us_10y",
        label="Residu de Fisher 10 ans US (reel + point mort - nominal)",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.us_real_10y", "rate.us_breakeven_10y", "rate.us10y"),
        combine=_residu_fisher,
        explanation="controle de coherence, attendu proche de zero",
    ),
    DerivedSpec(
        series_id="spread.jp_curve_10_2",
        label="Pente de la courbe japonaise (10 ans - 2 ans)",
        unit="points de %", category="taux", frequency="daily",
        inputs=("rate.jp10y", "rate.jp02y"), combine=_difference,
        explanation="sortie de la politique de controle de la courbe",
    ),
)


def compute(reference_par_serie: dict[str, dict[Any, float]]
            ) -> dict[str, list[Observation]]:
    """Calcule les series derivees a partir des observations disponibles.

    ``reference_par_serie`` associe un identifiant de serie a ses valeurs
    indexees par date, deja reduites a une source unique par le consensus.
    """
    resultats: dict[str, list[Observation]] = {}
    for spec in toutes_les_specs():
        sources = [reference_par_serie.get(i) or {} for i in spec.inputs]
        if any(not s for s in sources):
            continue
        dates_communes = set(sources[0])
        for autre in sources[1:]:
            dates_communes &= set(autre)
        if not dates_communes:
            continue
        observations = [
            Observation(
                series_id=spec.series_id,
                source="calcule",
                date=jour,
                value=spec.combine([s[jour] for s in sources]),
                unit=spec.unit,
                frequency=spec.frequency,
                meta={"composantes": list(spec.inputs)},
            )
            for jour in sorted(dates_communes, reverse=True)
        ]
        resultats[spec.series_id] = observations
    return resultats


def _specs_societes() -> tuple[DerivedSpec, ...]:
    """Passif total deduit de l'identite comptable, par societe.

    Toutes les societes ne deposent pas la balise ``Liabilities`` : Amazon
    ne la publie pas du tout. Or le passif se retrouve exactement par
    difference entre l'actif et les capitaux propres, deux balises qu'elles
    deposent toutes. Ces series ne servent que de filet : le pipeline les
    ignore la ou le passif a bien ete collecte.
    """
    from .registry import COMPANIES
    return tuple(
        DerivedSpec(
            series_id=f"fundamental.{ticker.lower()}.liabilities",
            label=f"{comp['label']} - Passif total",
            unit="USD", category="fondamentaux", frequency="instant",
            inputs=(f"fundamental.{ticker.lower()}.assets",
                    f"fundamental.{ticker.lower()}.equity"),
            combine=_difference,
            explanation="deduit : actif total moins capitaux propres",
        )
        for ticker, comp in COMPANIES.items()
    )


def toutes_les_specs() -> tuple[DerivedSpec, ...]:
    return CATALOGUE + _specs_societes()


def spec_par_id() -> dict[str, DerivedSpec]:
    return {s.series_id: s for s in toutes_les_specs()}
