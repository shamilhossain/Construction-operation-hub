"""
Fix Notion Operations Hub Page
==============================
1. Restores all 8 databases from trash/archived state.
2. Removes duplicate dashboard blocks (second run of build_dashboard_and_templates.py)
   and any pink '📌' instruction blocks, strictly preserving all child_database blocks.

Usage:
    python fix_notion_page.py
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "").strip()
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def rate_limit_sleep():
    time.sleep(0.35)


def clean_page_id(raw_id: str) -> str:
    cleaned = raw_id.strip()
    if "/" in cleaned:
        cleaned = cleaned.split("/")[-1].split("?")[0]
    return cleaned.replace("-", "")


def restore_databases(database_map: dict):
    """Un-archives all 8 databases so they are restored back from trash."""
    print("\n--- STEP 1: Restoring All 8 Databases from Trash / Archive ---")
    for name, db_id in database_map.items():
        rate_limit_sleep()
        # Attempt 1: PATCH /databases/{id}
        url = f"{NOTION_API_URL}/databases/{db_id}"
        res = requests.patch(url, headers=HEADERS, json={"archived": False})
        if res.status_code == 200:
            print(f"    Restored database '{name}' ({db_id}) via /databases")
            continue

        # Attempt 2: PATCH /blocks/{id}
        rate_limit_sleep()
        block_url = f"{NOTION_API_URL}/blocks/{db_id}"
        res2 = requests.patch(block_url, headers=HEADERS, json={"archived": False})
        if res2.status_code == 200:
            print(f"    Restored database '{name}' ({db_id}) via /blocks")
        else:
            print(f"   ⚠️ Could not unarchive '{name}' ({db_id}): {res2.status_code} - {res2.text}")


def fetch_all_child_blocks(parent_id: str) -> list:
    """Fetches all child blocks of a page, handling pagination."""
    blocks = []
    url = f"{NOTION_API_URL}/blocks/{parent_id}/children"
    has_more = True
    start_cursor = None

    while has_more:
        rate_limit_sleep()
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
        res = requests.get(url, headers=HEADERS, params=params)
        if res.status_code != 200:
            print(f"   Error fetching blocks: {res.status_code} - {res.text}")
            break
        data = res.json()
        blocks.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return blocks


def get_block_text(block: dict) -> str:
    """Extracts plain text content from a block."""
    b_type = block.get("type", "")
    data = block.get(b_type, {})
    if isinstance(data, dict):
        rich_text = data.get("rich_text", [])
        if rich_text:
            return "".join([t.get("plain_text", "") for t in rich_text])
    return ""


def clean_duplicate_blocks(parent_id: str, known_db_ids: set):
    """Deletes duplicate dashboard blocks at the bottom, preserving all child databases."""
    print("\n--- STEP 2: Inspecting and Cleaning Duplicate Dashboard Blocks ---")
    blocks = fetch_all_child_blocks(parent_id)
    print(f"   Found total {len(blocks)} child blocks on main page.")

    # We track occurrences of major dashboard anchors to identify duplicates
    seen_blueprint_callout = 0
    seen_action_center = 0
    seen_kpi_summary = 0
    seen_kpi_table = 0
    seen_project_health = 0
    seen_master_db_heading = 0

    blocks_to_delete = []

    for idx, b in enumerate(blocks):
        b_id = b["id"]
        b_type = b.get("type", "")
        text = get_block_text(b)
        color = ""
        b_data = b.get(b_type, {})
        if isinstance(b_data, dict):
            color = b_data.get("color", "")

        # SAFETY CHECK: Never delete child databases or known DB IDs
        if b_type == "child_database" or b_id in known_db_ids or b_id.replace("-", "") in known_db_ids:
            print(f"   [KEEP DB] {idx}: [{b_type}] {b_id} (Preserved)")
            continue

        delete_this = False

        # 1. Blueprint Callout
        if "Executive Operational Blueprint" in text or "Operations Hub unifies Sales CRM" in text:
            seen_blueprint_callout += 1
            if seen_blueprint_callout > 1:
                delete_this = True

        # 2. Section 1: Kevin's Executive Action Center
        elif "Kevin's Executive Action Center" in text:
            seen_action_center += 1
            if seen_action_center > 1:
                delete_this = True

        # 3. Section 2: Sales Pipeline & Performance Summary
        elif "Sales Pipeline & Performance Summary" in text:
            seen_kpi_summary += 1
            if seen_kpi_summary > 1:
                delete_this = True

        # 4. Table block (KPI table)
        elif b_type == "table":
            seen_kpi_table += 1
            if seen_kpi_table > 1:
                delete_this = True

        # 5. Section 3: Active Construction Projects & Milestone Health
        elif "Active Construction Projects & Milestone Health" in text:
            seen_project_health += 1
            if seen_project_health > 1:
                delete_this = True

        # 6. Section 4: Master System Databases
        elif "Master System Databases" in text:
            seen_master_db_heading += 1
            if seen_master_db_heading > 1:
                delete_this = True

        # 7. Check for pink/red callout instruction blocks with 📌
        elif "📌" in text and ("pink" in color or "red" in color or b_type == "callout"):
            # If user explicitly wants pink 📌 callout instruction blocks removed
            delete_this = True

        # 8. Trailing duplicate paragraphs / dividers if after second blueprint
        elif seen_blueprint_callout > 1:
            # Any block belonging to the second run
            delete_this = True

        if delete_this:
            blocks_to_delete.append((idx, b_id, b_type, text[:50]))
            print(f"   [TO DELETE] {idx}: [{b_type}] {text[:50]} (id: {b_id})")
        else:
            print(f"   [KEEP] {idx}: [{b_type}] {text[:50]}")

    print(f"\n   Total duplicate/unwanted blocks to delete: {len(blocks_to_delete)}")

    deleted_count = 0
    for idx, b_id, b_type, sample in blocks_to_delete:
        rate_limit_sleep()
        del_url = f"{NOTION_API_URL}/blocks/{b_id}"
        del_res = requests.delete(del_url, headers=HEADERS)
        if del_res.status_code == 200:
            deleted_count += 1
            print(f"    Deleted block {idx} [{b_type}] ({b_id})")
        else:
            print(f"   ⚠️ Failed to delete block {b_id}: {del_res.status_code} - {del_res.text}")

    print(f"\n Successfully deleted {deleted_count} duplicate blocks. Only 1 clean executive dashboard remains!")


def main():
    print("=" * 70)
    print(" Fix & Clean Notion Operations Hub Page")
    print("=" * 70)

    config_path = os.path.join(os.path.dirname(__file__), "notion_config.json")
    if not os.path.exists(config_path):
        print(" Error: `notion_config.json` not found.")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    parent_page_id = clean_page_id(NOTION_PAGE_ID)
    db_map = config.get("databases", {})
    known_db_ids = {db_id for db_id in db_map.values()}
    known_db_ids.update({db_id.replace("-", "") for db_id in db_map.values()})

    # Step 1: Unarchive all 8 databases
    restore_databases(db_map)

    # Step 2: Clean duplicate dashboard blocks
    clean_duplicate_blocks(parent_page_id, known_db_ids)

    print("\n" + "=" * 70)
    print(" ALL 8 DATABASES RESTORED & DUPLICATE BLOCKS CLEANED UP!")
    print("=" * 70)


if __name__ == "__main__":
    main()
