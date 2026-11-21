# Kevin's Residential Construction Operations Hub & Sales CRM

> **Business Process Optimization Assessment**  
> An automated, relational business operating system built for residential construction management using **Notion API**, **Python**, and **n8n**.

---

## 🏗️ System Overview

This system solves core operational bottlenecks for a growing residential construction company:
* **Eliminating the Owner Bottleneck:** Offloads initial lead intake and design agreement drafting from Kevin to the new salesperson, while preserving an executive **"Needs Kevin's Review"** approval gateway before client dispatch.
* **Unified Sales CRM Pipeline:** An 8-stage relational deal pipeline (`New Enquiry` $\rightarrow$ `Qualification` $\rightarrow$ `Pre-Contract Estimate / Bid` $\rightarrow$ `Drafting Design Agreement` $\rightarrow$ `Needs Kevin's Review` $\rightarrow$ `Design Agreement Signed` $\rightarrow$ `Construction Agreement Signed` $\rightarrow$ `Closed Lost`).
* **Pre-Contract Estimating Workspace:** Solves the challenge of gathering subcontractor trade bids and lumber estimates *before* contracts are executed (`PRJ-103`).
* **Milestone-Based Project Management:** Reusable 4-phase project architecture (Pre-Construction, Active Construction, Closeout, Warranty) without cluttering executive views with daily field micro-tasks.
* **Client Off-App Decision Audit Trail:** Centralized logging for decisions agreed upon outside the project tool (direct phone calls, texts, or emails to Kevin) so site managers and office teams maintain a single source of truth.
* **Invoice & Cost Tracking (n8n Ready):** Captures incoming vendor invoices, flags unclear charges, links expenses to construction projects, and updates monthly supplier summaries.

---

## 🗄️ Relational Database Architecture

The workspace consists of 8 interconnected databases:

| # | Database Name | Purpose | Key Relations |
|---|---|---|---|
| 1 | **Contacts** | Directory of Clients/Homeowners, Architects/Designers, and Trade Subcontractors | Linked to Opportunities & Projects |
| 2 | **Sales Opportunities (CRM)** | 8-stage sales pipeline with deal ownership, qualification, and approval flags | Relates to Contacts & Activities |
| 3 | **Sales Activities** | Log for calls, texts, emails, site visits, and internal reviews | Relates to Opportunities |
| 4 | **Construction Projects** | Master projects tracking lifecycle phases, budgets, and site leadership | Relates to Opportunities, Contacts, Milestones, Materials, Costs |
| 5 | **Project Milestones** | High-level delivery milestone tracking across all 4 phases | Relates to Projects |
| 6 | **Materials & Deliveries** | Material procurement, supplier tracking, delivery dates, and costs | Relates to Projects |
| 7 | **Client Decision & Comm Log** | Audit trail for off-app decisions (calls/texts to Kevin) with notification status | Relates to Projects |
| 8 | **Project Costs & Invoices** | Tracks vendor invoices, payment status (Paid/Unpaid), due dates, and flags | Relates to Projects (n8n automated) |

---

## 📁 Repository Structure

```
├── .env.example                     # Environment variable template
├── .gitignore                       # Protects .env and sensitive secrets
├── requirements.txt                 # Python dependencies (requests, python-dotenv)
├── setup_notion.py                  # Core script: builds all 8 databases & seeds realistic business data
├── build_dashboard_and_templates.py # Generates live executive KPI dashboard & 4-phase project checklists
├── fix_notion_page.py               # Maintenance & cleanup utility for databases and page blocks
├── notion_config.json               # Auto-generated database IDs and sample project mapping
└── README.md                        # System documentation & walkthrough guide
```

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.10+
* A Notion account with an Internal Integration created at [notion.so/my-integrations](https://www.notion.so/my-integrations).

### 2. Installation
```bash
git clone <repository_url>
cd <repository_folder>
pip install -r requirements.txt
```

### 3. Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and provide your Notion credentials:
   ```env
   NOTION_TOKEN=secret_your_notion_integration_token
   NOTION_PAGE_ID=your_parent_notion_page_id
   ```
3. Connect your Notion Integration to your parent page:
   * Open the parent page in Notion.
   * Click `...` in the top right corner $\rightarrow$ **Connections** $\rightarrow$ add your integration.

### 4. Build & Seed the Workspace
```bash
# 1. Create the 8 databases and seed scenario data
python setup_notion.py

# 2. Build the live Executive KPI Dashboard and project checklists
python build_dashboard_and_templates.py
```

---

## 📊 Live Seed Scenarios Demonstrated
* **Kevin's Approval Bottleneck:** `Oakridge Kitchen & Bath Remodel` in stage `5. Needs Kevin's Review` with `Needs Kevin Review = True`.
* **Full Contract Handoff:** `Maple Ave Custom Home Build` in stage `7. Construction Agreement Signed`, linked to active project `PRJ-101`.
* **Pre-Construction Design Coordination:** `Pinecrest Master Suite Addition` linked to `PRJ-102` (gathering plans with architect Elena Rostova).
* **Pre-Contract Estimating Before Signing:** `Cedar Lane Deck & Sunroom` linked to `PRJ-103` to gather subcontractor bids before contract finalization.
* **Overdue Follow-up Warning:** `Elm Street Basement Finishing` flagged with `Overdue Follow-up - Needs Attention`.
* **Client Off-App Decision Logging:** Text and phone call to Kevin logged with notifications to site supervisor Mike.
* **Automated Cost Tracking:** 3 sample invoices (Paid, Unpaid with due date, and Flagged for review).

---

## ⚡ Assessment Part 3: Invoice & Cost Automation (n8n & Test Runner)

### 1. Test Invoices (`test_invoices/`)
Generate the 3 evaluation invoices in PDF format:
```bash
python generate_test_invoices.py
```
* `1_Apex_Lumber_INV-2026-881_Unpaid.pdf`: Valid project (`PRJ-101`), $4,850.00, Unpaid.
* `2_Apex_Lumber_INV-2026-881_PAID_Update.pdf`: Same doc ref (`INV-2026-881`), Paid. Demonstrates deduplication and status update without double-counting.
* `3_Unknown_Vendor_Missing_Project.pdf`: Metro Concrete Pumping ($1,200.00) without project name/code. Demonstrates `Needs Clarification / Review` flag.

### 2. End-to-End Test Automation Runner
Run the complete automated extraction and Notion pipeline in one command:
```bash
python test_automation_runner.py
```
To also test forwarding payloads to a live n8n webhook:
```bash
python test_automation_runner.py --webhook http://localhost:5678/webhook/invoice-upload
```

### 3. n8n Importable Workflow (`n8n_invoice_workflow.json`)
Import `n8n_invoice_workflow.json` into n8n:
1. Open n8n $\rightarrow$ **Workflows** $\rightarrow$ **Import from File**.
2. Select `n8n_invoice_workflow.json`.
3. Set your environment variables or credentials (`NOTION_TOKEN`, `NOTION_PROJECTS_DB_ID`, `NOTION_COSTS_DB_ID`).
4. Activate the workflow to handle incoming Gmail attachments or trigger via the Webhook node.

