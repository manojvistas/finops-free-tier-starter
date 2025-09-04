\
import os
import sqlite3
from typing import Iterable, Tuple, Optional, Dict

DB_PATH = os.environ.get("FINOPS_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "finops.db"))
DB_PATH = os.path.abspath(DB_PATH)

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS usage_type_daily (
    date TEXT NOT NULL,                -- YYYY-MM-DD
    service TEXT NOT NULL,
    usage_type TEXT NOT NULL,
    usage_amount REAL,
    unit TEXT,
    cost_amount REAL,
    currency TEXT,
    PRIMARY KEY (date, service, usage_type)
);

CREATE TABLE IF NOT EXISTS thresholds (
    service TEXT NOT NULL,
    usage_type TEXT,                   -- nullable for global cost guardrails
    metric TEXT NOT NULL CHECK (metric IN ('usage','cost')),
    unit TEXT,
    monthly_limit REAL NOT NULL,
    warning_ratio REAL NOT NULL DEFAULT 0.8,
    critical_ratio REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (service, usage_type, metric, unit)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,               -- alert evaluation date YYYY-MM-DD
    service TEXT NOT NULL,
    usage_type TEXT,
    severity TEXT CHECK (severity IN ('info','warning','critical')) NOT NULL,
    rule TEXT,
    message TEXT
);

CREATE VIEW IF NOT EXISTS service_cost_daily AS
SELECT date, service, SUM(cost_amount) AS cost_usd
FROM usage_type_daily
GROUP BY date, service;
"""

def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)

def upsert_usage_type_rows(rows: Iterable[Tuple[str,str,str,float,str,float,str]]):
    """
    rows: iterable of (date, service, usage_type, usage_amount, unit, cost_amount, currency)
    """
    with get_conn() as conn:
        conn.executemany("""
            INSERT INTO usage_type_daily (date, service, usage_type, usage_amount, unit, cost_amount, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, service, usage_type) DO UPDATE SET
                usage_amount=excluded.usage_amount,
                unit=excluded.unit,
                cost_amount=excluded.cost_amount,
                currency=excluded.currency
        """, list(rows))

def replace_thresholds(thresholds: Iterable[Dict]):
    with get_conn() as conn:
        conn.execute("DELETE FROM thresholds")
        conn.executemany("""
            INSERT INTO thresholds (service, usage_type, metric, unit, monthly_limit, warning_ratio, critical_ratio)
            VALUES (:service, :usage_type, :metric, :unit, :monthly_limit, :warning_ratio, :critical_ratio)
        """, list(thresholds))

def insert_alert(date: str, service: str, usage_type: Optional[str], severity: str, rule: str, message: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO alerts (date, service, usage_type, severity, rule, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, service, usage_type, severity, rule, message))
