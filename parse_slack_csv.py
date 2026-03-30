"""
Slack CSV Export Parser for Ghost Auditor.

How to get the CSV:
1. Go to your Slack workspace: https://yourworkspace.slack.com/admin/members
2. Click "Export member data" button (top right)
3. Slack emails you a CSV download link
4. Download it and save as: slack_members.csv (in this project folder)

Then run: python parse_slack_csv.py
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone

CSV_FILE = "slack_members.csv"


def parse_date(date_str: str) -> datetime | None:
    """Parse various Slack CSV date formats."""
    if not date_str or date_str.lower() in ("never", "", "n/a"):
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def is_inactive(last_active_str: str, threshold_days: int = 30) -> bool:
    """Return True if last_active is more than threshold_days ago."""
    dt = parse_date(last_active_str)
    if dt is None:
        return True  # Never logged in = inactive
    days_ago = (datetime.now(timezone.utc) - dt).days
    return days_ago > threshold_days


def load_from_csv(csv_path: str = CSV_FILE) -> list:
    """
    Parse Slack admin CSV export into Ghost Auditor member format.

    Slack CSV columns (may vary):
    username, email, status, billing-active, has-2fa, has-sso,
    userid, fullname, displayname, expiration-timestamp,
    allow-guests, date-created, date-of-last-login

    Returns list of dicts: [{name, email, last_active, status}]
    """
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found.")
        print()
        print("To get your Slack member CSV:")
        print("  1. Go to https://yourworkspace.slack.com/admin/members")
        print("  2. Click 'Export member data' (top right)")
        print("  3. Slack emails you a download link")
        print("  4. Download and save as: slack_members.csv")
        sys.exit(1)

    members = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Normalize column names (lowercase, strip whitespace)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
        
        for row in reader:
            # Skip deactivated accounts
            status_val = row.get("status", "").strip().lower()
            if status_val in ("deactivated", "deleted"):
                continue

            email = row.get("email", "").strip().lower()
            if not email or "@" not in email:
                continue  # skip bots/apps with no email

            name = (
                row.get("fullname") or
                row.get("displayname") or
                row.get("username") or
                "Unknown"
            ).strip()

            # Last login date — Slack CSV often uses "date-of-last-login" or "last_active"
            last_active_raw = (
                row.get("date-of-last-login") or
                row.get("last_active") or
                row.get("last-active") or
                ""
            ).strip()

            status = "active"
            billing = row.get("billing-active", "").strip().lower()
            if billing == "0" or billing == "false":
                status = "inactive-billing"

            members.append({
                "name": name,
                "email": email,
                "last_active": last_active_raw or "Never",
                "status": status,
                "raw": dict(row),
            })

    return members


if __name__ == "__main__":
    print("=" * 60)
    print("Ghost Auditor — Slack CSV Parser")
    print("=" * 60)
    print()

    members = load_from_csv()
    print(f"Total active members loaded: {len(members)}")

    inactive = [m for m in members if is_inactive(m["last_active"])]
    print(f"Inactive (30+ days):         {len(inactive)}")
    print()

    if inactive:
        print("Inactive members:")
        for m in inactive[:10]:
            print(f"  {m['email']} — last active: {m['last_active']}")

    # Save to members.json for use by analysis + web UI
    output = [
        {k: v for k, v in m.items() if k != "raw"}
        for m in members
    ]
    with open("members.json", "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Saved {len(output)} members to members.json")
    print("=" * 60)
