"""Rendu du rapport de veille (console et Markdown)."""
from __future__ import annotations


from .pipeline import RunResult, SeriesReport

STATUS_MARK = {"ok": "OK", "warning": "!!", "error": "XX"}

CATEGORY_LABEL = {
    "change": "Taux de change",
    "taux": "Taux d'interet",
    "macro": "Macroeconomie",
    "actions": "Marches actions",
    "matieres": "Matieres premieres",
    "crypto": "Crypto-actifs",
    "fondamentaux": "Fondamentaux societes",
}


def _fmt_value(rep: SeriesReport) -> str:
    if not rep.reference:
        return "n/d"
    v = rep.reference.value
    if abs(v) >= 1e9:
        return f"{v/1e9:,.2f} Md"
    if abs(v) >= 1e6:
        return f"{v/1e6:,.2f} M"
    if abs(v) >= 100:
        return f"{v:,.2f}"
    return f"{v:,.4f}"


def _fmt_change(rep: SeriesReport) -> str:
    ch = rep.change()
    if ch is None:
        return ""
    # "pt" = points de pourcentage, pour ne pas confondre avec une variation
    # relative sur une serie qui est elle-meme un pourcentage.
    return f"{ch:+.2f} pt" if rep.is_percentage else f"{ch:+.2f}%"


def render_console(run: RunResult) -> str:
    s = run.summary()
    lines = [
        "",
        "=" * 96,
        f"  VEILLE FINANCIERE - {run.started_at:%Y-%m-%d %H:%M UTC}"
        f"   (run {run.run_id})",
        "=" * 96,
        f"  {s['series']} series | {s['observations']} observations | "
        f"{s['sources_ok']} appels OK / {s['sources_failed']} en echec",
        f"  controles: {s['passed']}/{s['total']} valides, "
        f"{s['warning']} avertissement(s), {s['error']} erreur(s)",
        "",
    ]

    by_cat: dict[str, list[SeriesReport]] = {}
    for rep in run.reports:
        by_cat.setdefault(rep.category or "autre", []).append(rep)

    for cat in sorted(by_cat):
        lines.append(f"-- {CATEGORY_LABEL.get(cat, cat).upper()} " + "-" * 60)
        lines.append(f"   {'':2} {'serie':34} {'valeur':>16} {'var':>9}  "
                     f"{'date':10} source")
        for rep in sorted(by_cat[cat], key=lambda r: r.series_id):
            ref = rep.reference
            lines.append(
                f"   {STATUS_MARK[rep.status]:2} {rep.label[:34]:34} "
                f"{_fmt_value(rep):>16} {_fmt_change(rep):>9}  "
                f"{str(ref.date) if ref else 'n/d':10} "
                f"{ref.source if ref else '-'}"
            )
        lines.append("")

    problems = [c for r in run.reports for c in r.checks if not c.passed]
    if problems:
        lines.append("-- POINTS D'ATTENTION " + "-" * 62)
        for c in sorted(problems, key=lambda c: (c.severity != "error", c.series_id)):
            mark = "XX" if c.severity == "error" else "!!"
            lines.append(f"   {mark} [{c.series_id}] {c.name}: {c.detail}")
        lines.append("")
    else:
        lines.append("   Aucun point d'attention.\n")

    failed = [r for r in run.results if not r.ok]
    if failed:
        lines.append("-- APPELS EN ECHEC " + "-" * 65)
        for r in failed:
            lines.append(f"   {r.source:12} {r.series_id:32} {r.error[:70]}")
        lines.append("")
    return "\n".join(lines)


def render_markdown(run: RunResult) -> str:
    s = run.summary()
    out = [
        f"# Veille financiere - {run.started_at:%d/%m/%Y %H:%M UTC}",
        "",
        f"*Run `{run.run_id}` - {s['series']} series, {s['observations']} "
        f"observations, {s['sources_ok']}/{s['sources_ok']+s['sources_failed']} "
        f"appels reussis.*",
        "",
        f"**Qualite** : {s['passed']}/{s['total']} controles valides "
        f"({s['warning']} avertissement(s), {s['error']} erreur(s))",
        "",
    ]

    by_cat: dict[str, list[SeriesReport]] = {}
    for rep in run.reports:
        by_cat.setdefault(rep.category or "autre", []).append(rep)

    for cat in sorted(by_cat):
        out += [f"## {CATEGORY_LABEL.get(cat, cat)}", "",
                "| | Serie | Valeur | Unite | Var. | Date | Source | Sources |",
                "|---|---|---:|---|---:|---|---|---|"]
        for rep in sorted(by_cat[cat], key=lambda r: r.series_id):
            ref = rep.reference
            icon = {"ok": "OK", "warning": "WARN", "error": "ERR"}[rep.status]
            out.append(
                f"| {icon} | {rep.label} | {_fmt_value(rep)} | {rep.unit} | "
                f"{_fmt_change(rep)} | {ref.date if ref else 'n/d'} | "
                f"{ref.source if ref else '-'} | {len(rep.by_source)} |"
            )
        out.append("")

    problems = [c for r in run.reports for c in r.checks if not c.passed]
    out += ["## Points d'attention", ""]
    if problems:
        out += ["| Gravite | Serie | Controle | Detail |", "|---|---|---|---|"]
        for c in sorted(problems, key=lambda c: (c.severity != "error", c.series_id)):
            out.append(f"| {c.severity} | `{c.series_id}` | {c.name} | {c.detail} |")
    else:
        out.append("Aucun point d'attention.")
    out.append("")

    failed = [r for r in run.results if not r.ok]
    if failed:
        out += ["## Appels en echec", "", "| Source | Serie | Erreur |",
                "|---|---|---|"]
        for r in failed:
            out.append(f"| {r.source} | `{r.series_id}` | {r.error[:160]} |")
        out.append("")

    out += ["---", "",
            "Sources : BCE, FRED (Federal Reserve Bank of St. Louis), Eurostat, "
            "Banque mondiale, FMI, SEC EDGAR, CoinGecko, Frankfurter, "
            "Yahoo Finance.", ""]
    return "\n".join(out)
