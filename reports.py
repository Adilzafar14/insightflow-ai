import io
import pandas as pd
from datetime import datetime

def generate_pdf_report(client_name, industry, kpis, insights, df):
    """Generate PDF report for client dashboard"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        # Colors
        DARK = HexColor('#0A0F1E')
        BLUE = HexColor('#388BFD')
        GREEN = HexColor('#3FB950')
        YELLOW = HexColor('#D29922')
        RED = HexColor('#F85149')
        GRAY = HexColor('#8B949E')
        LIGHT = HexColor('#E6EDF3')
        DARK2 = HexColor('#161B22')

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle('title',
            fontSize=20, fontName='Helvetica-Bold',
            textColor=BLUE, alignment=TA_CENTER, spaceAfter=12)

        subtitle_style = ParagraphStyle('subtitle',
            fontSize=11, fontName='Helvetica',
            textColor=GRAY, alignment=TA_CENTER, spaceAfter=12)

        section_style = ParagraphStyle('section',
            fontSize=13, fontName='Helvetica-Bold',
            textColor=BLUE, spaceBefore=16, spaceAfter=8)

        body_style = ParagraphStyle('body',
            fontSize=10, fontName='Helvetica',
            textColor=black, spaceAfter=6, leading=14)

        kpi_label_style = ParagraphStyle('kpi_label',
            fontSize=8, fontName='Helvetica',
            textColor=GRAY, alignment=TA_CENTER)

        kpi_value_style = ParagraphStyle('kpi_value',
            fontSize=16, fontName='Helvetica-Bold',
            textColor=BLUE, alignment=TA_CENTER)

        story = []

        # ── HEADER ──────────────────────────────────────────
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("InsightFlow AI", title_style))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("Data Analytics Report", subtitle_style))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(Spacer(1, 0.5*cm))

        # Client info table
        ind_icons = {"hospital": "🏥", "ecommerce": "🛒", "logistics": "🚚", "education": "🎓", "generic": "📊"}
        info_data = [
            ["Client:", client_name, "Industry:", industry.title()],
            ["Date:", datetime.now().strftime("%d %B %Y"), "Records:", f"{len(df):,}"],
        ]
        info_table = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('TEXTCOLOR', (0,0), (0,-1), GRAY),
            ('TEXTCOLOR', (2,0), (2,-1), GRAY),
            ('TEXTCOLOR', (1,0), (1,-1), black),
            ('TEXTCOLOR', (3,0), (3,-1), black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))

        # ── KPI CARDS ────────────────────────────────────────
        story.append(Paragraph("Key Performance Indicators", section_style))

        kpi_items = [(k, v) for k, v in kpis.items() if v is not None and isinstance(v, (int, float))][:6]
        if kpi_items:
            # Format values
            def fmt_kpi(k, v):
                if any(x in k.lower() for x in ["revenue", "cost", "fee", "fuel"]):
                    if v >= 1e7: return f"Rs {v/1e7:.2f}Cr"
                    elif v >= 1e5: return f"Rs {v/1e5:.1f}L"
                    else: return f"Rs {v:,.0f}"
                elif any(x in k.lower() for x in ["rate", "%", "discount"]):
                    return f"{v:.1f}%"
                elif "days" in k.lower() or "cgpa" in k.lower():
                    return f"{v:.1f}"
                else:
                    return f"{int(v):,}"

            # Create KPI table (3 per row)
            kpi_rows = []
            for i in range(0, len(kpi_items), 3):
                chunk = kpi_items[i:i+3]
                label_row = []
                value_row = []
                for k, v in chunk:
                    label_row.append(Paragraph(k, kpi_label_style))
                    value_row.append(Paragraph(fmt_kpi(k, v), kpi_value_style))
                # Pad to 3
                while len(label_row) < 3:
                    label_row.append(Paragraph("", kpi_label_style))
                    value_row.append(Paragraph("", kpi_value_style))
                kpi_rows.append(label_row)
                kpi_rows.append(value_row)
                kpi_rows.append([Spacer(1, 0.2*cm)]*3)

            kpi_table = Table(kpi_rows, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), HexColor('#F8F9FA')),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor('#DEE2E6')),
                ('ROWBACKGROUND', (0,0), (-1,-1), [HexColor('#F8F9FA'), white]),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(kpi_table)

        # String KPIs
        str_kpis = [(k, v) for k, v in kpis.items() if isinstance(v, str)]
        if str_kpis:
            story.append(Spacer(1, 0.3*cm))
            for k, v in str_kpis[:4]:
                story.append(Paragraph(f"<b>{k}:</b> {v}", body_style))

        # ── INSIGHTS ─────────────────────────────────────────
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("Business Insights", section_style))

        for tp, txt in insights:
            # Clean markdown
            clean = txt.replace("**", "").replace("*", "")
            color = GREEN if tp == "good" else RED if tp == "danger" else YELLOW if tp == "warn" else BLUE
            style = ParagraphStyle('ins',
                fontSize=9, fontName='Helvetica',
                textColor=black, spaceAfter=4,
                leftIndent=10, leading=13,
                borderPad=4)
            story.append(Paragraph(f"• {clean}", style))

        # ── DATA SUMMARY ─────────────────────────────────────
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("Data Summary", section_style))

        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            desc = df[num_cols[:6]].describe().round(1)
            table_data = [[""] + list(desc.columns)]
            for idx in desc.index:
                row = [str(idx)] + [str(x) for x in desc.loc[idx]]
                table_data.append(row)

            col_w = [2*cm] + [2.5*cm] * min(len(num_cols[:6]), 6)
            summary_table = Table(table_data, colWidths=col_w)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), BLUE),
                ('TEXTCOLOR', (0,0), (-1,0), white),
                ('BACKGROUND', (0,0), (0,-1), HexColor('#F0F0F0')),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('ALIGN', (1,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor('#DEE2E6')),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('ROWBACKGROUND', (0,1), (-1,-1), [white, HexColor('#F8F9FA')]),
            ]))
            story.append(summary_table)

        # ── FOOTER ───────────────────────────────────────────
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
        story.append(Spacer(1, 0.2*cm))
        footer_style = ParagraphStyle('footer',
            fontSize=8, fontName='Helvetica',
            textColor=GRAY, alignment=TA_CENTER)
        story.append(Paragraph(
            f"Generated by InsightFlow AI | {datetime.now().strftime('%d %B %Y %I:%M %p')} | insightflow-adil.streamlit.app",
            footer_style))
        story.append(Paragraph(
            "Lucknow Ki Data Analytics Agency | Confidential Report",
            footer_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        return None, str(e)
