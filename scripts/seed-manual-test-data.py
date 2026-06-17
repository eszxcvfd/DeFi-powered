#!/usr/bin/env python3
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

# Add src to sys.path so we can import the settings
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from livelead.runtime.settings import parse_settings

DEV_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"


def main():
    settings = parse_settings()
    db_path = Path(settings.sqlite_path)

    if not db_path.exists():
        print(f"Database file does not exist: {db_path}")
        return 1

    print(f"Seeding manual test data in database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    existing_tables = {
        r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    try:
        # 1. Ensure Developer Organization exists
        if "organizations" in existing_tables:
            cursor.execute(
                "INSERT OR IGNORE INTO organizations (id, name) VALUES (?, ?)",
                (DEV_ORGANIZATION_ID, "LiveLead Dev Organization")
            )

        # 2. Seed default sources if they don't exist
        source_id = "41214f59-6219-4f54-bf94-76d2406475c7"  # TechCrunch Web3 Events
        if "sources" in existing_tables:
            cursor.execute("SELECT id FROM sources WHERE id = ?", (source_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO sources (
                        id, organization_id, name, domain, connector_type, 
                        automation_engine, authentication_mode, enabled, approved, 
                        approved_by, approved_at, policy_json, rate_limit_json, 
                        secret_ciphertext, created_at, updated_at
                    ) VALUES (
                        ?, ?, 'TechCrunch Web3 Events', 'techcrunch.com', 'rss', 
                        'none', 'none', 1, 1, 'admin', ?, '{"access_mode": "feed", "quota_per_day": 500}', '{}',
                        None, datetime('now'), datetime('now')
                    )
                    """,
                    (source_id, DEV_ORGANIZATION_ID, datetime.now(UTC).isoformat())
                )

        # 3. Recreate the 3 Manual Test Campaigns
        campaigns_to_seed = [
            {
                "id": "083a85a1-4f60-4cc5-8dba-449d6c90fcaf",
                "name": "Manual Test Campaign 2026",
                "target_industry": "DeFi",
                "product_or_service_focus": "Lending Protocols",
                "scoring_weights_json": '{"webinar": 0.8, "hackathon": 0.5}',
                "status": "active"
            },
            {
                "id": "6537f112-19fd-4b01-8b80-ab3aceb162fd",
                "name": "Manual Test Campaign RWA",
                "target_industry": "Fintech / RWA",
                "product_or_service_focus": "Tokenized Assets",
                "scoring_weights_json": '{"compliance": 0.9, "regulation": 0.7}',
                "status": "active"
            },
            {
                "id": "4b2b0df7-c60e-451d-9571-1f21bb6d8ffd",
                "name": "Manual AI Feedback Test",
                "target_industry": "Payments",
                "product_or_service_focus": "Cross-border Payments",
                "scoring_weights_json": '{"fintech": 0.6}',
                "status": "active"
            }
        ]

        if "campaigns" in existing_tables:
            for camp in campaigns_to_seed:
                cursor.execute("SELECT id FROM campaigns WHERE id = ?", (camp["id"],))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO campaigns (
                            id, organization_id, name, description, target_industry, 
                            product_or_service_focus, scoring_weights_json, status, created_at, updated_at
                        ) VALUES (?, ?, ?, 'Manual testing campaign', ?, ?, ?, ?, datetime('now'), datetime('now'))
                        """,
                        (camp["id"], DEV_ORGANIZATION_ID, camp["name"], camp["target_industry"], camp["product_or_service_focus"], camp["scoring_weights_json"], camp["status"])
                    )
                    print(f"  + Recreated campaign: {camp['name']} ({camp['id']})")
                    
                    # Associate with TechCrunch Web3 Events source
                    if "campaign_sources" in existing_tables:
                        cursor.execute(
                            "INSERT OR IGNORE INTO campaign_sources (campaign_id, source_id) VALUES (?, ?)",
                            (camp["id"], source_id)
                        )

        # 4. Recreate mock events for the campaigns
        events_to_seed = [
            {
                "id": "e6de06ba-a10c-4bc3-a808-bd8f75b6ee01",
                "campaign_id": "083a85a1-4f60-4cc5-8dba-449d6c90fcaf",
                "canonical_title": "Ethereum Lending Hackathon 2026",
                "description": "Annual DeFi lending event focusing on smart contract security.",
                "source_url": "https://techcrunch.com/events/eth-lending-2026"
            },
            {
                "id": "e6de06ba-a10c-4bc3-a808-bd8f75b6ee02",
                "campaign_id": "6537f112-19fd-4b01-8b80-ab3aceb162fd",
                "canonical_title": "RWA Tokenization Workshop",
                "description": "Developer API workshop regarding RWA asset integration.",
                "source_url": "https://defillama-com/events/rwa-workshop"
            },
            {
                "id": "e6de06ba-a10c-4bc3-a808-bd8f75b6ee03",
                "campaign_id": "4b2b0df7-c60e-451d-9571-1f21bb6d8ffd",
                "canonical_title": "Fintech Cross-Border Webinar",
                "description": "Discussion on cross-border payments regulations.",
                "source_url": "https://techcrunch.com/events/fintech-payments"
            }
        ]

        if "events" in existing_tables:
            for ev in events_to_seed:
                cursor.execute("SELECT id FROM events WHERE id = ?", (ev["id"],))
                if not cursor.fetchone():
                    now_str = datetime.now(UTC).isoformat()
                    cursor.execute(
                        """
                        INSERT INTO events (
                            id, organization_id, campaign_id, canonical_title, source_url, observed_at,
                            description, starts_at, metadata_json, created_at, discovery_job_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', datetime('now'), 'manual-job-id')
                        """,
                        (ev["id"], DEV_ORGANIZATION_ID, ev["campaign_id"], ev["canonical_title"], ev["source_url"], now_str, ev["description"], now_str)
                    )
                    print(f"  + Added event: {ev['canonical_title']}")

                    # Add event_source_observation
                    if "event_source_observations" in existing_tables:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO event_source_observations (
                                id, event_id, source_id, source_url, observed_at, raw_title, discovery_job_id
                            ) VALUES (?, ?, ?, ?, ?, ?, 'manual-job-id')
                            """,
                            (str(uuid4()), ev["id"], source_id, ev["source_url"], now_str, ev["canonical_title"])
                        )

                    # Add event_scores
                    if "event_scores" in existing_tables:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO event_scores (
                                id, event_id, campaign_id, total_score, priority_level, scoring_version, calculated_at
                            ) VALUES (?, ?, ?, 85.0, 'high', 'v1', datetime('now'))
                            """,
                            (str(uuid4()), ev["id"], ev["campaign_id"])
                        )

        # 5. Recreate mock lead for RWA
        if "leads" in existing_tables:
            lead_id = "0c31fb31-d886-49b1-9aec-b7515547e618"
            cursor.execute("SELECT id FROM leads WHERE id = ?", (lead_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO leads (
                        id, organization_id, campaign_id, display_name, company, title, public_url,
                        discovery_source, event_id, interests, pain_points, owner, stage, created_at, updated_at
                    ) VALUES (
                        ?, ?, ?, 'Developer API Workshop — defillama-com #5', 'DeFiLlama', 'Organizer',
                        'https://defillama-com/events/rwa-workshop', 'TechCrunch Web3 Events', ?,
                        'RWA, APIs', 'Integration', 'analyst', 'newly_discovered', datetime('now'), datetime('now')
                    )
                    """,
                    (lead_id, DEV_ORGANIZATION_ID, "6537f112-19fd-4b01-8b80-ab3aceb162fd", "e6de06ba-a10c-4bc3-a808-bd8f75b6ee02")
                )
                print(f"  + Recreated lead: Developer API Workshop — defillama-com #5")

        # 6. Recreate discovery copilot response for AI Feedback test
        if "discovery_copilot_responses" in existing_tables:
            copilot_res_id = "bfa14641-c5bd-44b7-a002-865e0abf07b7"
            cursor.execute("SELECT id FROM discovery_copilot_responses WHERE id = ?", (copilot_res_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO discovery_copilot_responses (
                        id, organization_id, campaign_id, question, response_json, provider_id, model_id, confidence, created_at
                    ) VALUES (
                        ?, ?, ?, 'What keywords should we use?', '{"keywords": ["defi", "lending"]}', 'gemini', 'gemini-2.0-flash', 0.9, datetime('now')
                    )
                    """,
                    (copilot_res_id, DEV_ORGANIZATION_ID, "4b2b0df7-c60e-451d-9571-1f21bb6d8ffd")
                )
                print(f"  + Recreated copilot response: {copilot_res_id}")

        # 7. Recreate AI feedback events
        if "ai_feedback_events" in existing_tables:
            fb_events = [
                {
                    "id": "651de6ba-d970-4bcf-992f-2691dfd6f2ac",
                    "target_type": "discovery_copilot_response",
                    "target_id": "bfa14641-c5bd-44b7-a002-865e0abf07b7",
                    "actor_key": "03812af2-8de5-480b-a89e-9992277dfa7b",
                    "state": "helpful"
                }
            ]
            for fb in fb_events:
                cursor.execute("SELECT id FROM ai_feedback_events WHERE id = ?", (fb["id"],))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO ai_feedback_events (
                            id, organization_id, target_type, target_id, actor_key, state, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (fb["id"], DEV_ORGANIZATION_ID, fb["target_type"], fb["target_id"], fb["actor_key"], fb["state"])
                    )
                    print(f"  + Recreated AI feedback event: {fb['id']}")

        conn.commit()
        print("Manual test data seeded successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error seeding manual test data: {e}")
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
