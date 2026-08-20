"""Couche HTTP partagee: backoff, respect du rate-limit, cache disque.

Les APIs publiques utilisees ici sont gratuites et donc fragiles: Yahoo
Finance renvoie regulierement des 429, CoinGecko limite a quelques appels
par minute. Centraliser les reessais et le cache evite que la qualite des
donnees depende de la chance qu'on a eue au moment du run.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

USER_AGENT = os.environ.get(
    "VF_USER_AGENT",
    "veille-financiere/0.1 (+https://github.com/aminmax9477/Veille_financiere)",
)

# Delai minimum entre deux appels vers un meme hote, en secondes.
_HOST_MIN_INTERVAL: dict[str, float] = {
    "query1.finance.yahoo.com": 1.5,
    "query2.finance.yahoo.com": 1.5,
    "api.coingecko.com": 2.5,
    "data.sec.gov": 0.15,      # SEC demande <= 10 req/s
}
_DEFAULT_MIN_INTERVAL = 0.25

_last_call: dict[str, float] = {}
_lock = threading.Lock()


def _throttle(url: str) -> None:
    host = urlsplit(url).netloc
    gap = _HOST_MIN_INTERVAL.get(host, _DEFAULT_MIN_INTERVAL)
    with _lock:
        prev = _last_call.get(host, 0.0)
        wait = gap - (time.monotonic() - prev)
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()


class HttpCache:
    """Cache disque simple, indexe par URL+params, avec TTL."""

    def __init__(self, root: Path, ttl_seconds: int = 3600) -> None:
        self.root = Path(root)
        self.ttl = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        return self.root / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        if self.ttl <= 0:
            return None
        p = self._path(key)
        if not p.exists() or (time.time() - p.stat().st_mtime) > self.ttl:
            return None
        try:
            return json.loads(p.read_text())["body"]
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, key: str, body: Any) -> None:
        if self.ttl <= 0:
            return
        try:
            self._path(key).write_text(json.dumps({"body": body}))
        except (OSError, TypeError):
            log.debug("cache write failed for %s", key[:80])


class Fetcher:
    """Client HTTP avec reessais; renvoie du JSON ou du texte."""

    RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}

    def __init__(
        self,
        cache: HttpCache | None = None,
        max_attempts: int = 4,
        timeout: int = 25,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
        self.cache = cache
        self.max_attempts = max_attempts
        self.timeout = timeout

    def _cache_key(self, url: str, params: dict | None, headers: dict | None) -> str:
        return json.dumps(
            [url, sorted((params or {}).items()), sorted((headers or {}).items())],
            sort_keys=True,
            default=str,
        )

    def fetch(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        as_json: bool = True,
        use_cache: bool = True,
    ) -> Any:
        key = self._cache_key(url, params, headers)
        if use_cache and self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                log.debug("cache hit %s", url)
                return hit

        last_err: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            _throttle(url)
            try:
                resp = self.session.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
            except requests.RequestException as exc:
                last_err = exc
                self._sleep_backoff(attempt)
                continue

            if resp.status_code in self.RETRY_STATUS:
                last_err = RuntimeError(f"HTTP {resp.status_code} on {url}")
                self._sleep_backoff(attempt, resp.headers.get("Retry-After"))
                continue
            if resp.status_code >= 400:
                # 4xx non transitoire: inutile d'insister.
                raise RuntimeError(
                    f"HTTP {resp.status_code} on {url}: {resp.text[:200]}"
                )

            body = resp.json() if as_json else resp.text
            if use_cache and self.cache is not None:
                self.cache.set(key, body)
            return body

        raise RuntimeError(f"echec apres {self.max_attempts} tentatives: {last_err}")

    def _sleep_backoff(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                time.sleep(min(float(retry_after), 30.0))
                return
            except ValueError:
                pass
        # exponentiel + jitter, plafonne
        time.sleep(min(2 ** attempt * 0.6, 20.0) + random.uniform(0, 0.4))
