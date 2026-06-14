#!/usr/bin/env python3
import json
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

    print(f"Cleaning US21/US22 campaigns from database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    existing_tables = {
        r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    if "campaigns" not in existing_tables:
        print("Campaigns table does not exist.")
        conn.close()
        return 0

    try:
        cursor.execute(
            """
            SELECT id, name FROM campaigns 
            WHERE name LIKE '%US022%' 
               OR name LIKE '%US22%' 
               OR name LIKE '%US-022%'
               OR name LIKE '%US021%' 
               OR name LIKE '%US21%'
               OR name LIKE '%US-021%'
            """
        )
        target_campaigns = cursor.fetchall()

        if not target_campaigns:
            print("No matching campaigns found to clean.")
            conn.close()
            return 0

        print(f"Found {len(target_campaigns)} campaign(s) to clean:")
        for cid, name in target_campaigns:
            print(f"  - {name} ({cid})")

        campaign_ids = [c[0] for c in target_campaigns]
        placeholders = ",".join("?" for _ in campaign_ids)

        # Fetch all event IDs linked to these campaigns
        event_ids = []
        if "events" in existing_tables:
            cursor.execute(
                f"SELECT id FROM events WHERE campaign_id IN ({placeholders})", campaign_ids
            )
            event_ids = [r[0] for r in cursor.fetchall()]

        # Clean transactional data based on event_ids
        if event_ids:
            event_placeholders = ",".join("?" for _ in event_ids)

            # Clean event_source_observations
            if "event_source_observations" in existing_tables:
                cursor.execute(
                    f"DELETE FROM event_source_observations WHERE event_id IN ({event_placeholders})",
                    event_ids,
                )
                print(f"  - Cleared event observations for {len(event_ids)} event(s)")

            # Clean audience_hypotheses
            if "audience_hypotheses" in existing_tables:
                cursor.execute(
                    f"DELETE FROM audience_hypotheses WHERE event_id IN ({event_placeholders})",
                    event_ids,
                )
                print("  - Cleared audience hypotheses")

            # Clean engagement_plans
            if "engagement_plans" in existing_tables:
                cursor.execute(
                    f"DELETE FROM engagement_plans WHERE event_id IN ({event_placeholders})",
                    event_ids,
                )
                print("  - Cleared engagement plans")

            # Clean generated content reviews and handoff records
            if "generated_content_drafts" in existing_tables:
                cursor.execute(
                    f"SELECT id FROM generated_content_drafts WHERE event_id IN ({event_placeholders})",
                    event_ids,
                )
                draft_ids = [r[0] for r in cursor.fetchall()]
                if draft_ids:
                    draft_placeholders = ",".join("?" for _ in draft_ids)
                    if "content_review_decisions" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM content_review_decisions WHERE draft_id IN ({draft_placeholders})",
                            draft_ids,
                        )
                    if "content_handoff_records" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM content_handoff_records WHERE draft_id IN ({draft_placeholders})",
                            draft_ids,
                        )
                    cursor.execute(
                        f"DELETE FROM generated_content_drafts WHERE event_id IN ({event_placeholders})",
                        event_ids,
                    )
                    print(f"  - Cleared {len(draft_ids)} content drafts and reviews")

        # Clean engagement_tasks
        if "engagement_tasks" in existing_tables and event_ids:
            event_placeholders = ",".join("?" for _ in event_ids)
            cursor.execute(
                f"DELETE FROM engagement_tasks WHERE event_id IN ({event_placeholders})",
                event_ids,
            )
            print("  - Cleared engagement tasks")

        # Clean event_scores
        if "event_scores" in existing_tables:
            cursor.execute(
                f"DELETE FROM event_scores WHERE campaign_id IN ({placeholders})",
                campaign_ids,
            )
            print("  - Cleared event scores")

        # Clean events
        if "events" in existing_tables:
            cursor.execute(
                f"DELETE FROM events WHERE campaign_id IN ({placeholders})", campaign_ids
            )
            print("  - Cleared events")

        # Clean discovery_jobs
        if "discovery_jobs" in existing_tables:
            cursor.execute(
                f"DELETE FROM discovery_jobs WHERE campaign_id IN ({placeholders})",
                campaign_ids,
            )
            print("  - Cleared discovery jobs")

        # Clean campaign_sources references
        if "campaign_sources" in existing_tables:
            cursor.execute(
                f"DELETE FROM campaign_sources WHERE campaign_id IN ({placeholders})",
                campaign_ids,
            )
            print("  - Cleared campaign sources references")

        # Clean campaigns
        cursor.execute(f"DELETE FROM campaigns WHERE id IN ({placeholders})", campaign_ids)
        print("  - Cleared campaigns")

        conn.commit()

        # Vacuum the database
        cursor.execute("VACUUM")
        print("Database vacuumed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error occurred: {e}")
        return 1
    finally:
        conn.close()

    print("Cleanup completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
