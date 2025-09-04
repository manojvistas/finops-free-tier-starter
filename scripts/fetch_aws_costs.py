\
#!/usr/bin/env python
import argparse
import os
import sys
import datetime as dt
from typing import List, Tuple

import boto3
import yaml

# Local imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from lib.db import init_db, upsert_usage_type_rows, replace_thresholds, DB_PATH

def daterange(start: dt.date, end_exclusive: dt.date):
    current = start
    while current < end_exclusive:
        yield current
        current += dt.timedelta(days=1)

def get_cost_and_usage(client, start: str, end: str):
    """
    Calls GetCostAndUsage grouped by SERVICE and USAGE_TYPE.
    Returns list of tuples ready for DB upsert: (date, service, usage_type, usage_amount, unit, cost_amount, currency)
    """
    rows: List[Tuple[str,str,str,float,str,float,str]] = []
    token = None
    while True:
        resp = client.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
            ],
            NextPageToken=token
        ) if token else client.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
            ]
        )
        for day in resp.get('ResultsByTime', []):
            date = day['TimePeriod']['Start']
            for group in day.get('Groups', []):
                service, usage_type = group['Keys']
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                currency = group['Metrics']['UnblendedCost']['Unit']
                usage_amount = float(group['Metrics']['UsageQuantity']['Amount'])
                unit = group['Metrics']['UsageQuantity']['Unit']
                rows.append((date, service, usage_type, usage_amount, unit, cost, currency))
        token = resp.get('NextPageToken')
        if not token:
            break
    return rows

def main():
    parser = argparse.ArgumentParser(description="Fetch AWS Cost Explorer daily usage+cost into SQLite")
    parser.add_argument("--start", help="Start date YYYY-MM-DD (default: yesterday)", default=None)
    parser.add_argument("--end", help="End date (exclusive) YYYY-MM-DD (default: today)", default=None)
    parser.add_argument("--region", help="AWS region for CE (use us-east-1)", default="us-east-1")
    parser.add_argument("--thresholds", help="Path to thresholds YAML", default=os.path.join(os.path.dirname(__file__), "..", "config", "thresholds.yaml"))
    args = parser.parse_args()

    today = dt.date.today()
    start = dt.date.fromisoformat(args.start) if args.start else (today - dt.timedelta(days=1))
    end = dt.date.fromisoformat(args.end) if args.end else today

    # Initialize DB and load thresholds
    init_db()
    with open(args.thresholds, "r") as f:
        cfg = yaml.safe_load(f) or {}
        replace_thresholds(cfg.get("thresholds", []))

    # AWS CE is a global service (use us-east-1)
    client = boto3.client("ce", region_name=args.region)

    rows = get_cost_and_usage(client, start.isoformat(), end.isoformat())
    if not rows:
        print("No rows returned from Cost Explorer (check CE enablement and IAM).")
        return

    upsert_usage_type_rows(rows)
    print(f"DB: {DB_PATH}")
    print(f"Inserted/updated {len(rows)} rows from {start} to {end} (end exclusive).")

if __name__ == "__main__":
    main()
