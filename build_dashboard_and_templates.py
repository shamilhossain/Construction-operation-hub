"""
Build Executive Dashboard & Project Workspace Templates in Notion
=================================================================
This script enhances the Notion workspace for Kevin's Residential Construction:
1. Builds a clean executive dashboard layout on the main hub page (NOTION_PAGE_ID)
   with live pipeline KPIs computed from the Sales Opportunities (CRM) database.
2. Injects a 4-phase project checklist template inside every project record in
   the Construction Projects database.

Usage:
    python build_dashboard_and_templates.py
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


def block_callout(text: str, emoji: str = "💡", color: str = "blue_background"):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color,
        },
    }


def block_heading_2(text: str, color: str = "default"):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": color,
        },
    }


def block_heading_3(text: str, color: str = "default"):
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": color,
        },
    }


def block_paragraph(text: str, color: str = "default"):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": color,
        },
    }


def block_divider():
    return {"object": "block", "type": "divider", "divider": {}}


def block_to_do(text: str, checked: bool = False):
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "checked": checked,
        },
    }


def block_table(rows: list):
    """Creates a Notion table block from a list of rows (each row is a list of strings)."""
    table_rows = []
    for r_idx, row in enumerate(rows):
        cells = []
        for cell_text in row:
            cells.append([
                {
                    "type": "text",
                    "text": {"content": cell_text},
                    "annotations": {"bold": (r_idx == 0)},
                }
            ])
        table_rows.append({"type": "table_row", "table_row": {"cells": cells}})

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(rows[0]),
            "has_column_header": True,
            "has_row_header": False,
            "children": table_rows,
        },
    }


def append_children_blocks(block_id: str, children: list) -> bool:
    """Appends child blocks to a page or block container in Notion."""
    url = f"{NOTION_API_URL}/blocks/{block_id}/children"
    payload = {"children": children}
    rate_limit_sleep()
    res = requests.patch(url, headers=HEADERS, json=payload)
    if res.status_code != 200:
        print(f"   Error appending blocks to {block_id}: {res.status_code} - {res.text}")
        return False
    return True


def fetch_database_records(database_id: str) -> list:
    """Fetches all records from a given database ID."""
    url = f"{NOTION_API_URL}/databases/{database_id}/query"
    rate_limit_sleep()
    res = requests.post(url, headers=HEADERS, json={})
    if res.status_code == 200:
        return res.json().get("results", [])
    print(f"   Error fetching database {database_id}: {res.status_code}")
    return []


def calculate_pipeline_kpis(opportunities_db_id: str):
    """Computes live KPIs directly from the Sales Opportunities database."""
    print("   Querying Sales Opportunities (CRM) database for live metrics...")
    deals = fetch_database_records(opportunities_db_id)

    total_pipeline_val = 0.0
    total_design_fees = 0.0
    active_deals_count = 0
    pending_kevin_review = 0
    needing_attention = 0

    for deal in deals:
        props = deal.get("properties", {})
        
        # Stage
        stage_prop = props.get("Stage", {}).get("select") or {}
        stage_name = stage_prop.get("name", "")
        if stage_name != "8. Closed Lost":
            active_deals_count += 1

        # Construction Value
        c_val = props.get("Est. Construction Value ($)", {}).get("number")
        if c_val:
            total_pipeline_val += float(c_val)

        # Design Fee
        d_fee = props.get("Design Fee ($)", {}).get("number")
        if d_fee:
            total_design_fees += float(d_fee)

        # Needs Kevin Review
        needs_review = props.get("Needs Kevin Review", {}).get("checkbox", False)
        if needs_review or "5. Needs Kevin's Review" in stage_name:
            pending_kevin_review += 1

        # Attention Flag
        att_prop = props.get("Attention Flag", {}).get("select") or {}
        att_name = att_prop.get("name", "")
        if "Needs Attention" in att_name or "Waiting on Kevin" in att_name:
            needing_attention += 1

    return {
        "total_pipeline_val": total_pipeline_val,
        "total_design_fees": total_design_fees,
        "active_deals_count": active_deals_count,
        "pending_kevin_review": pending_kevin_review,
        "needing_attention": needing_attention,
    }


def main():
    print("=" * 70)
    print(" Enhancing Notion Hub: Executive Dashboard & Project Templates")
    print("=" * 70)

    # 1. Load config
    config_path = os.path.join(os.path.dirname(__file__), "notion_config.json")
    if not os.path.exists(config_path):
        print(" Error: `notion_config.json` not found. Please run setup_notion.py first.")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    parent_page_id = clean_page_id(NOTION_PAGE_ID)
    opportunities_db_id = config["databases"]["opportunities"]
    projects_db_id = config["databases"]["projects"]

    # 2. Compute live KPIs
    kpis = calculate_pipeline_kpis(opportunities_db_id)
    print(f"      Total Pipeline Value: ${kpis['total_pipeline_val']:,.2f}")
    print(f"      Total Design Fees:    ${kpis['total_design_fees']:,.2f}")
    print(f"      Active Opportunities: {kpis['active_deals_count']}")
    print(f"      Pending Kevin Review: {kpis['pending_kevin_review']}")
    print(f"      Needing Attention:    {kpis['needing_attention']}\n")

    # 3. Construct Executive Dashboard Blocks
    print("--- STEP 1: Building Executive Dashboard on Main Hub Page ---")
    dashboard_blocks = [
        block_callout(
            "Executive Operational Blueprint: This centralized Operations Hub unifies Sales CRM, "
            "Pre-Construction estimating, and Field execution. Field crews use their dedicated tool for day-to-day work, "
            "while high-level milestones, client decisions, and automated invoice costs sync directly here.",
            emoji="🏗️",
            color="blue_background",
        ),
        block_divider(),
        # Section 1
        block_heading_2("🚨 Kevin's Executive Action Center (Reviews & Stale Deals)", color="red"),
        block_paragraph(
            "📌 Morning Briefing: Create a Linked View of 'Sales Opportunities (CRM)' here with Filter: "
            "[Needs Kevin Review is Checked] OR [Attention Flag = 'Waiting on Kevin's Approval' / 'Overdue Follow-up - Needs Attention']. "
            "This gives Kevin instant visibility into bottlenecked deals without asking the team."
        ),
        block_divider(),
        # Section 2
        block_heading_2("📊 Sales Pipeline & Performance Summary", color="blue"),
        block_paragraph(
            "Live snapshot calculated across active CRM opportunities:"
        ),
        block_table([
            ["Executive Sales Metric", "Value", "Strategic Context"],
            [
                "Total Active Pipeline Value",
                f"${kpis['total_pipeline_val']:,.0f}",
                "Aggregate construction volume across all active opportunities",
            ],
            [
                "Total Design Agreement Fees",
                f"${kpis['total_design_fees']:,.0f}",
                "Pre-construction fee revenue committed or pending",
            ],
            [
                "Active Opportunities in Pipeline",
                f"{kpis['active_deals_count']} Deals",
                "Total qualified deals currently progressing through sales",
            ],
            [
                "Deals Pending Kevin's Review",
                f"{kpis['pending_kevin_review']} Deal(s)",
                "Design agreements drafted by Sarah awaiting Kevin's sign-off",
            ],
            [
                "Deals Requiring Urgent Follow-up",
                f"{kpis['needing_attention']} Deal(s)",
                "Opportunities with overdue follow-ups or action flags",
            ],
        ]),
        block_divider(),
        # Section 3
        block_heading_2("🏗️ Active Construction Projects & Milestone Health", color="green"),
        block_paragraph(
            "📌 Project Health View: Create a Linked View of 'Construction Projects' here displayed as a "
            "Board View grouped by 'Current Phase' (Pre-Contract, Pre-Construction, Active Construction, Closeout, Warranty). "
            "Kevin monitors 4-6 major milestones per project without micro-managing field tasks."
        ),
        block_divider(),
        # Section 4
        block_heading_2("🗄️ Master System Databases", color="default"),
        block_paragraph(
            "The 8 underlying relational databases below manage all company data records:"
        ),
    ]

    success = append_children_blocks(parent_page_id, dashboard_blocks)
    if success:
        print("   Executive Dashboard successfully created on main page!\n")
    else:
        print("   Warning: Could not append dashboard blocks to main page.\n")

    # 4. Construct Reusable Project Workspace Template Inside Every Project
    print("--- STEP 2: Adding 4-Phase Workspaces Inside Every Project Record ---")
    projects = fetch_database_records(projects_db_id)
    print(f"   Found {len(projects)} project records to enhance with workspace templates...\n")

    template_blocks = [
        block_callout(
            "Project Workspace Hub: Daily field tasks stay in the Field App. "
            "Use this project workspace for milestone status, material delivery tracking, "
            "logging off-app client conversations (calls/texts to Kevin), and reviewing automated vendor invoices.",
            emoji="🛠️",
            color="gray_background",
        ),
        block_divider(),
        # Phase 1
        block_heading_3("📋 Phase 1: Pre-Construction (Office Team)", color="blue"),
        block_to_do("Gather preliminary architectural plans and coordinate revisions with designer", checked=False),
        block_to_do("Compile preliminary estimates & solicit subcontractor trade bids", checked=False),
        block_to_do("Submit municipal building permit package & verify zoning setback clearances", checked=False),
        block_to_do("Finalize client material allowances and prepare binding Construction Agreement", checked=False),
        # Phase 2
        block_heading_3("🔨 Phase 2: Active Construction (Field Lead)", color="green"),
        block_to_do("Site mobilization, safety barriers, portable sanitation, and material staging area", checked=False),
        block_to_do("Foundation excavation, formwork, rebar inspection, and concrete pour", checked=False),
        block_to_do("Structural framing, trusses, exterior sheathing, and municipal framing inspection", checked=False),
        block_to_do("Rough MEP installation (Mechanical HVAC, Electrical wiring, Plumbing lines)", checked=False),
        block_to_do("Insulation, drywall hang/tape/mud, interior prime & finish paint", checked=False),
        block_to_do("Cabinetry, countertops, flooring, tile, and plumbing/electrical fixtures", checked=False),
        # Phase 3
        block_heading_3("🏁 Phase 3: Project Closeout", color="purple"),
        block_to_do("Conduct comprehensive internal pre-punch walkthrough with field lead & trades", checked=False),
        block_to_do("Pass final building, electrical, and plumbing municipal inspections", checked=False),
        block_to_do("Obtain formal Certificate of Occupancy (CO) from city / county", checked=False),
        block_to_do("Client final walkthrough, sign off completion punch-list, and deliver Warranty Binder", checked=False),
        # Phase 4
        block_heading_3("🛡️ Phase 4: Warranty & Post-Completion", color="orange"),
        block_to_do("30-day post-occupancy client satisfaction check-in call", checked=False),
        block_to_do("11-month builder warranty inspection before 1-year coverage expiration", checked=False),
        block_to_do("Log any warranty repair requests into Client Decision & Comm Log with owner notification", checked=False),
    ]

    for p in projects:
        p_id = p["id"]
        props = p.get("properties", {})
        name_list = props.get("Project Name", {}).get("title", [])
        p_name = name_list[0].get("plain_text", "Untitled Project") if name_list else "Untitled Project"
        code_list = props.get("Project Code", {}).get("rich_text", [])
        p_code = code_list[0].get("plain_text", "") if code_list else ""

        display_title = f"{p_code} - {p_name}" if p_code else p_name
        print(f"   Injecting workspace template into: '{display_title}' ({p_id})...")
        append_children_blocks(p_id, template_blocks)

    print("\n" + "=" * 70)
    print(" ENHANCEMENTS COMPLETE!")
    print("=" * 70)
    print("1. Main Hub Executive Dashboard: Pre-configured with live KPI table and action center.")
    print("2. Reusable Project Checklists: All 4 project phases injected into every project record.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
