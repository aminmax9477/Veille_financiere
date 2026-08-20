"""Teste chaque adaptateur contre les APIs reelles et affiche le resultat."""
import sys, os, logging
sys.path.insert(0, "src")
logging.basicConfig(level=logging.ERROR)
from veille_financiere.config import settings
from veille_financiere.http import Fetcher, HttpCache
from veille_financiere import sources as S
from veille_financiere.registry import iter_specs, iter_company_specs

f = Fetcher(cache=HttpCache(settings.cache_dir, ttl_seconds=1800))
reg = {
    "fred": S.FredSource(f, settings.fred_api_key),
    "ecb": S.EcbSource(f), "eurostat": S.EurostatSource(f),
    "worldbank": S.WorldBankSource(f), "imf": S.ImfSource(f),
    "oecd": S.OecdSource(f),
    "lse": S.LseSource(f, os.environ.get("LSE_API_KEY","")),
    "coingecko": S.CoinGeckoSource(f), "frankfurter": S.FrankfurterSource(f),
    "yahoo": S.YahooSource(f),
    "sec_edgar": S.SecEdgarSource(f, settings.sec_contact),
}
only = sys.argv[1] if len(sys.argv) > 1 else None
specs = iter_specs() + iter_company_specs()
if only:
    specs = [s for s in specs if s["source"] == only]

ok = fail = 0
for spec in specs:
    src = reg.get(spec["source"])
    if src is None:
        continue
    r = src.fetch(spec)
    if r.ok and r.observations:
        latest = r.latest
        ok += 1
        print(f"  OK   {spec['source']:12} {spec['series_id']:34} "
              f"n={len(r.observations):4}  {latest.date}  {latest.value:,.4f}")
    else:
        fail += 1
        print(f"  FAIL {spec['source']:12} {spec['series_id']:34} {r.error[:90]}")
print(f"\n=> {ok} OK / {fail} en echec")
