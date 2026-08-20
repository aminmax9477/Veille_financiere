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
