"""Tests de la persistance et de la couche HTTP."""
import datetime as dt
import json

import pytest

from veille_financiere.http import HttpCache
from veille_financiere.models import Observation, SeriesResult
from veille_financiere.quality import Check
from veille_financiere.storage import Store


def obs(source="ecb", date=dt.date(2026, 8, 20), value=1.1681, series="fx.eurusd"):
    return Observation(series_id=series, source=source, date=date, value=value,
                       unit="USD pour 1 EUR", frequency="daily")


def test_upsert_est_idempotent(tmp_path):
    store = Store(tmp_path / "t.sqlite3")
    store.upsert_observations([obs(), obs()])
    store.upsert_observations([obs()])
    rows = store.history("fx.eurusd")
    assert len(rows) == 1
    store.close()


def test_upsert_met_a_jour_une_valeur_revisee(tmp_path):
    """Les series macro sont revisees: relancer doit corriger, pas dupliquer."""
    store = Store(tmp_path / "t.sqlite3")
    store.upsert_observations([obs(value=1.1600)])
    store.upsert_observations([obs(value=1.1681)])
    rows = store.history("fx.eurusd")
    assert len(rows) == 1 and rows[0]["value"] == pytest.approx(1.1681)
    store.close()


def test_sources_distinctes_coexistent(tmp_path):
    store = Store(tmp_path / "t.sqlite3")
    store.upsert_observations([obs(source="ecb"), obs(source="fred", value=1.1581)])
    assert len(store.history("fx.eurusd")) == 2
    assert len(store.history("fx.eurusd", source="ecb")) == 1
    store.close()


def test_latest_by_series_prend_la_derniere_date(tmp_path):
    store = Store(tmp_path / "t.sqlite3")
    store.upsert_observations([
        obs(date=dt.date(2026, 8, 19), value=1.1605),
        obs(date=dt.date(2026, 8, 20), value=1.1681),
    ])
    latest = store.latest_by_series()
    assert len(latest) == 1 and latest[0]["date"] == "2026-08-20"
    store.close()


def test_journalisation_des_runs_et_controles(tmp_path):
    store = Store(tmp_path / "t.sqlite3")
    res = SeriesResult(series_id="fx.eurusd", source="ecb",
                       observations=[obs()], latency_ms=42)
    store.log_run("run1", "2026-08-20T16:00:00", [res])
    store.log_checks("run1", "2026-08-20T16:00:00",
                     [Check("fx.eurusd", "freshness", "info", True, "ok")])
    assert store.conn.execute("SELECT COUNT(*) FROM run_log").fetchone()[0] == 1
    assert store.conn.execute(
        "SELECT COUNT(*) FROM quality_checks").fetchone()[0] == 1
    store.close()


def test_cache_restitue_puis_expire(tmp_path):
    cache = HttpCache(tmp_path / "cache", ttl_seconds=600)
    cache.set("k", {"a": 1})
    assert cache.get("k") == {"a": 1}

    expire = HttpCache(tmp_path / "cache2", ttl_seconds=0)
    expire.set("k", {"a": 1})
    assert expire.get("k") is None


def test_cache_ignore_un_fichier_corrompu(tmp_path):
    cache = HttpCache(tmp_path / "cache", ttl_seconds=600)
    cache.set("k", {"a": 1})
    cache._path("k").write_text("{ pas du json")
    assert cache.get("k") is None


def test_series_result_expose_la_derniere_observation():
    res = SeriesResult(series_id="s", source="ecb", observations=[
        obs(date=dt.date(2026, 8, 19)), obs(date=dt.date(2026, 8, 20)),
    ])
    assert res.latest.date == dt.date(2026, 8, 20)
    assert SeriesResult(series_id="s", source="ecb").latest is None


def test_series_result_failed():
    res = SeriesResult.failed("s", "ecb", "boom")
    assert not res.ok and res.error == "boom" and res.observations == []


def test_observation_serialisable():
    row = obs().as_row()
    assert row["date"] == "2026-08-20"
    json.dumps(row)   # ne doit pas lever


# ------------------------------------------------------------- disjoncteur
class FlakyTransport:
    """Session factice: renvoie toujours le meme code HTTP."""

    def __init__(self, status, body=None):
        self.status, self.body, self.calls = status, body or {}, 0
        self.headers = {}

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls += 1
        return self

    @property
    def status_code(self):
        return self.status

    @property
    def text(self):
        return "erreur"

    def json(self):
        return self.body


def _fetcher(status, body=None, **kw):
    from veille_financiere.http import Fetcher
    f = Fetcher(cache=None, max_attempts=1, **kw)
    f.session = FlakyTransport(status, body)
    return f


def test_disjoncteur_coupe_apres_trois_echecs(monkeypatch):
    from veille_financiere.http import CircuitOpen
    monkeypatch.setattr("veille_financiere.http.time.sleep", lambda *_: None)
    f = _fetcher(429, circuit_threshold=3)

    for _ in range(3):
        with pytest.raises(RuntimeError):
            f.fetch("https://exemple.test/a")
    calls_avant = f.session.calls

    # Le quatrieme appel ne doit plus atteindre le reseau.
    with pytest.raises(CircuitOpen):
        f.fetch("https://exemple.test/b")
    assert f.session.calls == calls_avant


def test_disjoncteur_se_referme_apres_un_succes(monkeypatch):
    monkeypatch.setattr("veille_financiere.http.time.sleep", lambda *_: None)
    f = _fetcher(429, circuit_threshold=3)
    with pytest.raises(RuntimeError):
        f.fetch("https://exemple.test/a")
    assert f._failures["exemple.test"] == 1

    f.session.status = 200
    f.session.body = {"ok": True}
    assert f.fetch("https://exemple.test/a") == {"ok": True}
    assert "exemple.test" not in f._failures


def test_une_4xx_definitive_n_ouvre_pas_le_disjoncteur(monkeypatch):
    """Un 404 signale une mauvaise requete, pas un hote en panne."""
    monkeypatch.setattr("veille_financiere.http.time.sleep", lambda *_: None)
    f = _fetcher(404, circuit_threshold=3)
    for _ in range(4):
        with pytest.raises(RuntimeError):
            f.fetch("https://exemple.test/a")
    assert f._failures.get("exemple.test", 0) == 0


def test_disjoncteur_isole_les_hotes(monkeypatch):
    from veille_financiere.http import CircuitOpen
    monkeypatch.setattr("veille_financiere.http.time.sleep", lambda *_: None)
    f = _fetcher(429, circuit_threshold=2)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            f.fetch("https://mauvais.test/a")
    with pytest.raises(CircuitOpen):
        f.fetch("https://mauvais.test/b")

    # Un autre hote reste joignable.
    f.session.status = 200
    f.session.body = {"ok": 1}
    assert f.fetch("https://bon.test/a") == {"ok": 1}
