#!/usr/bin/env python3
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

# Add src to sys.path so we can import settings
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from livelead.runtime.settings import parse_settings

DEV_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"


def main():
    settings = parse_settings()
    db_path = Path(settings.sqlite_path)

    if not db_path.exists():
        print(f"Database file does not exist: {db_path}")
        return 1

    print(f"Reseeding sources in database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Clear campaign-sources references
        cursor.execute("DELETE FROM campaign_sources")
        print("  - Cleared campaign_sources table")

        # Clear sources table
        cursor.execute("DELETE FROM sources")
        print("  - Cleared sources table")

        # Define 2 clean, realistic sources
        new_sources = [
            {
                "id": str(uuid4()),
                "organization_id": DEV_ORGANIZATION_ID,
                "name": "TechCrunch Web3 Events",
                "domain": "techcrunch.com",
                "connector_type": "rss",
                "automation_engine": "none",
                "authentication_mode": "none",
                "enabled": 1,
                "approved": 1,
                "approved_by": "admin",
                "approved_at": datetime.now(UTC).isoformat(),
                "policy_json": json.dumps(
                    {
                        "access_mode": "feed",
                        "quota_per_day": 500,
                        "quota_used_today": 0,
                        "window_start_hour": 0,
                        "window_end_hour": 23,
                        "retention_days": 90,
                        "valid": True,
                    }
                ),
                "rate_limit_json": "{}",
                "secret_ciphertext": None,
            },
            {
                "id": str(uuid4()),
                "organization_id": DEV_ORGANIZATION_ID,
                "name": "CoinDesk Crypto Events",
                "domain": "coindesk.com",
                "connector_type": "ics",
                "automation_engine": "none",
                "authentication_mode": "none",
                "enabled": 1,
                "approved": 1,
                "approved_by": "admin",
                "approved_at": datetime.now(UTC).isoformat(),
                "policy_json": json.dumps(
                    {
                        "access_mode": "feed",
                        "quota_per_day": 500,
                        "quota_used_today": 0,
                        "window_start_hour": 0,
                        "window_end_hour": 23,
                        "retention_days": 90,
                        "valid": True,
                    }
                ),
                "rate_limit_json": "{}",
                "secret_ciphertext": None,
            },
        ]

        for src in new_sources:
            cursor.execute(
                """
                INSERT INTO sources (
                    id, organization_id, name, domain, connector_type, 
                    automation_engine, authentication_mode, enabled, approved, 
                    approved_by, approved_at, policy_json, rate_limit_json, 
                    secret_ciphertext, created_at, updated_at
                ) VALUES (
                    :id, :organization_id, :name, :domain, :connector_type, 
                    :automation_engine, :authentication_mode, :enabled, :approved, 
                    :approved_by, :approved_at, :policy_json, :rate_limit_json, 
                    :secret_ciphertext, datetime('now'), datetime('now')
                )
                """,
                src,
            )
            print(f"  + Added source '{src['name']}' ({src['domain']})")

        conn.commit()
        print("Reseed completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error occurred during reseed: {e}")
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
