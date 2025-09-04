\
from dataclasses import dataclass
from typing import Optional, List, Tuple
import calendar
import datetime as dt
import sqlite3

@dataclass
class Threshold:
    service: str
    usage_type: Optional[str]
    metric: str               # 'usage' or 'cost'
    unit: Optional[str]
    monthly_limit: float
    warning_ratio: float = 0.8
    critical_ratio: float = 1.0

def month_start_end(month_str: Optional[str] = None) -> Tuple[str, str, int, int]:
    """
    Returns (start_date, end_date_exclusive, day_of_month_today, days_in_month)
    month_str: 'YYYY-MM' or None for current month
    """
    today = dt.date.today()
    if month_str:
        y, m = map(int, month_str.split("-"))
        first = dt.date(y, m, 1)
    else:
        first = dt.date(today.year, today.month, 1)
    days_in_month = calendar.monthrange(first.year, first.month)[1]
    last_exclusive = first + dt.timedelta(days=days_in_month)
    # if evaluating current month, use today's day index, else full month
    dom = today.day if (first.year == today.year and first.month == today.month) else days_in_month
    return (first.isoformat(), last_exclusive.isoformat(), dom, days_in_month)

def evaluate_thresholds_to_alerts(conn: sqlite3.Connection, when: Optional[str]=None, month: Optional[str]=None) -> List[Tuple[str,str,Optional[str],str,str,str]]:
    """
    Evaluate thresholds and return list of alerts: (date, service, usage_type, severity, rule, message)
    """
    if when is None:
        when = dt.date.today().isoformat()
    start, end, dom, dim = month_start_end(month)
    cur = conn.cursor()

    # Load thresholds
    cur.execute("SELECT service, usage_type, metric, unit, monthly_limit, warning_ratio, critical_ratio FROM thresholds")
    ths = [Threshold(*row) for row in cur.fetchall()]

    alerts: List[Tuple[str,str,Optional[str],str,str,str]] = []

    # Helper: compute MTD aggregates
    # MTD usage by (service, usage_type, unit)
    cur.execute("""
        SELECT service, usage_type, unit, SUM(usage_amount)
        FROM usage_type_daily
        WHERE date >= ? AND date < ?
        GROUP BY service, usage_type, unit
    """, (start, end))
    mtd_usage = {(s,u_t,u): amt for (s,u_t,u,amt) in cur.fetchall()}

    # MTD cost overall and per-service
    cur.execute("""
        SELECT SUM(cost_amount) FROM usage_type_daily
        WHERE date >= ? AND date < ?
    """, (start, end))
    mtd_cost_all = cur.fetchone()[0] or 0.0

    cur.execute("""
        SELECT service, SUM(cost_amount)
        FROM usage_type_daily
        WHERE date >= ? AND date < ?
        GROUP BY service
    """, (start, end))
    mtd_cost_by_service = {s: amt for (s, amt) in cur.fetchall()}

    # Evaluate
    for th in ths:
        if th.metric == 'usage':
            key = (th.service, th.usage_type, th.unit)
            mtd_val = mtd_usage.get(key, 0.0)
            ratio = (mtd_val / th.monthly_limit) if th.monthly_limit else 0.0
            projected = (mtd_val / max(dom,1)) * dim if mtd_val else 0.0

            severity = None
            rule = 'usage_threshold'
            if projected > th.monthly_limit * 1.1 or ratio >= th.critical_ratio:
                severity = 'critical'
            elif projected > th.monthly_limit or ratio >= th.warning_ratio:
                severity = 'warning'

            if severity:
                msg = (f"{th.service} / {th.usage_type or '—'}: "
                       f"MTD {mtd_val:.2f} {th.unit or ''} "
                       f"({ratio*100:.1f}% of {th.monthly_limit:g}); "
                       f"projected {projected:.2f} by month-end.")
                alerts.append((when, th.service, th.usage_type, severity, rule, msg))

        elif th.metric == 'cost':
            if th.service == 'All Services':
                mtd_val = mtd_cost_all
            else:
                mtd_val = mtd_cost_by_service.get(th.service, 0.0)

            ratio = (mtd_val / th.monthly_limit) if th.monthly_limit else 0.0
            projected = (mtd_val / max(dom,1)) * dim if mtd_val else 0.0

            severity = None
            rule = 'cost_guardrail'
            if projected > th.monthly_limit * 1.1 or ratio >= th.critical_ratio:
                severity = 'critical'
            elif projected > th.monthly_limit or ratio >= th.warning_ratio:
                severity = 'warning'

            if severity:
                msg = (f"{th.service}: MTD cost {mtd_val:.4f} {th.unit or 'USD'} "
                       f"({ratio*100:.1f}% of {th.monthly_limit:g}); "
                       f"projected {projected:.4f} by month-end.")
                alerts.append((when, th.service, None, severity, rule, msg))

    return alerts
