"""Adaptateurs de sources de donnees."""
from .base import Source
from .borsa_italiana import BorsaItalianaSource
from .coingecko import CoinGeckoSource
from .ecb import EcbSource
from .eodhd import EodhdSource
from .eurostat import EurostatSource
from .frankfurter import FrankfurterSource
from .fred import FredSource
from .imf import ImfSource
from .lse import LseSource
from .oecd import OecdSource
from .sec_edgar import SecEdgarSource
from .worldbank import WorldBankSource
from .yahoo import YahooSource

__all__ = [
    "Source", "BorsaItalianaSource", "CoinGeckoSource", "EcbSource", "EodhdSource",
    "EurostatSource",
    "FrankfurterSource", "FredSource", "ImfSource", "LseSource",
    "OecdSource",
    "SecEdgarSource",
    "WorldBankSource", "YahooSource",
]
