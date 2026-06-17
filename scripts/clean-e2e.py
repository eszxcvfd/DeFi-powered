#!/usr/bin/env python3
import json
import sqlite3
import sys
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

# Add src to sys.path so we can import the settings
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from livelead.runtime.settings import parse_settings

DEV_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"

DEFAULT_SOURCES = [
    {
        "name": "TechCrunch Web3 Events",
        "domain": "techcrunch.com",
        "connector_type": "rss",
        "policy": {
            "access_mode": "feed",
            "quota_per_day": 500,
            "quota_used_today": 0,
            "window_start_hour": 0,
            "window_end_hour": 23,
            "retention_days": 90,
            "valid": True,
        },
    },
    {
        "name": "CoinDesk Crypto Events",
        "domain": "coindesk.com",
        "connector_type": "ics",
        "policy": {
            "access_mode": "feed",
            "quota_per_day": 500,
            "quota_used_today": 0,
            "window_start_hour": 0,
            "window_end_hour": 23,
            "retention_days": 90,
            "valid": True,
        },
    },
    {
        "name": "DeFi Llama Events",
        "domain": "defillama.com",
        "connector_type": "rss",
        "policy": {
            "access_mode": "feed",
            "quota_per_day": 500,
            "quota_used_today": 0,
            "window_start_hour": 0,
            "window_end_hour": 23,
            "retention_days": 90,
            "valid": True,
        },
    },
    {
        "name": "Ethereum Foundation Events",
        "domain": "ethereum.org",
        "connector_type": "ics",
        "policy": {
            "access_mode": "feed",
            "quota_per_day": 500,
            "quota_used_today": 0,
            "window_start_hour": 0,
            "window_end_hour": 23,
            "retention_days": 90,
            "valid": True,
        },
    },
    {
        "name": "Fintech Futures Events",
        "domain": "fintechfutures.com",
        "connector_type": "rss",
        "policy": {
            "access_mode": "feed",
            "quota_per_day": 500,
            "quota_used_today": 0,
            "window_start_hour": 0,
            "window_end_hour": 23,
            "retention_days": 90,
            "valid": True,
        },
    },
    {
        "name": "Product Hunt Product Launches",
        "domain": "producthunt.com",
        "connector_type": "rss",
        "policy": {
            "access_mode": "feed",
            "quota_per_day": 500,
            "quota_used_today": 0,
            "window_start_hour": 0,
            "window_end_hour": 23,
            "retention_days": 90,
            "valid": True,
        },
    },
]


def main():
    settings = parse_settings()
    db_path = Path(settings.sqlite_path)

    if not db_path.exists():
        print(f"Database file does not exist: {db_path}")
        return 0

    print(f"Cleaning E2E and test garbage from database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    existing_tables = {
        r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    test_patterns = [
        "e2e", "discovery camp", "browser e2e", "us021", "us022", "us023", "us024",
        "us025", "us026", "live feed", "website pw", "website selenium", 
        "schedule camp", "copilot camp", "qe camp", "ai feedback", "scoring suggest",
        "manual test campaign", "test campaign", "manual test profile", "test profile"
    ]

    try:
        # 1. Clean E2E & Test Campaigns and all cascading data
        if "campaigns" in existing_tables:
            cursor.execute("SELECT id, name FROM campaigns")
            all_campaigns = cursor.fetchall()
            
            e2e_campaigns = []
            for cid, name in all_campaigns:
                name_lower = name.lower()
                if any(pat in name_lower for pat in test_patterns):
                    e2e_campaigns.append((cid, name))

            if e2e_campaigns:
                print(f"Found {len(e2e_campaigns)} E2E/test campaign(s) to clean:")
                for cid, name in e2e_campaigns:
                    print(f"  - {name} ({cid})")

                campaign_ids = [c[0] for c in e2e_campaigns]
                placeholders = ",".join("?" for _ in campaign_ids)

                # Fetch all event IDs linked to these campaigns
                event_ids = []
                if "events" in existing_tables:
                    cursor.execute(
                        f"SELECT id FROM events WHERE campaign_id IN ({placeholders})", campaign_ids
                    )
                    event_ids = [r[0] for r in cursor.fetchall()]

                # Fetch all browser session IDs linked to these events
                session_ids = []
                if event_ids and "browser_sessions" in existing_tables:
                    event_placeholders = ",".join("?" for _ in event_ids)
                    cursor.execute(
                        f"SELECT id FROM browser_sessions WHERE event_id IN ({event_placeholders})",
                        event_ids,
                    )
                    session_ids = [r[0] for r in cursor.fetchall()]

                # Fetch all draft IDs linked to these events
                draft_ids = []
                if event_ids and "generated_content_drafts" in existing_tables:
                    event_placeholders = ",".join("?" for _ in event_ids)
                    cursor.execute(
                        f"SELECT id FROM generated_content_drafts WHERE event_id IN ({event_placeholders})",
                        event_ids,
                    )
                    draft_ids = [r[0] for r in cursor.fetchall()]

                # Fetch all schedule IDs linked to these campaigns
                schedule_ids = []
                if "discovery_schedules" in existing_tables:
                    cursor.execute(
                        f"SELECT id FROM discovery_schedules WHERE campaign_id IN ({placeholders})", campaign_ids
                    )
                    schedule_ids = [r[0] for r in cursor.fetchall()]

                # Fetch all copilot response IDs linked to these campaigns
                copilot_response_ids = []
                if "discovery_copilot_responses" in existing_tables:
                    cursor.execute(
                        f"SELECT id FROM discovery_copilot_responses WHERE campaign_id IN ({placeholders})", campaign_ids
                    )
                    copilot_response_ids = [r[0] for r in cursor.fetchall()]

                # Fetch all audience hypothesis IDs linked to these events
                hypothesis_ids = []
                if event_ids and "audience_hypotheses" in existing_tables:
                    event_placeholders = ",".join("?" for _ in event_ids)
                    cursor.execute(
                        f"SELECT id FROM audience_hypotheses WHERE event_id IN ({event_placeholders})",
                        event_ids,
                    )
                    hypothesis_ids = [r[0] for r in cursor.fetchall()]

                # Collect all lead IDs linked to these campaigns or events
                lead_ids = []
                if "leads" in existing_tables:
                    cursor.execute(
                        f"SELECT id FROM leads WHERE campaign_id IN ({placeholders})", campaign_ids
                    )
                    lead_ids = [r[0] for r in cursor.fetchall()]
                    
                    if event_ids:
                        event_placeholders = ",".join("?" for _ in event_ids)
                        cursor.execute(
                            f"SELECT id FROM leads WHERE event_id IN ({event_placeholders})", event_ids
                        )
                        lead_ids.extend([r[0] for r in cursor.fetchall()])
                    lead_ids = list(set(lead_ids))

                # Collect all other mock leads based on name or URL patterns
                if "leads" in existing_tables:
                    cursor.execute(
                        """
                        SELECT id FROM leads 
                        WHERE display_name LIKE '%E2E%' 
                           OR display_name LIKE 'Org %' 
                           OR public_url LIKE '%example.com%' 
                           OR public_url LIKE '%coindesk.com%' 
                           OR public_url LIKE '%techcrunch.com%'
                        """
                    )
                    matched_lead_ids = [r[0] for r in cursor.fetchall()]
                    lead_ids = list(set(lead_ids + matched_lead_ids))

                # Delete leads and their activities, reminders, history
                if lead_ids:
                    lead_placeholders = ",".join("?" for _ in lead_ids)
                    if "lead_activities" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM lead_activities WHERE lead_id IN ({lead_placeholders})", lead_ids
                        )
                    if "follow_up_reminders" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM follow_up_reminders WHERE lead_id IN ({lead_placeholders})", lead_ids
                        )
                    if "reminder_history" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM reminder_history WHERE lead_id IN ({lead_placeholders})", lead_ids
                        )
                    cursor.execute(f"DELETE FROM leads WHERE id IN ({lead_placeholders})", lead_ids)
                    print(f"  - Cleared {len(lead_ids)} test leads and their activities/reminders")

                # Delete event watchlist details
                if event_ids:
                    event_placeholders = ",".join("?" for _ in event_ids)
                    for tbl in ["event_watchlist_entries", "event_watchlist_history", "event_manual_overrides", "event_change_history", "cutover_events", "calendar_export_audits"]:
                        if tbl in existing_tables:
                            cursor.execute(f"DELETE FROM {tbl} WHERE event_id IN ({event_placeholders})", event_ids)
                            print(f"  - Cleared {tbl} entries")

                # Delete E2E transactional data based on event_ids
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
                        print("  - Cleared E2E audience hypotheses")

                    # Clean engagement_plans
                    if "engagement_plans" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM engagement_plans WHERE event_id IN ({event_placeholders})",
                            event_ids,
                        )
                        print("  - Cleared E2E engagement plans")

                # Delete draft-related review/handoff details
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
                    if "generated_content_drafts" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM generated_content_drafts WHERE id IN ({draft_placeholders})",
                            draft_ids,
                        )
                    print(f"  - Cleared {len(draft_ids)} E2E content drafts and reviews")

                # Clean engagement_tasks
                if "engagement_tasks" in existing_tables and event_ids:
                    event_placeholders = ",".join("?" for _ in event_ids)
                    cursor.execute(
                        f"DELETE FROM engagement_tasks WHERE event_id IN ({event_placeholders})",
                        event_ids,
                    )
                    print("  - Cleared E2E engagement tasks")

                # Clean browser session actions, confirmations, artifacts, and sessions
                if session_ids:
                    session_placeholders = ",".join("?" for _ in session_ids)
                    if "browser_session_actions" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM browser_session_actions WHERE session_id IN ({session_placeholders})",
                            session_ids,
                        )
                    if "browser_action_confirmations" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM browser_action_confirmations WHERE session_id IN ({session_placeholders})",
                            session_ids,
                        )
                    if "browser_debug_artifacts" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM browser_debug_artifacts WHERE session_id IN ({session_placeholders})",
                            session_ids,
                        )
                    if "browser_sessions" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM browser_sessions WHERE id IN ({session_placeholders})",
                            session_ids,
                        )
                    print(f"  - Cleared {len(session_ids)} browser sessions and actions")

                # Clean AI Feedback Events
                if "ai_feedback_events" in existing_tables:
                    feedback_target_ids = []
                    if copilot_response_ids:
                        feedback_target_ids.extend(copilot_response_ids)
                    if hypothesis_ids:
                        feedback_target_ids.extend(hypothesis_ids)
                    if feedback_target_ids:
                        fb_placeholders = ",".join("?" for _ in feedback_target_ids)
                        cursor.execute(
                            f"DELETE FROM ai_feedback_events WHERE target_id IN ({fb_placeholders})",
                            feedback_target_ids
                        )
                        print(f"  - Cleared {cursor.rowcount} AI feedback event records")

                # Clean Discovery Copilot Responses
                if "discovery_copilot_responses" in existing_tables:
                    cursor.execute(
                        f"DELETE FROM discovery_copilot_responses WHERE campaign_id IN ({placeholders})",
                        campaign_ids,
                    )
                    print("  - Cleared discovery copilot responses")

                # Clean Discovery Schedule Dispatches and Schedules
                if schedule_ids:
                    sch_placeholders = ",".join("?" for _ in schedule_ids)
                    if "discovery_schedule_dispatches" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM discovery_schedule_dispatches WHERE schedule_id IN ({sch_placeholders})",
                            schedule_ids,
                        )
                    if "discovery_schedules" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM discovery_schedules WHERE id IN ({sch_placeholders})",
                            schedule_ids,
                        )
                    print("  - Cleared discovery schedules and dispatches")

                # Clean Query Expansion Sets
                if "query_expansion_sets" in existing_tables:
                    cursor.execute(
                        f"DELETE FROM query_expansion_sets WHERE campaign_id IN ({placeholders})",
                        campaign_ids,
                    )
                    print("  - Cleared query expansion sets")

                # Clean Scoring Suggestion Sets
                if "scoring_suggestion_sets" in existing_tables:
                    cursor.execute(
                        f"DELETE FROM scoring_suggestion_sets WHERE campaign_id IN ({placeholders})",
                        campaign_ids,
                    )
                    print("  - Cleared scoring suggestion sets")

                # Clean Campaign Scoring Weight Snapshots
                if "campaign_scoring_weight_snapshots" in existing_tables:
                    cursor.execute(
                        f"DELETE FROM campaign_scoring_weight_snapshots WHERE campaign_id IN ({placeholders})",
                        campaign_ids,
                    )
                    print("  - Cleared campaign scoring weight snapshots")

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

                # Clean campaign_sources
                if "campaign_sources" in existing_tables:
                    cursor.execute(
                        f"DELETE FROM campaign_sources WHERE campaign_id IN ({placeholders})",
                        campaign_ids,
                    )
                    print("  - Cleared campaign sources references")

                # Clean campaigns
                cursor.execute(f"DELETE FROM campaigns WHERE id IN ({placeholders})", campaign_ids)
                print("  - Cleared campaigns")
            else:
                print("No E2E campaigns found.")

        # 2. Clean E2E/Playwright Sources (Connector Registry)
        if "sources" in existing_tables:
            cursor.execute(
                """
                SELECT id, name, domain FROM sources 
                WHERE name LIKE '%E2E%' 
                   OR name LIKE '%Playwright%' 
                   OR name LIKE '%Selenium%'
                   OR domain LIKE '%localhost%'
                   OR (domain LIKE '%example.com%' AND domain NOT IN ('success-mock.example.com'))
                """
            )
            e2e_sources = cursor.fetchall()

            if e2e_sources:
                print(f"Found {len(e2e_sources)} E2E source(s) to clean:")
                for sid, name, domain in e2e_sources:
                    print(f"  - {name} ({domain})")

                source_ids = [s[0] for s in e2e_sources]
                placeholders = ",".join("?" for _ in source_ids)

                # Clean campaign_sources references first
                if "campaign_sources" in existing_tables:
                    cursor.execute(
                        f"DELETE FROM campaign_sources WHERE source_id IN ({placeholders})",
                        source_ids,
                    )
                    print("  - Cleared E2E source references from campaign_sources")

                # Delete from sources
                cursor.execute(f"DELETE FROM sources WHERE id IN ({placeholders})", source_ids)
                print("  - Cleared E2E sources")
            else:
                print("No E2E/Playwright sources found.")

        # 3. Clean any remaining E2E/test browser sessions by name or domain patterns
        if "browser_sessions" in existing_tables:
            cursor.execute("SELECT id, source_name, initial_url FROM browser_sessions")
            all_sessions = cursor.fetchall()
            test_session_ids = []
            for sid, disp_name, target_url in all_sessions:
                disp_name_lower = (disp_name or "").lower()
                target_url_lower = (target_url or "").lower()
                if any(pat in disp_name_lower for pat in test_patterns) or \
                   any(pat in target_url_lower for pat in test_patterns) or \
                   "example.com" in target_url_lower or \
                   "localhost" in target_url_lower:
                    test_session_ids.append(sid)
            
            if test_session_ids:
                ts_placeholders = ",".join("?" for _ in test_session_ids)
                if "browser_session_actions" in existing_tables:
                    cursor.execute(f"DELETE FROM browser_session_actions WHERE session_id IN ({ts_placeholders})", test_session_ids)
                if "browser_action_confirmations" in existing_tables:
                    cursor.execute(f"DELETE FROM browser_action_confirmations WHERE session_id IN ({ts_placeholders})", test_session_ids)
                if "browser_debug_artifacts" in existing_tables:
                    cursor.execute(f"DELETE FROM browser_debug_artifacts WHERE session_id IN ({ts_placeholders})", test_session_ids)
                cursor.execute(f"DELETE FROM browser_sessions WHERE id IN ({ts_placeholders})", test_session_ids)
                print(f"  - Cleared {len(test_session_ids)} remaining test browser sessions")

        # 4. Clean browser profiles matching test patterns
        if "browser_profiles" in existing_tables:
            cursor.execute("SELECT id, name FROM browser_profiles")
            all_profiles = cursor.fetchall()
            test_profile_ids = []
            for pid, name in all_profiles:
                name_lower = (name or "").lower()
                if any(pat in name_lower for pat in test_patterns) or \
                   "profile" in name_lower:
                    test_profile_ids.append(pid)
            
            if test_profile_ids:
                tp_placeholders = ",".join("?" for _ in test_profile_ids)
                if "browser_sessions" in existing_tables:
                    cursor.execute(f"DELETE FROM browser_sessions WHERE browser_profile_id IN ({tp_placeholders})", test_profile_ids)
                cursor.execute(f"DELETE FROM browser_profiles WHERE id IN ({tp_placeholders})", test_profile_ids)
                print(f"  - Cleared {len(test_profile_ids)} remaining test browser profiles")

        # 5. Clean up all orphaned records (referential integrity checks)
        print("Cleaning up orphaned records from all tables...")
        orphaned_cleanups = [
            ("lead_activities", "lead_id", "leads", "id"),
            ("follow_up_reminders", "lead_id", "leads", "id"),
            ("reminder_history", "lead_id", "leads", "id"),
            ("event_source_observations", "event_id", "events", "id"),
            ("audience_hypotheses", "event_id", "events", "id"),
            ("engagement_plans", "event_id", "events", "id"),
            ("engagement_tasks", "event_id", "events", "id"),
            ("generated_content_drafts", "event_id", "events", "id"),
            ("content_review_decisions", "draft_id", "generated_content_drafts", "id"),
            ("content_handoff_records", "draft_id", "generated_content_drafts", "id"),
            ("browser_sessions", "event_id", "events", "id"),
            ("browser_sessions", "source_id", "sources", "id"),
            ("browser_session_actions", "session_id", "browser_sessions", "id"),
            ("browser_action_confirmations", "session_id", "browser_sessions", "id"),
            ("browser_debug_artifacts", "session_id", "browser_sessions", "id"),
            ("event_watchlist_entries", "event_id", "events", "id"),
            ("event_watchlist_history", "event_id", "events", "id"),
            ("event_manual_overrides", "event_id", "events", "id"),
            ("event_change_history", "event_id", "events", "id"),
            ("cutover_events", "event_id", "events", "id"),
            ("calendar_export_audits", "event_id", "events", "id"),
            ("event_scores", "campaign_id", "campaigns", "id"),
            ("events", "campaign_id", "campaigns", "id"),
            ("discovery_jobs", "campaign_id", "campaigns", "id"),
            ("campaign_sources", "campaign_id", "campaigns", "id"),
            ("campaign_sources", "source_id", "sources", "id"),
            ("discovery_schedule_dispatches", "schedule_id", "discovery_schedules", "id"),
            ("discovery_schedules", "campaign_id", "campaigns", "id"),
            ("query_expansion_sets", "campaign_id", "campaigns", "id"),
            ("discovery_copilot_responses", "campaign_id", "campaigns", "id"),
            ("scoring_suggestion_sets", "campaign_id", "campaigns", "id"),
            ("campaign_scoring_weight_snapshots", "campaign_id", "campaigns", "id"),
        ]

        for tbl, col, ref_tbl, ref_col in orphaned_cleanups:
            if tbl in existing_tables and ref_tbl in existing_tables:
                q = f"DELETE FROM {tbl} WHERE {col} IS NOT NULL AND {col} NOT IN (SELECT {ref_col} FROM {ref_tbl})"
                cursor.execute(q)
                if cursor.rowcount > 0:
                    print(f"  - Cleared {cursor.rowcount} orphaned row(s) from {tbl}")

        # Clean AI feedback events whose targets no longer exist
        if "ai_feedback_events" in existing_tables:
            cursor.execute(
                """
                DELETE FROM ai_feedback_events 
                WHERE target_id NOT IN (SELECT id FROM discovery_copilot_responses)
                  AND target_id NOT IN (SELECT id FROM audience_hypotheses)
                """
            )
            if cursor.rowcount > 0:
                print(f"  - Cleared {cursor.rowcount} orphaned AI feedback event record(s)")

        # 6. Ensure the default clean sources exist
        if "sources" in existing_tables:
            for s in DEFAULT_SOURCES:
                cursor.execute("SELECT name FROM sources WHERE name = ?", (s["name"],))
                exists = cursor.fetchone()

                if not exists:
                    src_payload = {
                        "id": str(uuid4()),
                        "organization_id": DEV_ORGANIZATION_ID,
                        "name": s["name"],
                        "domain": s["domain"],
                        "connector_type": s["connector_type"],
                        "automation_engine": "none",
                        "authentication_mode": "none",
                        "enabled": 1,
                        "approved": 1,
                        "approved_by": "admin",
                        "approved_at": datetime.now(UTC).isoformat(),
                        "policy_json": json.dumps(s["policy"]),
                        "rate_limit_json": "{}",
                        "secret_ciphertext": None,
                    }
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
                        src_payload,
                    )
                    print(f"  + Restored default source '{s['name']}'")

        # 7. Make sure developer organization exists
        if "organizations" in existing_tables:
            cursor.execute(
                "INSERT OR IGNORE INTO organizations (id, name) VALUES ('00000000-0000-4000-8000-000000000001', 'LiveLead Dev Organization')"
            )

        # Collect active browser profile and session IDs before committing
        remaining_profile_ids = set()
        if "browser_profiles" in existing_tables:
            cursor.execute("SELECT id FROM browser_profiles")
            remaining_profile_ids = {r[0] for r in cursor.fetchall()}

        remaining_session_ids = set()
        if "browser_sessions" in existing_tables:
            cursor.execute("SELECT id FROM browser_sessions")
            remaining_session_ids = {r[0] for r in cursor.fetchall()}

        conn.commit()

        # Vacuum the database
        cursor.execute("VACUUM")
        print("Database vacuumed successfully.")

        # Disk Cleanup: Clean orphaned browser profile and session artifact directories
        # 1. Clean browser profile directories
        profile_root = Path(settings.browser_profile_root)
        if profile_root.exists():
            cleaned_profiles_count = 0
            for path in profile_root.iterdir():
                if path.is_dir():
                    # Format: <org_id>_<profile_id>
                    parts = path.name.split('_')
                    profile_id = parts[-1] if len(parts) > 1 else path.name
                    if profile_id not in remaining_profile_ids:
                        try:
                            shutil.rmtree(path)
                            cleaned_profiles_count += 1
                        except Exception as e:
                            print(f"Failed to delete profile directory {path}: {e}")
            if cleaned_profiles_count > 0:
                print(f"Cleared {cleaned_profiles_count} orphaned browser profile directories on disk.")
                
        # 2. Clean browser session artifact directories
        artifact_root = Path(settings.artifact_root) / "browser_artifacts"
        if artifact_root.exists():
            cleaned_sessions_count = 0
            for org_dir in artifact_root.iterdir():
                if org_dir.is_dir():
                    for session_dir in org_dir.iterdir():
                        if session_dir.is_dir():
                            session_id = session_dir.name
                            if session_id not in remaining_session_ids:
                                try:
                                    shutil.rmtree(session_dir)
                                    cleaned_sessions_count += 1
                                except Exception as e:
                                    print(f"Failed to delete session artifact directory {session_dir}: {e}")
            if cleaned_sessions_count > 0:
                print(f"Cleared {cleaned_sessions_count} orphaned browser session artifact directories on disk.")

    except Exception as e:
        conn.rollback()
        print(f"Error occurred during E2E database cleanup: {e}")
        return 1
    finally:
        conn.close()

    print("Database E2E cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
