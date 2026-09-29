"""Deterministic ATS single-column PDF generator using ReportLab."""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.schemas.rendering import DeterministicResumeDocument


class ATSPdfRenderer:
    """Renders a structured, validated DeterministicResumeDocument into an ATS-safe single-column PDF."""

    def __init__(self, doc: DeterministicResumeDocument) -> None:
        self.doc = doc
        self.config = doc.config

    def render_pdf_bytes(self) -> bytes:
        """Produces deterministic PDF binary bytes with selectable text and standard typography."""
        buffer = io.BytesIO()

        # Convert inch margins to points (72 points per inch)
        margin_pts = self.config.margins_inch * 72.0

        pdf = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=margin_pts,
            rightMargin=margin_pts,
            topMargin=margin_pts,
            bottomMargin=margin_pts,
            title=f"{self.doc.header.name} - Resume",
            author=self.doc.header.name,
        )

        styles = getSampleStyleSheet()

        font_name = "Helvetica" if self.config.font_family.lower() == "helvetica" else "Times-Roman"
        font_bold = "Helvetica-Bold" if font_name == "Helvetica" else "Times-Bold"

        # Styles
        name_style = ParagraphStyle(
            "ATS_Name",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=18,
            leading=22,
            alignment=1,  # Centered
            textColor=HexColor("#111827"),
            spaceAfter=3,
        )

        contact_style = ParagraphStyle(
            "ATS_Contact",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=1,  # Centered
            textColor=HexColor("#4B5563"),
            spaceAfter=8,
        )

        heading_style = ParagraphStyle(
            "ATS_SectionHeading",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=self.config.heading_size_pt,
            leading=self.config.heading_size_pt + 3,
            textColor=HexColor("#1F2937"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        )

        item_title_style = ParagraphStyle(
            "ATS_ItemTitle",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=self.config.font_size_pt + 0.5,
            leading=self.config.font_size_pt + 3,
            textColor=HexColor("#111827"),
            spaceBefore=4,
            spaceAfter=2,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "ATS_Body",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=self.config.font_size_pt,
            leading=int(self.config.font_size_pt * self.config.line_spacing + 2),
            textColor=HexColor("#374151"),
            spaceAfter=3,
        )

        bullet_style = ParagraphStyle(
            "ATS_Bullet",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=self.config.font_size_pt,
            leading=int(self.config.font_size_pt * self.config.line_spacing + 2),
            leftIndent=14,
            firstLineIndent=-10,
            textColor=HexColor("#374151"),
            spaceAfter=2,
        )

        story: list = []

        # 1. Candidate Header Block
        story.append(Paragraph(escape(self.doc.header.name), name_style))

        contact_parts: list[str] = [self.doc.header.email]
        if self.doc.header.phone:
            contact_parts.append(self.doc.header.phone)
        if self.doc.header.location:
            contact_parts.append(self.doc.header.location)
        if self.doc.header.linkedin:
            contact_parts.append(self.doc.header.linkedin)
        if self.doc.header.github:
            contact_parts.append(self.doc.header.github)
        if self.doc.header.portfolio:
            contact_parts.append(self.doc.header.portfolio)

        contact_line = " | ".join(escape(p) for p in contact_parts)
        story.append(Paragraph(contact_line, contact_style))

        if self.config.show_dividers:
            story.append(HRFlowable(width="100%", thickness=0.75, color=HexColor("#D1D5DB"), spaceAfter=6))

        # 2. Section Blocks
        for section in self.doc.sections:
            if not section.items:
                continue

            # Section Heading
            story.append(Paragraph(escape(section.heading.upper()), heading_style))
            if self.config.show_dividers:
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=4))

            # Section Items
            for item in section.items:
                if item.title:
                    story.append(Paragraph(escape(item.title), item_title_style))

                if item.raw_text:
                    story.append(Paragraph(escape(item.raw_text), body_style))

                for bullet in item.bullets:
                    bullet_text = f"&bull; {escape(bullet)}"
                    story.append(Paragraph(bullet_text, bullet_style))

            story.append(Spacer(1, 4))

        pdf.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
