# Veille financiere - 20/08/2026 16:05 UTC

*Run `1a180b4a267d` - 29 series, 1236 observations, 32/44 appels reussis.*

**Qualite** : 103/108 controles valides (2 avertissement(s), 3 erreur(s))

## Marches actions

| | Serie | Valeur | Unite | Var. | Date | Source | Sources |
|---|---|---:|---|---:|---|---|---|
| ERR | CAC 40 | n/d | points |  | n/d | - | 0 |
| ERR | Euro Stoxx 50 | n/d | points |  | n/d | - | 0 |
| OK | S&P 500 | 7,707.98 | points | +0.21% | 2026-08-19 | fred | 1 |
| OK | VIX (volatilite implicite S&P 500) | 14.8900 | points | -6.00% | 2026-08-19 | fred | 1 |

## Taux de change

| | Serie | Valeur | Unite | Var. | Date | Source | Sources |
|---|---|---:|---|---:|---|---|---|
| OK | Euro / Dollar US | 1.1681 | USD pour 1 EUR | +0.65% | 2026-08-20 | ecb | 3 |
| OK | Livre sterling / Dollar US | 1.3626 | USD pour 1 GBP | +0.52% | 2026-08-20 | frankfurter | 2 |
| OK | Dollar US / Yen | 159.21 | JPY pour 1 USD | -0.09% | 2026-08-14 | fred | 1 |

## Crypto-actifs

| | Serie | Valeur | Unite | Var. | Date | Source | Sources |
|---|---|---:|---|---:|---|---|---|
| OK | Bitcoin / USD | 72,438.00 | USD |  | 2026-08-20 | coingecko | 1 |
| OK | Ethereum / USD | 2,330.59 | USD |  | 2026-08-20 | coingecko | 1 |

## Fondamentaux societes

| | Serie | Valeur | Unite | Var. | Date | Source | Sources |
|---|---|---:|---|---:|---|---|---|
| OK | Apple Inc. - Actif total | 383.27 Md | USD | +3.28% | 2026-06-27 | sec_edgar | 1 |
| OK | Apple Inc. - Resultat net | 101.46 Md | USD | +41.56% | 2026-06-27 | sec_edgar | 1 |
| OK | Apple Inc. - Capitaux propres | 107.52 Md | USD | +0.97% | 2026-06-27 | sec_edgar | 1 |
| OK | Microsoft Corp. - Actif total | 758.38 Md | USD | +9.24% | 2026-06-30 | sec_edgar | 1 |
| OK | Microsoft Corp. - Resultat net | 133.75 Md | USD | +36.50% | 2026-06-30 | sec_edgar | 1 |
| OK | Microsoft Corp. - Capitaux propres | 442.39 Md | USD | +6.76% | 2026-06-30 | sec_edgar | 1 |
| OK | NVIDIA Corp. - Actif total | 259.47 Md | USD | +25.47% | 2026-04-26 | sec_edgar | 1 |
| OK | NVIDIA Corp. - Resultat net | 58.32 Md | USD | -51.43% | 2026-04-26 | sec_edgar | 1 |
| OK | NVIDIA Corp. - Capitaux propres | 195.47 Md | USD | +24.27% | 2026-04-26 | sec_edgar | 1 |

## Macroeconomie

| | Serie | Valeur | Unite | Var. | Date | Source | Sources |
|---|---|---:|---|---:|---|---|---|
| WARN | Inflation zone euro (IPCH, glissement annuel) | 1.9000 | % | -0.20 pt | 2025-12-31 | ecb | 2 |
| OK | Croissance du PIB France | 1.1000 | % | +0.00 pt | 2031-12-31 | imf | 2 |
| WARN | Inflation France (IPCH, glissement annuel) | 0.7000 | % | -0.10 pt | 2025-12-31 | ecb | 2 |
| OK | Inflation US (IPC, glissement annuel) | 3.3039 | % | -0.16 pt | 2026-07-01 | fred | 1 |
| OK | Taux de chomage Etats-Unis | 4.1000 | % | -0.10 pt | 2026-07-01 | fred | 1 |

## Matieres premieres

| | Serie | Valeur | Unite | Var. | Date | Source | Sources |
|---|---|---:|---|---:|---|---|---|
| OK | Petrole Brent | 95.2900 | USD/baril | +3.09% | 2026-08-18 | fred | 1 |
| ERR | Or | n/d | USD/once |  | n/d | - | 0 |

## Taux d'interet

| | Serie | Valeur | Unite | Var. | Date | Source | Sources |
|---|---|---:|---|---:|---|---|---|
| OK | Taux de facilite de depot BCE | 2.2500 | % | +0.00 pt | 2026-08-20 | ecb | 1 |
| OK | Taux effectif des Fed Funds | 3.6300 | % | +0.00 pt | 2026-08-18 | fred | 1 |
| OK | Taux 2 ans Etats-Unis | 4.1900 | % | +0.00 pt | 2026-08-18 | fred | 1 |
| OK | Taux 10 ans Etats-Unis | 4.7100 | % | -0.01 pt | 2026-08-18 | fred | 1 |

## Points d'attention

| Gravite | Serie | Controle | Detail |
|---|---|---|---|
| error | `commodity.gold` | collecte | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/GC=F |
| error | `equity.cac40` | collecte | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/^FCHI |
| error | `equity.eurostoxx50` | collecte | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/^STOXX50E |
| warning | `macro.ea_hicp_yoy` | freshness | donnee obsolete: 2025-12-31 soit 232 j (seuil 75 j pour frequence monthly) |
| warning | `macro.fr_hicp_yoy` | freshness | donnee obsolete: 2025-12-31 soit 232 j (seuil 75 j pour frequence monthly) |

## Appels en echec

| Source | Serie | Erreur |
|---|---|---|
| yahoo | `fx.eurusd` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X |
| yahoo | `fx.gbpusd` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/GBPUSD=X |
| yahoo | `fx.usdjpy` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/USDJPY=X |
| yahoo | `rate.us10y` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/^TNX |
| yahoo | `equity.sp500` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/^GSPC |
| yahoo | `equity.cac40` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/^FCHI |
| yahoo | `equity.eurostoxx50` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/^STOXX50E |
| yahoo | `equity.vix` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/^VIX |
| yahoo | `commodity.brent` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/BZ=F |
| yahoo | `commodity.gold` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/GC=F |
| yahoo | `crypto.btcusd` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD |
| yahoo | `crypto.ethusd` | echec apres 4 tentatives: HTTP 429 on https://query1.finance.yahoo.com/v8/finance/chart/ETH-USD |

---

Sources : BCE, FRED (Federal Reserve Bank of St. Louis), Eurostat, Banque mondiale, FMI, SEC EDGAR, CoinGecko, Frankfurter, Yahoo Finance.
