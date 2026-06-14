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

    print(f"Cleaning campaign data in database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables_to_clean = [
        "event_scores",
        "event_source_observations",
        "events",
        "discovery_jobs",
        "campaign_sources",
        "campaigns",
    ]

    # Check if tables exist before deleting
    existing_tables = {
        r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    try:
        for table in tables_to_clean:
            if table in existing_tables:
                cursor.execute(f"DELETE FROM {table}")
                print(f"  - Cleared table '{table}'")
            else:
                print(f"  - Table '{table}' does not exist, skipping")

        # Clean organizations table
        if "organizations" in existing_tables:
            cursor.execute("DELETE FROM organizations")
            print("  - Cleared table 'organizations'")

        conn.commit()

        # Vacuum the database to shrink the file size
        cursor.execute("VACUUM")
        print("Database vacuumed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error occurred during cleanup: {e}")
        return 1
    finally:
        conn.close()

    print("Cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
