import io
from app.models import Payment
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_invoice_pdf(invoice) -> io.BytesIO:
    """Generates a professional, print-ready PDF invoice using ReportLab.
    
    Returns an in-memory BytesIO buffer ready for streaming.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
    )
    
    business_name_style = ParagraphStyle(
        "BusinessName",
        parent=styles["Normal"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
    )
    
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
        fontName="Helvetica",
    )
    
    meta_value = ParagraphStyle(
        "MetaValue",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#ffffff"),
        fontName="Helvetica-Bold",
    )

    elements = []

    # 1. Header: Business Info (Left) & Invoice Title / Status (Right)
    user = invoice.user
    client = invoice.client
    business_name = user.business_name or user.name or "Freelancer"
    user_email = user.email or ""

    status_color = {
        "paid": "#16a34a",
        "partially_paid": "#d97706",
        "sent": "#2563eb",
        "draft": "#64748b",
        "cancelled": "#dc2626",
    }.get(invoice.status, "#64748b")

    status_text = invoice.status.replace("_", " ").upper()

    header_data = [
        [
            Paragraph(f"<b>{business_name}</b><br/>{user_email}", business_name_style),
            Paragraph(
                f'<font color="#0f172a" size="20"><b>INVOICE</b></font><br/>'
                f'<font color="{status_color}" size="11"><b>[ {status_text} ]</b></font>',
                ParagraphStyle("RightHeader", parent=styles["Normal"], alignment=2),
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=15))

    # 2. Bill To & Invoice Meta Details
    bill_to_html = f"""
    <font color="#64748b" size="9"><b>BILLED TO:</b></font><br/>
    <font size="12" color="#0f172a"><b>{client.name if client else 'N/A'}</b></font><br/>
    <font color="#475569" size="10">{client.email if client else ''}</font>
    """

    meta_html = f"""
    <table width="100%">
        <tr>
            <td align="right"><font color="#64748b" size="9"><b>INVOICE NUMBER:</b></font></td>
            <td align="right"><font color="#0f172a" size="10"><b>#{invoice.invoice_number}</b></font></td>
        </tr>
        <tr>
            <td align="right"><font color="#64748b" size="9"><b>ISSUE DATE:</b></font></td>
            <td align="right"><font color="#0f172a" size="10">{invoice.issue_date}</font></td>
        </tr>
        <tr>
            <td align="right"><font color="#64748b" size="9"><b>DUE DATE:</b></font></td>
            <td align="right"><font color="#0f172a" size="10"><b>{invoice.due_date}</b></font></td>
        </tr>
    </table>
    """

    info_data = [
        [
            Paragraph(bill_to_html, body_style),
            Paragraph(meta_html, ParagraphStyle("MetaRight", parent=styles["Normal"], alignment=2)),
        ]
    ]
    info_table = Table(info_data, colWidths=[300, 240])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # 3. Line Items Table
    description = invoice.description or "Professional Services Rendered"
    items_data = [
        [
            Paragraph("<b>DESCRIPTION</b>", table_header_style),
            Paragraph("<b>AMOUNT</b>", ParagraphStyle("HeaderAmt", parent=table_header_style, alignment=2)),
        ],
        [
            Paragraph(description.replace("\n", "<br/>"), body_style),
            Paragraph(f"<b>{invoice.currency} {invoice.amount:,.2f}</b>", ParagraphStyle("RowAmt", parent=body_style, alignment=2)),
        ],
    ]

    items_table = Table(items_data, colWidths=[400, 140])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 15))

    # 4. Payments breakdown (if any)
    payments_list = list(invoice.payments.order_by(Payment.paid_on).all())
    if payments_list:
        pay_rows = [
            [
                Paragraph("<b>Payment Date</b>", ParagraphStyle("PH", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=colors.HexColor("#475569"))),
                Paragraph("<b>Notes / Method</b>", ParagraphStyle("PH2", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=colors.HexColor("#475569"))),
                Paragraph("<b>Amount Paid</b>", ParagraphStyle("PH3", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=colors.HexColor("#475569"), alignment=2)),
            ]
        ]
        for p in payments_list:
            method_desc = (p.method or "Payment").upper()
            if p.reference:
                method_desc += f" (Ref: {p.reference})"
            pay_rows.append([
                Paragraph(str(p.paid_on), meta_label),
                Paragraph(method_desc, meta_label),
                Paragraph(f"<font color='#16a34a'>-{invoice.currency} {p.amount:,.2f}</font>", ParagraphStyle("PVal", parent=meta_label, alignment=2)),
            ])
        pay_table = Table(pay_rows, colWidths=[120, 280, 140])
        pay_table.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#cbd5e1")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(Paragraph("<font size='10' color='#1e293b'><b>Recorded Payments:</b></font>", body_style))
        elements.append(Spacer(1, 4))
        elements.append(pay_table)
        elements.append(Spacer(1, 15))

    # 5. Financial Summary / Totals
    balance_color = "#dc2626" if invoice.balance_due > 0 else "#16a34a"
    summary_data = [
        [
            Paragraph("Total Amount:", ParagraphStyle("S1", parent=styles["Normal"], alignment=2, textColor=colors.HexColor("#64748b"))),
            Paragraph(f"<b>{invoice.currency} {invoice.amount:,.2f}</b>", ParagraphStyle("S2", parent=styles["Normal"], alignment=2, textColor=colors.HexColor("#0f172a"))),
        ],
        [
            Paragraph("Total Paid:", ParagraphStyle("S3", parent=styles["Normal"], alignment=2, textColor=colors.HexColor("#64748b"))),
            Paragraph(f"<b>{invoice.currency} {invoice.total_paid:,.2f}</b>", ParagraphStyle("S4", parent=styles["Normal"], alignment=2, textColor=colors.HexColor("#16a34a"))),
        ],
        [
            Paragraph("<b>Balance Due:</b>", ParagraphStyle("S5", parent=styles["Normal"], alignment=2, fontSize=12, textColor=colors.HexColor("#0f172a"))),
            Paragraph(f"<b><font size='13' color='{balance_color}'>{invoice.currency} {invoice.balance_due:,.2f}</font></b>", ParagraphStyle("S6", parent=styles["Normal"], alignment=2)),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[400, 140])
    summary_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#cbd5e1")),
    ]))
    elements.append(KeepTogether([summary_table]))

    # 6. Footer / Notes
    elements.append(Spacer(1, 40))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=10))
    footer_text = f"""
    <font color="#94a3b8" size="8">
    Thank you for your business. For any queries regarding this invoice, please reach out to {user_email}.<br/>
    Generated by InvoiceTrail SaaS platform.
    </font>
    """
    elements.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=styles["Normal"], alignment=1)))

    doc.build(elements)
    buffer.seek(0)
    return buffer
