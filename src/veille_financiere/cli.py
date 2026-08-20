"""Interface en ligne de commande de la veille financiere."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import settings
from .pipeline import run as run_pipeline
from .registry import CATALOGUE, COMPANIES
from .report import render_console, render_markdown
from .storage import Store


def _cmd_collect(args: argparse.Namespace) -> int:
    result = run_pipeline(
        settings,
        include_fundamentals=not args.no_fundamentals,
        only_sources=set(args.source) if args.source else None,
        only_series=set(args.series) if args.series else None,
        persist=not args.no_store,
    )
    if args.format == "markdown":
        text = render_markdown(result)
    elif args.format == "json":
        text = json.dumps({
            "run_id": result.run_id,
            "started_at": result.started_at.isoformat(),
            "summary": result.summary(),
            "series": [
                {
                    "series_id": r.series_id, "label": r.label, "unit": r.unit,
                    "category": r.category, "status": r.status,
                    "value": r.reference.value if r.reference else None,
                    "date": r.reference.date.isoformat() if r.reference else None,
                    "source": r.reference.source if r.reference else None,
                    "sources_used": sorted(r.by_source),
                    "checks": [
                        {"name": c.name, "severity": c.severity,
                         "passed": c.passed, "detail": c.detail}
                        for c in r.checks
                    ],
                }
                for r in result.reports
            ],
        }, indent=2, ensure_ascii=False)
    else:
        text = render_console(result)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"rapport ecrit dans {args.output}")
    else:
        print(text)

    s = result.summary()
    if args.strict and (s["error"] or s["sources_failed"]):
        return 1
    return 0


def _cmd_catalogue(args: argparse.Namespace) -> int:
    print(f"{len(CATALOGUE)} series canoniques\n")
    for series_id, entry in sorted(CATALOGUE.items()):
        provs = ", ".join(p["source"] for p in entry["providers"])
        print(f"  {series_id:26} {entry['label'][:40]:42} [{provs}]")
    print(f"\n{len(COMPANIES)} societes suivies via SEC EDGAR: "
          f"{', '.join(sorted(COMPANIES))}")
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    store = Store(settings.db_path)
    try:
        rows = store.history(args.series_id, args.source, args.limit)
        if not rows:
            print(f"aucune donnee pour {args.series_id} "
                  f"(lancer 'collect' d'abord)")
            return 1
        print(f"{'date':12} {'valeur':>16} {'source':12}")
        for r in rows:
            print(f"{r['date']:12} {r['value']:>16,.4f} {r['source']:12}")
    finally:
        store.close()
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Verifie la configuration et la joignabilite de chaque source."""
    print("Configuration:")
    print(f"  base de donnees : {settings.db_path}")
    print(f"  cache           : {settings.cache_dir} (TTL {settings.cache_ttl}s)")
    print(f"  cle FRED        : {'presente' if settings.fred_api_key else 'ABSENTE'}")
    print(f"  cle LSE         : {'presente' if settings.lse_api_key else 'ABSENTE'}")
    print(f"  contact SEC     : {settings.sec_contact or 'non declare'}")
    print("\nTest de joignabilite (1 serie par source):")

    probes = {
        "fred": "rate.us10y", "ecb": "fx.eurusd", "eurostat": "macro.ea_hicp_yoy",
        "oecd": "equity.fr_share_index_m", "worldbank": "macro.fr_gdp_growth",
        "imf": "macro.fr_gdp_growth", "frankfurter": "fx.eurusd",
        "coingecko": "crypto.btcusd", "yahoo": "equity.sp500",
        "lse": "equity.cac40",
        "sec_edgar": "fundamental.aapl.assets",
    }
    enabled = settings.enabled_sources()
    disabled = [s for s, on in enabled.items() if not on]
    if disabled:
        print(f"  (desactivees faute de cle: {', '.join(sorted(disabled))})")
    probes = {s: sid for s, sid in probes.items() if enabled.get(s, True)}

    ok = 0
    for source, series_id in probes.items():
        res = run_pipeline(settings,
                           include_fundamentals=(source == "sec_edgar"),
                           only_sources={source}, only_series={series_id},
                           persist=False)
        calls = [r for r in res.results if r.source == source]
        good = [r for r in calls if r.ok and r.observations]
        if good:
            ok += 1
            latest = good[0].latest
            print(f"  OK   {source:12} {latest.date}  {latest.value:,.4f}")
        else:
            err = calls[0].error[:70] if calls else "aucun appel"
            print(f"  ECHEC {source:12} {err}")
    print(f"\n{ok}/{len(probes)} sources joignables")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="veille", description="Veille financiere multi-sources")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("collect", help="collecte, controle et rapport")
    p.add_argument("-f", "--format", choices=["console", "markdown", "json"],
                   default="console")
    p.add_argument("-o", "--output", help="fichier de sortie")
    p.add_argument("--source", action="append", help="limiter a ces sources")
    p.add_argument("--series", action="append", help="limiter a ces series")
    p.add_argument("--no-fundamentals", action="store_true",
                   help="ignorer les fondamentaux SEC EDGAR")
    p.add_argument("--no-store", action="store_true",
                   help="ne pas ecrire en base")
    p.add_argument("--strict", action="store_true",
                   help="code de sortie 1 si erreur ou appel en echec")
    p.set_defaults(func=_cmd_collect)

    p = sub.add_parser("catalogue", help="lister les series suivies")
    p.set_defaults(func=_cmd_catalogue)

    p = sub.add_parser("history", help="historique d'une serie en base")
    p.add_argument("series_id")
    p.add_argument("--source")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=_cmd_history)

    p = sub.add_parser("doctor", help="diagnostiquer configuration et sources")
    p.set_defaults(func=_cmd_doctor)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
