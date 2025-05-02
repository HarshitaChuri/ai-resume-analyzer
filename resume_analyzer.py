import pdfplumber
import re
import nltk
from nltk.tokenize import word_tokenize
import os
import google.generativeai as genai
import logging
from collections import Counter
import json
import io
import time
import plotly.graph_objects as go
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Download NLTK data
try:
    nltk.download('punkt_tab', quiet=True)
    logger.debug("NLTK punkt_tab downloaded")
except Exception as e:
    logger.error(f"Failed to download NLTK punkt_tab: {e}")

# Configure Gemini API
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    logger.debug("Gemini API configured")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    raise Exception("Gemini API configuration failed")

class FeedbackAgent:
    def __init__(self):
        """Initialize the feedback agent with the Gemini API key"""
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-001')
            logger.debug("Using gemini-2.0-flash-001 model")
        except Exception as e:
            logger.error(f"Failed to initialize gemini-2.0-flash-001: {e}")
            raise Exception("Gemini API initialization failed")
    
    def analyze_resume(self, resume_text, job_role):
        """Analyze resume for a specific job role and provide feedback"""
        prompt = f"""
        You are an ATS optimization expert. Analyze this resume for a {job_role} position and provide detailed feedback in the following JSON format:
        {{
            "score": 75,
            "strengths": [
                "Strong technical skills in relevant technologies",
                "Relevant project experience",
                "Clear educational background"
            ],
            "improvements": [
                "Include more quantifiable achievements",
                "Expand on project outcomes",
                "Add specific tools or frameworks"
            ],
            "ats_suggestions": [
                "Incorporate more keywords from the job description",
                "Use standard section headings",
                "Ensure consistent formatting"
            ],
            "missing_skills": [
                "Skill 1",
                "Skill 2"
            ]
        }}
        
        Resume:
        {resume_text}
        
        Respond ONLY with the JSON object, nothing else.
        """
        
        for attempt in range(3):
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    feedback_data = json.loads(json_str)
                    logger.debug("FeedbackAgent: Successfully parsed feedback")
                    return feedback_data
                else:
                    logger.warning(f"FeedbackAgent: JSON not found in response, attempt {attempt + 1}")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"FeedbackAgent: Error analyzing resume, attempt {attempt + 1}: {e}")
                time.sleep(2)
        
        logger.warning("FeedbackAgent: All retries failed")
        return {
            "score": 70,
            "strengths": ["Could not extract specific strengths"],
            "improvements": ["Could not extract specific improvements"],
            "ats_suggestions": ["Ensure resume is in a standard PDF format"],
            "missing_skills": ["Could not determine missing skills"]
        }

class ExtractorAgent:
    def __init__(self):
        """Initialize the extractor agent with the Gemini API key"""
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-001')
            logger.debug("Using gemini-2.0-flash-001 model")
        except Exception as e:
            logger.error(f"Failed to initialize gemini-2.0-flash-001: {e}")
            raise Exception("Gemini API initialization failed")
    
    def extract_text(self, file):
        """Extract text from a resume file using pdfplumber"""
        try:
            with pdfplumber.open(file) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        text += page_text + "\n"
            logger.debug("ExtractorAgent: PDF text extracted successfully")
            return text.strip()
        except Exception as e:
            logger.error(f"ExtractorAgent: Error extracting PDF text: {e}")
            return ""
    
    def parse_resume(self, file):
        """Parse resume and extract structured information"""
        resume_text = self.extract_text(file)
        
        prompt = f"""
        Extract the following information from this resume in JSON format, focusing only on essential details:
        {{
            "personal_info": {{
                "name": "",
                "email": "",
                "phone": "",
                "location": "",
                "linkedin": "",
                "github": ""
            }},
            "education": [
                {{
                    "degree": "",
                    "institution": "",
                    "graduation_date": "",
                    "gpa": ""
                }}
            ],
            "experience": [
                {{
                    "title": "",
                    "company": "",
                    "duration": "",
                    "description": []
                }}
            ],
            "skills": [],
            "projects": [
                {{
                    "name": "",
                    "description": "",
                    "technologies": []
                }}
            ],
            "certifications": []
        }}
        
        Resume text:
        {resume_text}
        
        Respond ONLY with the JSON object, nothing else.
        """
        
        for attempt in range(3):
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    parsed_data = json.loads(json_str)
                    logger.debug("ExtractorAgent: Successfully parsed resume")
                    return parsed_data
                else:
                    logger.warning(f"ExtractorAgent: JSON not found in response, attempt {attempt + 1}")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"ExtractorAgent: Error parsing resume, attempt {attempt + 1}: {e}")
                time.sleep(2)
        
        logger.warning("ExtractorAgent: All retries failed")
        return {"error": "Could not extract structured data from the resume"}

def extract_text_from_pdf(file):
    """Wrapper function for ExtractorAgent text extraction"""
    try:
        extractor = ExtractorAgent()
        text = extractor.extract_text(file)
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return {"error": str(e)}

def parse_resume(file):
    """Parse resume using ExtractorAgent with regex fallback"""
    try:
        extractor = ExtractorAgent()
        parsed_data = extractor.parse_resume(file)
        if "error" not in parsed_data:
            logger.debug(f"Parsed resume data: {parsed_data}")
            return parsed_data
        
        logger.warning(f"Parse resume fallback to regex due to: {parsed_data['error']}")
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text += page_text + "\n"
            text = text.strip()
        
        parsed_data = {}
        # Name
        name_pattern = r"^[A-Z][a-zA-Z\s]+[A-Z][a-zA-Z\s]+$"
        for line in text.split('\n')[:5]:
            if re.match(name_pattern, line.strip()):
                parsed_data['name'] = line.strip()
                break
        else:
            parsed_data['name'] = "N/A"
        
        # Email
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        email = re.search(email_pattern, text)
        parsed_data['email'] = email.group(0) if email else "N/A"
        
        # Education
        education_pattern = r"(?:Education|EDUCATION)[\s\S]*?(?=\n\n|\Z)"
 
        education_match = re.search(education_pattern, text, re.IGNORECASE)
        education = []
        if education_match:
            education_text = education_match.group(0).strip()
            for line in education_text.split('\n')[1:]:
                if 'CGPA' in line or '%' in line:
                    degree_info = line.split('CGPA')[0].strip() if 'CGPA' in line else line.split('%')[0].strip()
                    gpa = re.search(r'CGPA\s*([\d.]+)|([\d.]+)%', line)
                    institution = re.search(r'(K J Somaiya Institute|Government Polytechnic|St Ann’s School)', education_text)
                    date = re.search(r'(\w+\s+\d{4}\s*-\s*\w+\s+\d{4}|\d{4}\s*-\s*\d{4})', line)
                    education.append({
                        "degree": degree_info,
                        "institution": institution.group(0) if institution else "N/A",
                        "graduation_date": date.group(0) if date else "N/A",
                        "gpa": gpa.group(1) or gpa.group(2) if gpa else "N/A"
                    })
        parsed_data['education'] = education if education else [{"degree": "N/A", "institution": "N/A", "graduation_date": "N/A", "gpa": "N/A"}]
        
        # Skills
        skills_pattern = r"(?:Skills|SKILLS)[\s\S]*?(?=\n\n|\Z)"
        skills_match = re.search(skills_pattern, text, re.IGNORECASE)
        skills = []
        if skills_match:
            skills_text = skills_match.group(0)
            known_skills = {
                'C', 'C++', 'Java', 'Python', 'HTML', 'CSS', 'JavaScript', 'Django',
                'MongoDB', 'ReactJS', 'NodeJS', 'Data Structure and Algorithm',
                'Operating System', 'Database Management System', 'Software Engineering',
                'Software Testing', 'Computer Network'
            }
            for line in skills_text.split('\n')[1:]:
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    skill_list = [s.strip() for s in line.split(':', 1)[1].split(',')]
                    skills.extend([s for s in skill_list if s in known_skills])
                elif line in known_skills and len(line.split()) < 5:
                    skills.append(line)
            parsed_data['skills'] = skills
        else:
            parsed_data['skills'] = []
        
        # Experience
        experience_pattern = r"(?:Experience|EXPERIENCE)[\s\S]*?(?=\n\n|\Z)"
        experience_match = re.search(experience_pattern, text, re.IGNORECASE)
        experience = []
        if experience_match:
            experience_text = experience_match.group(0).strip()
            for line in experience_text.split('\n')[1:]:
                if 'Intern' in line or '-' in line:
                    match = re.match(r'(.+?)\s+((?:\w+\s+)?\d{4}\s*-\s*(?:\w+\s+)?\d{4}.*)', line)
                    if match:
                        title = match.group(1).strip()
                        duration = match.group(2).strip()
                        experience.append({
                            "title": title,
                            "company": "N/A",
                            "duration": duration,
                            "description": []
                        })
        parsed_data['experience'] = experience if experience else [{"title": "N/A", "company": "N/A", "duration": "N/A", "description": []}]
        
        # Projects
        projects_pattern = r"(?:Projects|PROJECTS)[\s\S]*?(?=\n\n|\Z)"
        projects_match = re.search(projects_pattern, text, re.IGNORECASE)
        projects = []
        if projects_match:
            projects_text = projects_match.group(0).strip()
            current_project = None
            for line in projects_text.split('\n')[1:]:
                line = line.strip()
                if not line:
                    continue
                if not current_project:
                    current_project = {"name": line, "description": "", "technologies": []}
                else:
                    if 'MERN' in line or 'Django' in line:
                        current_project['technologies'] = [t for t in ['MERN', 'Django', 'Python'] if t in line]
                        current_project['description'] = line
                        projects.append(current_project)
                        current_project = None
            if current_project:
                projects.append(current_project)
        parsed_data['projects'] = projects if projects else [{"name": "N/A", "description": "", "technologies": []}]
        
        parsed_data['certifications'] = []
        
        logger.debug(f"Fallback parsed resume data: {parsed_data}")
        return parsed_data
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        return {"error": str(e)}

def analyze_resume(text, job_role=""):
    """Analyze resume using FeedbackAgent and fallback to NLTK"""
    try:
        feedback_agent = FeedbackAgent()
        feedback = feedback_agent.analyze_resume(text, job_role)
        
        skills = []
        skills_pattern = r"(?:Skills|SKILLS)[\s\S]*?(?=\n\n|\Z)"
        skills_match = re.search(skills_pattern, text, re.IGNORECASE)
        if skills_match:
            skills_text = skills_match.group(0)
            known_skills = {
                'C', 'C++', 'Java', 'Python', 'HTML', 'CSS', 'JavaScript', 'Django',
                'MongoDB', 'ReactJS', 'NodeJS', 'Data Structure and Algorithm',
                'Operating System', 'Database Management System', 'Software Engineering',
                'Software Testing', 'Computer Network'
            }
            for line in skills_text.split('\n')[1:]:
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    skill_list = [s.strip() for s in line.split(':', 1)[1].split(',')]
                    skills.extend([s for s in skill_list if s in known_skills])
                elif line in known_skills and len(line.split()) < 5:
                    skills.append(line)
        skills_freq = dict(Counter(skills))
        
        ats_score = feedback.get('score', 70)
        if "error" in feedback or ats_score == 70:
            logger.warning("FeedbackAgent failed, using NLTK fallback for ATS score")
            try:
                resume_tokens = set(word_tokenize(text.lower()))
                job_keywords = set(word_tokenize(job_role.lower())) if job_role else set()
                if job_keywords:
                    matched_keywords = resume_tokens.intersection(job_keywords)
                    ats_score = (len(matched_keywords) / len(job_keywords)) * 100
                else:
                    ats_score = 0.0
            except Exception as e:
                logger.error(f"NLTK ATS score calculation failed: {e}")
                ats_score = 0.0
        
        keywords = []
        if skills:
            keywords.extend(skills)
        if job_role:
            keywords.extend(word_tokenize(job_role.lower()))
        keywords = list(set(keywords))[:10]
        
        return {
            'ats_score': round(ats_score, 2),
            'word_count': len(text.split()),
            'skills': skills,
            'skills_freq': skills_freq,
            'feedback': feedback,
            'keywords': keywords
        }
    except Exception as e:
        logger.error(f"Error in resume analysis: {e}")
        return {
            'ats_score': 0.0,
            'word_count': len(text.split()) if text else 0,
            'skills': [],
            'skills_freq': {},
            'feedback': {
                'score': 0,
                'strengths': [],
                'improvements': [],
                'ats_suggestions': [],
                'missing_skills': []
            },
            'keywords': []
        }

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
            plot_bgcolor='#E8F5E9',
            paper_bgcolor='#E8F5E9',
            font=dict(color='#2E7D32'),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        
        logger.debug("ATS chart generated successfully")
        return fig
    except Exception as e:
        logger.error(f"Failed to generate ATS chart: {e}")
        raise

def generate_recommendations(analysis, job_role):
    """Generate clear, job-role-specific recommendations"""
    try:
        feedback = analysis.get('feedback', {})
        recommendations = []
        
        improvements = feedback.get('improvements', [])
        ats_suggestions = feedback.get('ats_suggestions', [])
        missing_skills = feedback.get('missing_skills', [])
        
        if improvements:
            recommendations.extend([f"For {job_role}: {imp}" for imp in improvements])
        if ats_suggestions:
            recommendations.extend([f"ATS Tip: {sug}" for sug in ats_suggestions])
        if missing_skills:
            recommendations.append(f"Add for {job_role}: {', '.join(missing_skills)}")
        if not recommendations:
            recommendations.append(f"Tailor your resume to include specific {job_role} skills and keywords.")
        
        result = "\n".join(recommendations)
        logger.debug(f"Recommendations generated: {result}")
        return result
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return "Error generating recommendations."

def chat_with_resume(resume_text, user_query, job_role):
    """Chat with resume using Gemini API"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        prompt = f"""
        You are an ATS and resume optimization expert. The user's resume contains: {resume_text[:1000]}...
        The user is applying for: {job_role}.
        The user's question is: {user_query}
        Provide a concise, professional response to improve their resume or answer their query, focusing on ATS compatibility and job-role relevance.
        """
        response = model.generate_content(prompt)
        logger.debug(f"Chat response generated: {response.text}")
        return response.text
    except Exception as e:
        logger.error(f"Error in chat response: {e}")
        return "Error in chat response: Please check your Gemini API key or network connection."