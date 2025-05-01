from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import plotly.graph_objects as go
import io
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_pdf_report(analysis, recommendations):
    try:
        logger.debug("Generating PDF report")
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph("Resume Analysis Report", styles['Title']))
        story.append(Spacer(1, 12))

        # Analysis Section
        story.append(Paragraph("Analysis", styles['Heading2']))
        story.append(Paragraph(f"Sentiment Score: {analysis['sentiment']:.2f}", styles['Normal']))
        story.append(Paragraph(f"Word Count: {analysis['word_count']}", styles['Normal']))
        story.append(Paragraph(f"Skills Detected: {', '.join(analysis['skills'])}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Recommendations Section
        story.append(Paragraph("Recommendations", styles['Heading2']))
        story.append(Paragraph(recommendations, styles['Normal']))
        story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        logger.debug("PDF report generated successfully")
        return buffer
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        return None

def generate_skill_chart(analysis):
    try:
        logger.debug("Generating skill chart")
        skills = list(analysis['skills_freq'].keys())
        frequencies = list(analysis['skills_freq'].values())

        fig = go.Figure(data=[
            go.Bar(
                x=skills,
                y=frequencies,
                marker_color='#4caf50',  # Vibrant green bars
            )
        ])

        fig.update_layout(
            title='Skill Frequency in Resume',
            xaxis_title='Skills',
            yaxis_title='Frequency',
            title_font=dict(size=20, color='#2e7d32', family='Arial', weight='bold'),
            xaxis_title_font=dict(size=16, color='#2e7d32', family='Arial', weight='bold'),
            yaxis_title_font=dict(size=16, color='#2e7d32', family='Arial', weight='bold'),
            xaxis_tickfont=dict(size=12, color='#2e7d32'),
            yaxis_tickfont=dict(size=12, color='#2e7d32'),
            plot_bgcolor='#e8f5e9',  # Light green background
            paper_bgcolor='#e8f5e9',  # Light green paper
            bargap=0.2,
            font=dict(color='#2e7d32'),
            margin=dict(l=50, r=50, t=50, b=50)
        )

        logger.debug("Skill chart generated successfully")
        return fig
    except Exception as e:
        logger.error(f"Failed to generate skill chart: {e}")
        return None