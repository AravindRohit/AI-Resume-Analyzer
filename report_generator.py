from __future__ import annotations

import io
from datetime import datetime
from typing import Any
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand colours ─────────────────────────────────────────────────────────────
DARK_BLUE = colors.HexColor("#0f3460")
ACCENT_RED = colors.HexColor("#e94560")
MID_BLUE = colors.HexColor("#16213e")
LIGHT_GREY = colors.HexColor("#f8f9fa")
GREY = colors.HexColor("#6c757d")
GREEN = colors.HexColor("#28a745")
ORANGE = colors.HexColor("#fd7e14")
RED_SOFT = colors.HexColor("#dc3545")
WHITE = colors.white
BLACK = colors.black

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


def _score_color(score: float) -> colors.Color:
    if score >= 75:
        return GREEN
    if score >= 50:
        return colors.HexColor("#ffc107")
    return RED_SOFT


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontSize=26,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#ccddee"),
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            parent=base["Heading2"],
            fontSize=13,
            textColor=DARK_BLUE,
            spaceBefore=10,
            spaceAfter=4,
            borderPad=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontSize=10,
            textColor=BLACK,
            spaceAfter=4,
            leading=14,
        ),
        "bullet_green": ParagraphStyle(
            "bullet_green",
            parent=base["Normal"],
            fontSize=10,
            textColor=GREEN,
            leftIndent=14,
            spaceAfter=3,
            leading=14,
        ),
        "bullet_red": ParagraphStyle(
            "bullet_red",
            parent=base["Normal"],
            fontSize=10,
            textColor=RED_SOFT,
            leftIndent=14,
            spaceAfter=3,
            leading=14,
        ),
        "bullet_orange": ParagraphStyle(
            "bullet_orange",
            parent=base["Normal"],
            fontSize=10,
            textColor=ORANGE,
            leftIndent=14,
            spaceAfter=3,
            leading=14,
        ),
        "bullet_body": ParagraphStyle(
            "bullet_body",
            parent=base["Normal"],
            fontSize=10,
            textColor=BLACK,
            leftIndent=14,
            spaceAfter=3,
            leading=14,
        ),
        "score_big": ParagraphStyle(
            "score_big",
            parent=base["Normal"],
            fontSize=48,
            textColor=ACCENT_RED,
            alignment=TA_CENTER,
            leading=52,
        ),
        "score_label": ParagraphStyle(
            "score_label",
            parent=base["Normal"],
            fontSize=11,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["Normal"],
            fontSize=8,
            textColor=GREY,
            alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontSize=7,
            textColor=GREY,
            alignment=TA_CENTER,
        ),
        "tag": ParagraphStyle(
            "tag",
            parent=base["Normal"],
            fontSize=9,
            textColor=DARK_BLUE,
            leftIndent=6,
            spaceAfter=2,
        ),
    }


def _divider(color: colors.Color = DARK_BLUE) -> HRFlowable:
    return HRFlowable(width="100%", thickness=1.5, color=color, spaceAfter=6)


def _section_title(text: str, styles: dict) -> list:
    return [
        Paragraph(text, styles["section_header"]),
        _divider(),
    ]


def generate_pdf_report(
    resume_text: str,
    jd_text: str,
    match_score: float,
    skill_overlap: float,
    llm_result: dict[str, Any],
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="SmartResume AI Report",
        author="SmartResume AI",
    )

    styles = _styles()
    story: list = []
    now = datetime.now().strftime("%d %B %Y, %H:%M")

    # ── 1. Header banner ──────────────────────────────────────────────────────
    header_data = [
        [Paragraph("SmartResume AI", styles["title"])],
        [Paragraph("Resume Analyzer & Job Matcher Report", styles["subtitle"])],
        [Paragraph(f"Generated: {now}", styles["subtitle"])],
    ]
    header_table = Table(
        header_data,
        colWidths=[PAGE_W - 2 * MARGIN],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), MID_BLUE),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [MID_BLUE]),
                ("TOPPADDING", (0, 0), (-1, 0), 16),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    # ── 2. Match score card ───────────────────────────────────────────────────
    score_color = _score_color(match_score)
    if match_score >= 75:
        verdict = "Strong Match 🟢"
    elif match_score >= 50:
        verdict = "Moderate Match 🟡"
    else:
        verdict = "Weak Match 🔴"

    score_data = [
        [
            Paragraph(f"{match_score:.1f}%", styles["score_big"]),
            Paragraph(
                f"<b>Overall Match Score</b><br/>{verdict}<br/><br/>"
                f"Semantic Similarity: {match_score:.1f}%<br/>"
                f"Skill Keyword Overlap: {skill_overlap:.1f}%<br/>"
                f"Experience Match: {llm_result.get('experience_match', 'N/A')}<br/>"
                f"Education Match: {llm_result.get('education_match', 'N/A')}<br/>"
                f"Hiring Recommendation: <b>{llm_result.get('hiring_recommendation', 'N/A')}</b>",
                styles["score_label"],
            ),
        ]
    ]
    score_table = Table(score_data, colWidths=[80 * mm, PAGE_W - 2 * MARGIN - 80 * mm])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEAFTER", (0, 0), (0, 0), 1, score_color),
            ]
        )
    )
    story.append(score_table)
    story.append(Spacer(1, 14))

    # ── 3. Executive summary ──────────────────────────────────────────────────
    summary = llm_result.get("summary", "")
    if summary:
        story.extend(_section_title("Executive Summary", styles))
        story.append(Paragraph(summary, styles["body"]))
        story.append(Spacer(1, 8))

    # ── 4. Strengths ──────────────────────────────────────────────────────────
    strengths = llm_result.get("strengths", [])
    story.extend(_section_title("Strengths", styles))
    if strengths:
        for item in strengths:
            story.append(Paragraph(f"{item}", styles["bullet_green"]))
    else:
        story.append(Paragraph("No specific strengths identified for this role.", styles["body"]))
    story.append(Spacer(1, 8))

    # ── 5. Missing skills ─────────────────────────────────────────────────────
    missing = llm_result.get("missing_skills", [])
    story.extend(_section_title("Missing / Skill Gaps", styles))
    if missing:
        for item in missing:
            story.append(Paragraph(f"{item}", styles["bullet_red"]))
    else:
        story.append(Paragraph("No critical skill gaps detected.", styles["body"]))
    story.append(Spacer(1, 8))

    # ── 6. Improvements ───────────────────────────────────────────────────────
    improvements = llm_result.get("improvements", [])
    story.extend(_section_title("Improvement Suggestions", styles))
    if improvements:
        for i, item in enumerate(improvements, start=1):
            story.append(Paragraph(f"{i}. {item}", styles["bullet_orange"]))
    else:
        story.append(Paragraph("No major improvements suggested.", styles["body"]))
    story.append(Spacer(1, 8))

    # ── 7. ATS keywords ───────────────────────────────────────────────────────
    ats_kw = llm_result.get("ats_keywords", [])
    story.extend(_section_title("ATS Keywords to Add", styles))
    if ats_kw:
        # Render as a 4-column table of pills
        rows = [ats_kw[i : i + 4] for i in range(0, len(ats_kw), 4)]
        # Pad last row
        if rows:
            last = rows[-1]
            while len(last) < 4:
                last.append("")
        kw_data = [
            [Paragraph(f"▸ {kw}", styles["tag"]) if kw else "" for kw in row]
            for row in rows
        ]
        kw_table = Table(
            kw_data,
            colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4,
        )
        kw_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(kw_table)
    else:
        story.append(Paragraph("No additional ATS keywords recommended.", styles["body"]))
    story.append(Spacer(1, 12))

    # ── 8. Evaluation metrics table ───────────────────────────────────────────
    story.extend(_section_title("Evaluation Metrics", styles))
    metrics_data = [
        ["Metric", "Value"],
        ["Overall Match Score", f"{match_score:.1f}%"],
        ["Semantic Similarity (Embeddings)", f"{match_score:.1f}%"],
        ["Keyword / Skill Overlap", f"{skill_overlap:.1f}%"],
        ["Experience Match", llm_result.get("experience_match", "N/A")],
        ["Education Match", llm_result.get("education_match", "N/A")],
        ["Hiring Recommendation", llm_result.get("hiring_recommendation", "N/A")],
        ["Resume Word Count", f"~{len(resume_text.split())} words"],
    ]
    metrics_table = Table(
        metrics_data,
        colWidths=[100 * mm, PAGE_W - 2 * MARGIN - 100 * mm],
    )
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(metrics_table)
    story.append(Spacer(1, 16))

    # ── 9. Footer ─────────────────────────────────────────────────────────────
    story.append(_divider(GREY))
    story.append(
        Paragraph(
            "SmartResume AI  •  Generated by llama-3.3-70b-versatile via Groq  •  "
            "sentence-transformers (all-MiniLM-L6-v2)  •  ReportLab  •  PyMuPDF  "
            f"•  {now}",
            styles["footer"],
        )
    )
    story.append(
        Paragraph(
            "This report is AI-generated and intended as a guide only. "
            "Always apply your professional judgment.",
            styles["footer"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
