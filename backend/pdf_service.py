"""
PDF and text export for dental claim narrative packets.
Uses reportlab to build a clean, printable single- or multi-page packet.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)


PRIMARY = HexColor("#4A6B5D")
TEXT = HexColor("#1A1A1A")
MUTED = HexColor("#5E5E5E")
LIGHT_BG = HexColor("#F9F9F8")
BORDER = HexColor("#E5E5E5")
BADGE_BG = HexColor("#EDF2EF")


def _styles():
    ss = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle(
            "h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
            fontSize=18, leading=22, textColor=TEXT, spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=PRIMARY, spaceBefore=10, spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "label": ParagraphStyle(
            "label", parent=ss["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=MUTED, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body", parent=ss["Normal"], fontName="Helvetica",
            fontSize=10, leading=15, textColor=TEXT, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small", parent=ss["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=MUTED,
        ),
        "code": ParagraphStyle(
            "code", parent=ss["Normal"], fontName="Courier-Bold",
            fontSize=10, leading=13, textColor=PRIMARY,
        ),
    }
    return styles


def _header(styles, title="Dental Claim Narrative Packet", subtitle=None):
    flow = [
        Paragraph(title, styles["h1"]),
    ]
    if subtitle:
        flow.append(Paragraph(subtitle, styles["small"]))
    flow.append(Spacer(1, 4))
    flow.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=2, spaceAfter=12))
    return flow


def _meta_table(styles, record):
    rows = [
        [Paragraph("<b>CDT</b>", styles["small"]), Paragraph(record.get("procedure_code", ""), styles["code"]),
         Paragraph("<b>Category</b>", styles["small"]), Paragraph(record.get("category", ""), styles["body"])],
        [Paragraph("<b>Procedure</b>", styles["small"]), Paragraph(record.get("procedure_name", ""), styles["body"]),
         Paragraph("<b>Tooth #</b>", styles["small"]), Paragraph(record.get("tooth_number") or "—", styles["body"])],
    ]
    if record.get("patient_label") or record.get("carrier"):
        rows.append([
            Paragraph("<b>Patient</b>", styles["small"]),
            Paragraph(record.get("patient_label") or "—", styles["body"]),
            Paragraph("<b>Carrier</b>", styles["small"]),
            Paragraph((record.get("carrier") or "generic").title(), styles["body"]),
        ])
    tbl = Table(rows, colWidths=[0.7 * inch, 2.8 * inch, 0.7 * inch, 2.3 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _narrative_flow(styles, record):
    flow = []
    flow.append(_meta_table(styles, record))
    flow.append(Spacer(1, 8))

    flow.append(Paragraph("SHORT NARRATIVE", styles["h2"]))
    flow.append(Paragraph((record.get("short_narrative") or "").replace("\n", "<br/>"), styles["body"]))

    flow.append(Paragraph("LONG NARRATIVE", styles["h2"]))
    flow.append(Paragraph((record.get("long_narrative") or "").replace("\n", "<br/>"), styles["body"]))

    rads = record.get("radiographs") or {}
    required = rads.get("required") or []
    recommended = rads.get("recommended") or []
    note = rads.get("note") or ""
    if required or recommended or note:
        flow.append(Paragraph("RADIOGRAPHS", styles["h2"]))
        if required:
            flow.append(Paragraph(f"<b>Required:</b> {', '.join(required)}", styles["body"]))
        if recommended:
            flow.append(Paragraph(f"<b>Recommended:</b> {', '.join(recommended)}", styles["body"]))
        if note:
            flow.append(Paragraph(f"<i>{note}</i>", styles["small"]))
    return flow


def build_pdf(record: dict, office_name: str = "Dental Office") -> bytes:
    """Build a single-narrative PDF packet. Returns bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title=f"Claim Narrative {record.get('procedure_code', '')}",
    )
    styles = _styles()
    date_str = datetime.now().strftime("%B %d, %Y")
    subtitle = f"{office_name} · Generated {date_str}"
    flow = _header(styles, subtitle=subtitle) + _narrative_flow(styles, record)
    doc.build(flow)
    return buf.getvalue()


def build_visit_pdf(visit: dict, office_name: str = "Dental Office") -> bytes:
    """Build a multi-procedure visit PDF packet. Returns bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title=f"Visit Claim Packet {visit.get('id', '')[:8]}",
    )
    styles = _styles()
    date_str = datetime.now().strftime("%B %d, %Y")
    parts = [
        f"{office_name}",
        f"Patient: {visit.get('patient_label') or '—'}",
        f"Carrier: {(visit.get('carrier') or 'generic').title()}",
        f"Date of service: {visit.get('date_of_service') or '—'}",
        f"Generated {date_str}",
    ]
    subtitle = " · ".join(parts)
    flow = _header(styles, title="Multi-Procedure Visit Claim Packet", subtitle=subtitle)

    if visit.get("visit_notes"):
        flow.append(Paragraph("VISIT NOTES", styles["h2"]))
        flow.append(Paragraph(visit["visit_notes"], styles["body"]))
        flow.append(Spacer(1, 8))

    records = visit.get("records") or []
    for i, rec in enumerate(records):
        if i > 0:
            flow.append(Spacer(1, 12))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=4, spaceAfter=10))
        flow.append(Paragraph(
            f"PROCEDURE {i + 1} OF {len(records)}",
            ParagraphStyle("p", parent=styles["small"], fontName="Helvetica-Bold", textColor=PRIMARY),
        ))
        flow.extend(_narrative_flow(styles, rec))

    doc.build(flow)
    return buf.getvalue()


def build_txt(record: dict) -> str:
    """Build a plain-text version of a single narrative packet."""
    lines = [
        "DENTAL CLAIM NARRATIVE PACKET",
        f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}",
        "-" * 60,
        f"CDT Code:     {record.get('procedure_code', '')}",
        f"Procedure:    {record.get('procedure_name', '')}",
        f"Category:     {record.get('category', '')}",
        f"Tooth #:      {record.get('tooth_number') or '—'}",
        f"Patient:      {record.get('patient_label') or '—'}",
        f"Carrier:      {(record.get('carrier') or 'generic').title()}",
        "",
        "SHORT NARRATIVE",
        "-" * 60,
        record.get("short_narrative", ""),
        "",
        "LONG NARRATIVE",
        "-" * 60,
        record.get("long_narrative", ""),
        "",
    ]
    rads = record.get("radiographs") or {}
    if rads.get("required") or rads.get("recommended") or rads.get("note"):
        lines.extend([
            "RADIOGRAPHS",
            "-" * 60,
            f"Required:    {', '.join(rads.get('required') or []) or '—'}",
            f"Recommended: {', '.join(rads.get('recommended') or []) or '—'}",
        ])
        if rads.get("note"):
            lines.append(f"Note:        {rads['note']}")
    return "\n".join(lines) + "\n"


def build_visit_txt(visit: dict) -> str:
    lines = [
        "MULTI-PROCEDURE VISIT CLAIM PACKET",
        f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}",
        f"Patient:   {visit.get('patient_label') or '—'}",
        f"Carrier:   {(visit.get('carrier') or 'generic').title()}",
        f"Date of service: {visit.get('date_of_service') or '—'}",
        "=" * 60,
    ]
    if visit.get("visit_notes"):
        lines += ["", "VISIT NOTES", "-" * 60, visit["visit_notes"], ""]
    for i, rec in enumerate(visit.get("records") or []):
        lines.append("")
        lines.append(f"PROCEDURE {i + 1}: {rec.get('procedure_code', '')} — {rec.get('procedure_name', '')}")
        lines.append("=" * 60)
        lines.append(build_txt(rec))
    return "\n".join(lines)


def build_appeal_pdf(appeal: dict, office_name: str = "Dental Office") -> bytes:
    """Build a formal appeal letter PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=f"Appeal Letter {appeal.get('id', '')[:8]}",
    )
    styles = _styles()
    date_str = datetime.now().strftime("%B %d, %Y")
    subtitle_parts = [f"{office_name}", f"Prepared {date_str}"]
    if appeal.get("subject_line"):
        subtitle_parts.append(appeal["subject_line"])
    subtitle = " · ".join(subtitle_parts)
    flow = _header(styles, title="Formal Claim Appeal Letter", subtitle=subtitle)

    letter = appeal.get("letter") or ""
    # Preserve paragraph breaks
    for para in letter.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        flow.append(Paragraph(para.replace("\n", "<br/>"), styles["body"]))
        flow.append(Spacer(1, 6))

    # Reference narrative footer
    if appeal.get("procedure_code") or appeal.get("procedure_name"):
        flow.append(Spacer(1, 12))
        flow.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=4, spaceAfter=8))
        flow.append(Paragraph("REFERENCE NARRATIVE", styles["h2"]))
        meta_bits = []
        if appeal.get("procedure_code"):
            meta_bits.append(f"CDT {appeal['procedure_code']}")
        if appeal.get("procedure_name"):
            meta_bits.append(appeal["procedure_name"])
        if appeal.get("tooth_number"):
            meta_bits.append(f"Tooth #{appeal['tooth_number']}")
        if appeal.get("carrier"):
            meta_bits.append(f"Carrier: {appeal['carrier'].title()}")
        flow.append(Paragraph(" · ".join(meta_bits), styles["small"]))
        flow.append(Spacer(1, 6))
        if appeal.get("original_long_narrative"):
            flow.append(Paragraph(appeal["original_long_narrative"], styles["body"]))
        if appeal.get("denial_reason"):
            flow.append(Spacer(1, 6))
            flow.append(Paragraph(f"<b>Carrier denial reason:</b> {appeal['denial_reason']}", styles["small"]))

    doc.build(flow)
    return buf.getvalue()


def build_appeal_txt(appeal: dict) -> str:
    parts = [
        "FORMAL CLAIM APPEAL LETTER",
        f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}",
    ]
    if appeal.get("subject_line"):
        parts.append(f"Subject: {appeal['subject_line']}")
    parts.append("=" * 60)
    parts.append("")
    parts.append(appeal.get("letter") or "")
    parts.append("")
    if appeal.get("procedure_code"):
        parts.append("-" * 60)
        parts.append("REFERENCE NARRATIVE")
        parts.append(f"CDT: {appeal.get('procedure_code', '')} — {appeal.get('procedure_name', '')}")
        if appeal.get("tooth_number"):
            parts.append(f"Tooth: #{appeal['tooth_number']}")
        if appeal.get("carrier"):
            parts.append(f"Carrier: {appeal['carrier'].title()}")
        if appeal.get("original_long_narrative"):
            parts.append("")
            parts.append(appeal["original_long_narrative"])
        if appeal.get("denial_reason"):
            parts.append("")
            parts.append(f"Carrier denial reason: {appeal['denial_reason']}")
    return "\n".join(parts) + "\n"
