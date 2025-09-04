\
#!/usr/bin/env python
import os
import sys
import datetime as dt
from pathlib import Path

import pandas as pd

# Local imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_conn, DB_PATH

def main():
    conn = get_conn()
    today = dt.date.today()
    start = today - dt.timedelta(days=6)
    reports_dir = Path(os.path.join(os.path.dirname(__file__), "..", "reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Daily totals
    df_daily = pd.read_sql_query("""
        SELECT date, ROUND(SUM(cost_amount), 6) AS cost_usd
        FROM usage_type_daily
        WHERE date >= ?
        GROUP BY date
        ORDER BY date
    """, conn, params=(start.isoformat(),))

    # Top services
    df_top = pd.read_sql_query("""
        SELECT service, ROUND(SUM(cost_amount), 6) AS cost_usd
        FROM usage_type_daily
        WHERE date >= ?
        GROUP BY service
        ORDER BY cost_usd DESC
        LIMIT 10
    """, conn, params=(start.isoformat(),))

    # Recent alerts
    df_alerts = pd.read_sql_query("""
        SELECT date, service, COALESCE(usage_type,'—') AS usage_type, severity, message
        FROM alerts
        WHERE date >= ?
        ORDER BY date DESC, severity DESC
    """, conn, params=(start.isoformat(),))

    # Write CSV
    csv_path = reports_dir / f"weekly_report_{today.isoformat()}.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("# Daily Totals\n")
        df_daily.to_csv(f, index=False)
        f.write("\n# Top Services\n")
        df_top.to_csv(f, index=False)
        f.write("\n# Alerts\n")
        df_alerts.to_csv(f, index=False)

    # Write Markdown
    md_path = reports_dir / f"weekly_report_{today.isoformat()}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Weekly Usage Report ({start.isoformat()} → {today.isoformat()})\n\n")
        total = float(df_daily["cost_usd"].sum()) if not df_daily.empty else 0.0
        f.write(f"**Total Cost (7d): ${total:.6f}**\n\n")

        f.write("## Daily Cost\n\n")
        if df_daily.empty:
            f.write("_No data for the period._\n\n")
        else:
            f.write(df_daily.to_markdown(index=False))
            f.write("\n\n")

        f.write("## Top Services (by cost)\n\n")
        if df_top.empty:
            f.write("_No data for the period._\n\n")
        else:
            f.write(df_top.to_markdown(index=False))
            f.write("\n\n")

        f.write("## Alerts (last 7 days)\n\n")
        if df_alerts.empty:
            f.write("_No alerts._\n")
        else:
            f.write(df_alerts.to_markdown(index=False))
            f.write("\n")

    print(f"DB: {DB_PATH}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")

if __name__ == "__main__":
    main()
