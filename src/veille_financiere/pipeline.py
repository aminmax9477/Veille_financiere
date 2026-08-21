"""Orchestration: collecte, controle qualite, persistance."""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from . import derived
from . import sources as S
from .config import Settings, settings as default_settings
from .http import Fetcher, HttpCache
from .models import CalendarEvent, Observation, SeriesResult
from .quality import (
    Check, check_continuity, check_freshness, check_outlier, consensus,
    projection, reconcile, summarize,
)
from .registry import CATALOGUE, iter_company_specs, iter_specs
from .storage import Store

log = logging.getLogger(__name__)

# Ordre de confiance: institutions officielles avant agregateurs de marche.
SOURCE_PRIORITY = [
    "ecb", "fred", "eurostat", "sec_edgar", "oecd", "eodhd", "worldbank", "imf",
    "lse", "frankfurter", "coingecko", "yahoo",
]


@dataclass(slots=True)
class SeriesReport:
    series_id: str
    label: str
    unit: str
    category: str
    frequency: str
    reference: Observation | None
    by_source: dict[str, list[Observation]]
    checks: list[Check] = field(default_factory=list)
    # Prevision a venir (FMI notamment), tenue a l'ecart de la reference.
    outlook: Observation | None = None

    @property
    def status(self) -> str:
        if not self.reference:
            return "error"
        if any(not c.passed and c.severity == "error" for c in self.checks):
            return "error"
        if any(not c.passed for c in self.checks):
            return "warning"
        return "ok"

    def change(self) -> float | None:
        """Variation par rapport au point precedent de la source de reference.

        Pour une serie deja exprimee en pourcentage (taux, inflation), on
        renvoie un ecart en points de pourcentage: dire qu'une inflation
        passee de 2,1 % a 1,9 % a baisse de 9,5 % serait trompeur.
        """
        if not self.reference:
            return None
        obs = sorted(self.by_source.get(self.reference.source, []),
                     key=lambda o: o.date)
        if len(obs) < 2:
            return None
        prev, last = obs[-2].value, obs[-1].value
        if self.is_percentage:
            return last - prev
        if prev == 0:
            return None
        return (last - prev) / abs(prev) * 100.0

    @property
    def is_percentage(self) -> bool:
        """Serie deja exprimee en pourcentage, ecart ou niveau.

        Un spread vaut 0,85 « point de pourcentage » : dire qu'il a varie de
        1,38 % laisserait croire a un mouvement relatif alors qu'il s'agit
        de 0,012 point.
        """
        return self.unit.strip() in ("%", "points de %")


@dataclass(slots=True)
class RunResult:
    run_id: str
    started_at: dt.datetime
    reports: list[SeriesReport]
    results: list[SeriesResult]
    events: list[CalendarEvent] = field(default_factory=list)

    @property
    def checks(self) -> list[Check]:
        return [c for r in self.reports for c in r.checks]

    def summary(self) -> dict[str, Any]:
        s = summarize(self.checks)
        s["series"] = len(self.reports)
        s["sources_ok"] = sum(1 for r in self.results if r.ok)
        s["sources_failed"] = sum(1 for r in self.results if not r.ok)
        s["observations"] = sum(len(r.observations) for r in self.results)
        s["events"] = len(self.events)
        return s

    def events_released(self) -> list[CalendarEvent]:
        """Publications deja parues, les plus recentes en tete."""
        return sorted([e for e in self.events if e.released],
                      key=lambda e: (e.date, e.time), reverse=True)

    def events_upcoming(self) -> list[CalendarEvent]:
        """Publications encore attendues, par ordre chronologique."""
        return sorted([e for e in self.events if not e.released],
                      key=lambda e: (e.date, e.time))


def build_sources(fetcher: Fetcher, cfg: Settings) -> dict[str, S.Source]:
    """Instancie les adaptateurs utilisables avec la configuration courante."""
    reg: dict[str, S.Source] = {
        "ecb": S.EcbSource(fetcher),
        "eurostat": S.EurostatSource(fetcher),
        "worldbank": S.WorldBankSource(fetcher),
        "imf": S.ImfSource(fetcher),
        "oecd": S.OecdSource(fetcher),
        "coingecko": S.CoinGeckoSource(fetcher),
        "frankfurter": S.FrankfurterSource(fetcher),
        "sec_edgar": S.SecEdgarSource(fetcher, cfg.sec_contact),
    }
    if cfg.fred_api_key:
        reg["fred"] = S.FredSource(fetcher, cfg.fred_api_key)
    else:
        log.warning("FRED_API_KEY absente: couverture macro US desactivee")
    if cfg.enable_yahoo:
        reg["yahoo"] = S.YahooSource(fetcher)
    if cfg.eodhd_api_key:
        reg["eodhd"] = S.EodhdSource(fetcher, cfg.eodhd_api_key)
    else:
        log.warning("EODHD_API_KEY absente: rendements souverains degrades")
    if cfg.lse_api_key:
        reg["lse"] = S.LseSource(fetcher, cfg.lse_api_key)
    else:
        log.warning("LSE_API_KEY absente: indices europeens et or desactives")
    return reg


def collect(specs: list[dict[str, Any]], registry: dict[str, S.Source],
            only_sources: set[str] | None = None) -> list[SeriesResult]:
    results: list[SeriesResult] = []
    for spec in specs:
        name = spec["source"]
        if only_sources and name not in only_sources:
            continue
        src = registry.get(name)
        if src is None:
            continue
        results.append(src.fetch(spec))
    return results


def collect_calendar(registry: dict[str, S.Source],
                     cfg: Settings) -> list[CalendarEvent]:
    """Agenda macro autour du jour courant; jamais bloquant."""
    src = registry.get("lse")
    if src is None:
        return []
    today = dt.date.today()
    try:
        return src.fetch_calendar(
            list(cfg.calendar_regions),
            today - dt.timedelta(days=cfg.calendar_lookback_days),
            today + dt.timedelta(days=cfg.calendar_lookahead_days),
        )
    except Exception as exc:  # noqa: BLE001 - l'agenda ne doit jamais casser le run
        log.warning("agenda economique indisponible: %s", exc)
        return []


def run(cfg: Settings | None = None, include_fundamentals: bool = True,
        only_sources: set[str] | None = None,
        only_series: set[str] | None = None,
        with_calendar: bool = True,
        persist: bool = True) -> RunResult:
    cfg = cfg or default_settings
    run_id = uuid.uuid4().hex[:12]
    started = dt.datetime.now(dt.timezone.utc)

    fetcher = Fetcher(cache=HttpCache(cfg.cache_dir, cfg.cache_ttl))
    registry = build_sources(fetcher, cfg)

    specs = iter_specs()
    if include_fundamentals:
        specs += iter_company_specs()
    # Un ensemble vide veut dire "aucune serie" (cas de la commande agenda),
    # a distinguer de None qui veut dire "toutes".
    if only_series is not None:
        specs = [s for s in specs if s["series_id"] in only_series]

    results = collect(specs, registry, only_sources)
    events = (collect_calendar(registry, cfg)
              if with_calendar and not only_sources else [])

    # Regroupement par serie canonique.
    grouped: dict[str, dict[str, list[Observation]]] = defaultdict(dict)
    for res in results:
        if res.ok and res.observations:
            grouped[res.series_id][res.source] = res.observations

    spec_by_series = {s["series_id"]: s for s in specs}
    reports: list[SeriesReport] = []
    for series_id, by_source in sorted(grouped.items()):
        entry = CATALOGUE.get(series_id, {})
        spec = spec_by_series.get(series_id, {})
        category = entry.get("category", spec.get("category", ""))
        frequency = entry.get("frequency", spec.get("frequency", ""))
        flat = [o for obs in by_source.values() for o in obs]
        ref = consensus(by_source, SOURCE_PRIORITY)
        outlook = projection(by_source)

        checks = [
            check_freshness(series_id, flat, frequency),
            check_continuity(series_id, flat, frequency),
        ]
        if ref:
            checks.append(check_outlier(series_id, by_source.get(ref.source, [])))
        checks += reconcile(series_id, by_source, category,
                            cfg.reconcile_tolerance)

        reports.append(SeriesReport(
            series_id=series_id,
            label=entry.get("label", spec.get("label", series_id)),
            unit=entry.get("unit", spec.get("unit", "")),
            category=category, frequency=frequency,
            reference=ref, by_source=by_source, checks=checks,
            outlook=outlook,
        ))

    # Series calculees: elles s'appuient sur la valeur de reference de chaque
    # composante, donc sur une seule source par serie, pour que le spread
    # affiche soit exactement la difference des rendements affiches.
    reference_par_serie: dict[str, dict[dt.date, float]] = {}
    for rapport in reports:
        if not rapport.reference:
            continue
        obs = rapport.by_source.get(rapport.reference.source, [])
        reference_par_serie[rapport.series_id] = {o.date: o.value for o in obs}

    deja_collectees = {r.series_id for r in reports if r.reference}
    for series_id, observations in derived.compute(reference_par_serie).items():
        # Une serie calculee ne sert que de filet : si la donnee a ete
        # collectee pour de vrai, elle fait foi.
        if series_id in deja_collectees:
            continue
        spec_derivee = derived.spec_par_id()[series_id]
        checks = [
            check_freshness(series_id, observations, spec_derivee.frequency),
            check_continuity(series_id, observations, spec_derivee.frequency),
            check_outlier(series_id, observations),
        ]
        reports.append(SeriesReport(
            series_id=series_id,
            label=spec_derivee.label,
            unit=spec_derivee.unit,
            category=spec_derivee.category,
            frequency=spec_derivee.frequency,
            reference=max(observations, key=lambda o: o.date),
            by_source={"calcule": observations},
            checks=checks,
        ))

    # Les series entierement en echec meritent d'apparaitre dans le rapport,
    # sauf celles qu'un calcul a comblees entre-temps : les signaler encore
    # afficherait deux fois la meme ligne, une fois renseignee et une fois
    # en erreur.
    comblees = {r.series_id for r in reports if r.reference}
    failed_ids = ({r.series_id for r in results if not r.ok}
                  - set(grouped) - comblees)
    for series_id in sorted(failed_ids):
        entry = CATALOGUE.get(series_id, {})
        spec = spec_by_series.get(series_id, {})
        errs = [r.error for r in results if r.series_id == series_id and not r.ok]
        reports.append(SeriesReport(
            series_id=series_id,
            label=entry.get("label", spec.get("label", series_id)),
            unit=entry.get("unit", spec.get("unit", "")),
            category=entry.get("category", spec.get("category", "")),
            frequency=entry.get("frequency", spec.get("frequency", "")),
            reference=None, by_source={},
            checks=[Check(series_id, "collecte", "error", False,
                          "; ".join(e[:120] for e in errs[:2]))],
        ))

    result = RunResult(run_id=run_id, started_at=started, reports=reports,
                       results=results, events=events)

    if persist:
        store = Store(cfg.db_path)
        try:
            for res in results:
                if res.ok:
                    store.upsert_observations(res.observations)
            for rapport in reports:
                if rapport.reference and rapport.reference.source == "calcule":
                    store.upsert_observations(rapport.by_source["calcule"])
            store.upsert_events(events)
            store.log_run(run_id, started.isoformat(), results)
            store.log_checks(run_id, started.isoformat(), result.checks)
        finally:
            store.close()

    return result
