\
#!/usr/bin/env python
import argparse
import os
import sys
import datetime as dt

# Local imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_conn, init_db, insert_alert
from lib.rules import evaluate_thresholds_to_alerts

def main():
    parser = argparse.ArgumentParser(description="Evaluate free-tier usage/cost rules and write alerts")
    parser.add_argument("--month", help="Month to evaluate YYYY-MM (default: current month)", default=None)
    args = parser.parse_args()

    init_db()
    conn = get_conn()
    today = dt.date.today().isoformat()

    alerts = evaluate_thresholds_to_alerts(conn, when=today, month=args.month)
    if not alerts:
        print("No alerts generated.")
        return

    for (date, service, usage_type, severity, rule, message) in alerts:
        insert_alert(date, service, usage_type, severity, rule, message)
        print(f"[{severity.upper()}] {service} / {usage_type or '—'} :: {message}")

if __name__ == "__main__":
    main()
