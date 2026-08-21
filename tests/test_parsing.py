"""Tests des parseurs: formats de periode et reponses reelles des APIs."""
import datetime as dt

import pytest

from veille_financiere.models import SourceError
from veille_financiere.sources.base import parse_period


@pytest.mark.parametrize("raw,expected", [
    ("2026-08-20", dt.date(2026, 8, 20)),
    ("2026-08", dt.date(2026, 8, 31)),
    ("2026-02", dt.date(2026, 2, 28)),
    ("2024-02", dt.date(2024, 2, 29)),      # annee bissextile
    ("2026", dt.date(2026, 12, 31)),
    ("2026-Q1", dt.date(2026, 3, 31)),
    ("2026-Q4", dt.date(2026, 12, 31)),
    ("2025-M11", dt.date(2025, 11, 30)),
    ("2026-12", dt.date(2026, 12, 31)),
])
def test_parse_period(raw, expected):
    assert parse_period(raw) == expected


def test_parse_period_rejette_valeur_invalide():
    with pytest.raises(SourceError):
        parse_period("pas-une-date")


class FakeFetcher:
    """Fetcher qui rejoue une charge utile figee."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def fetch(self, url, params=None, headers=None, **kwargs):
        self.calls.append((url, params))
        return self.payload


def test_ecb_croise_observations_et_periodes():
    from veille_financiere.sources.ecb import EcbSource
    payload = {
        "dataSets": [{"series": {"0:0:0:0:0": {"observations": {
            "0": [1.1605, 0], "1": [1.1681, 0]}}}}],
        "structure": {"dimensions": {"observation": [{
            "id": "TIME_PERIOD", "role": "time",
            "values": [{"id": "2026-08-19"}, {"id": "2026-08-20"}]}]}},
    }
    src = EcbSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "fx.eurusd", "native_id": "EXR/x"})
    assert {(o.date, o.value) for o in obs} == {
        (dt.date(2026, 8, 19), 1.1605), (dt.date(2026, 8, 20), 1.1681)}


def test_ecb_signale_reponse_vide():
    from veille_financiere.sources.ecb import EcbSource
    src = EcbSource(FakeFetcher({"dataSets": []}))
    with pytest.raises(SourceError):
        src._fetch_series({"series_id": "x", "native_id": "y"})


def test_eurostat_retrouve_la_position_temporelle():
    from veille_financiere.sources.eurostat import EurostatSource
    payload = {
        "value": {"0": 2.1, "1": 1.9},
        "id": ["freq", "unit", "coicop", "geo", "time"],
        "size": [1, 1, 1, 1, 2],
        "dimension": {"time": {"category": {
            "index": {"2025-11": 0, "2025-12": 1}}}},
    }
    src = EurostatSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "macro.ea_hicp_yoy",
                             "native_id": "prc_hicp_manr"})
    assert {(o.date, o.value) for o in obs} == {
        (dt.date(2025, 11, 30), 2.1), (dt.date(2025, 12, 31), 1.9)}


def test_fred_ignore_les_valeurs_manquantes():
    from veille_financiere.sources.fred import FredSource
    payload = {"observations": [
        {"date": "2026-08-18", "value": "4.71"},
        {"date": "2026-08-17", "value": "."},       # jour ferie chez FRED
        {"date": "2026-08-14", "value": "4.68"},
    ]}
    src = FredSource(FakeFetcher(payload), api_key="test")
    obs = src._fetch_series({"series_id": "rate.us10y", "native_id": "DGS10"})
    assert len(obs) == 2
    assert all(o.value > 0 for o in obs)


def test_fred_exige_une_cle():
    from veille_financiere.sources.fred import FredSource
    with pytest.raises(SourceError):
        FredSource(FakeFetcher({}), api_key="")


def test_worldbank_gere_une_liste_de_valeurs_nulles():
    from veille_financiere.sources.worldbank import WorldBankSource
    payload = [{"page": 1}, [
        {"date": "2025", "value": 0.84},
        {"date": "2026", "value": None},
    ]]
    src = WorldBankSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "macro.fr_gdp_growth",
                             "native_id": "NY.GDP.MKTP.KD.ZG"})
    assert len(obs) == 1
    assert obs[0].date == dt.date(2025, 12, 31)


def test_yahoo_privilegie_adjclose():
    from veille_financiere.sources.yahoo import YahooSource
    payload = {"chart": {"result": [{
        "meta": {"currency": "USD"},
        "timestamp": [1755648000],
        "indicators": {"quote": [{"close": [100.0]}],
                       "adjclose": [{"adjclose": [98.5]}]},
    }], "error": None}}
    src = YahooSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "equity.sp500", "native_id": "^GSPC"})
    assert obs[0].value == 98.5


def test_le_facteur_echelle_est_applique():
    from veille_financiere.sources.yahoo import YahooSource
    payload = {"chart": {"result": [{
        "meta": {}, "timestamp": [1755648000],
        "indicators": {"quote": [{"close": [47.1]}]},
    }], "error": None}}
    src = YahooSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "rate.us10y", "native_id": "^TNX",
                             "scale": 0.1})
    assert obs[0].value == pytest.approx(4.71)


def test_oecd_gere_des_periodes_desordonnees():
    """L'OCDE renvoie les periodes dans un ordre arbitraire: l'association
    doit se faire par index, pas par position de lecture."""
    from veille_financiere.sources.oecd import OecdSource
    payload = {"data": {
        "dataSets": [{"series": {"0:0": {"observations": {
            "0": [167.068], "1": [163.4456], "2": [165.8217]}}}}],
        "structures": [{"dimensions": {"observation": [{
            "id": "TIME_PERIOD",
            "values": [{"id": "2026-02"}, {"id": "2026-01"},
                       {"id": "2026-06"}]}]}}],
    }}
    src = OecdSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "equity.fr_share_index_m",
                             "native_id": "X"})
    by_date = {o.date: o.value for o in obs}
    assert by_date[dt.date(2026, 1, 31)] == pytest.approx(163.4456)
    assert by_date[dt.date(2026, 6, 30)] == pytest.approx(165.8217)


def test_sec_ne_melange_pas_trimestres_et_exercices():
    """NetIncomeLoss existe en version 3 mois (10-Q) et 12 mois (10-K);
    melanger les deux fabriquerait des variations absurdes."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    payload = {"units": {"USD": [
        {"start": "2026-03-29", "end": "2026-06-27", "val": 29_790_000_000,
         "form": "10-Q", "filed": "2026-08-01"},
        {"start": "2025-09-29", "end": "2026-06-27", "val": 101_460_000_000,
         "form": "10-Q", "filed": "2026-08-01"},   # cumul 9 mois
    ]}}
    src = SecEdgarSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "f.aapl", "native_id": "NetIncomeLoss",
                             "cik": 320193, "duration_days": 91})
    assert len(obs) == 1
    assert obs[0].value == pytest.approx(29_790_000_000)


def test_sec_conserve_les_concepts_instantanes():
    """Assets n'a pas de 'start': le filtre de duree ne doit pas l'ecarter."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    payload = {"units": {"USD": [
        {"end": "2026-06-27", "val": 383_270_000_000, "form": "10-Q",
         "filed": "2026-08-01"},
    ]}}
    src = SecEdgarSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "f.aapl", "native_id": "Assets",
                             "cik": 320193, "duration_days": 91})
    assert len(obs) == 1


def test_sec_retient_la_publication_la_plus_recente():
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    payload = {"units": {"USD": [
        {"end": "2026-06-27", "val": 100.0, "form": "10-Q", "filed": "2026-08-01"},
        {"end": "2026-06-27", "val": 105.0, "form": "10-K", "filed": "2026-11-01"},
    ]}}
    src = SecEdgarSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "f.x", "native_id": "Assets", "cik": 1})
    assert len(obs) == 1 and obs[0].value == pytest.approx(105.0)


def test_frankfurter_rejette_une_paire_mal_formee():
    from veille_financiere.sources.frankfurter import FrankfurterSource
    src = FrankfurterSource(FakeFetcher({}))
    with pytest.raises(SourceError):
        src._fetch_series({"series_id": "fx.x", "native_id": "EURUSD"})


def test_frankfurter_lit_une_serie_temporelle():
    from veille_financiere.sources.frankfurter import FrankfurterSource
    payload = {"rates": {"2026-08-19": {"USD": 1.1605},
                         "2026-08-20": {"USD": 1.1681}}}
    src = FrankfurterSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "fx.eurusd", "native_id": "EUR/USD"})
    assert len(obs) == 2 and obs[0].date == dt.date(2026, 8, 20)


def test_coingecko_agrege_en_cloture_quotidienne():
    """market_chart renvoie des points horaires: on garde le dernier de
    chaque journee UTC pour obtenir une cloture comparable a Coinbase."""
    from veille_financiere.sources.coingecko import CoinGeckoSource
    j19 = int(dt.datetime(2026, 8, 19, 12, tzinfo=dt.timezone.utc).timestamp() * 1000)
    j19b = int(dt.datetime(2026, 8, 19, 23, tzinfo=dt.timezone.utc).timestamp() * 1000)
    j20 = int(dt.datetime(2026, 8, 20, 16, tzinfo=dt.timezone.utc).timestamp() * 1000)
    payload = {"prices": [[j19, 69000.0], [j19b, 69487.6], [j20, 72280.2]]}
    src = CoinGeckoSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "crypto.btcusd", "native_id": "bitcoin"})
    by_date = {o.date: o.value for o in obs}
    assert len(obs) == 2
    assert by_date[dt.date(2026, 8, 19)] == pytest.approx(69487.6)
    assert by_date[dt.date(2026, 8, 20)] == pytest.approx(72280.2)


def test_coingecko_signale_un_historique_absent():
    from veille_financiere.sources.coingecko import CoinGeckoSource
    src = CoinGeckoSource(FakeFetcher({"status": {"error_code": 429}}))
    with pytest.raises(SourceError):
        src._fetch_series({"series_id": "crypto.btcusd", "native_id": "bitcoin"})


# ------------------------------------------------------------------ LSE
def test_lse_exige_une_cle():
    from veille_financiere.sources.lse import LseSource
    with pytest.raises(SourceError):
        LseSource(FakeFetcher([]), api_key="")


def test_lse_candles_retient_la_cloture():
    from veille_financiere.sources.lse import LseSource
    payload = [
        {"ts": "2026-08-20 00:00:00.000000", "symbol": "FR40/EUR",
         "open": 8498.2, "high": 8516.8, "low": 8446.9, "close": 8461.4},
        {"ts": "2026-08-19 00:00:00.000000", "symbol": "FR40/EUR",
         "open": 8503.2, "high": 8564.3, "low": 8491.2, "close": 8503.7},
    ]
    src = LseSource(FakeFetcher(payload), api_key="k")
    obs = src._fetch_series({"series_id": "equity.cac40",
                             "native_id": "FR40/EUR"})
    by_date = {o.date: o.value for o in obs}
    assert by_date[dt.date(2026, 8, 20)] == pytest.approx(8461.4)
    assert by_date[dt.date(2026, 8, 19)] == pytest.approx(8503.7)


def test_lse_candles_accepte_le_champ_timestamp():
    """Le SDK officiel renomme 'ts' en 'timestamp': les deux doivent passer."""
    from veille_financiere.sources.lse import LseSource
    payload = [{"timestamp": "2026-08-20T00:00:00", "close": 4508.02}]
    src = LseSource(FakeFetcher(payload), api_key="k")
    obs = src._fetch_series({"series_id": "commodity.gold",
                             "native_id": "XAU/USD"})
    assert obs[0].date == dt.date(2026, 8, 20)
    assert obs[0].value == pytest.approx(4508.02)


def test_lse_series_lit_date_et_valeur():
    from veille_financiere.sources.lse import LseSource
    payload = [{"symbol": "US10YT=RR", "date": "2026-08-10", "value": 4.70365},
               {"symbol": "US10YT=RR", "date": "2026-08-07", "value": 4.68}]
    src = LseSource(FakeFetcher(payload), api_key="k")
    obs = src._fetch_series({"series_id": "rate.us10y",
                             "native_id": "US10YT=RR", "mode": "series"})
    assert len(obs) == 2
    assert obs[0].value == pytest.approx(4.70365)


def test_lse_bond_yields_utilise_la_cloture():
    from veille_financiere.sources.lse import LseSource
    payload = [{"symbol": "US2Y", "date": "2026-07-24", "open": 4.74,
                "high": 4.774, "low": 4.717, "close": 4.745}]
    src = LseSource(FakeFetcher(payload), api_key="k")
    obs = src._fetch_series({"series_id": "rate.us02y", "native_id": "US2Y",
                             "mode": "bond_yields"})
    assert obs[0].value == pytest.approx(4.745)


def test_lse_remonte_l_erreur_de_l_api():
    """L'API encapsule ses erreurs dans un dict 'detail' avec un HTTP 200."""
    from veille_financiere.sources.lse import LseSource
    src = LseSource(FakeFetcher({"detail": "bad symbol"}), api_key="k")
    with pytest.raises(SourceError, match="bad symbol"):
        src._fetch_series({"series_id": "x", "native_id": "^FCHI"})


def test_lse_rejette_un_mode_inconnu():
    from veille_financiere.sources.lse import LseSource
    src = LseSource(FakeFetcher([]), api_key="k")
    with pytest.raises(SourceError, match="mode LSE inconnu"):
        src._fetch_series({"series_id": "x", "native_id": "y", "mode": "zzz"})


# ------------------------------------------------- normalisation des dates
def test_normalisation_aligne_les_series_mensuelles():
    """FRED et LSE datent le mois a son premier jour, la BCE et Eurostat a
    son libelle: sans recalage, aucune date commune donc aucun recoupement."""
    from veille_financiere.sources.base import normalize_date
    assert normalize_date(dt.date(2026, 6, 1), "monthly") == dt.date(2026, 6, 30)
    assert normalize_date(dt.date(2026, 6, 30), "monthly") == dt.date(2026, 6, 30)
    assert normalize_date(dt.date(2026, 2, 1), "monthly") == dt.date(2026, 2, 28)


def test_normalisation_laisse_les_trimestres_intacts():
    """Le premier trimestre de NVIDIA se termine en avril: le recaler sur une
    fin de trimestre civil afficherait une date fausse."""
    from veille_financiere.sources.base import normalize_date
    assert normalize_date(dt.date(2026, 4, 26), "quarterly") == dt.date(2026, 4, 26)


def test_normalisation_ne_touche_pas_au_quotidien():
    from veille_financiere.sources.base import normalize_date
    assert normalize_date(dt.date(2026, 8, 20), "daily") == dt.date(2026, 8, 20)


def test_deux_sources_mensuelles_deviennent_comparables():
    """Regression de bout en bout: LSE (1er du mois) et Eurostat (libelle du
    mois) doivent produire la meme date apres normalisation."""
    from veille_financiere.sources.lse import LseSource
    from veille_financiere.sources.eurostat import EurostatSource

    lse = LseSource(FakeFetcher([{"date": "2026-06-01", "value": 2.8}]),
                    api_key="k")
    o_lse = lse._fetch_series({"series_id": "macro.ea_hicp_yoy",
                               "native_id": "eccpemuy", "mode": "series",
                               "frequency": "monthly"})

    euro = EurostatSource(FakeFetcher({
        "value": {"0": 2.7}, "id": ["geo", "time"], "size": [1, 1],
        "dimension": {"time": {"category": {"index": {"2026-06": 0}}}},
    }))
    o_euro = euro._fetch_series({"series_id": "macro.ea_hicp_yoy",
                                 "native_id": "prc_hicp_manr",
                                 "frequency": "monthly"})
    assert o_lse[0].date == o_euro[0].date == dt.date(2026, 6, 30)


# ------------------------------------------------- agenda macroeconomique
def test_calendrier_separe_paru_et_attendu():
    from veille_financiere.sources.lse import LseSource
    payload = [
        {"date": "2026-08-19", "time": "09:00 AM", "region_code": "EU",
         "event": "HICP YoY", "period_hint": "JUL", "actual": "2.2%",
         "consensus": "2.2%", "previous": "2.8%"},
        {"date": "2026-08-20", "time": "12:30 PM", "region_code": "US",
         "event": "Initial Jobless Claims", "actual": None,
         "consensus": "210K", "previous": "209K"},
    ]
    src = LseSource(FakeFetcher(payload), api_key="k")
    events = src.fetch_calendar(["EU", "US"], dt.date(2026, 8, 19),
                                dt.date(2026, 8, 20))
    assert len(events) == 2
    paru = [e for e in events if e.released]
    attendu = [e for e in events if not e.released]
    assert len(paru) == 1 and paru[0].event == "HICP YoY"
    assert len(attendu) == 1 and attendu[0].consensus == "210K"


def test_calendrier_ignore_les_lignes_incompletes():
    from veille_financiere.sources.lse import LseSource
    payload = [
        {"date": "2026-08-20", "event": "Valide", "actual": "1%"},
        {"date": None, "event": "Sans date"},
        {"date": "2026-08-20", "event": None},
    ]
    src = LseSource(FakeFetcher(payload), api_key="k")
    events = src.fetch_calendar([], dt.date(2026, 8, 20), dt.date(2026, 8, 20))
    assert len(events) == 1


def test_surprise_compare_constate_et_consensus():
    from veille_financiere.models import CalendarEvent
    e = CalendarEvent("lse", dt.date(2026, 8, 20), "US", "Claims",
                      actual="209K", consensus="210K")
    assert e.surprise() == pytest.approx(-1000.0)


@pytest.mark.parametrize("actual,consensus", [
    (None, "210K"), ("209K", None), ("n/a", "210K"), ("", "210K"),
])
def test_surprise_absente_quand_incomparable(actual, consensus):
    from veille_financiere.models import CalendarEvent
    e = CalendarEvent("lse", dt.date(2026, 8, 20), "US", "X",
                      actual=actual, consensus=consensus)
    assert e.surprise() is None


@pytest.mark.parametrize("raw,expected", [
    ("209K", 209_000.0), ("1.5M", 1_500_000.0), ("3.2%", 3.2),
    ("-3.28", -3.28), ("1,777K", 1_777_000.0), ("2.1B", 2_100_000_000.0),
])
def test_conversion_des_valeurs_textuelles(raw, expected):
    from veille_financiere.models import _to_number
    assert _to_number(raw) == pytest.approx(expected)


# ----------------------------------------------------------------- EODHD
def test_eodhd_exige_une_cle():
    from veille_financiere.sources.eodhd import EodhdSource
    with pytest.raises(SourceError):
        EodhdSource(FakeFetcher([]), api_key="")


def test_eodhd_lit_les_rendements_souverains():
    from veille_financiere.sources.eodhd import EodhdSource
    payload = [{"date": "2026-08-20", "close": 3.2753},
               {"date": "2026-08-19", "close": 3.2410}]
    fetcher = FakeFetcher(payload)
    src = EodhdSource(fetcher, api_key="k")
    obs = src._fetch_series({"series_id": "rate.de10y", "native_id": "DE10Y"})
    assert len(obs) == 2
    assert obs[0].value == pytest.approx(3.2753)
    # La bourse virtuelle par defaut est GBOND.
    assert fetcher.calls[0][0].endswith("/eod/DE10Y.GBOND")


def test_eodhd_bascule_sur_la_bourse_des_indices():
    from veille_financiere.sources.eodhd import EodhdSource
    fetcher = FakeFetcher([{"date": "2026-08-20", "close": 19811.0}])
    src = EodhdSource(fetcher, api_key="k")
    obs = src._fetch_series({"series_id": "equity.ibex35", "native_id": "IBEX",
                             "market": "INDX"})
    assert obs[0].value == pytest.approx(19811.0)
    assert fetcher.calls[0][0].endswith("/eod/IBEX.INDX")


def test_eodhd_remonte_une_erreur_renvoyee_en_objet():
    """Les erreurs arrivent sous forme de dict la ou le succes est une liste."""
    from veille_financiere.sources.eodhd import EodhdSource
    src = EodhdSource(FakeFetcher({"message": "Ticker Not Found"}), api_key="k")
    with pytest.raises(SourceError, match="Ticker Not Found"):
        src._fetch_series({"series_id": "x", "native_id": "ENI"})


def test_eodhd_ignore_les_lignes_sans_valeur():
    from veille_financiere.sources.eodhd import EodhdSource
    payload = [{"date": "2026-08-20", "close": None},
               {"date": None, "close": 1.0},
               {"date": "2026-08-19", "close": 4.12}]
    src = EodhdSource(FakeFetcher(payload), api_key="k")
    obs = src._fetch_series({"series_id": "rate.fr10y", "native_id": "FR10Y"})
    assert len(obs) == 1 and obs[0].value == pytest.approx(4.12)


def test_eodhd_se_rabat_sur_adjusted_close():
    from veille_financiere.sources.eodhd import EodhdSource
    src = EodhdSource(FakeFetcher([{"date": "2026-08-20",
                                    "adjusted_close": 5.07}]), api_key="k")
    obs = src._fetch_series({"series_id": "rate.gb10y", "native_id": "UK10Y"})
    assert obs[0].value == pytest.approx(5.07)


def test_sec_reconstitue_le_quatrieme_trimestre():
    """Aucun 10-Q n'est depose pour le T4 : il n'existe que fondu dans le
    cumul annuel du 10-K, ce qui faisait sauter un point a la serie."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    payload = {"units": {"USD": [
        {"start": "2025-07-28", "end": "2025-10-26", "val": 31_910_000_000,
         "form": "10-Q", "filed": "2025-11-20"},
        {"start": "2025-01-27", "end": "2025-10-26", "val": 77_110_000_000,
         "form": "10-Q", "filed": "2025-11-20"},          # cumul 9 mois
        {"start": "2025-01-27", "end": "2026-01-25", "val": 120_070_000_000,
         "form": "10-K", "filed": "2026-02-26"},          # exercice complet
        {"start": "2026-01-26", "end": "2026-04-26", "val": 58_320_000_000,
         "form": "10-Q", "filed": "2026-05-28"},
    ]}}
    src = SecEdgarSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "f.nvda", "native_id": "NetIncomeLoss",
                             "cik": 1045810, "duration_days": 91})
    par_date = {o.date: o for o in obs}
    t4 = par_date[dt.date(2026, 1, 25)]
    assert t4.value == pytest.approx(42_960_000_000)
    assert t4.meta.get("derive") is True
    # Les trimestres deposes restent inchanges et non marques.
    assert par_date[dt.date(2026, 4, 26)].meta.get("derive") is None


def test_sec_ne_reconstitue_rien_sans_cumul_correspondant():
    """Sans cumul de reference, le T4 n'est pas deduit — et le concept, vide
    de tout trimestre, remonte en echec au lieu de disparaitre en silence."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    payload = {"units": {"USD": [
        {"start": "2025-01-27", "end": "2026-01-25", "val": 120_070_000_000,
         "form": "10-K", "filed": "2026-02-26"},
    ]}}
    src = SecEdgarSource(FakeFetcher(payload))
    with pytest.raises(SourceError):
        src._fetch_series({"series_id": "f.x", "native_id": "NetIncomeLoss",
                           "cik": 1, "duration_days": 91})


def test_sec_ne_reconstitue_pas_les_concepts_instantanes():
    """Assets n'a pas de duree : rien a deduire, et surtout rien a fausser."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    payload = {"units": {"USD": [
        {"end": "2026-04-26", "val": 259_470_000_000, "form": "10-Q",
         "filed": "2026-05-28"},
    ]}}
    src = SecEdgarSource(FakeFetcher(payload))
    obs = src._fetch_series({"series_id": "f.x", "native_id": "Assets", "cik": 1})
    assert len(obs) == 1 and obs[0].meta.get("derive") is None


class AliasFetcher:
    """Renvoie une charge utile differente selon le concept demande."""

    def __init__(self, par_concept):
        self.par_concept = par_concept
        self.calls = []

    def fetch(self, url, params=None, headers=None, **kwargs):
        self.calls.append((url, params))
        for concept, payload in self.par_concept.items():
            if f"/{concept}.json" in url:
                return payload
        raise RuntimeError("HTTP 404")


def test_sec_essaie_les_synonymes_de_concept():
    """Le chiffre d'affaires se lit sous deux balises selon les societes."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    fetcher = AliasFetcher({
        # Concept moderne present mais vide chez cette societe.
        "RevenueFromContractWithCustomerExcludingAssessedTax":
            {"units": {"USD": []}},
        "Revenues": {"units": {"USD": [
            {"start": "2026-01-26", "end": "2026-04-26", "val": 44_060_000_000,
             "form": "10-Q", "filed": "2026-05-28"},
        ]}},
    })
    src = SecEdgarSource(fetcher)
    obs = src._fetch_series({
        "series_id": "f.nvda.revenue", "cik": 1045810, "duration_days": 91,
        "native_id": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                      "Revenues"],
    })
    assert len(obs) == 1 and obs[0].value == pytest.approx(44_060_000_000)
    assert len(fetcher.calls) == 2   # le premier synonyme a bien ete tente


def test_sec_signale_l_echec_de_tous_les_synonymes():
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    src = SecEdgarSource(AliasFetcher({}))
    with pytest.raises(SourceError):
        src._fetch_series({"series_id": "f.x", "cik": 1,
                           "native_id": ["Inexistant", "PasPlus"]})


def test_sec_retient_le_synonyme_le_plus_a_jour():
    """Une balise abandonnee continue de servir son historique : chez
    JPMorgan le concept moderne s'arrete en 2014 quand l'ancien est tenu a
    jour. Prendre le premier qui repond figerait la serie douze ans en
    arriere sans que rien ne le signale."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    fetcher = AliasFetcher({
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            {"start": "2014-10-01", "end": "2014-12-31", "val": 23_419_000_000,
             "form": "10-K", "filed": "2015-02-24"},
        ]}},
        "Revenues": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 45_680_000_000,
             "form": "10-Q", "filed": "2026-08-05"},
        ]}},
    })
    src = SecEdgarSource(fetcher)
    obs = src._fetch_series({
        "series_id": "f.jpm.revenue", "cik": 19617, "duration_days": 91,
        "native_id": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                      "Revenues"],
    })
    assert obs[0].date == dt.date(2026, 6, 30)
    assert obs[0].value == pytest.approx(45_680_000_000)


def test_sec_raccorde_deux_balises_concordantes():
    """Alphabet alterne entre deux balises : les recoller donne un historique
    continu, une fois verifie qu'elles disent la meme chose."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    fetcher = AliasFetcher({
        "Revenues": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 100,
             "form": "10-Q", "filed": "2026-08-01"},
            {"start": "2024-04-01", "end": "2024-06-30", "val": 80,
             "form": "10-Q", "filed": "2024-08-01"},
        ]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            {"start": "2024-04-01", "end": "2024-06-30", "val": 80,
             "form": "10-Q", "filed": "2024-08-01"},      # date commune, valeur identique
            {"start": "2025-04-01", "end": "2025-06-30", "val": 90,
             "form": "10-Q", "filed": "2025-08-01"},      # trimestre absent de l'autre
        ]}},
    })
    src = SecEdgarSource(fetcher)
    obs = src._fetch_series({"series_id": "f.googl.revenue", "cik": 1652044,
                             "duration_days": 91,
                             "native_id": ["Revenues",
                                           "RevenueFromContractWithCustomer"
                                           "ExcludingAssessedTax"]})
    dates = sorted(o.date for o in obs)
    assert dt.date(2025, 6, 30) in dates      # le trou est comble
    assert len(dates) == 3


def test_sec_refuse_de_raccorder_deux_grandeurs_differentes():
    """Si les deux balises divergent la ou elles se recoupent, les recoller
    fabriquerait une rupture invisible au point de raccord."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    fetcher = AliasFetcher({
        "Revenues": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 100,
             "form": "10-Q", "filed": "2026-08-01"},
            {"start": "2024-04-01", "end": "2024-06-30", "val": 80,
             "form": "10-Q", "filed": "2024-08-01"},
        ]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            {"start": "2024-04-01", "end": "2024-06-30", "val": 65,
             "form": "10-Q", "filed": "2024-08-01"},      # desaccord de 19 %
            {"start": "2025-04-01", "end": "2025-06-30", "val": 70,
             "form": "10-Q", "filed": "2025-08-01"},
        ]}},
    })
    src = SecEdgarSource(fetcher)
    obs = src._fetch_series({"series_id": "f.x.revenue", "cik": 1,
                             "duration_days": 91,
                             "native_id": ["Revenues",
                                           "RevenueFromContractWithCustomer"
                                           "ExcludingAssessedTax"]})
    dates = sorted(o.date for o in obs)
    assert dt.date(2025, 6, 30) not in dates
    assert len(dates) == 2


def test_sec_ne_raccorde_pas_sans_date_commune():
    """Sans recoupement, rien ne permet d'affirmer que c'est la meme
    grandeur : on s'abstient plutot que de parier."""
    from veille_financiere.sources.sec_edgar import SecEdgarSource
    fetcher = AliasFetcher({
        "Revenues": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 100,
             "form": "10-Q", "filed": "2026-08-01"},
        ]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            {"start": "2020-04-01", "end": "2020-06-30", "val": 50,
             "form": "10-Q", "filed": "2020-08-01"},
        ]}},
    })
    src = SecEdgarSource(fetcher)
    obs = src._fetch_series({"series_id": "f.x", "cik": 1, "duration_days": 91,
                             "native_id": ["Revenues",
                                           "RevenueFromContractWithCustomer"
                                           "ExcludingAssessedTax"]})
    assert len(obs) == 1 and obs[0].date == dt.date(2026, 6, 30)
