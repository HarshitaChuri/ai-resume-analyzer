import plotly.graph_objects as go
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import logging

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