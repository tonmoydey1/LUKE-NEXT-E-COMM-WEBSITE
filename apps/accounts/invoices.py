from io import BytesIO

from django.utils import timezone


def premium_invoice_number(payment):
    return f"PINV-{payment.transaction_id}"


def money(value):
    return f"Rs. {value:,.2f}"


def latest_membership_for_payment(payment):
    return (
        payment.user.memberships.filter(plan=payment.plan, amount=payment.amount, created_at__gte=payment.created_at)
        .order_by("created_at")
        .first()
        or payment.user.memberships.filter(plan=payment.plan, amount=payment.amount).order_by("-created_at").first()
    )


def render_premium_invoice_pdf(payment):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return (
            b"%PDF-1.4\n"
            b"1 0 obj<<>>endobj\n"
            b"2 0 obj<</Length 72>>stream\nBT /F1 18 Tf 72 720 Td (LuxeNest Premium invoice requires reportlab) Tj ET\nendstream endobj\n"
            b"trailer<<>>\n%%EOF"
        )

    membership = latest_membership_for_payment(payment)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=34, leftMargin=34, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandWhite", parent=styles["Title"], textColor=colors.white, fontSize=30, leading=34))
    styles.add(ParagraphStyle(name="White", parent=styles["Normal"], textColor=colors.white, fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="Muted", parent=styles["Normal"], textColor=colors.HexColor("#667085"), fontSize=9, leading=13))
    styles.add(ParagraphStyle(name="Heading", parent=styles["Heading2"], textColor=colors.HexColor("#062F69"), fontSize=14, leading=18))

    customer = payment.user.get_full_name() or payment.user.username
    invoice_no = premium_invoice_number(payment)
    plan_label = payment.get_plan_display()
    issued_on = timezone.localtime(payment.updated_at or payment.created_at)
    start_date = membership.starts_at.strftime("%d %b %Y") if membership else issued_on.strftime("%d %b %Y")
    expiry_date = membership.expires_at.strftime("%d %b %Y") if membership else "Pending activation"

    header = Table(
        [
            [
                Paragraph("LuxeNest Premium", styles["BrandWhite"]),
                Paragraph(
                    f"<b>Premium Tax Invoice</b><br/>{invoice_no}<br/>Transaction: {payment.transaction_id}<br/>Issued: {issued_on:%d %b %Y}",
                    styles["White"],
                ),
            ]
        ],
        colWidths=[305, 210],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#062F69")),
                ("LINEBELOW", (0, 0), (-1, -1), 5, colors.HexColor("#D7A928")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 16),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )

    details = Table(
        [
            [
                Paragraph(f"<b>Member</b><br/>{customer}<br/>{payment.user.email}", styles["Normal"]),
                Paragraph(f"<b>Plan</b><br/>{plan_label}<br/>Valid: {start_date} to {expiry_date}", styles["Normal"]),
                Paragraph(f"<b>Payment</b><br/>{payment.method.upper()}<br/>{payment.get_status_display()}", styles["Normal"]),
            ]
        ],
        colWidths=[175, 220, 120],
    )
    details.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFF")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DCE7F5")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5EAF3")),
                ("PADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    rows = [
        ["Description", "Membership ID", "Amount"],
        [Paragraph(f"LuxeNest Premium {plan_label} membership", styles["Normal"]), payment.provider_payment_id or payment.transaction_id, money(payment.amount)],
        ["", "Grand Total", money(payment.amount)],
    ]
    item_table = Table(rows, colWidths=[265, 150, 100])
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B4AA2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5EAF3")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFF6D8")),
                ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, -1), (-1, -1), colors.HexColor("#062F69")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("PADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    benefits = Table(
        [
            [
                Paragraph(
                    "<b>Premium benefits included</b><br/>Priority delivery messaging, premium-only offers, early access deals, invoice priority, and the LuxeNest Premium Member badge.",
                    styles["Muted"],
                )
            ]
        ],
        colWidths=[515],
    )
    benefits.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFF")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DCE7F5")),
                ("PADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    story = [header, Spacer(1, 16), details, Spacer(1, 18), Paragraph("Premium Subscription Summary", styles["Heading"]), Spacer(1, 8), item_table, Spacer(1, 18), benefits]
    doc.build(story)
    return buffer.getvalue()


def send_premium_invoice_email(payment):
    from apps.orders.services import send_luxe_email

    pdf = render_premium_invoice_pdf(payment)
    return send_luxe_email(
        "Your LuxeNest Premium invoice",
        payment.user.email,
        "emails/premium_invoice.html",
        {"payment": payment, "invoice_no": premium_invoice_number(payment), "membership": latest_membership_for_payment(payment)},
        attachments=[(f"{premium_invoice_number(payment)}.pdf", pdf, "application/pdf")],
    )
