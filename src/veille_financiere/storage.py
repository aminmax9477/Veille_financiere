"""Persistance SQLite des observations et des controles qualite.

La table ``observations`` est idempotente: relancer la collecte met a jour
les valeurs revisees (frequent en macro) sans creer de doublons.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Any

from .models import Observation

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    series_id    TEXT NOT NULL,
    source       TEXT NOT NULL,
    date         TEXT NOT NULL,
    value        REAL NOT NULL,
    unit         TEXT,
    frequency    TEXT,
    native_id    TEXT,
    retrieved_at TEXT NOT NULL,
    meta         TEXT,
    PRIMARY KEY (series_id, source, date)
);
CREATE INDEX IF NOT EXISTS idx_obs_series ON observations(series_id, date DESC);

CREATE TABLE IF NOT EXISTS run_log (
    run_id      TEXT NOT NULL,
    series_id   TEXT NOT NULL,
    source      TEXT NOT NULL,
    ok          INTEGER NOT NULL,
    n_obs       INTEGER NOT NULL,
    latency_ms  INTEGER,
    error       TEXT,
    started_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_checks (
    run_id     TEXT NOT NULL,
    series_id  TEXT NOT NULL,
    check_name TEXT NOT NULL,
    severity   TEXT NOT NULL,
    passed     INTEGER NOT NULL,
    detail     TEXT,
    created_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert_observations(self, observations: Iterable[Observation]) -> int:
        rows = [
            (
                o.series_id, o.source, o.date.isoformat(), float(o.value),
                o.unit, o.frequency, o.native_id,
                o.retrieved_at.isoformat(), json.dumps(o.meta or {}),
            )
            for o in observations
        ]
        if not rows:
            return 0
        self.conn.executemany(
            """INSERT INTO observations
               (series_id, source, date, value, unit, frequency, native_id,
                retrieved_at, meta)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(series_id, source, date) DO UPDATE SET
                 value=excluded.value,
                 retrieved_at=excluded.retrieved_at,
                 meta=excluded.meta""",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def log_run(self, run_id: str, started_at: str, results: Iterable[Any]) -> None:
        self.conn.executemany(
            """INSERT INTO run_log
               (run_id, series_id, source, ok, n_obs, latency_ms, error, started_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            [
                (run_id, r.series_id, r.source, int(r.ok), len(r.observations),
                 r.latency_ms, r.error, started_at)
                for r in results
            ],
        )
        self.conn.commit()

    def log_checks(self, run_id: str, created_at: str, checks: Iterable[Any]) -> None:
        self.conn.executemany(
            """INSERT INTO quality_checks
               (run_id, series_id, check_name, severity, passed, detail, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            [
                (run_id, c.series_id, c.name, c.severity, int(c.passed),
                 c.detail, created_at)
                for c in checks
            ],
        )
        self.conn.commit()

    def latest_by_series(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT o.* FROM observations o
               JOIN (SELECT series_id, source, MAX(date) AS mx
                     FROM observations GROUP BY series_id, source) m
                 ON o.series_id = m.series_id AND o.source = m.source
                AND o.date = m.mx
               ORDER BY o.series_id, o.source"""
        ).fetchall()

    def history(self, series_id: str, source: str | None = None,
                limit: int = 400) -> list[sqlite3.Row]:
        if source:
            return self.conn.execute(
                """SELECT * FROM observations WHERE series_id=? AND source=?
                   ORDER BY date DESC LIMIT ?""",
                (series_id, source, limit),
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM observations WHERE series_id=? ORDER BY date DESC LIMIT ?",
            (series_id, limit),
        ).fetchall()

    def close(self) -> None:
        self.conn.close()
