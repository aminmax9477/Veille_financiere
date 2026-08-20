"""Configuration: chemins, cles d'API, parametres de qualite."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Charge un .env minimal sans ecraser l'environnement existant."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip("'\""))


_load_dotenv(ROOT / ".env")


@dataclass(slots=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: ROOT / "data")
    cache_ttl: int = int(os.environ.get("VF_CACHE_TTL", "3600"))

    # Cles d'API. Seule FRED est requise pour la couverture macro US.
    fred_api_key: str = field(
        default_factory=lambda: os.environ.get("FRED_API_KEY", "")
    )
    # Contact envoye a la SEC, qui exige un User-Agent identifiable.
    sec_contact: str = field(
        default_factory=lambda: os.environ.get("VF_SEC_CONTACT", "")
    )

    # Seuil de divergence relative au-dela duquel deux sources sont en desaccord.
    reconcile_tolerance: float = float(
        os.environ.get("VF_RECONCILE_TOLERANCE", "0.005")
    )

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "veille.sqlite3"

    def enabled_sources(self) -> dict[str, bool]:
        """Quelles sources sont utilisables compte tenu des cles presentes."""
        return {
            "fred": bool(self.fred_api_key),
            "ecb": True,
            "eurostat": True,
            "worldbank": True,
            "imf": True,
            "oecd": True,
            "sec_edgar": True,
            "coingecko": True,
            "frankfurter": True,
            "yahoo": True,
        }


settings = Settings()
