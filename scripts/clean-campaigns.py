#!/usr/bin/env python3
import sqlite3
import sys
from pathlib import Path

# Add src to sys.path so we can import the settings
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from livelead.runtime.settings import parse_settings


def main():
    settings = parse_settings()
    db_path = Path(settings.sqlite_path)

    if not db_path.exists():
        print(f"Database file does not exist: {db_path}")
        return 0

    print(f"Cleaning E2E campaign data in database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if tables exist before deleting
    existing_tables = {
        r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    if "campaigns" not in existing_tables:
        print("Campaigns table does not exist. Nothing to clean.")
        conn.close()
        return 0

    try:
        # Find all campaign IDs that contain "E2E" or "e2e"
        cursor.execute(
            "SELECT id, name FROM campaigns WHERE name LIKE '%E2E%' OR name LIKE '%e2e%'"
        )
        e2e_campaigns = cursor.fetchall()

        if not e2e_campaigns:
            print("No campaigns with 'E2E' in their name were found. Skipping cleanup.")
            conn.close()
            return 0

        print(f"Found {len(e2e_campaigns)} E2E campaign(s) to clean:")
        for cid, name in e2e_campaigns:
            print(f"  - {name} ({cid})")

        campaign_ids = [c[0] for c in e2e_campaigns]

        # 1. Clean event_source_observations by querying event_ids first
        if "events" in existing_tables and "event_source_observations" in existing_tables:
            # Get all event IDs for these campaigns
            placeholders = ",".join("?" for _ in campaign_ids)
            cursor.execute(
                f"SELECT id FROM events WHERE campaign_id IN ({placeholders})", campaign_ids
            )
            event_ids = [r[0] for r in cursor.fetchall()]

            if event_ids:
                event_placeholders = ",".join("?" for _ in event_ids)
                cursor.execute(
                    f"DELETE FROM event_source_observations WHERE event_id IN ({event_placeholders})",
                    event_ids,
                )
                print(f"  - Cleared event observations for {len(event_ids)} event(s)")

        # 2. Clean event_scores
        if "event_scores" in existing_tables:
            placeholders = ",".join("?" for _ in campaign_ids)
            cursor.execute(
                f"DELETE FROM event_scores WHERE campaign_id IN ({placeholders})", campaign_ids
            )
            print("  - Cleared event scores")

        # 3. Clean events
        if "events" in existing_tables:
            placeholders = ",".join("?" for _ in campaign_ids)
            cursor.execute(
                f"DELETE FROM events WHERE campaign_id IN ({placeholders})", campaign_ids
            )
            print("  - Cleared events")

        # 4. Clean discovery_jobs
        if "discovery_jobs" in existing_tables:
            placeholders = ",".join("?" for _ in campaign_ids)
            cursor.execute(
                f"DELETE FROM discovery_jobs WHERE campaign_id IN ({placeholders})", campaign_ids
            )
            print("  - Cleared discovery jobs")

        # 5. Clean campaign_sources
        if "campaign_sources" in existing_tables:
            placeholders = ",".join("?" for _ in campaign_ids)
            cursor.execute(
                f"DELETE FROM campaign_sources WHERE campaign_id IN ({placeholders})", campaign_ids
            )
            print("  - Cleared campaign sources")

        # 6. Finally, clean the campaigns
        placeholders = ",".join("?" for _ in campaign_ids)
        cursor.execute(f"DELETE FROM campaigns WHERE id IN ({placeholders})", campaign_ids)
        print("  - Cleared campaigns")

        conn.commit()

        # Vacuum the database to shrink the file size
        cursor.execute("VACUUM")
        print("Database vacuumed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error occurred during E2E cleanup: {e}")
        return 1
    finally:
        conn.close()

    print("E2E Cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
