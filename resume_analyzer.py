import PyPDF2
import pdfplumber
import re
from textblob import TextBlob
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in .env file")
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(uploaded_file):
    try:
        logger.debug("Extracting text from PDF")
        # Reset file pointer to start
        uploaded_file.seek(0)
        # Use pdfplumber for text extraction
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        logger.debug(f"Extracted text length: {len(text)}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return {"error": str(e)}

def parse_resume(uploaded_file):
    try:
        logger.debug(f"Parsing resume: {uploaded_file.name}")
        # Extract text
        text = extract_text_from_pdf(uploaded_file)
        if isinstance(text, dict) and "error" in text:
            return text
        
        # Initialize parsed data
        parsed_data = {
            "name": "N/A",
            "email": "N/A",
            "skills": [],
            "education": "N/A"
        }

        # Parse name (assume first line or capitalized words)
        lines = text.split('\n')
        if lines:
            # Assume name is at the top (first non-empty line)
            for line in lines[:5]:  # Check first 5 lines
                if line.strip() and re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', line.strip()):
                    parsed_data["name"] = line.strip()
                    break

        # Parse email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, text)
        if email_match:
            parsed_data["email"] = email_match.group(0)

        # Parse education (look for degree keywords)
        education_pattern = r'(Bachelor|Master|Ph\.D|Associate|B\.S\.|M\.S\.|B\.Tech|B\.E\.)\s*(?:of|in)?\s*([\w\s]+?)(?=\n|\s{2,}|$|\d{4})'
        education_match = re.search(education_pattern, text, re.IGNORECASE)
        if education_match:
            parsed_data["education"] = f"{education_match.group(1)} {education_match.group(2).strip()}"

        # Parse skills (extend based on resume content)
        skills_list = ['python', 'java', 'javascript', 'sql', 'r', 'machine learning', 'data analysis', 'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'tableau', 'power bi', 'aws', 'azure', 'gcp', 'hadoop', 'spark', 'mongodb', 'mysql']
        found_skills = []
        for skill in skills_list:
            if re.search(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE):
                found_skills.append(skill)
        parsed_data["skills"] = found_skills

        logger.debug(f"Parsed data: {parsed_data}")
        return parsed_data
    except Exception as e:
        logger.error(f"Failed to parse resume: {e}")
        return {"error": str(e)}

def analyze_resume(text):
    try:
        logger.debug("Analyzing resume text")
        # Handle empty or invalid text
        if not text or isinstance(text, dict):
            logger.error("Invalid resume text for analysis")
            return {"error": "Invalid resume text"}

        # Sentiment analysis
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity

        # Word count
        word_count = len(text.split())

        # Skills detection with frequency
        skills_list = ['python', 'java', 'javascript', 'sql', 'r', 'machine learning', 'data analysis', 'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'tableau', 'power bi', 'aws', 'azure', 'gcp', 'hadoop', 'spark', 'mongodb', 'mysql']
        skills = []
        skills_freq = {}
        for skill in skills_list:
            matches = len(re.findall(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE))
            if matches > 0:
                skills.append(skill)
                skills_freq[skill] = matches

        analysis = {
            "sentiment": sentiment,
            "word_count": word_count,
            "skills": skills,
            "skills_freq": skills_freq
        }
        logger.debug(f"Analysis result: {analysis}")
        return analysis
    except Exception as e:
        logger.error(f"Failed to analyze resume: {e}")
        return {"error": str(e)}

def generate_recommendations(analysis, job_role=""):
    try:
        logger.debug("Generating recommendations")
        if "error" in analysis:
            logger.error("Invalid analysis for recommendations")
            return "Unable to generate recommendations due to analysis error."

        # Prepare prompt
        prompt = f"""
        You are an expert resume reviewer. Based on the following resume analysis, provide 3 specific, actionable recommendations to improve the resume. Tailor the recommendations to the target job role if provided. Ensure the recommendations are concise, professional, and focus on improving the resume's effectiveness.

        Resume Analysis:
        - Sentiment: {analysis['sentiment']}
        - Word Count: {analysis['word_count']}
        - Skills: {', '.join(analysis['skills'])}
        - Skill Frequencies: {analysis['skills_freq']}

        Target Job Role/Description (if any): {job_role}

        Provide recommendations in a structured format with bullet points, including why the change is needed and how to implement it.
        """
        logger.debug(f"Using model: gemini-2.0-flash-001")
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        response = model.generate_content(
            prompt,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
            }
        )
        recommendations = response.text
        logger.debug(f"Recommendations: {recommendations}")
        return recommendations
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        return f"Error generating recommendations: {e}"

def chat_with_resume(resume_text, user_query, job_role=""):
    try:
        logger.debug(f"Processing chat query: {user_query}")
        if not resume_text or isinstance(resume_text, dict):
            logger.error("Invalid resume text for chat")
            return "Cannot process chat query due to invalid resume text."

        # Prepare prompt
        prompt = f"""
        You are an expert resume reviewer. The user has uploaded a resume with the following content (summarized for brevity):

        Resume Content:
        {resume_text[:1000]}... (truncated)

        The target job role or description (if any) is:
        {job_role}

        The user has asked: "{user_query}"

        Provide a professional, concise, and actionable response to the user's query. If the query is about improving the resume, offer specific suggestions tailored to the job role (if provided). If the query is about something else (e.g., certifications, skills), provide relevant advice based on the resume content and job role.
        """
        logger.debug(f"Using model: gemini-2.0-flash-001")
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        response = model.generate_content(
            prompt,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
            }
        )
        chat_response = response.text
        logger.debug(f"Chat response: {chat_response}")
        return chat_response
    except Exception as e:
        logger.error(f"Failed to process chat query: {e}")
        return f"Error processing chat query: {e}"