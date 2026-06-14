#!/usr/bin/env python3
import json
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, UTC

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
        }
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
        }
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
        }
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
        }
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
        }
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
        }
    }
]

def main():
    settings = parse_settings()
    db_path = Path(settings.sqlite_path)
    
    if not db_path.exists():
        print(f"Database file does not exist: {db_path}")
        return 0
        
    print(f"Cleaning E2E garbage from database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    existing_tables = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    
    try:
        # 1. Clean E2E Campaigns and their dependencies
        if "campaigns" in existing_tables:
            cursor.execute("SELECT id, name FROM campaigns WHERE name LIKE '%E2E%' OR name LIKE '%e2e%'")
            e2e_campaigns = cursor.fetchall()
            
            if e2e_campaigns:
                print(f"Found {len(e2e_campaigns)} E2E campaign(s) to clean:")
                for cid, name in e2e_campaigns:
                    print(f"  - {name} ({cid})")
                    
                campaign_ids = [c[0] for c in e2e_campaigns]
                placeholders = ",".join("?" for _ in campaign_ids)
                
                # Fetch all event IDs linked to these campaigns
                event_ids = []
                if "events" in existing_tables:
                    cursor.execute(f"SELECT id FROM events WHERE campaign_id IN ({placeholders})", campaign_ids)
                    event_ids = [r[0] for r in cursor.fetchall()]

                # Clean E2E transactional data based on event_ids
                if event_ids:
                    event_placeholders = ",".join("?" for _ in event_ids)
                    
                    # Clean event_source_observations
                    if "event_source_observations" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM event_source_observations WHERE event_id IN ({event_placeholders})", 
                            event_ids
                        )
                        print(f"  - Cleared event observations for {len(event_ids)} event(s)")
                        
                    # Clean audience_hypotheses
                    if "audience_hypotheses" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM audience_hypotheses WHERE event_id IN ({event_placeholders})", 
                            event_ids
                        )
                        print("  - Cleared E2E audience hypotheses")

                    # Clean engagement_plans
                    if "engagement_plans" in existing_tables:
                        cursor.execute(
                            f"DELETE FROM engagement_plans WHERE event_id IN ({event_placeholders})", 
                            event_ids
                        )
                        print("  - Cleared E2E engagement plans")

                    # Clean generated content reviews and handoff records
                    if "generated_content_drafts" in existing_tables:
                        # Find draft IDs
                        cursor.execute(
                            f"SELECT id FROM generated_content_drafts WHERE event_id IN ({event_placeholders})", 
                            event_ids
                        )
                        draft_ids = [r[0] for r in cursor.fetchall()]
                        if draft_ids:
                            draft_placeholders = ",".join("?" for _ in draft_ids)
                            if "content_review_decisions" in existing_tables:
                                cursor.execute(
                                    f"DELETE FROM content_review_decisions WHERE draft_id IN ({draft_placeholders})", 
                                    draft_ids
                                )
                            if "content_handoff_records" in existing_tables:
                                cursor.execute(
                                    f"DELETE FROM content_handoff_records WHERE draft_id IN ({draft_placeholders})", 
                                    draft_ids
                                )
                            cursor.execute(
                                f"DELETE FROM generated_content_drafts WHERE event_id IN ({event_placeholders})", 
                                event_ids
                            )
                            print(f"  - Cleared {len(draft_ids)} E2E content drafts and reviews")

                # Clean engagement_tasks
                if "engagement_tasks" in existing_tables and event_ids:
                    event_placeholders = ",".join("?" for _ in event_ids)
                    cursor.execute(f"DELETE FROM engagement_tasks WHERE event_id IN ({event_placeholders})", event_ids)
                    print("  - Cleared E2E engagement tasks")

                # Clean event_scores
                if "event_scores" in existing_tables:
                    cursor.execute(f"DELETE FROM event_scores WHERE campaign_id IN ({placeholders})", campaign_ids)
                    print("  - Cleared event scores")
                    
                # Clean events
                if "events" in existing_tables:
                    cursor.execute(f"DELETE FROM events WHERE campaign_id IN ({placeholders})", campaign_ids)
                    print("  - Cleared events")
                    
                # Clean discovery_jobs
                if "discovery_jobs" in existing_tables:
                    cursor.execute(f"DELETE FROM discovery_jobs WHERE campaign_id IN ({placeholders})", campaign_ids)
                    print("  - Cleared discovery jobs")
                    
                # Clean campaign_sources
                if "campaign_sources" in existing_tables:
                    cursor.execute(f"DELETE FROM campaign_sources WHERE campaign_id IN ({placeholders})", campaign_ids)
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
                   OR domain LIKE '%example.com%' 
                   OR domain LIKE '%localhost%'
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
                    cursor.execute(f"DELETE FROM campaign_sources WHERE source_id IN ({placeholders})", source_ids)
                    print("  - Cleared E2E source references from campaign_sources")
                    
                # Delete from sources
                cursor.execute(f"DELETE FROM sources WHERE id IN ({placeholders})", source_ids)
                print("  - Cleared E2E sources")
            else:
                print("No E2E/Playwright sources found.")

        # 3. Clean E2E/Mock Leads and their reminders/activities
        if "leads" in existing_tables:
            cursor.execute(
                """
                SELECT id, display_name FROM leads 
                WHERE display_name LIKE '%E2E%' 
                   OR display_name LIKE 'Org %' 
                   OR public_url LIKE '%example.com%' 
                   OR public_url LIKE '%coindesk.com%' 
                   OR public_url LIKE '%techcrunch.com%'
                """
            )
            e2e_leads = cursor.fetchall()
            
            if e2e_leads:
                lead_ids = [r[0] for r in e2e_leads]
                lead_placeholders = ",".join("?" for _ in lead_ids)
                
                if "lead_activities" in existing_tables:
                    cursor.execute(f"DELETE FROM lead_activities WHERE lead_id IN ({lead_placeholders})", lead_ids)
                if "follow_up_reminders" in existing_tables:
                    cursor.execute(f"DELETE FROM follow_up_reminders WHERE lead_id IN ({lead_placeholders})", lead_ids)
                if "reminder_history" in existing_tables:
                    cursor.execute(f"DELETE FROM reminder_history WHERE lead_id IN ({lead_placeholders})", lead_ids)
                    
                cursor.execute(f"DELETE FROM leads WHERE id IN ({lead_placeholders})", lead_ids)
                print(f"  - Cleared {len(lead_ids)} E2E/test leads and their activities/reminders")
                
        # 4. Ensure the default clean sources exist
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
                        "secret_ciphertext": None
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
                        src_payload
                    )
                    print(f"  + Restored default source '{s['name']}'")
                
        # 5. Make sure developer organization exists
        if "organizations" in existing_tables:
            cursor.execute("INSERT OR IGNORE INTO organizations (id, name) VALUES ('00000000-0000-4000-8000-000000000001', 'LiveLead Dev Organization')")
            
        conn.commit()
        
        # Vacuum the database
        cursor.execute("VACUUM")
        print("Database vacuumed successfully.")
        
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
