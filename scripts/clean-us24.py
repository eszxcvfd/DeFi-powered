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

    print(f"Cleaning US24 data from database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    existing_tables = {
        r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    try:
        # 1. Clean browser profiles matching US024 / US24
        if "browser_profiles" in existing_tables:
            cursor.execute(
                """
                SELECT id, name FROM browser_profiles 
                WHERE name LIKE '%US024%' 
                   OR name LIKE '%US24%' 
                   OR name LIKE '%US-024%'
                """
            )
            target_profiles = cursor.fetchall()
            if target_profiles:
                print(f"Found {len(target_profiles)} browser profile(s) to clean:")
                for pid, name in target_profiles:
                    print(f"  - {name} ({pid})")

                profile_ids = [p[0] for p in target_profiles]
                placeholders = ",".join("?" for _ in profile_ids)

                # Clean browser sessions referencing these profiles
                if "browser_sessions" in existing_tables:
                    cursor.execute(
                        f"SELECT id FROM browser_sessions WHERE browser_profile_id IN ({placeholders})",
                        profile_ids,
                    )
                    session_ids = [r[0] for r in cursor.fetchall()]

                    if session_ids:
                        session_placeholders = ",".join("?" for _ in session_ids)
                        
                        # Clean browser_session_actions
                        if "browser_session_actions" in existing_tables:
                            cursor.execute(
                                f"DELETE FROM browser_session_actions WHERE session_id IN ({session_placeholders})",
                                session_ids,
                            )
                            print(f"  - Cleared browser session actions for {len(session_ids)} session(s)")

                        # Clean browser_action_confirmations
                        if "browser_action_confirmations" in existing_tables:
                            cursor.execute(
                                f"DELETE FROM browser_action_confirmations WHERE session_id IN ({session_placeholders})",
                                session_ids,
                            )
                            print(f"  - Cleared browser action confirmations for {len(session_ids)} session(s)")

                        # Clean browser_debug_artifacts
                        if "browser_debug_artifacts" in existing_tables:
                            cursor.execute(
                                f"DELETE FROM browser_debug_artifacts WHERE session_id IN ({session_placeholders})",
                                session_ids,
                            )
                            print(f"  - Cleared browser debug artifacts for {len(session_ids)} session(s)")

                        # Clean browser_sessions themselves
                        cursor.execute(
                            f"DELETE FROM browser_sessions WHERE id IN ({session_placeholders})",
                            session_ids,
                        )
                        print(f"  - Cleared {len(session_ids)} browser session(s)")

                # Delete the profiles
                cursor.execute(
                    f"DELETE FROM browser_profiles WHERE id IN ({placeholders})",
                    profile_ids,
                )
                print("  - Cleared browser profiles")
            else:
                print("No browser profiles found matching US024.")

        # 2. Clean sources (connectors) matching US024 / US24
        if "sources" in existing_tables:
            cursor.execute(
                """
                SELECT id, name FROM sources 
                WHERE name LIKE '%US024%' 
                   OR name LIKE '%US24%' 
                   OR name LIKE '%US-024%'
                """
            )
            target_sources = cursor.fetchall()
            if target_sources:
                print(f"Found {len(target_sources)} source(s) to clean:")
                for sid, name in target_sources:
                    print(f"  - {name} ({sid})")

                source_ids = [s[0] for s in target_sources]
                placeholders = ",".join("?" for _ in source_ids)

                # Clean campaign_sources references first
                if "campaign_sources" in existing_tables:
                    cursor.execute(
                        f"DELETE FROM campaign_sources WHERE source_id IN ({placeholders})",
                        source_ids,
                    )
                    print("  - Cleared source references from campaign_sources")

                # Delete from sources
                cursor.execute(f"DELETE FROM sources WHERE id IN ({placeholders})", source_ids)
                print("  - Cleared sources")
            else:
                print("No sources found matching US024.")

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

    print("US024 Cleanup completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
