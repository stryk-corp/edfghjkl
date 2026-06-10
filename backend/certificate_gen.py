"""
Certificate Generator
─────────────────────
Generates a PDF clearance certificate with an embedded QR code.
Uses ReportLab for PDF and the qrcode library for the QR image.
"""
import os, uuid
from datetime import datetime
from pathlib import Path
from io import BytesIO
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, Image as RLImage)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from dotenv import load_dotenv

load_dotenv()

CERT_DIR = os.getenv("CERT_DIR", "certificates")
UNIVERSITY = os.getenv("UNIVERSITY_NAME", "University of Nigeria")
SHORT = os.getenv("UNIVERSITY_SHORTNAME", "UNN")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

os.makedirs(CERT_DIR, exist_ok=True)


def _qr_image(data: str, size_cm: float = 4.5) -> RLImage:
    """Generate an in-memory QR code and return a ReportLab Image."""
    qr = qrcode.QRCode(version=2, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a2e4a", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    px = size_cm * cm
    return RLImage(buf, width=px, height=px)


def generate_certificate(
    certificate_code: str,
    student_name: str,
    matric_number: str,
    department: str,
    faculty: str,
    graduation_year: int,
) -> str:
    """
    Generate a PDF certificate and return the file path.
    The QR code encodes the public verification URL.
    """
    filename = f"{certificate_code}.pdf"
    filepath = os.path.join(CERT_DIR, filename)
    verify_url = f"{BASE_URL}/verify/{certificate_code}"

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=colors.HexColor("#1a2e4a"),
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#4a6fa5"),
        spaceAfter=2, alignment=TA_CENTER
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#222222"),
        leading=18, alignment=TA_LEFT
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#666666"), fontName="Helvetica"
    )
    value_style = ParagraphStyle(
        "Value", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#111111"), fontName="Helvetica-Bold"
    )
    code_style = ParagraphStyle(
        "Code", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER, fontName="Courier"
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────
    story.append(Paragraph(UNIVERSITY.upper(), title_style))
    story.append(Paragraph("Office of the Registrar — Student Clearance Division", sub_style))
    story.append(Spacer(1, 0.4*cm))

    # Horizontal rule
    story.append(Table(
        [[""]],
        colWidths=[17*cm],
        style=TableStyle([
            ("LINEBELOW", (0,0), (-1,-1), 2, colors.HexColor("#1a2e4a")),
        ])
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── Certificate title ─────────────────────────────────────────────
    story.append(Paragraph("FINAL YEAR CLEARANCE CERTIFICATE", title_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"This is to certify that the student named below has successfully completed all "
        f"clearance requirements for the {graduation_year} graduating class.",
        body_style
    ))
    story.append(Spacer(1, 0.6*cm))

    # ── Student details table ─────────────────────────────────────────
    detail_data = [
        [Paragraph("FULL NAME", label_style),    Paragraph(student_name.upper(), value_style)],
        [Paragraph("MATRIC NUMBER", label_style), Paragraph(matric_number, value_style)],
        [Paragraph("DEPARTMENT", label_style),   Paragraph(department, value_style)],
        [Paragraph("FACULTY", label_style),      Paragraph(faculty, value_style)],
        [Paragraph("GRADUATION YEAR", label_style), Paragraph(str(graduation_year), value_style)],
        [Paragraph("DATE ISSUED", label_style),  Paragraph(
            datetime.utcnow().strftime("%d %B %Y"), value_style)],
    ]
    detail_table = Table(detail_data, colWidths=[4*cm, 11*cm])
    detail_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#f4f7fc"), colors.white]),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [4]),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 0.6*cm))

    # ── QR + certificate code side by side ────────────────────────────
    qr_img = _qr_image(verify_url)
    qr_cell_data = [[
        qr_img,
        Paragraph(
            f"<b>Certificate Code</b><br/><font name='Courier' size='13'>"
            f"{certificate_code}</font><br/><br/>"
            f"<font size='8' color='#666666'>Scan the QR code or visit:<br/>"
            f"{verify_url}</font>",
            body_style
        )
    ]]
    qr_table = Table(qr_cell_data, colWidths=[5.5*cm, 11.5*cm])
    qr_table.setStyle(TableStyle([
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("BOX",          (0,0), (-1,-1), 1, colors.HexColor("#dce6f2")),
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#f9fbff")),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [6]),
    ]))
    story.append(qr_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Footer ────────────────────────────────────────────────────────
    story.append(Table(
        [[""]],
        colWidths=[17*cm],
        style=TableStyle([
            ("LINEABOVE", (0,0), (-1,-1), 1, colors.HexColor("#cccccc")),
        ])
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"This document was generated electronically by the {SHORT} Digital Clearance System. "
        f"It is valid without a physical signature. Verify authenticity at: {verify_url}",
        code_style
    ))

    doc.build(story)
    return filepath
