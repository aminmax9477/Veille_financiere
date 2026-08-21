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
            {"source": "lse", "native_id": "EUR/USD", "limit": 90},
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
            {"source": "lse", "native_id": "GBP/USD", "limit": 90},
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
            {"source": "lse", "native_id": "USD/JPY", "limit": 90},
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
            {"source": "eodhd", "native_id": "US10Y", "limit": 90},
            {"source": "lse", "native_id": "US10YT=RR", "mode": "series", "limit": 90},
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
        "providers": [
            {"source": "eodhd", "native_id": "US2Y", "limit": 90},
            {"source": "lse", "native_id": "US2YT=RR", "mode": "series", "limit": 90},{"source": "fred", "native_id": "DGS2", "limit": 90}],
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


    "rate.it10y": {
        "label": "Taux 10 ans Italie (BTP)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "eodhd", "native_id": "IT10Y", "limit": 90}],
    },
    "rate.es10y": {
        "label": "Taux 10 ans Espagne",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "eodhd", "native_id": "ES10Y", "limit": 90}],
    },
    "rate.gb10y": {
        "label": "Taux 10 ans Royaume-Uni (Gilt)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "eodhd", "native_id": "UK10Y", "limit": 90}],
    },
    "rate.jp10y": {
        "label": "Taux 10 ans Japon (JGB)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "eodhd", "native_id": "JP10Y", "limit": 90}],
    },
    "rate.jp02y": {
        "label": "Taux 2 ans Japon",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "eodhd", "native_id": "JP2Y", "limit": 90}],
    },
    "rate.cn10y": {
        "label": "Taux 10 ans Chine",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "eodhd", "native_id": "CN10Y", "limit": 90}],
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
            {"source": "lse", "native_id": "eccpemuy", "mode": "series", "limit": 36},
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
            {"source": "lse", "native_id": "frcpiyoy", "mode": "series", "limit": 36},
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


    # ---------------- Credit et conditions financieres ----------------
    "credit.us_hy_oas": {
        "label": "Spread haut rendement US (OAS)",
        "unit": "%",
        "frequency": "daily",
        "category": "credit",
        "providers": [{"source": "fred", "native_id": "BAMLH0A0HYM2",
                       "limit": 90}],
    },
    "credit.baa_10y": {
        "label": "Spread Baa - 10 ans US",
        "unit": "%",
        "frequency": "daily",
        "category": "credit",
        "providers": [{"source": "fred", "native_id": "BAA10Y", "limit": 90}],
    },
    "credit.us_financial_conditions": {
        "label": "Conditions financieres US (Fed de Chicago)",
        "unit": "indice",
        "frequency": "weekly",
        "category": "credit",
        "providers": [{"source": "fred", "native_id": "NFCI", "limit": 60}],
    },
    "credit.us_financial_stress": {
        "label": "Stress financier US (Fed de Saint-Louis)",
        "unit": "indice",
        "frequency": "weekly",
        "category": "credit",
        "providers": [{"source": "fred", "native_id": "STLFSI4", "limit": 60}],
    },

    # ---------------- Taux reels et anticipations ----------------
    "rate.us_real_10y": {
        "label": "Taux reel 10 ans US (TIPS)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "fred", "native_id": "DFII10", "limit": 90}],
    },
    "rate.us_breakeven_10y": {
        "label": "Point mort d'inflation 10 ans US",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [{"source": "fred", "native_id": "T10YIE", "limit": 90}],
    },

    # ---------------- Macro US elargie ----------------
    "macro.us_payrolls_change": {
        "label": "Emplois non agricoles US (variation mensuelle)",
        "unit": "milliers",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "PAYEMS", "limit": 36,
                       "fred_units": "chg"}],
    },
    "macro.us_core_pce_yoy": {
        "label": "Inflation sous-jacente US (PCE, glissement annuel)",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "PCEPILFE", "limit": 36,
                       "fred_units": "pc1"}],
    },
    "macro.us_retail_sales_yoy": {
        "label": "Ventes de detail US (glissement annuel)",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "RSAFS", "limit": 36,
                       "fred_units": "pc1"}],
    },
    "macro.us_industrial_production_yoy": {
        "label": "Production industrielle US (glissement annuel)",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "INDPRO", "limit": 36,
                       "fred_units": "pc1"}],
    },
    "macro.us_consumer_sentiment": {
        "label": "Confiance des menages US (Michigan)",
        "unit": "indice",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "UMCSENT", "limit": 36}],
    },
    "macro.us_m2_yoy": {
        "label": "Masse monetaire M2 US (glissement annuel)",
        "unit": "%",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "M2SL", "limit": 36,
                       "fred_units": "pc1"}],
    },
    "macro.us_housing_starts": {
        "label": "Mises en chantier US",
        "unit": "milliers (rythme annuel)",
        "frequency": "monthly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "HOUST", "limit": 36}],
    },
    "macro.us_jobless_claims": {
        "label": "Inscriptions hebdomadaires au chomage US",
        "unit": "personnes",
        "frequency": "weekly",
        "category": "macro",
        "providers": [{"source": "fred", "native_id": "ICSA", "limit": 60}],
    },

    # ---------------- Marches actions ----------------
    "equity.sp500": {
        "label": "S&P 500",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "lse", "native_id": "SPX500/USD", "limit": 90},
            {"source": "yahoo", "native_id": "^GSPC", "range": "3mo"},
            {"source": "fred", "native_id": "SP500", "limit": 90},
        ],
    },
    "equity.cac40": {
        "label": "CAC 40",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "lse", "native_id": "FR40/EUR", "limit": 90},{"source": "yahoo", "native_id": "^FCHI", "range": "3mo"}],
    },
    "equity.eurostoxx50": {
        "label": "Euro Stoxx 50",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "lse", "native_id": "EU50/EUR", "limit": 90},{"source": "yahoo", "native_id": "^STOXX50E", "range": "3mo"}],
    },
    "equity.vix": {
        "label": "VIX (volatilite implicite S&P 500)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "lse", "native_id": "VIX/USD", "limit": 90},
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
            {"source": "lse", "native_id": "BCO/USD", "limit": 90},
            {"source": "fred", "native_id": "DCOILBRENTEU", "limit": 90},
            {"source": "yahoo", "native_id": "BZ=F", "range": "3mo"},
        ],
    },
    "commodity.gold": {
        "label": "Or",
        "unit": "USD/once",
        "frequency": "daily",
        "category": "matieres",
        "providers": [
            {"source": "lse", "native_id": "XAU/USD", "limit": 90},{"source": "yahoo", "native_id": "GC=F", "range": "3mo"}],
    },


    "equity.nasdaq": {
        "label": "Nasdaq Composite",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "lse", "native_id": "NASCOMP/USD", "limit": 90},
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
            {"source": "lse", "native_id": "US30/USD", "limit": 90},
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
            {"source": "lse", "native_id": "WTICO/USD", "limit": 90},
            {"source": "fred", "native_id": "DCOILWTICO", "limit": 90},
            {"source": "yahoo", "native_id": "CL=F", "range": "3mo"},
        ],
    },
    "rate.us30y": {
        "label": "Taux 30 ans Etats-Unis",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "US30Y", "limit": 90},
            {"source": "lse", "native_id": "US30YT=RR", "mode": "series", "limit": 90},{"source": "fred", "native_id": "DGS30", "limit": 90}],
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
            {"source": "lse", "native_id": "USD/CHF", "limit": 90},
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


    "equity.dax": {
        "label": "DAX (Allemagne)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [{"source": "lse", "native_id": "DE30/EUR", "limit": 90}],
    },
    "equity.ftse100": {
        "label": "FTSE 100 (Royaume-Uni)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [{"source": "lse", "native_id": "UK100/GBP", "limit": 90}],
    },
    "equity.nikkei225": {
        "label": "Nikkei 225 (Japon)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [{"source": "lse", "native_id": "JP225/USD", "limit": 90}],
    },
    "equity.ibex35": {
        "label": "IBEX 35 (Espagne)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            # LSE cote ES35/EUR autour de 1 900 quand l'indice vaut 19 800,
            # et sa serie s'arrete a juin 2026 : ce n'est pas le meme
            # instrument, l'y adosser fabriquait une divergence permanente.
            {"source": "eodhd", "native_id": "IBEX", "market": "INDX",
             "limit": 90}],
    },
    "commodity.silver": {
        "label": "Argent",
        "unit": "USD/once",
        "frequency": "daily",
        "category": "matieres",
        "providers": [{"source": "lse", "native_id": "XAG/USD", "limit": 90}],
    },
    "commodity.copper": {
        "label": "Cuivre",
        "unit": "USD/livre",
        "frequency": "daily",
        "category": "matieres",
        "providers": [{"source": "lse", "native_id": "XCU/USD", "limit": 90}],
    },
    "commodity.natgas": {
        "label": "Gaz naturel",
        "unit": "USD/MMBtu",
        "frequency": "daily",
        "category": "matieres",
        "providers": [{"source": "lse", "native_id": "NATGAS/USD", "limit": 90}],
    },
    "rate.de10y": {
        "label": "Taux 10 ans Allemagne (Bund)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "DE10Y", "limit": 90},{"source": "lse", "native_id": "DE10YT=RR", "mode": "series",
                       "limit": 90}],
    },
    "rate.fr10y": {
        "label": "Taux 10 ans France (OAT)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "FR10Y", "limit": 90},{"source": "lse", "native_id": "FR10YT=RR", "mode": "series",
                       "limit": 90}],
    },


    "fx.usdcnh": {
        "label": "Dollar US / Yuan offshore (CNH)",
        "unit": "CNH pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [{"source": "lse", "native_id": "USD/CNH", "limit": 90}],
    },
    "fx.dxy": {
        "label": "Indice dollar DXY (panier 6 devises)",
        "unit": "indice",
        "frequency": "daily",
        "category": "change",
        "providers": [{"source": "lse", "native_id": "DXY/USD", "limit": 90}],
    },
    "equity.nasdaq100": {
        "label": "Nasdaq 100",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [{"source": "lse", "native_id": "NAS100/USD", "limit": 90}],
    },
    "rate.ea_10y_aaa": {
        "label": "Taux 10 ans zone euro (courbe AAA, BCE)",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "ecb",
             "native_id": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", "limit": 90},
        ],
    },


    # ---------------- Places hors Europe de l'Ouest ----------------
    "equity.kospi": {
        "label": "Kospi (Seoul)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "KS11", "market": "INDX", "limit": 90},
        ],
    },
    "equity.hangseng": {
        "label": "Hang Seng (Hong Kong)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "HSI", "market": "INDX", "limit": 90},
            {"source": "lse", "native_id": "HK33/HKD", "limit": 90},
        ],
    },
    "equity.shanghai": {
        "label": "Shanghai Composite",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "SSEC", "market": "INDX", "limit": 90},
        ],
    },
    "equity.china_a50": {
        "label": "China A50",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "lse", "native_id": "CN50/USD", "limit": 90},
        ],
    },
    "equity.taiwan": {
        "label": "Taiex (Taiwan)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "TWII", "market": "INDX", "limit": 90},
        ],
    },
    "equity.nifty50": {
        "label": "Nifty 50 (Inde)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "NSEI", "market": "INDX", "limit": 90},
        ],
    },
    "equity.sensex": {
        "label": "Sensex (Bombay)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "BSESN", "market": "INDX", "limit": 90},
        ],
    },
    "equity.asx200": {
        "label": "S&P/ASX 200 (Australie)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "AXJO", "market": "INDX", "limit": 90},
            {"source": "lse", "native_id": "AU200/AUD", "limit": 90},
        ],
    },
    "equity.bovespa": {
        "label": "Bovespa (Sao Paulo)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "BVSP", "market": "INDX", "limit": 90},
        ],
    },
    "equity.tsx": {
        "label": "S&P/TSX (Toronto)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "GSPTSE", "market": "INDX", "limit": 90},
        ],
    },
    "equity.mexbol": {
        "label": "S&P/BMV IPC (Mexique)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "MXX", "market": "INDX", "limit": 90},
        ],
    },
    "equity.smi": {
        "label": "SMI (Suisse)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "SSMI", "market": "INDX", "limit": 90},
        ],
    },
    "equity.aex": {
        "label": "AEX (Pays-Bas)",
        "unit": "points",
        "frequency": "daily",
        "category": "actions",
        "providers": [
            {"source": "eodhd", "native_id": "AEX", "market": "INDX", "limit": 90},
        ],
    },


    # ---------------- Italie : l'indice lui-meme est introuvable ----------
    # Le niveau du FTSE MIB n'est servi correctement par aucune source
    # cablee : EODHD ne l'expose pas, Twelve Data le catalogue mais le
    # reserve a ses offres payantes, et le flux IT40 de LSE est fige a juin
    # 2026 au dixieme de sa valeur.
    #
    # Un ETF repliquant avait ete essaye comme approximation quotidienne, puis
    # retire : ses cotations parisiennes se traitent a quelques centaines de
    # parts par seance et reconduisent leur cloture d'un jour sur l'autre. Le
    # 20 aout 2026, l'indice officiel montait de 0,09 % quand l'ETF affichait
    # -1,00 %. Deux trackers compares entre eux semblaient pourtant concorder
    # a 0,14 point pres : ils etaient figes les memes jours, ce qui mesurait
    # leur immobilite commune et non leur fidelite.
    #
    # Reste donc l'indice mensuel de l'OCDE, officiel et sans ambiguite.
    "equity.it_share_index_m": {
        "label": "Indice des cours boursiers Italie (OCDE, base 100)",
        "unit": "indice",
        "frequency": "monthly",
        "category": "actions",
        "providers": [
            {"source": "oecd",
             "native_id": "OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/ITA.M.SHARE......",
             "params": {"startPeriod": "2023-01"}, "limit": 48},
        ],
    },

    # ---------------- Change hors G7 ----------------
    "fx.usdkrw": {
        "label": "Dollar US / Won coreen",
        "unit": "KRW pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDKRW", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdinr": {
        "label": "Dollar US / Roupie indienne",
        "unit": "INR pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDINR", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdbrl": {
        "label": "Dollar US / Real bresilien",
        "unit": "BRL pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDBRL", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdmxn": {
        "label": "Dollar US / Peso mexicain",
        "unit": "MXN pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDMXN", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.audusd": {
        "label": "Dollar australien / Dollar US",
        "unit": "USD pour 1 AUD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "AUDUSD", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdcad": {
        "label": "Dollar US / Dollar canadien",
        "unit": "CAD pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDCAD", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdtwd": {
        "label": "Dollar US / Dollar taiwanais",
        "unit": "TWD pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDTWD", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdsgd": {
        "label": "Dollar US / Dollar de Singapour",
        "unit": "SGD pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDSGD", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdzar": {
        "label": "Dollar US / Rand sud-africain",
        "unit": "ZAR pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDZAR", "market": "FOREX", "limit": 90},
        ],
    },
    "fx.usdtry": {
        "label": "Dollar US / Livre turque",
        "unit": "TRY pour 1 USD",
        "frequency": "daily",
        "category": "change",
        "providers": [
            {"source": "eodhd", "native_id": "USDTRY", "market": "FOREX", "limit": 90},
        ],
    },

    # ---------------- Rendements souverains hors G7 ----------------
    "rate.kr10y": {
        "label": "Taux 10 ans Coree du Sud",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "KR10Y", "limit": 90},
        ],
    },
    "rate.in10y": {
        "label": "Taux 10 ans Inde",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "IN10Y", "limit": 90},
        ],
    },
    "rate.br10y": {
        "label": "Taux 10 ans Bresil",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "BR10Y", "limit": 90},
        ],
    },
    "rate.au10y": {
        "label": "Taux 10 ans Australie",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "AU10Y", "limit": 90},
        ],
    },
    "rate.ca10y": {
        "label": "Taux 10 ans Canada",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "CA10Y", "limit": 90},
        ],
    },
    "rate.mx10y": {
        "label": "Taux 10 ans Mexique",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "MX10Y", "limit": 90},
        ],
    },
    "rate.za10y": {
        "label": "Taux 10 ans Afrique du Sud",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "ZA10Y", "limit": 90},
        ],
    },
    "rate.tr10y": {
        "label": "Taux 10 ans Turquie",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "TR10Y", "limit": 90},
        ],
    },
    "rate.id10y": {
        "label": "Taux 10 ans Indonesie",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "ID10Y", "limit": 90},
        ],
    },
    "rate.hk10y": {
        "label": "Taux 10 ans Hong Kong",
        "unit": "%",
        "frequency": "daily",
        "category": "taux",
        "providers": [
            {"source": "eodhd", "native_id": "HK10Y", "limit": 90},
        ],
    },

    # ---------------- Crypto ----------------
    "crypto.btcusd": {
        "label": "Bitcoin / USD",
        "unit": "USD",
        "frequency": "daily",
        "category": "crypto",
        "providers": [
            {"source": "lse", "native_id": "BTC/USD", "limit": 90},
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
            {"source": "lse", "native_id": "ETH/USD", "limit": 90},
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
    "GOOGL": {"cik": 1652044, "label": "Alphabet Inc."},
    "AMZN": {"cik": 1018724, "label": "Amazon.com Inc."},
    "META": {"cik": 1326801, "label": "Meta Platforms Inc."},
    "TSLA": {"cik": 1318605, "label": "Tesla Inc."},
    "JPM": {"cik": 19617, "label": "JPMorgan Chase & Co."},
}

# Les balises sont donnees par ordre de preference : la taxonomie US-GAAP
# evolue et les societes ne migrent pas au meme rythme, le premier synonyme
# qui renvoie des donnees l'emporte.
XBRL_CONCEPTS = [
    {"key": "assets", "label": "Actif total", "xbrl_unit": "USD",
     "native_id": ["Assets"]},
    {"key": "liabilities", "label": "Passif total", "xbrl_unit": "USD",
     "native_id": ["Liabilities"]},
    {"key": "equity", "label": "Capitaux propres", "xbrl_unit": "USD",
     "native_id": ["StockholdersEquity"]},
    # Les banques ne tiennent pas leur tresorerie sous la meme balise que
    # les societes industrielles.
    {"key": "cash", "label": "Tresorerie", "xbrl_unit": "USD",
     "native_id": ["CashAndCashEquivalentsAtCarryingValue",
                   "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                   "CashAndDueFromBanks"]},
    # Concepts de flux : cibles sur le trimestre, cumuls ecartes.
    {"key": "revenue", "label": "Chiffre d'affaires trimestriel",
     "xbrl_unit": "USD", "duration_days": 91,
     # Une banque ne declare pas de chiffre d'affaires mais un produit net
     # bancaire, sous RevenuesNetOfInterestExpense.
     "native_id": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                   "Revenues",
                   "RevenueFromContractWithCustomerIncludingAssessedTax",
                   "RevenuesNetOfInterestExpense"]},
    # OperatingIncomeLoss n'existe pas chez les banques : leur equivalent est
    # le resultat avant impot des activites poursuivies.
    {"key": "operating_income", "label": "Resultat operationnel trimestriel",
     "xbrl_unit": "USD", "duration_days": 91,
     "native_id": ["OperatingIncomeLoss",
                   "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
                   "ExtraordinaryItemsNoncontrollingInterest"]},
    {"key": "netincome", "label": "Resultat net trimestriel",
     "xbrl_unit": "USD", "duration_days": 91,
     "native_id": ["NetIncomeLoss"]},
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
            duree = concept.get("duration_days")
            specs.append({
                "series_id": f"fundamental.{ticker.lower()}.{concept['key']}",
                "source": "sec_edgar",
                "native_id": concept["native_id"],
                "cik": comp["cik"],
                "xbrl_unit": concept["xbrl_unit"],
                "duration_days": duree,
                "label": f"{comp['label']} - {concept['label']}",
                "unit": "USD",
                # Les concepts de stock sont dates a un instant, pas sur une
                # periode : les declarer trimestriels ferait mentir la
                # frequence annoncee aux controles de fraicheur.
                "frequency": "quarterly" if duree else "instant",
                "category": "fondamentaux",
                "limit": 16,
            })
    return specs
