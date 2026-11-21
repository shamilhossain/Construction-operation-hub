"""
Generate Realistic Construction PDF Invoices for Testing Automation
===================================================================
Generates 3 realistic PDF invoices in `test_invoices/`:
1. `1_Apex_Lumber_INV-2026-881_Unpaid.pdf`: Valid project (PRJ-101), Unpaid
2. `2_Apex_Lumber_INV-2026-881_PAID_Update.pdf`: Same doc ref & vendor, Paid in full (Deduplication test)
3. `3_Unknown_Vendor_Missing_Project.pdf`: Metro Concrete Pumping, no project hint (Flag for review test)
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_invoices")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_invoice_pdf(
    filename: str,
    vendor_name: str,
    vendor_address: list[str],
    doc_ref: str,
    invoice_date: str,
    due_date: str,
    project_hint: str,
    payment_status: str,
    items: list[tuple[str, str, float, float]],
    currency_symbol: str = "$",
    notes: str = "",
    paid_details: str = "",
):
    pdf_path = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1e293b"),
    )
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748b"),
    )
    header_right = ParagraphStyle(
        "HeaderRight",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        alignment=2,
        textColor=colors.HexColor("#334155"),
    )
    header_right_sub = ParagraphStyle(
        "HeaderRightSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        alignment=2,
        textColor=colors.HexColor("#64748b"),
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )
    body_regular = ParagraphStyle(
        "BodyRegular",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    status_unpaid = ParagraphStyle(
        "StatusUnpaid",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=1,
        textColor=colors.HexColor("#dc2626"),
    )
    status_paid = ParagraphStyle(
        "StatusPaid",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=1,
        textColor=colors.HexColor("#16a34a"),
    )

    story = []

    # 1. Header Bar: Vendor Name vs INVOICE Title
    vendor_lines = [f"<b>{vendor_name}</b>"] + vendor_address
    vendor_p = Paragraph("<br/>".join(vendor_lines), body_regular)

    invoice_meta_text = f"""
    <b>INVOICE</b><br/>
    <b>Invoice #:</b> {doc_ref}<br/>
    <b>Date:</b> {invoice_date}<br/>
    <b>Due Date:</b> {due_date}
    """
    invoice_meta_p = Paragraph(invoice_meta_text, header_right_sub)

    header_table = Table([[vendor_p, invoice_meta_p]], colWidths=[3.5 * inch, 3.8 * inch])
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=14))

    # 2. Bill To & Project Info Box
    bill_to_text = """
    <b>BILL TO:</b><br/>
    Kevin's Residential Construction LLC<br/>
    Attn: Accounts Payable / Kevin<br/>
    742 Evergreen Terrace, Suite 100<br/>
    Email: billing@kevinconstruction.com
    """
    bill_to_p = Paragraph(bill_to_text, body_regular)

    if project_hint:
        project_box_content = f"""
        <b>PROJECT / JOB SITE:</b><br/>
        <font color="#0284c7"><b>{project_hint}</b></font><br/>
        PO / Work Order: WO-2026-44<br/>
        Job Site Manager: Mike (Field Lead)
        """
    else:
        project_box_content = """
        <b>PROJECT / JOB SITE:</b><br/>
        <font color="#dc2626"><b>[NOT SPECIFIED]</b></font><br/>
        <i>* Dispatch slip attached. Call site superintendent.</i>
        """
    project_p = Paragraph(project_box_content, body_regular)

    # Status badge box
    is_paid = payment_status.upper() == "PAID"
    status_p = Paragraph(
        f"STATUS:<br/><b>{'PAID IN FULL' if is_paid else 'PAYMENT DUE'}</b>",
        status_paid if is_paid else status_unpaid,
    )

    info_table = Table(
        [[bill_to_p, project_p, status_p]],
        colWidths=[2.6 * inch, 2.7 * inch, 2.0 * inch],
    )
    info_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#f0fdf4") if is_paid else colors.HexColor("#fef2f2")),
            ("BOX", (2, 0), (2, 0), 1, colors.HexColor("#86efac") if is_paid else colors.HexColor("#fca5a5")),
            ("PADDING", (2, 0), (2, 0), 8),
            ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ])
    )
    story.append(info_table)
    story.append(Spacer(1, 16))

    # 3. Line Items Table
    table_data = [[
        Paragraph("<b>Item / Description</b>", body_bold),
        Paragraph("<b>Qty</b>", body_bold),
        Paragraph("<b>Unit Price</b>", body_bold),
        Paragraph("<b>Total</b>", body_bold),
    ]]

    subtotal = 0.0
    for desc, qty_str, unit_price, line_total in items:
        subtotal += line_total
        table_data.append([
            Paragraph(desc, body_regular),
            Paragraph(qty_str, body_regular),
            Paragraph(f"{currency_symbol}{unit_price:,.2f}", body_regular),
            Paragraph(f"{currency_symbol}{line_total:,.2f}", body_regular),
        ])

    tax = round(subtotal * 0.0, 2)  # Construction wholesale tax-exempt or pre-calculated
    grand_total = subtotal + tax

    items_table = Table(
        table_data,
        colWidths=[4.2 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch],
    )
    items_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#cbd5e1")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ])
    )
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Totals Table
    balance_due = 0.0 if is_paid else grand_total

    totals_data = [
        [Paragraph("Subtotal:", body_bold), Paragraph(f"{currency_symbol}{subtotal:,.2f}", body_regular)],
        [Paragraph("Tax (Exempt Resale):", body_bold), Paragraph(f"{currency_symbol}{tax:,.2f}", body_regular)],
        [Paragraph("Total Amount:", body_bold), Paragraph(f"<b>{currency_symbol}{grand_total:,.2f}</b>", body_bold)],
    ]

    if is_paid:
        totals_data.append([
            Paragraph("Payment Received:", body_bold),
            Paragraph(f"<font color='#16a34a'><b>-{currency_symbol}{grand_total:,.2f}</b></font>", body_bold),
        ])
        totals_data.append([
            Paragraph("Balance Due:", body_bold),
            Paragraph(f"<b>{currency_symbol}0.00</b>", body_bold),
        ])
    else:
        totals_data.append([
            Paragraph("Balance Due:", body_bold),
            Paragraph(f"<font color='#dc2626'><b>{currency_symbol}{balance_due:,.2f}</b></font>", body_bold),
        ])

    totals_table = Table(totals_data, colWidths=[1.8 * inch, 1.2 * inch], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#cbd5e1")),
        ])
    )
    story.append(totals_table)
    story.append(Spacer(1, 16))

    # 5. Payment details or Notes
    if is_paid and paid_details:
        paid_p = Paragraph(f"<b>PAYMENT RECEIPT CONFIRMATION:</b><br/>{paid_details}", body_regular)
        paid_box = Table([[paid_p]], colWidths=[7.3 * inch])
        paid_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(paid_box)
        story.append(Spacer(1, 10))
    elif notes:
        notes_p = Paragraph(f"<b>REMITTANCE NOTES:</b><br/>{notes}", body_regular)
        notes_box = Table([[notes_p]], colWidths=[7.3 * inch])
        notes_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(notes_box)
        story.append(Spacer(1, 10))

    doc.build(story)
    print(f" Generated PDF invoice: {pdf_path}")
    return pdf_path


def main():
    print("=" * 70)
    print(" Generating Test Invoices for Automation Evaluation")
    print("=" * 70)

    # 1. Unpaid Invoice (Standard happy path with project match)
    build_invoice_pdf(
        filename="1_Apex_Lumber_INV-2026-881_Unpaid.pdf",
        vendor_name="Apex Lumber & Supply Co.",
        vendor_address=[
            "1400 Industrial Way, Bldg C",
            "Portland, OR 97201",
            "Phone: (503) 555-0199",
            "Email: billing@apexlumber.com",
        ],
        doc_ref="INV-2026-881",
        invoice_date="2026-11-18",
        due_date="2026-12-18",
        project_hint="PRJ-101 - Maple Ave Custom Build",
        payment_status="Unpaid",
        items=[
            ("2x6x16 KD Douglas Fir Framing Lumber", "120 pcs", 18.50, 2220.00),
            ("3/4 in. T&G OSB Subfloor Panels (4x8)", "45 sheets", 38.00, 1710.00),
            ("3-1/4 in. 16D Framing Nails (50lb box)", "4 boxes", 85.00, 340.00),
            ("Job Site Flatbed Freight Delivery (Boom Drop)", "1 drop", 580.00, 580.00),
        ],
        currency_symbol="$",
        notes="Net 30 days. Please include invoice number INV-2026-881 on your check or wire transfer. Wire instructions: Bank of the West, Routing #123456789, Acct #987654321.",
    )

    # 2. Paid Update Invoice (Duplicate prevention test - same supplier & doc ref)
    build_invoice_pdf(
        filename="2_Apex_Lumber_INV-2026-881_PAID_Update.pdf",
        vendor_name="Apex Lumber & Supply Co.",
        vendor_address=[
            "1400 Industrial Way, Bldg C",
            "Portland, OR 97201",
            "Phone: (503) 555-0199",
            "Email: billing@apexlumber.com",
        ],
        doc_ref="INV-2026-881",
        invoice_date="2026-11-18",
        due_date="2026-12-18",
        project_hint="PRJ-101 - Maple Ave Custom Build",
        payment_status="Paid",
        items=[
            ("2x6x16 KD Douglas Fir Framing Lumber", "120 pcs", 18.50, 2220.00),
            ("3/4 in. T&G OSB Subfloor Panels (4x8)", "45 sheets", 38.00, 1710.00),
            ("3-1/4 in. 16D Framing Nails (50lb box)", "4 boxes", 85.00, 340.00),
            ("Job Site Flatbed Freight Delivery (Boom Drop)", "1 drop", 580.00, 580.00),
        ],
        currency_symbol="$",
        paid_details="PAID IN FULL via Corporate ACH on 2026-11-20. Auth Ref: ACH-884210. Remaining balance: $0.00. Thank you for your business!",
    )

    # 3. Missing Project / Flagged for Review
    build_invoice_pdf(
        filename="3_Unknown_Vendor_Missing_Project.pdf",
        vendor_name="Metro Concrete Pumping",
        vendor_address=[
            "8800 Highway 26 West",
            "Beaverton, OR 97005",
            "Phone: (503) 555-0812",
            "Email: dispatch@metroconcretepump.com",
        ],
        doc_ref="MCP-404",
        invoice_date="2026-11-19",
        due_date="2026-12-05",
        project_hint="",  # Missing project!
        payment_status="Unpaid",
        items=[
            ("38-Meter Boom Pump Service (4.0 hrs @ $225/hr)", "4.0 hrs", 225.00, 900.00),
            ("Environmental Washout Disposal Fee", "1 ea", 150.00, 150.00),
            ("Extra 5-inch Heavy-Duty Slickline Setup (50ft)", "1 ea", 150.00, 150.00),
        ],
        currency_symbol="$",
        notes="ATTN: Site ticket was signed by crew foreman 'Dave' on-site, but ticket lacked project name or project number. Please remit payment within 15 days.",
    )

    print("\n All 3 test invoice PDFs created successfully in `test_invoices/`!\n")


if __name__ == "__main__":
    main()
