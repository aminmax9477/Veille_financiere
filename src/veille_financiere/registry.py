"""Catalogue des series suivies.

Chaque entree associe un identifiant canonique interne a un ou plusieurs
couples (source, identifiant natif). Les series couvertes par plusieurs
sources sont volontaires: c'est ce recoupement qui alimente la
reconciliation et permet de detecter une source qui derive.
"""
from __future__ import annotations

from typing import Any

# unit: libelle lisible; scale: multiplicateur applique pour ramener toutes
# les sources d'une meme serie a la meme unite avant comparaison.
CATALOGUE: dict[str, dict[str, Any]] = {
    # ---------------- Taux de change ----------------
    "fx.eurusd": {
        "label": "Euro / Dollar US",
        "unit": "USD pour 1 EUR",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "ecb", "native_id": "EXR/D.USD.EUR.SP00.A", "limit": 60},
            {"source": "frankfurter", "native_id": "EUR/USD"},
            {"source": "fred", "native_id": "DEXUSEU", "limit": 60},
            {"source": "yahoo", "native_id": "EURUSD=X", "range": "1mo"},
        ],
    },
    "fx.gbpusd": {
        "label": "Livre sterling / Dollar US",
        "unit": "USD pour 1 GBP",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "frankfurter", "native_id": "GBP/USD"},
            {"source": "fred", "native_id": "DEXUSUK", "limit": 60},
            {"source": "yahoo", "native_id": "GBPUSD=X", "range": "1mo"},
        ],
    },
    "fx.usdjpy": {
        "label": "Dollar US / Yen",
        "unit": "JPY pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "fred", "native_id": "DEXJPUS", "limit": 60},
            {"source": "yahoo", "native_id": "USDJPY=X", "range": "1mo"},
        ],
    },

    # ---------------- Taux d'interet ----------------
    "rate.us10y": {
        "label": "Taux 10 ans Etats-Unis",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "fred", "native_id": "DGS10", "limit": 90},
            # ^TNX est cote en pourcentage chez Yahoo (ex. 4.71).
            {"source": "yahoo", "native_id": "^TNX", "range": "1mo"},
        ],
    },
    "rate.us02y": {
        "label": "Taux 2 ans Etats-Unis",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "fred", "native_id": "DGS2", "limit": 90}],
    },
    "rate.fed_funds": {
        "label": "Taux effectif des Fed Funds",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "fred", "native_id": "DFF", "limit": 60}],
    },
    "rate.ecb_depo": {
        "label": "Taux de facilite de depot BCE",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "ecb", "native_id": "FM/D.U2.EUR.4F.KR.DFR.LEV",
             "limit": 40},
        ],
    },

    # ---------------- Inflation / macro ----------------
    "macro.us_cpi_yoy": {
        "label": "Inflation US (IPC, glissement annuel)",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [
            {"source": "fred", "native_id": "CPIAUCSL", "limit": 40,
             "fred_units": "pc1"},
        ],
    },
    "macro.ea_hicp_yoy": {
        "label": "Inflation zone euro (IPCH, glissement annuel)",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [
            {"source": "eurostat", "native_id": "prc_hicp_manr", "limit": 24,
             "params": {"geo": "EA", "coicop": "CP00", "unit": "RCH_A"}},
            {"source": "ecb", "native_id": "ICP/M.U2.N.000000.4.ANR", "limit": 24},
        ],
    },
    "macro.fr_hicp_yoy": {
        "label": "Inflation France (IPCH, glissement annuel)",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [
            {"source": "eurostat", "native_id": "prc_hicp_manr", "limit": 24,
             "params": {"geo": "FR", "coicop": "CP00", "unit": "RCH_A"}},
            {"source": "ecb", "native_id": "ICP/M.FR.N.000000.4.ANR", "limit": 24},
        ],
    },
    "macro.us_unemployment": {
        "label": "Taux de chomage Etats-Unis",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "UNRATE", "limit": 36}],
    },
    "macro.fr_gdp_growth": {
        "label": "Croissance du PIB France",
        "unit": "%",
        "frequency": "annual",
        "category": "macro",
        "providers": [
            {"source": "imf", "native_id": "NGDP_RPCH", "country": "FRA",
             "limit": 30},
            {"source": "worldbank", "native_id": "NY.GDP.MKTP.KD.ZG",
             "country": "FRA", "limit": 30},
        ],
    },

    # ---------------- Marches actions ----------------
    "equity.sp500": {
        "label": "S&P 500",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "yahoo", "native_id": "^GSPC", "range": "3mo"},
            {"source": "fred", "native_id": "SP500", "limit": 90},
        ],
    },
    "equity.cac40": {
        "label": "CAC 40",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [{"source": "yahoo", "native_id": "^FCHI", "range": "3mo"}],
    },
    "equity.eurostoxx50": {
        "label": "Euro Stoxx 50",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [{"source": "yahoo", "native_id": "^STOXX50E", "range": "3mo"}],
    },
    "equity.vix": {
        "label": "VIX (volatilite implicite S&P 500)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "yahoo", "native_id": "^VIX", "range": "3mo"},
            {"source": "fred", "native_id": "VIXCLS", "limit": 90},
        ],
    },

    # ---------------- Matieres premieres ----------------
    "commodity.brent": {
        "label": "Petrole Brent",
        "unit": "USD/baril",
        "frequency": "daily",
        "category": "matieres",
        "providers": [
            {"source": "fred", "native_id": "DCOILBRENTEU", "limit": 90},
            {"source": "yahoo", "native_id": "BZ=F", "range": "3mo"},
        ],
    },
    "commodity.gold": {
        "label": "Or",
        "unit": "USD/once",
        "frequency": "daily",
        "category": "matieres",
        "providers": [{"source": "yahoo", "native_id": "GC=F", "range": "3mo"}],
    },


    "equity.nasdaq": {
        "label": "Nasdaq Composite",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "fred", "native_id": "NASDAQCOM", "limit": 90},
            {"source": "yahoo", "native_id": "^IXIC", "range": "3mo"},
        ],
    },
    "equity.dowjones": {
        "label": "Dow Jones Industrial Average",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "fred", "native_id": "DJIA", "limit": 90},
            {"source": "yahoo", "native_id": "^DJI", "range": "3mo"},
        ],
    },
    "equity.fr_share_index_m": {
        "label": "Indice des cours boursiers France (OCDE, base 100)",
        "unit": "indice",
        "frequency": "monthly",
        "category": "actions",
        "providers": [
            {"source": "oecd",
             "native_id": "OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/FRA.M.SHARE......",
             "params": {"startPeriod": "2023-01"}, "limit": 48},
        ],
    },
    "equity.eurostoxx50_m": {
        "label": "Euro Stoxx 50 (releve mensuel BCE)",
        "unit": "points",
        "frequency": "monthly",
        "category": "actions",
        "providers": [
            {"source": "ecb", "native_id": "FM/M.U2.EUR.DS.EI.DJES50I.HSTA",
             "limit": 36},
        ],
    },
    "commodity.wti": {
        "label": "Petrole WTI",
        "unit": "USD/baril",
        "frequency": "daily",
        "category": "matieres",
        "providers": [
            {"source": "fred", "native_id": "DCOILWTICO", "limit": 90},
            {"source": "yahoo", "native_id": "CL=F", "range": "3mo"},
        ],
    },
    "rate.us30y": {
        "label": "Taux 30 ans Etats-Unis",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "fred", "native_id": "DGS30", "limit": 90}],
    },
    "rate.us_curve_10y2y": {
        "label": "Pente de la courbe US (10 ans - 2 ans)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "fred", "native_id": "T10Y2Y", "limit": 90}],
    },
    "fx.usdchf": {
        "label": "Dollar US / Franc suisse",
        "unit": "CHF pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "fred", "native_id": "DEXSZUS", "limit": 60},
            {"source": "yahoo", "native_id": "USDCHF=X", "range": "1mo"},
        ],
    },
    "fx.usdcny": {
        "label": "Dollar US / Yuan",
        "unit": "CNY pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [{"source": "fred", "native_id": "DEXCHUS", "limit": 60}],
    },
    "fx.dollar_index": {
        "label": "Indice dollar (large, pondere des echanges)",
        "unit": "indice",
        "frequency": "daily",
        "category": "change",
        "providers": [{"source": "fred", "native_id": "DTWEXBGS", "limit": 90}],
    },

    # ---------------- Crypto ----------------
    "crypto.btcusd": {
        "label": "Bitcoin / USD",
        "unit": "USD",
        "frequency": "daily",
        "category": "crypto",
        "providers": [
            {"source": "coingecko", "native_id": "bitcoin"},
            {"source": "fred", "native_id": "CBBTCUSD", "limit": 60},
            {"source": "yahoo", "native_id": "BTC-USD", "range": "1mo"},
        ],
    },
    "crypto.ethusd": {
        "label": "Ethereum / USD",
        "unit": "USD",
        "frequency": "daily",
        "category": "crypto",
        "providers": [
            {"source": "coingecko", "native_id": "ethereum"},
            {"source": "fred", "native_id": "CBETHUSD", "limit": 60},
            {"source": "yahoo", "native_id": "ETH-USD", "range": "1mo"},
        ],
    },
}

# Fondamentaux d'entreprises via SEC EDGAR (CIK -> concepts XBRL).
COMPANIES: dict[str, dict[str, Any]] = {
    "AAPL": {"cik": 320193, "label": "Apple Inc."},
    "MSFT": {"cik": 789019, "label": "Microsoft Corp."},
    "NVDA": {"cik": 1045810, "label": "NVIDIA Corp."},
}

XBRL_CONCEPTS = [
    {"native_id": "Assets", "label": "Actif total", "xbrl_unit": "USD"},
    {"native_id": "StockholdersEquity", "label": "Capitaux propres",
     "xbrl_unit": "USD"},
    # Concept de flux: on cible explicitement le trimestre (~91 jours) pour
    # ne pas melanger resultats trimestriels et annuels.
    {"native_id": "NetIncomeLoss", "label": "Resultat net trimestriel",
     "xbrl_unit": "USD", "duration_days": 91},
]


def iter_specs() -> list[dict[str, Any]]:
    """Aplatit le catalogue en une liste de specs prete pour les adaptateurs."""
    specs: list[dict[str, Any]] = []
    for series_id, entry in CATALOGUE.items():
        for prov in entry["providers"]:
            spec = dict(prov)
            spec.update(
                series_id=series_id,
                label=entry["label"],
                unit=entry["unit"],
                frequency=entry["frequency"],
                category=entry["category"],
            )
            specs.append(spec)
    return specs


def iter_company_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for ticker, comp in COMPANIES.items():
        for concept in XBRL_CONCEPTS:
            specs.append({
                "series_id": f"fundamental.{ticker.lower()}.{concept['native_id'].lower()}",
                "source": "sec_edgar",
                "native_id": concept["native_id"],
                "cik": comp["cik"],
                "xbrl_unit": concept["xbrl_unit"],
                "duration_days": concept.get("duration_days"),
                "label": f"{comp['label']} - {concept['label']}",
                "unit": "USD",
                "frequency": "quarterly",
                "category": "fondamentaux",
                "limit": 16,
            })
    return specs
