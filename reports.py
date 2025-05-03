import plotly.graph_objects as go
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import logging
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_ats_chart(analysis):
    """Generate a doughnut pie chart for ATS score"""
    try:
        ats_score = analysis.get('ats_score', 0)
        remaining = 100 - ats_score
        
        fig = go.Figure(data=[
            go.Pie(
                values=[ats_score, remaining],
                labels=['ATS Score', 'Remaining'],
                hole=0.4,
                marker=dict(colors=['#4CAF50', '#D3D3D3']),
                textinfo='percent+label',
                textfont=dict(size=14, color='#2E7D32')
            )
        ])
        
        fig.update_layout(
            title=dict(
                text="ATS Score",
                font=dict(size=18, color='#2E7D32'),
                x=0.5,
                xanchor='center'
            ),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2E7D32'),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        
        logger.debug("ATS chart generated successfully")
        return fig
    except Exception as e:
        logger.error(f"Failed to generate ATS chart: {e}")
        raise

def generate_pdf_report(analysis, recommendations):
    """Generate a PDF report with resume analysis and recommendations"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("Resume Analysis Report", styles['Title']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph(f"ATS Score: {analysis.get('ats_score', 0):.2f}", styles['Normal']))
        story.append(Paragraph(f"Word Count: {analysis.get('word_count', 0)}", styles['Normal']))
        story.append(Paragraph(f"Skills Detected: {', '.join(analysis.get('skills', []))}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("Recommendations", styles['Heading2']))
        story.append(Paragraph(recommendations, styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        logger.debug("PDF report generated successfully")
        return buffer
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        raise

def generate_csv_report(filtered_resumes):
    """Generate a CSV report from filtered resumes"""
    try:
        df = pd.DataFrame(filtered_resumes)
        df = df[["file_name", "matching_score", "matched_skills", "experience", "education", "ats_score"]]
        df.columns = ["File Name", "Matching Score (%)", "Matched Skills", "Experience", "Education", "ATS Score"]
        df["Matched Skills"] = df["Matched Skills"].apply(lambda x: ", ".join(x) if x else "None")
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_buffer.seek(0)
        logger.debug("CSV report generated successfully")
        return csv_buffer
    except Exception as e:
        logger.error(f"Failed to generate CSV report: {e}")
        raise

def generate_recruiter_pdf_report(filtered_resumes, jd_data):
    """Generate a PDF report summarizing filtered resumes for recruiters"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        story.append(Paragraph("Recruiter Resume Analysis Report", styles['Title']))
        story.append(Spacer(1, 12))
        
        # Job Description Summary
        story.append(Paragraph("Job Description Summary", styles['Heading2']))
        story.append(Paragraph(f"Skills: {', '.join(jd_data.get('skills', []))}", styles['Normal']))
        story.append(Paragraph(f"Experience: {jd_data.get('experience', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"Education: {jd_data.get('education', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Candidate Summary
        story.append(Paragraph(f"Filtered Candidates ({len(filtered_resumes)})", styles['Heading2']))
        
        # Prepare table data
        table_data = [["File Name", "Matching Score (%)", "Skills", "Experience", "Education", "ATS Score"]]
        for resume in filtered_resumes:
            table_data.append([
                resume.get('file_name', 'N/A'),
                f"{resume.get('matching_score', 0):.2f}",
                ", ".join(resume.get('matched_skills', [])) or "None",
                resume.get('experience', 'N/A'),
                resume.get('education', 'N/A'),
                f"{resume.get('ats_score', 0):.2f}"
            ])
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8F5E9')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        
        doc.build(story)
        buffer.seek(0)
        
        logger.debug("Recruiter PDF report generated successfully")
        return buffer
    except Exception as e:
        logger.error(f"Failed to generate recruiter PDF report: {e}")
        raise