"""Tests des controles qualite et de la reconciliation inter-sources."""
import datetime as dt

import pytest

from veille_financiere.models import Observation
from veille_financiere.quality import (
    check_continuity, check_freshness, check_outlier, consensus, reconcile,
    summarize,
)

TODAY = dt.date(2026, 8, 20)


def obs(source, date, value, series="s"):
    return Observation(series_id=series, source=source, date=date, value=value)


def daily(source, n, start=1.0, step=0.001, end=TODAY):
    return [obs(source, end - dt.timedelta(days=i), start + i * step)
            for i in range(n)]


# --------------------------------------------------------------- fraicheur
def test_fraicheur_ok_pour_une_serie_du_jour():
    c = check_freshness("s", daily("ecb", 5), "daily", today=TODAY)
    assert c.passed


def test_fraicheur_signale_une_serie_obsolete():
    old = [obs("eurostat", dt.date(2025, 12, 31), 1.9)]
    c = check_freshness("s", old, "monthly", today=TODAY)
    assert not c.passed and "obsolete" in c.detail


def test_fraicheur_tolere_les_projections_futures():
    """Le FMI publie des projections datees dans le futur."""
    proj = [obs("imf", dt.date(2031, 12, 31), 1.1)]
    c = check_freshness("s", proj, "annual", today=TODAY)
    assert c.passed and "prospective" in c.detail


def test_fraicheur_echoue_sans_observation():
    c = check_freshness("s", [], "daily", today=TODAY)
    assert not c.passed and c.severity == "error"


# --------------------------------------------------------------- continuite
def test_continuite_ne_signale_rien_sur_une_serie_reguliere():
    monthly = [obs("ecb", dt.date(2025, m, 28), 2.0) for m in range(1, 13)]
    assert check_continuity("s", monthly, "monthly").passed


def test_continuite_tolere_les_dates_dupliquees_multi_sources():
    """Regression: deux sources aux memes dates ramenaient le pas median a 0,
    faisant passer chaque intervalle normal pour un trou."""
    dates = [dt.date(2025, m, 28) for m in range(1, 13)]
    both = ([obs("ecb", d, 2.0) for d in dates]
            + [obs("eurostat", d, 2.1) for d in dates])
    c = check_continuity("s", both, "monthly")
    assert c.passed, c.detail


def test_continuite_detecte_un_vrai_trou():
    dates = [dt.date(2025, 1, 31), dt.date(2025, 2, 28), dt.date(2025, 3, 31),
             dt.date(2026, 6, 30)]     # 15 mois manquants
    c = check_continuity("s", [obs("x", d, 1.0) for d in dates], "monthly")
    assert not c.passed and "trou" in c.detail


# ----------------------------------------------------------------- outliers
def test_outlier_ignore_une_serie_stable():
    assert check_outlier("s", daily("fred", 40, step=0.01)).passed


def test_outlier_detecte_un_saut_brutal():
    series = daily("fred", 30, step=0.001)
    series.sort(key=lambda o: o.date)
    series[-1] = obs("fred", series[-1].date, 500.0)   # valeur aberrante
    c = check_outlier("s", series)
    assert not c.passed and "anormale" in c.detail


def test_outlier_ne_signale_pas_une_serie_constante():
    flat = [obs("ecb", TODAY - dt.timedelta(days=i), 2.25) for i in range(30)]
    assert check_outlier("s", flat).passed


# ------------------------------------------------------------ reconciliation
def test_reconciliation_sans_recoupement_possible():
    c = reconcile("s", {"ecb": daily("ecb", 3)}, "change")
    assert c[0].passed and "une seule source" in c[0].detail


def test_reconciliation_valide_deux_sources_concordantes():
    d = TODAY
    by = {"ecb": [obs("ecb", d, 1.1681)], "frankfurter": [obs("frankfurter", d, 1.1681)]}
    checks = reconcile("s", by, "change")
    assert all(c.passed for c in checks)


def test_reconciliation_detecte_une_divergence_reelle():
    d = TODAY
    by = {"a": [obs("a", d, 1.1681)], "b": [obs("b", d, 1.2500)]}
    checks = reconcile("s", by, "change")
    assert any(not c.passed and "divergence" in c.detail for c in checks)


def test_reconciliation_compare_uniquement_les_dates_communes():
    """Deux sources fraiches a des dates differentes ne doivent pas etre
    comparees terme a terme: seule la date commune fait foi."""
    by = {
        "ecb": [obs("ecb", dt.date(2026, 8, 20), 1.1681),
                obs("ecb", dt.date(2026, 8, 14), 1.1567)],
        "fred": [obs("fred", dt.date(2026, 8, 14), 1.1581)],
    }
    checks = reconcile("s", by, "change")
    assert all(c.passed for c in checks), [c.detail for c in checks]


def test_reconciliation_signale_absence_de_date_commune():
    by = {
        "a": [obs("a", dt.date(2026, 8, 20), 1.16)],
        "b": [obs("b", dt.date(2026, 1, 5), 1.16)],
    }
    checks = reconcile("s", by, "change")
    assert any("aucune date commune" in c.detail for c in checks)


def test_plancher_absolu_evite_un_faux_positif_pres_de_zero():
    """0,70 % contre 0,86 % de croissance: 19 % d'ecart relatif mais
    seulement 0,16 point, ce qui ne constitue pas une anomalie."""
    d = dt.date(2016, 12, 31)
    by = {"imf": [obs("imf", d, 0.70)], "worldbank": [obs("worldbank", d, 0.86)]}
    assert all(c.passed for c in reconcile("s", by, "macro"))


def test_erreur_d_echelle_est_diagnostiquee():
    d = TODAY
    by = {"fred": [obs("fred", d, 4.71)], "yahoo": [obs("yahoo", d, 47.1)]}
    checks = reconcile("s", by, "taux")
    failed = [c for c in checks if not c.passed]
    assert failed and "echelle" in failed[0].detail


# ------------------------------------------------------------------ consensus
def test_consensus_prefere_la_source_la_plus_fraiche():
    by = {
        "fred": [obs("fred", dt.date(2026, 8, 14), 1.1581)],
        "ecb": [obs("ecb", dt.date(2026, 8, 20), 1.1681)],
    }
    ref = consensus(by, ["ecb", "fred"])
    assert ref.source == "ecb" and ref.date == dt.date(2026, 8, 20)


def test_consensus_departage_par_priorite_a_date_egale():
    d = TODAY
    by = {"yahoo": [obs("yahoo", d, 1.17)], "ecb": [obs("ecb", d, 1.1681)]}
    assert consensus(by, ["ecb", "fred", "yahoo"]).source == "ecb"


def test_consensus_renvoie_none_sans_donnee():
    assert consensus({"ecb": []}, ["ecb"]) is None


def test_summarize_compte_les_severites():
    from veille_financiere.quality import Check
    checks = [
        Check("s", "a", "info", True), Check("s", "b", "warning", False),
        Check("s", "c", "error", False),
    ]
    assert summarize(checks) == {"total": 3, "passed": 1, "warning": 1, "error": 1}


def test_tolerance_propre_a_une_serie_prime_sur_la_categorie():
    """Le VIX est dans la categorie actions mais bouge trop pour son seuil."""
    d = TODAY
    by = {"fred": [obs("fred", d, 15.15)], "lse": [obs("lse", d, 15.29)]}
    # 0,92 % d'ecart: refuse au seuil actions (0,5 %), accepte a celui du VIX.
    assert any(not c.passed for c in reconcile("equity.sp500", by, "actions"))
    assert all(c.passed for c in reconcile("equity.vix", by, "actions"))


def test_reference_ecarte_les_projections_futures():
    """Le FMI projette jusqu'en 2031: retenir cette valeur reviendrait a
    presenter une prevision comme le dernier chiffre connu."""
    from veille_financiere.quality import projection
    by = {
        "imf": [obs("imf", dt.date(2031, 12, 31), 1.1),
                obs("imf", dt.date(2025, 12, 31), 0.90)],
        "worldbank": [obs("worldbank", dt.date(2025, 12, 31), 0.84)],
    }
    ref = consensus(by, ["worldbank", "imf"], today=TODAY)
    assert ref.date == dt.date(2025, 12, 31)
    assert projection(by, today=TODAY).date == dt.date(2031, 12, 31)


def test_projection_absente_si_serie_entierement_passee():
    from veille_financiere.quality import projection
    assert projection({"ecb": daily("ecb", 5)}, today=TODAY) is None


def test_reference_none_si_tout_est_dans_le_futur():
    by = {"imf": [obs("imf", dt.date(2031, 12, 31), 1.1)]}
    assert consensus(by, ["imf"], today=TODAY) is None


def test_continuite_tolere_une_fermeture_de_fete_nationale():
    """La semaine d'or chinoise ferme la place une dizaine de jours : c'est
    une coupure normale, pas une donnee manquante."""
    dates = [dt.date(2025, 9, d) for d in (26, 29, 30)]
    dates += [dt.date(2025, 10, d) for d in (9, 10, 13, 14, 15, 16, 17, 20)]
    c = check_continuity("rate.cn10y", [obs("eodhd", d, 1.7) for d in dates],
                         "daily")
    assert c.passed, c.detail


def test_continuite_signale_encore_un_vrai_trou_quotidien():
    dates = [dt.date(2026, 1, d) for d in (5, 6, 7)] + [dt.date(2026, 3, 2)]
    c = check_continuity("x", [obs("eodhd", d, 1.0) for d in dates], "daily")
    assert not c.passed
