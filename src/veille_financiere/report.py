"""Rendu du rapport de veille (console et Markdown)."""
from __future__ import annotations


from .pipeline import RunResult, SeriesReport

STATUS_MARK = {"ok": "OK", "warning": "!!", "error": "XX"}

# Un ecart statistique n'est pas un defaut de collecte : c'est le mouvement
# lui-meme qui est remarquable. Le confondre avec une donnee obsolete ou deux
# sources en desaccord noie l'information dans le bruit technique.
CHECKS_INFORMATIFS = {"outlier"}


def _partager_constats(run):
    """Separe ce qui met la donnee en doute de ce qui merite d'etre lu."""
    doutes, mouvements = [], []
    for rapport in run.reports:
        for controle in rapport.checks:
            if controle.passed:
                continue
            cible = (mouvements if controle.name in CHECKS_INFORMATIFS
                     else doutes)
            cible.append((rapport, controle))
    return doutes, mouvements


def _decrire_mouvement(rapport, controle) -> str:
    """Reformule un ecart statistique en langage lisible."""
    obs = sorted(rapport.by_source.get(
        rapport.reference.source if rapport.reference else "", []),
        key=lambda o: o.date)
    if len(obs) < 2:
        return controle.detail
    avant, apres = obs[-2].value, obs[-1].value
    if avant == 0:
        return controle.detail
    variation = (apres - avant) / abs(avant) * 100
    return (f"{_fmt_nombre(avant)} -> {_fmt_nombre(apres)} "
            f"({variation:+.1f} %) au {obs[-1].date}")


def _fmt_nombre(v: float) -> str:
    if abs(v) >= 1e9:
        return f"{v/1e9:,.2f} Md"
    if abs(v) >= 1e6:
        return f"{v/1e6:,.2f} M"
    return f"{v:,.2f}"

CATEGORY_LABEL = {
    "change": "Taux de change",
    "taux": "Taux d'interet",
    "macro": "Macroeconomie",
    "actions": "Marches actions",
    "matieres": "Matieres premieres",
    "crypto": "Crypto-actifs",
    "fondamentaux": "Fondamentaux societes",
    "credit": "Credit et conditions financieres",
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
        f"{s['events']} evenements | "
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

    released, upcoming = run.events_released(), run.events_upcoming()
    if released or upcoming:
        lines.append("-- AGENDA MACROECONOMIQUE " + "-" * 58)
        for title, evts in (("deja paru", released[:8]),
                            ("attendu", upcoming[:8])):
            if not evts:
                continue
            lines.append(f"   [{title}]")
            for e in evts:
                lines.append(
                    f"     {e.time or '--':9} {e.region:3} "
                    f"{e.event[:38]:40} constate={str(e.actual or '--'):>9} "
                    f"consensus={str(e.consensus or '--'):>9}")
        lines.append("")

    outlooks = [r for r in run.reports if r.outlook]
    if outlooks:
        lines.append("-- PROJECTIONS " + "-" * 69)
        for rep in sorted(outlooks, key=lambda r: r.series_id):
            o = rep.outlook
            lines.append(f"   {rep.label[:40]:42} {o.value:>10,.2f} "
                         f"a l'horizon {o.date.year} ({o.source})")
        lines.append("")

    doutes, mouvements = _partager_constats(run)

    if mouvements:
        lines.append("-- MOUVEMENTS NOTABLES " + "-" * 61)
        for rapport, controle in sorted(mouvements,
                                        key=lambda x: x[0].series_id):
            lines.append(f"   {rapport.label[:40]:42} "
                         f"{_decrire_mouvement(rapport, controle)}")
        lines.append("")

    if doutes:
        lines.append("-- POINTS D'ATTENTION " + "-" * 62)
        for _, c in sorted(doutes, key=lambda x: (x[1].severity != "error",
                                                  x[1].series_id)):
            mark = "XX" if c.severity == "error" else "!!"
            lines.append(f"   {mark} [{c.series_id}] {c.name}: {c.detail}")
        lines.append("")
    else:
        lines.append("   Aucune donnee mise en doute.\n")

    failed = [r for r in run.results if not r.ok]
    if failed:
        lines.append("-- APPELS EN ECHEC " + "-" * 65)
        for r in failed:
            lines.append(f"   {r.source:12} {r.series_id:32} {r.error[:70]}")
        lines.append("")
    return "\n".join(lines)


def _fmt_event_row(e) -> str:
    surprise = e.surprise()
    if surprise is None:
        verdict = ""
    elif surprise > 0:
        verdict = "au-dessus"
    elif surprise < 0:
        verdict = "en dessous"
    else:
        verdict = "conforme"
    return (f"| {e.time or '--'} | {e.region} | {e.event} "
            f"{'(' + e.period + ')' if e.period else ''} | "
            f"{e.actual or '--'} | {e.consensus or '--'} | "
            f"{e.previous or '--'} | {verdict} |")


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

    released, upcoming = run.events_released(), run.events_upcoming()
    if released or upcoming:
        out += ["## Agenda macroeconomique", ""]
        if released:
            out += [f"### Deja paru ({len(released)})", "",
                    "| Heure | Zone | Publication | Constate | Consensus | "
                    "Precedent | |", "|---|---|---|---:|---:|---:|---|"]
            out += [_fmt_event_row(e) for e in released[:20]]
            if len(released) > 20:
                out.append(f"\n*... et {len(released) - 20} autres.*")
            out.append("")
        if upcoming:
            out += [f"### Attendu ({len(upcoming)})", "",
                    "| Heure | Zone | Publication | Constate | Consensus | "
                    "Precedent | |", "|---|---|---|---:|---:|---:|---|"]
            out += [_fmt_event_row(e) for e in upcoming[:20]]
            if len(upcoming) > 20:
                out.append(f"\n*... et {len(upcoming) - 20} autres.*")
            out.append("")

    outlooks = [r for r in run.reports if r.outlook]
    if outlooks:
        out += ["## Projections", "",
                "*Previsions, tenues a l'ecart des chiffres constates.*", "",
                "| Serie | Valeur projetee | Horizon | Source |",
                "|---|---:|---|---|"]
        for rep in sorted(outlooks, key=lambda r: r.series_id):
            o = rep.outlook
            out.append(f"| {rep.label} | {o.value:,.2f} {rep.unit} | "
                       f"{o.date.year} | {o.source} |")
        out.append("")

    doutes, mouvements = _partager_constats(run)

    if mouvements:
        out += ["## Mouvements notables", "",
                "*Variations qui sortent nettement de l'ordinaire de leur "
                "serie. La donnee est verifiee ; c'est le mouvement qui est "
                "remarquable.*", "",
                "| Serie | Evolution |", "|---|---|"]
        for rapport, controle in sorted(mouvements,
                                        key=lambda x: x[0].series_id):
            out.append(f"| {rapport.label} | "
                       f"{_decrire_mouvement(rapport, controle)} |")
        out.append("")

    out += ["## Points d'attention", ""]
    if doutes:
        out += ["| Gravite | Serie | Controle | Detail |", "|---|---|---|---|"]
        for _, c in sorted(doutes,
                           key=lambda x: (x[1].severity != "error",
                                          x[1].series_id)):
            out.append(f"| {c.severity} | `{c.series_id}` | {c.name} | {c.detail} |")
    else:
        out.append("Aucune donnee mise en doute.")
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
