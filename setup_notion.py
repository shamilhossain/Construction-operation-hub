"""
Setup Notion Workspace for Kevin's Residential Construction Company
===================================================================
This script creates all 8 relational databases under a specified parent Notion page
and populates them with comprehensive, realistic seed data covering all business scenarios.

Usage:
    1. Copy `.env.example` to `.env` and fill in `NOTION_TOKEN` and `NOTION_PAGE_ID`.
    2. Run: python setup_notion.py
"""

import os
import sys
import time
import json
import re
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
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


def clean_page_id(raw_id: str) -> str:
    """Extract and normalize a 32-character Notion page ID from string or URL."""
    if not raw_id:
        return ""
    # Strip URL and query parameters
    cleaned = raw_id.strip()
    if "/" in cleaned:
        cleaned = cleaned.split("/")[-1].split("?")[0]
    # Extract last 32 hex characters if title is included in slug
    hex_match = re.search(r"([a-f0-9]{32})$", cleaned.replace("-", ""), re.IGNORECASE)
    if hex_match:
        return hex_match.group(1)
    return cleaned.replace("-", "")


def rate_limit_sleep():
    """Gentle pause to respect Notion's 3 requests per second limit."""
    time.sleep(0.35)


def verify_connection(page_id: str) -> bool:
    """Verifies that the Notion token is valid and the parent page is accessible."""
    print(" Verifying connection to Notion API...")
    url = f"{NOTION_API_URL}/pages/{page_id}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        data = response.json()
        title = "Parent Page"
        # Extract title if present
        props = data.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_list = prop.get("title", [])
                if title_list:
                    title = title_list[0].get("plain_text", title)
        print(f" Connected successfully to parent page: '{title}' ({page_id})\n")
        return True
    elif response.status_code == 401:
        print(" Error 401: Invalid NOTION_TOKEN. Please verify your integration secret in .env.")
        return False
    elif response.status_code in (403, 404):
        print(f" Error {response.status_code}: The parent page could not be accessed.")
        print("   Did you invite your Integration to the page?")
        print("   -> Open the page in Notion -> Click '...' at the top right -> 'Connections' -> Add your Integration.")
        return False
    else:
        print(f" Error {response.status_code}: {response.text}")
        return False


def create_database(parent_page_id: str, title: str, properties: dict) -> str:
    """Creates a Notion database under the parent page and returns its ID."""
    print(f"   Creating Database: '{title}'...")
    url = f"{NOTION_API_URL}/databases"
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": properties,
    }
    rate_limit_sleep()
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f" Failed to create database '{title}': {response.status_code} - {response.text}")
        sys.exit(1)

    db_data = response.json()
    db_id = db_data["id"]
    print(f"   Created '{title}' (ID: {db_id})")
    return db_id


# Property helper constructors
def prop_title(val):
    return {"title": [{"text": {"content": str(val or "")}}]}

def prop_rich_text(val):
    return {"rich_text": [{"text": {"content": str(val or "")}}]}

def prop_select(val):
    return {"select": {"name": str(val)}} if val else None

def prop_number(val):
    return {"number": float(val)} if val is not None else None

def prop_checkbox(val):
    return {"checkbox": bool(val)}

def prop_date(val):
    return {"date": {"start": str(val)}} if val else None

def prop_email(val):
    return {"email": str(val)} if val else None

def prop_phone(val):
    return {"phone_number": str(val)} if val else None

def prop_relation(ids):
    valid_ids = [i for i in ids if i]
    return {"relation": [{"id": i} for i in valid_ids]} if valid_ids else None


def create_page(db_id: str, properties: dict) -> str:
    """Creates a page (row) in the specified database."""
    url = f"{NOTION_API_URL}/pages"
    filtered_props = {k: v for k, v in properties.items() if v is not None}
    payload = {
        "parent": {"database_id": db_id},
        "properties": filtered_props,
    }
    rate_limit_sleep()
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"   Failed to insert record: {response.status_code} - {response.text}")
        return ""
    return response.json()["id"]


def main():
    print("=" * 70)
    print(" Kevin's Residential Construction - Notion Workspace Setup")
    print("=" * 70)

    if not NOTION_TOKEN or NOTION_TOKEN.startswith("secret_your"):
        print(" Error: NOTION_TOKEN is not configured.")
        print("Please copy `.env.example` to `.env` and provide your real Notion integration secret.")
        sys.exit(1)

    cleaned_parent_id = clean_page_id(NOTION_PAGE_ID)
    if not cleaned_parent_id or cleaned_parent_id.startswith("your_parent"):
        print(" Error: NOTION_PAGE_ID is not configured.")
        print("Please provide the ID of the parent Notion page in `.env`.")
        sys.exit(1)

    if not verify_connection(cleaned_parent_id):
        sys.exit(1)

    print("\n--- PHASE 1: Creating 8 Relational Databases in Notion ---\n")

    # 1. Contacts
    contacts_schema = {
        "Name": {"title": {}},
        "Contact Type": {
            "select": {
                "options": [
                    {"name": "Client/Homeowner", "color": "blue"},
                    {"name": "Designer/Architect", "color": "purple"},
                    {"name": "Vendor/Subcontractor", "color": "orange"},
                ]
            }
        },
        "Phone": {"phone_number": {}},
        "Email": {"email": {}},
        "Intake Source": {
            "select": {
                "options": [
                    {"name": "Referral - Direct to Kevin", "color": "green"},
                    {"name": "Phone Call", "color": "blue"},
                    {"name": "Text Message", "color": "yellow"},
                    {"name": "Website Email", "color": "gray"},
                ]
            }
        },
        "Notes": {"rich_text": {}},
    }
    contacts_db_id = create_database(cleaned_parent_id, "Contacts", contacts_schema)

    # 2. Sales Opportunities (CRM)
    sales_crm_schema = {
        "Opportunity Name": {"title": {}},
        "Client": {
            "relation": {
                "database_id": contacts_db_id,
                "single_property": {},
            }
        },
        "Stage": {
            "select": {
                "options": [
                    {"name": "1. New Enquiry", "color": "gray"},
                    {"name": "2. Qualification", "color": "brown"},
                    {"name": "3. Pre-Contract Estimate / Bid", "color": "orange"},
                    {"name": "4. Drafting Design Agreement", "color": "yellow"},
                    {"name": "5. Needs Kevin's Review", "color": "pink"},
                    {"name": "6. Design Agreement Signed", "color": "purple"},
                    {"name": "7. Construction Agreement Signed", "color": "green"},
                    {"name": "8. Closed Lost", "color": "red"},
                ]
            }
        },
        "Lead Owner": {
            "select": {
                "options": [
                    {"name": "Sarah (Salesperson)", "color": "blue"},
                    {"name": "Kevin (Owner)", "color": "green"},
                ]
            }
        },
        "Intake Channel": {
            "select": {
                "options": [
                    {"name": "Direct Text/Call to Kevin", "color": "yellow"},
                    {"name": "Phone Enquiry", "color": "blue"},
                    {"name": "Email Enquiry", "color": "gray"},
                    {"name": "Referral", "color": "green"},
                ]
            }
        },
        "Good Fit?": {
            "select": {
                "options": [
                    {"name": "Pending Evaluation", "color": "yellow"},
                    {"name": "Yes - Good Fit", "color": "green"},
                    {"name": "No - Out of Scope", "color": "red"},
                ]
            }
        },
        "Needs Kevin Review": {"checkbox": {}},
        "Design Fee ($)": {"number": {"format": "dollar"}},
        "Est. Construction Value ($)": {"number": {"format": "dollar"}},
        "Last Contact Date": {"date": {}},
        "Next Follow-up Date": {"date": {}},
        "Attention Flag": {
            "select": {
                "options": [
                    {"name": "On Track", "color": "green"},
                    {"name": "Overdue Follow-up - Needs Attention", "color": "red"},
                    {"name": "Waiting on Kevin's Approval", "color": "orange"},
                ]
            }
        },
        "Agreement / Proposal Notes": {"rich_text": {}},
    }
    opportunities_db_id = create_database(cleaned_parent_id, "Sales Opportunities (CRM)", sales_crm_schema)

    # 3. Sales Activities
    activities_schema = {
        "Activity Summary": {"title": {}},
        "Opportunity": {
            "relation": {
                "database_id": opportunities_db_id,
                "single_property": {},
            }
        },
        "Activity Type": {
            "select": {
                "options": [
                    {"name": "Phone Call", "color": "blue"},
                    {"name": "Text Message", "color": "yellow"},
                    {"name": "Email", "color": "gray"},
                    {"name": "Site Visit", "color": "green"},
                    {"name": "Internal Review", "color": "purple"},
                ]
            }
        },
        "Logged By": {
            "select": {
                "options": [
                    {"name": "Sarah (Salesperson)", "color": "blue"},
                    {"name": "Kevin (Owner)", "color": "green"},
                ]
            }
        },
        "Activity Date": {"date": {}},
        "Outcome & Next Steps": {"rich_text": {}},
    }
    activities_db_id = create_database(cleaned_parent_id, "Sales Activities", activities_schema)

    # 4. Construction Projects
    projects_schema = {
        "Project Name": {"title": {}},
        "Project Code": {"rich_text": {}},
        "Linked Opportunity": {
            "relation": {
                "database_id": opportunities_db_id,
                "single_property": {},
            }
        },
        "Client": {
            "relation": {
                "database_id": contacts_db_id,
                "single_property": {},
            }
        },
        "Current Phase": {
            "select": {
                "options": [
                    {"name": "0. Pre-Contract Estimate / Bid", "color": "yellow"},
                    {"name": "1. Pre-Construction (Office)", "color": "blue"},
                    {"name": "2. Active Construction (Field)", "color": "green"},
                    {"name": "3. Closeout", "color": "purple"},
                    {"name": "4. Warranty", "color": "gray"},
                ]
            }
        },
        "Overall Health": {
            "select": {
                "options": [
                    {"name": "On Track", "color": "green"},
                    {"name": "At Risk / Delayed", "color": "red"},
                    {"name": "Waiting on Client Decision", "color": "orange"},
                    {"name": "Completed", "color": "gray"},
                ]
            }
        },
        "Office Coordinator": {
            "select": {
                "options": [
                    {"name": "Rachel (Office Lead)", "color": "blue"},
                    {"name": "Sarah (Salesperson)", "color": "purple"},
                ]
            }
        },
        "Field Lead": {
            "select": {
                "options": [
                    {"name": "Mike (Field Lead)", "color": "orange"},
                    {"name": "Dave (Field Lead)", "color": "yellow"},
                    {"name": "Unassigned (Pre-Con)", "color": "gray"},
                ]
            }
        },
        "Start Date": {"date": {}},
        "Target Completion": {"date": {}},
        "Total Approved Budget ($)": {"number": {"format": "dollar"}},
        "Scope Summary": {"rich_text": {}},
    }
    projects_db_id = create_database(cleaned_parent_id, "Construction Projects", projects_schema)

    # 5. Project Milestones
    milestones_schema = {
        "Milestone Name": {"title": {}},
        "Project": {
            "relation": {
                "database_id": projects_db_id,
                "single_property": {},
            }
        },
        "Phase": {
            "select": {
                "options": [
                    {"name": "Pre-Construction", "color": "blue"},
                    {"name": "Construction", "color": "green"},
                    {"name": "Closeout", "color": "purple"},
                    {"name": "Warranty", "color": "gray"},
                ]
            }
        },
        "Responsible Owner": {
            "select": {
                "options": [
                    {"name": "Rachel (Office Team)", "color": "blue"},
                    {"name": "Mike (Field Lead)", "color": "orange"},
                    {"name": "Dave (Field Lead)", "color": "yellow"},
                    {"name": "Kevin (Owner)", "color": "green"},
                ]
            }
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "Not Started", "color": "gray"},
                    {"name": "In Progress", "color": "blue"},
                    {"name": "Completed", "color": "green"},
                    {"name": "Delayed", "color": "red"},
                ]
            }
        },
        "Deadline": {"date": {}},
        "Progress Update": {"rich_text": {}},
    }
    milestones_db_id = create_database(cleaned_parent_id, "Project Milestones", milestones_schema)

    # 6. Materials & Deliveries
    materials_schema = {
        "Item / Material": {"title": {}},
        "Project": {
            "relation": {
                "database_id": projects_db_id,
                "single_property": {},
            }
        },
        "Supplier": {"rich_text": {}},
        "Order Status": {
            "select": {
                "options": [
                    {"name": "To Order", "color": "gray"},
                    {"name": "Ordered", "color": "yellow"},
                    {"name": "Shipped", "color": "blue"},
                    {"name": "Delivered on Site", "color": "green"},
                    {"name": "Delayed / Backordered", "color": "red"},
                ]
            }
        },
        "Ordered By": {
            "select": {
                "options": [
                    {"name": "Rachel (Office Team)", "color": "blue"},
                    {"name": "Mike (Field Lead)", "color": "orange"},
                ]
            }
        },
        "Expected Delivery": {"date": {}},
        "Cost ($)": {"number": {"format": "dollar"}},
        "Delivery Notes": {"rich_text": {}},
    }
    materials_db_id = create_database(cleaned_parent_id, "Materials & Deliveries", materials_schema)

    # 7. Client Decision & Comm Log
    decision_log_schema = {
        "Decision / Topic": {"title": {}},
        "Project": {
            "relation": {
                "database_id": projects_db_id,
                "single_property": {},
            }
        },
        "Communication Channel": {
            "select": {
                "options": [
                    {"name": "Text to Kevin", "color": "yellow"},
                    {"name": "Call to Kevin", "color": "blue"},
                    {"name": "Email to Kevin", "color": "gray"},
                    {"name": "Project App", "color": "green"},
                ]
            }
        },
        "Date Agreed": {"date": {}},
        "Logged By": {
            "select": {
                "options": [
                    {"name": "Kevin (Owner)", "color": "green"},
                    {"name": "Rachel (Office Team)", "color": "blue"},
                    {"name": "Mike (Field Lead)", "color": "orange"},
                ]
            }
        },
        "Notified Field/Office Team?": {"checkbox": {}},
        "Details of Agreement": {"rich_text": {}},
    }
    decision_log_db_id = create_database(cleaned_parent_id, "Client Decision & Comm Log", decision_log_schema)

    # 8. Project Costs & Invoices (Part 3 n8n Automation ready)
    costs_schema = {
        "Invoice / Receipt Title": {"title": {}},
        "Project": {
            "relation": {
                "database_id": projects_db_id,
                "single_property": {},
            }
        },
        "Supplier / Vendor": {"rich_text": {}},
        "Document Reference": {"rich_text": {}},
        "Invoice Date": {"date": {}},
        "Due Date": {"date": {}},
        "Amount": {"number": {"format": "dollar"}},
        "Currency": {
            "select": {
                "options": [
                    {"name": "USD", "color": "green"},
                    {"name": "CAD", "color": "blue"},
                    {"name": "EUR", "color": "purple"},
                    {"name": "GBP", "color": "orange"},
                ]
            }
        },
        "Payment Status": {
            "select": {
                "options": [
                    {"name": "Paid", "color": "green"},
                    {"name": "Unpaid", "color": "red"},
                    {"name": "Partially Paid", "color": "yellow"},
                ]
            }
        },
        "Needs Clarification / Review": {"checkbox": {}},
        "Review / Flag Reason": {"rich_text": {}},
        "Source Email / Attachment Info": {"rich_text": {}},
    }
    costs_db_id = create_database(cleaned_parent_id, "Project Costs & Invoices", costs_schema)

    print("\n All 8 databases successfully created in Notion!\n")

    # --- PHASE 2: Seeding Data ---
    print("--- PHASE 2: Seeding Realistic Business Scenario Data ---\n")

    # 1. Seed Contacts
    print("   Seeding Contacts...")
    contact_vance_id = create_page(contacts_db_id, {
        "Name": prop_title("Robert & Linda Vance"),
        "Contact Type": prop_select("Client/Homeowner"),
        "Phone": prop_phone("555-0144"),
        "Email": prop_email("vance.residence@example.com"),
        "Intake Source": prop_select("Referral - Direct to Kevin"),
        "Notes": prop_rich_text("Longtime personal friends of Kevin. Referred for high-end kitchen & primary bathroom expansion."),
    })

    contact_pendelton_id = create_page(contacts_db_id, {
        "Name": prop_title("Arthur & Clara Pendelton"),
        "Contact Type": prop_select("Client/Homeowner"),
        "Phone": prop_phone("555-0182"),
        "Email": prop_email("arthur.pendelton@example.com"),
        "Intake Source": prop_select("Website Email"),
        "Notes": prop_rich_text("Custom single-family residence build on Maple Ave. High attention to detail on architectural finishes."),
    })

    contact_chen_id = create_page(contacts_db_id, {
        "Name": prop_title("Marcus Chen"),
        "Contact Type": prop_select("Client/Homeowner"),
        "Phone": prop_phone("555-0291"),
        "Email": prop_email("mchen.architectural@example.com"),
        "Intake Source": prop_select("Phone Call"),
        "Notes": prop_rich_text("Inquired for second-story master suite addition over two-car garage."),
    })

    contact_hayes_id = create_page(contacts_db_id, {
        "Name": prop_title("Emily & Greg Hayes"),
        "Contact Type": prop_select("Client/Homeowner"),
        "Phone": prop_phone("555-0374"),
        "Email": prop_email("hayes.home@example.com"),
        "Intake Source": prop_select("Text Message"),
        "Notes": prop_rich_text("Texted Kevin's direct mobile regarding a multi-tier cedar sunroom & deck."),
    })

    contact_miller_id = create_page(contacts_db_id, {
        "Name": prop_title("David Miller"),
        "Contact Type": prop_select("Client/Homeowner"),
        "Phone": prop_phone("555-0450"),
        "Email": prop_email("dmiller@example.com"),
        "Intake Source": prop_select("Phone Call"),
        "Notes": prop_rich_text("Basement finishing inquiry. Currently overdue for follow-up questionnaire."),
    })

    contact_architect_id = create_page(contacts_db_id, {
        "Name": prop_title("Elena Rostova (Studio Linea Architecture)"),
        "Contact Type": prop_select("Designer/Architect"),
        "Phone": prop_phone("555-0819"),
        "Email": prop_email("elena@studiolinea.com"),
        "Intake Source": prop_select("Referral - Direct to Kevin"),
        "Notes": prop_rich_text("Preferred architectural design partner for pre-construction schematic packages."),
    })

    # 2. Seed Sales Opportunities (CRM)
    print("   Seeding Sales Opportunities (CRM)...")
    # Deal 1: Needs Kevin's Review
    deal_oakridge_id = create_page(opportunities_db_id, {
        "Opportunity Name": prop_title("Oakridge Kitchen & Bath Remodel"),
        "Client": prop_relation([contact_vance_id]),
        "Stage": prop_select("5. Needs Kevin's Review"),
        "Lead Owner": prop_select("Sarah (Salesperson)"),
        "Intake Channel": prop_select("Referral"),
        "Good Fit?": prop_select("Yes - Good Fit"),
        "Needs Kevin Review": prop_checkbox(True),
        "Design Fee ($)": prop_number(4500),
        "Est. Construction Value ($)": prop_number(125000),
        "Last Contact Date": prop_date("2026-11-15"),
        "Next Follow-up Date": prop_date("2026-11-20"),
        "Attention Flag": prop_select("Waiting on Kevin's Approval"),
        "Agreement / Proposal Notes": prop_rich_text(
            "Sarah drafted the preliminary design agreement. Scope includes load-bearing wall removal, island re-orientation, and plumbing rough-in. Awaiting Kevin's sign-off before sending."
        ),
    })

    # Deal 2: Construction Agreement Signed
    deal_maple_id = create_page(opportunities_db_id, {
        "Opportunity Name": prop_title("Maple Ave Custom Home Build"),
        "Client": prop_relation([contact_pendelton_id]),
        "Stage": prop_select("7. Construction Agreement Signed"),
        "Lead Owner": prop_select("Kevin (Owner)"),
        "Intake Channel": prop_select("Direct Text/Call to Kevin"),
        "Good Fit?": prop_select("Yes - Good Fit"),
        "Needs Kevin Review": prop_checkbox(False),
        "Design Fee ($)": prop_number(12000),
        "Est. Construction Value ($)": prop_number(680000),
        "Last Contact Date": prop_date("2026-11-12"),
        "Next Follow-up Date": prop_date("2026-11-25"),
        "Attention Flag": prop_select("On Track"),
        "Agreement / Proposal Notes": prop_rich_text(
            "Full construction contract executed. Retainer received. Handoff to project team completed."
        ),
    })

    # Deal 3: Design Agreement Signed
    deal_pinecrest_id = create_page(opportunities_db_id, {
        "Opportunity Name": prop_title("Pinecrest Master Suite Addition"),
        "Client": prop_relation([contact_chen_id]),
        "Stage": prop_select("6. Design Agreement Signed"),
        "Lead Owner": prop_select("Sarah (Salesperson)"),
        "Intake Channel": prop_select("Phone Enquiry"),
        "Good Fit?": prop_select("Yes - Good Fit"),
        "Needs Kevin Review": prop_checkbox(False),
        "Design Fee ($)": prop_number(5500),
        "Est. Construction Value ($)": prop_number(185000),
        "Last Contact Date": prop_date("2026-11-14"),
        "Next Follow-up Date": prop_date("2026-11-21"),
        "Attention Flag": prop_select("On Track"),
        "Agreement / Proposal Notes": prop_rich_text(
            "Design retainer paid. In pre-construction phase: coordinating architectural elevations with Elena Rostova."
        ),
    })

    # Deal 4: Pre-Contract Estimate / Bid (Pre-contract estimating before agreement!)
    deal_cedar_id = create_page(opportunities_db_id, {
        "Opportunity Name": prop_title("Cedar Lane Deck & Sunroom"),
        "Client": prop_relation([contact_hayes_id]),
        "Stage": prop_select("3. Pre-Contract Estimate / Bid"),
        "Lead Owner": prop_select("Sarah (Salesperson)"),
        "Intake Channel": prop_select("Email Enquiry"),
        "Good Fit?": prop_select("Yes - Good Fit"),
        "Needs Kevin Review": prop_checkbox(False),
        "Design Fee ($)": prop_number(0),
        "Est. Construction Value ($)": prop_number(58000),
        "Last Contact Date": prop_date("2026-11-16"),
        "Next Follow-up Date": prop_date("2026-11-22"),
        "Attention Flag": prop_select("On Track"),
        "Agreement / Proposal Notes": prop_rich_text(
            "Pre-contract estimating stage. Need to request preliminary bids from framing and glazing subcontractors before putting together binding numbers."
        ),
    })

    # Deal 5: Overdue Qualification
    deal_elm_id = create_page(opportunities_db_id, {
        "Opportunity Name": prop_title("Elm Street Basement Finishing"),
        "Client": prop_relation([contact_miller_id]),
        "Stage": prop_select("2. Qualification"),
        "Lead Owner": prop_select("Sarah (Salesperson)"),
        "Intake Channel": prop_select("Phone Enquiry"),
        "Good Fit?": prop_select("Pending Evaluation"),
        "Needs Kevin Review": prop_checkbox(False),
        "Design Fee ($)": prop_number(0),
        "Est. Construction Value ($)": prop_number(45000),
        "Last Contact Date": prop_date("2026-11-04"),
        "Next Follow-up Date": prop_date("2026-11-11"),  # Deliberately overdue
        "Attention Flag": prop_select("Overdue Follow-up - Needs Attention"),
        "Agreement / Proposal Notes": prop_rich_text(
            "Follow-up was scheduled for Nov 11. Overdue by several days. Sarah must follow up regarding budget fit."
        ),
    })

    # 3. Seed Construction Projects
    print("   Seeding Construction Projects...")
    # Project 1: Active Construction
    prj_maple_id = create_page(projects_db_id, {
        "Project Name": prop_title("Maple Ave Custom Build"),
        "Project Code": prop_rich_text("PRJ-101"),
        "Linked Opportunity": prop_relation([deal_maple_id]),
        "Client": prop_relation([contact_pendelton_id]),
        "Current Phase": prop_select("2. Active Construction (Field)"),
        "Overall Health": prop_select("On Track"),
        "Office Coordinator": prop_select("Rachel (Office Lead)"),
        "Field Lead": prop_select("Mike (Field Lead)"),
        "Start Date": prop_date("2026-09-01"),
        "Target Completion": prop_date("2027-05-30"),
        "Total Approved Budget ($)": prop_number(680000),
        "Scope Summary": prop_rich_text("3,400 sqft residential custom build. Framing completed; rough plumbing and electrical underway."),
    })

    # Project 2: Pre-Construction
    prj_pinecrest_id = create_page(projects_db_id, {
        "Project Name": prop_title("Pinecrest Addition"),
        "Project Code": prop_rich_text("PRJ-102"),
        "Linked Opportunity": prop_relation([deal_pinecrest_id]),
        "Client": prop_relation([contact_chen_id]),
        "Current Phase": prop_select("1. Pre-Construction (Office)"),
        "Overall Health": prop_select("On Track"),
        "Office Coordinator": prop_select("Rachel (Office Lead)"),
        "Field Lead": prop_select("Unassigned (Pre-Con)"),
        "Start Date": prop_date("2026-11-01"),
        "Target Completion": prop_date("2027-04-15"),
        "Total Approved Budget ($)": prop_number(185000),
        "Scope Summary": prop_rich_text("Master suite addition. Gathering architectural drawings, soil report, and structural engineering."),
    })

    # Project 3: Pre-Contract Estimating Space
    prj_cedar_id = create_page(projects_db_id, {
        "Project Name": prop_title("Cedar Lane Estimate & Bidding"),
        "Project Code": prop_rich_text("PRJ-103"),
        "Linked Opportunity": prop_relation([deal_cedar_id]),
        "Client": prop_relation([contact_hayes_id]),
        "Current Phase": prop_select("0. Pre-Contract Estimate / Bid"),
        "Overall Health": prop_select("On Track"),
        "Office Coordinator": prop_select("Sarah (Salesperson)"),
        "Field Lead": prop_select("Unassigned (Pre-Con)"),
        "Start Date": prop_date("2026-11-15"),
        "Target Completion": prop_date("2026-12-05"),
        "Total Approved Budget ($)": prop_number(58000),
        "Scope Summary": prop_rich_text("Pre-contract workspace created prior to signing to request lumber quotes and glazier subcontractor bids."),
    })

    # Project 4: Warranty Phase
    prj_birchwood_id = create_page(projects_db_id, {
        "Project Name": prop_title("Birchwood Residence Remodel"),
        "Project Code": prop_rich_text("PRJ-104"),
        "Client": prop_relation([contact_vance_id]),
        "Current Phase": prop_select("4. Warranty"),
        "Overall Health": prop_select("Completed"),
        "Office Coordinator": prop_select("Rachel (Office Lead)"),
        "Field Lead": prop_select("Dave (Field Lead)"),
        "Start Date": prop_date("2026-01-15"),
        "Target Completion": prop_date("2026-08-30"),
        "Total Approved Budget ($)": prop_number(210000),
        "Scope Summary": prop_rich_text("Main floor living & dining overhaul completed in August 2026. Currently in 1-year warranty coverage."),
    })

    # 4. Seed Sales Activities
    print("   Seeding Sales Activities...")
    create_page(activities_db_id, {
        "Activity Summary": prop_title("Initial Consultation & Scope Review"),
        "Opportunity": prop_relation([deal_oakridge_id]),
        "Activity Type": prop_select("Phone Call"),
        "Logged By": prop_select("Sarah (Salesperson)"),
        "Activity Date": prop_date("2026-11-10"),
        "Outcome & Next Steps": prop_rich_text("Reviewed kitchen layout sketches with Linda Vance. Agreed to draft $4,500 design agreement."),
    })

    create_page(activities_db_id, {
        "Activity Summary": prop_title("Design Agreement Review Presentation"),
        "Opportunity": prop_relation([deal_oakridge_id]),
        "Activity Type": prop_select("Internal Review"),
        "Logged By": prop_select("Sarah (Salesperson)"),
        "Activity Date": prop_date("2026-11-15"),
        "Outcome & Next Steps": prop_rich_text("Presented completed draft to Kevin for review. Kevin flagged verification of beam load calculations."),
    })

    create_page(activities_db_id, {
        "Activity Summary": prop_title("Site Measurement & Feasibility Inspection"),
        "Opportunity": prop_relation([deal_pinecrest_id]),
        "Activity Type": prop_select("Site Visit"),
        "Logged By": prop_select("Sarah (Salesperson)"),
        "Activity Date": prop_date("2026-11-08"),
        "Outcome & Next Steps": prop_rich_text("Checked garage foundation and side setback clearances. Project is structurally viable."),
    })

    create_page(activities_db_id, {
        "Activity Summary": prop_title("Direct Inbound Lead Relay from Kevin"),
        "Opportunity": prop_relation([deal_maple_id]),
        "Activity Type": prop_select("Phone Call"),
        "Logged By": prop_select("Kevin (Owner)"),
        "Activity Date": prop_date("2026-09-01"),
        "Outcome & Next Steps": prop_rich_text("Arthur contacted Kevin directly. Kevin logged initial requirements and scheduled contract signing."),
    })

    create_page(activities_db_id, {
        "Activity Summary": prop_title("Qualification Follow-up Call"),
        "Opportunity": prop_relation([deal_elm_id]),
        "Activity Type": prop_select("Phone Call"),
        "Logged By": prop_select("Sarah (Salesperson)"),
        "Activity Date": prop_date("2026-11-04"),
        "Outcome & Next Steps": prop_rich_text("Left voicemail regarding basement budget breakdown. Needs follow-up."),
    })

    # 5. Seed Project Milestones
    print("   Seeding Project Milestones...")
    create_page(milestones_db_id, {
        "Milestone Name": prop_title("Architectural Plans & Zoning Approval"),
        "Project": prop_relation([prj_pinecrest_id]),
        "Phase": prop_select("Pre-Construction"),
        "Responsible Owner": prop_select("Rachel (Office Team)"),
        "Status": prop_select("In Progress"),
        "Deadline": prop_date("2026-12-15"),
        "Progress Update": prop_rich_text("Architect submitted initial draft elevations; awaiting client review."),
    })

    create_page(milestones_db_id, {
        "Milestone Name": prop_title("Roof Framing & Sheathing Inspection"),
        "Project": prop_relation([prj_maple_id]),
        "Phase": prop_select("Construction"),
        "Responsible Owner": prop_select("Mike (Field Lead)"),
        "Status": prop_select("Completed"),
        "Deadline": prop_date("2026-11-10"),
        "Progress Update": prop_rich_text("Passed municipal building department structural inspection on first inspection."),
    })

    create_page(milestones_db_id, {
        "Milestone Name": prop_title("Rough Plumbing & Electrical Rough-in"),
        "Project": prop_relation([prj_maple_id]),
        "Phase": prop_select("Construction"),
        "Responsible Owner": prop_select("Mike (Field Lead)"),
        "Status": prop_select("In Progress"),
        "Deadline": prop_date("2026-12-01"),
        "Progress Update": prop_rich_text("Electrical 65% complete; plumbing manifold installed. Subcontractors on schedule."),
    })

    create_page(milestones_db_id, {
        "Milestone Name": prop_title("Final Occupancy Certificate & Handover"),
        "Project": prop_relation([prj_birchwood_id]),
        "Phase": prop_select("Closeout"),
        "Responsible Owner": prop_select("Dave (Field Lead)"),
        "Status": prop_select("Completed"),
        "Deadline": prop_date("2026-08-25"),
        "Progress Update": prop_rich_text("All punch-list defects resolved. Certificate of Occupancy issued."),
    })

    create_page(milestones_db_id, {
        "Milestone Name": prop_title("90-Day Post-Completion Warranty Check-in"),
        "Project": prop_relation([prj_birchwood_id]),
        "Phase": prop_select("Warranty"),
        "Responsible Owner": prop_select("Rachel (Office Team)"),
        "Status": prop_select("Completed"),
        "Deadline": prop_date("2026-11-15"),
        "Progress Update": prop_rich_text("Homeowner contacted; minor caulking and cabinet hinge adjustment completed under warranty."),
    })

    # 6. Seed Materials & Deliveries
    print("   Seeding Materials & Deliveries...")
    create_page(materials_db_id, {
        "Item / Material": prop_title("Engineered Trusses & Framing Lumber Package"),
        "Project": prop_relation([prj_maple_id]),
        "Supplier": prop_rich_text("BuildPro Lumber & Supply"),
        "Order Status": prop_select("Delivered on Site"),
        "Ordered By": prop_select("Rachel (Office Team)"),
        "Expected Delivery": prop_date("2026-10-15"),
        "Cost ($)": prop_number(28500),
        "Delivery Notes": prop_rich_text("Delivered on two flatbeds; verified and signed off by Mike on site."),
    })

    create_page(materials_db_id, {
        "Item / Material": prop_title("Pella Lifestyle Series Windows (14 Units)"),
        "Project": prop_relation([prj_maple_id]),
        "Supplier": prop_rich_text("Apex Window Specialists"),
        "Order Status": prop_select("Shipped"),
        "Ordered By": prop_select("Rachel (Office Team)"),
        "Expected Delivery": prop_date("2026-11-28"),
        "Cost ($)": prop_number(14200),
        "Delivery Notes": prop_rich_text("Tracking #APX-9921; staging area cleared on ground floor for offloading."),
    })

    create_page(materials_db_id, {
        "Item / Material": prop_title("Custom White Oak Double Vanity & Mirrors"),
        "Project": prop_relation([prj_pinecrest_id]),
        "Supplier": prop_rich_text("Starlight Custom Millwork"),
        "Order Status": prop_select("To Order"),
        "Ordered By": prop_select("Rachel (Office Team)"),
        "Expected Delivery": prop_date("2027-01-15"),
        "Cost ($)": prop_number(6800),
        "Delivery Notes": prop_rich_text("Awaiting final finish approval from client."),
    })

    create_page(materials_db_id, {
        "Item / Material": prop_title("Rough-in Copper Pipe & PEX Manifold Package"),
        "Project": prop_relation([prj_maple_id]),
        "Supplier": prop_rich_text("Metro Plumbing Wholesalers"),
        "Order Status": prop_select("Ordered"),
        "Ordered By": prop_select("Mike (Field Lead)"),
        "Expected Delivery": prop_date("2026-11-22"),
        "Cost ($)": prop_number(4950),
        "Delivery Notes": prop_rich_text("Direct jobsite delivery scheduled for 8:00 AM."),
    })

    # 7. Seed Client Decision & Comm Log (Key scenario from brief!)
    print("   Seeding Client Decision & Comm Log...")
    create_page(decision_log_db_id, {
        "Decision / Topic": prop_title("Upgrade Countertops: Calacatta Gold Quartz"),
        "Project": prop_relation([prj_maple_id]),
        "Communication Channel": prop_select("Text to Kevin"),
        "Date Agreed": prop_date("2026-11-14"),
        "Logged By": prop_select("Kevin (Owner)"),
        "Notified Field/Office Team?": prop_checkbox(True),
        "Details of Agreement": prop_rich_text(
            "Arthur Pendelton texted Kevin directly requesting upgrade from Carrara to Calacatta Gold 3cm quartz. Kevin agreed on +$1,450 price delta. Logged here so Mike (Field Lead) and Rachel update the order without confusion."
        ),
    })

    create_page(decision_log_db_id, {
        "Decision / Topic": prop_title("Cabinet Pull Finish Changed to Matte Black"),
        "Project": prop_relation([prj_maple_id]),
        "Communication Channel": prop_select("Call to Kevin"),
        "Date Agreed": prop_date("2026-11-12"),
        "Logged By": prop_select("Kevin (Owner)"),
        "Notified Field/Office Team?": prop_checkbox(True),
        "Details of Agreement": prop_rich_text(
            "Clara called Kevin while visiting showroom. Selected matte black hardware instead of brushed brass. Notified Mike to reflect in millwork packet."
        ),
    })

    create_page(decision_log_db_id, {
        "Decision / Topic": prop_title("Master Walk-in Closet Door Shifted 2ft East"),
        "Project": prop_relation([prj_pinecrest_id]),
        "Communication Channel": prop_select("Project App"),
        "Date Agreed": prop_date("2026-11-16"),
        "Logged By": prop_select("Rachel (Office Team)"),
        "Notified Field/Office Team?": prop_checkbox(True),
        "Details of Agreement": prop_rich_text(
            "Marcus Chen marked up architectural PDF inside the app to accommodate a larger dresser. Architect updated Rev 2 drawings."
        ),
    })

    create_page(decision_log_db_id, {
        "Decision / Topic": prop_title("Trex Composite Selected Over Pressure-Treated Pine"),
        "Project": prop_relation([prj_cedar_id]),
        "Communication Channel": prop_select("Email to Kevin"),
        "Date Agreed": prop_date("2026-11-15"),
        "Logged By": prop_select("Kevin (Owner)"),
        "Notified Field/Office Team?": prop_checkbox(True),
        "Details of Agreement": prop_rich_text(
            "Emily Hayes emailed Kevin requesting composite decking pricing for the preliminary estimate. Forwarded to Sarah for bid compilation."
        ),
    })

    # 8. Seed Project Costs & Invoices (Pre-populating for Part 3 n8n Automation)
    print("   Seeding Project Costs & Invoices (Automation baseline)...")
    # 1 Paid
    create_page(costs_db_id, {
        "Invoice / Receipt Title": prop_title("BuildPro Lumber - Framing Package Inv #BPL-8821"),
        "Project": prop_relation([prj_maple_id]),
        "Supplier / Vendor": prop_rich_text("BuildPro Lumber & Supply"),
        "Document Reference": prop_rich_text("INV-BPL-8821"),
        "Invoice Date": prop_date("2026-11-05"),
        "Due Date": prop_date("2026-11-20"),
        "Amount": prop_number(18450),
        "Currency": prop_select("USD"),
        "Payment Status": prop_select("Paid"),
        "Needs Clarification / Review": prop_checkbox(False),
        "Review / Flag Reason": prop_rich_text(""),
        "Source Email / Attachment Info": prop_rich_text("Email from billing@buildpro.com with attached INV-BPL-8821.pdf"),
    })

    # 1 Unpaid with Due Date
    create_page(costs_db_id, {
        "Invoice / Receipt Title": prop_title("All-Star Concrete - Slab Pour & Foundation Walls"),
        "Project": prop_relation([prj_maple_id]),
        "Supplier / Vendor": prop_rich_text("All-Star Concrete LLC"),
        "Document Reference": prop_rich_text("INV-ASC-4029"),
        "Invoice Date": prop_date("2026-11-12"),
        "Due Date": prop_date("2026-11-27"),
        "Amount": prop_number(12800),
        "Currency": prop_select("USD"),
        "Payment Status": prop_select("Unpaid"),
        "Needs Clarification / Review": prop_checkbox(False),
        "Review / Flag Reason": prop_rich_text(""),
        "Source Email / Attachment Info": prop_rich_text("Email from accounts@allstarconcrete.com, due in 15 days"),
    })

    # 1 Flagged: Needs Clarification / Review
    create_page(costs_db_id, {
        "Invoice / Receipt Title": prop_title("Elite MEP Consulting - Engineering Review"),
        "Project": prop_relation([prj_pinecrest_id]),
        "Supplier / Vendor": prop_rich_text("Elite Engineering Group"),
        "Document Reference": prop_rich_text("INV-EEG-104"),
        "Invoice Date": prop_date("2026-11-14"),
        "Due Date": prop_date("2026-11-30"),
        "Amount": prop_number(3200),
        "Currency": prop_select("USD"),
        "Payment Status": prop_select("Unpaid"),
        "Needs Clarification / Review": prop_checkbox(True),
        "Review / Flag Reason": prop_rich_text(
            "Invoice lacks itemized breakdown between structural calculation and Title 24 energy report. Need clarification before payment approval."
        ),
        "Source Email / Attachment Info": prop_rich_text("Email from intake@eliteeng.com with unitemized PDF invoice"),
    })

    print("\n Data seeding completed successfully!\n")

    # --- PHASE 3: Saving Configuration ---
    config = {
        "parent_page_id": cleaned_parent_id,
        "created_at": datetime.now().isoformat(),
        "databases": {
            "contacts": contacts_db_id,
            "opportunities": opportunities_db_id,
            "sales_activities": activities_db_id,
            "projects": projects_db_id,
            "milestones": milestones_db_id,
            "materials": materials_db_id,
            "decision_log": decision_log_db_id,
            "costs_invoices": costs_db_id,
        },
        "sample_projects": {
            "PRJ-101 (Maple Ave - Construction)": prj_maple_id,
            "PRJ-102 (Pinecrest - Pre-Con)": prj_pinecrest_id,
            "PRJ-103 (Cedar Lane - Estimating)": prj_cedar_id,
            "PRJ-104 (Birchwood - Warranty)": prj_birchwood_id,
        },
    }

    config_path = os.path.join(os.path.dirname(__file__), "notion_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(" Saved workspace configuration to `notion_config.json`")

    # Print clean summary table
    print("\n" + "=" * 70)
    print(" WORKSPACE SUMMARY: ALL 8 DATABASES & SAMPLE DATA ARE READY")
    print("=" * 70)
    print(f" {'Database Name':<32} | {'Database ID':<36}")
    print("-" * 70)
    for name, db_id in config["databases"].items():
        print(f" {name:<32} | {db_id:<36}")
    print("=" * 70)
    print("\nKey Scenarios Demonstrated:")
    print("  1. Deal 1 ('Oakridge Remodel'): Stage '5. Needs Kevin's Review', flagged for approval.")
    print("  2. Deal 2 ('Maple Ave Custom'): Linked to PRJ-101 (Active Construction, Mike lead).")
    print("  3. Deal 3 ('Pinecrest Addition'): Linked to PRJ-102 (Pre-Construction, plans & design).")
    print("  4. Deal 4 ('Cedar Lane Deck'): Linked to PRJ-103 (Pre-Contract estimating before signing).")
    print("  5. Deal 5 ('Elm Street'): In Qualification with an overdue follow-up flag.")
    print("  6. PRJ-104 ('Birchwood'): In Warranty phase to complete all 4 project phases.")
    print("  7. Client Decision Log: Shows off-app texts/calls to Kevin documented for site crew.")
    print("  8. Project Costs & Invoices: Ready with Paid, Unpaid, and Flagged sample invoices for n8n.\n")


if __name__ == "__main__":
    main()
