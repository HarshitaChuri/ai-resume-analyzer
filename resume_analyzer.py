import logging
import pdfplumber
import re
import nltk
from nltk.tokenize import word_tokenize
import google.generativeai as genai
import json
import plotly.graph_objects as go
from io import BytesIO
from collections import Counter
from dotenv import load_dotenv
import os
import time

# Load environment variables
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

def extract_text_from_pdf(file):
    """Extract text from a PDF file using pdfplumber."""
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text += page_text + "\n"
        logger.debug("Successfully extracted text from PDF")
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def parse_resume(file):
    """
    Parse resume using Gemini API with regex fallback to extract structured data.
    Returns a dictionary with personal_info, skills, education, experience, projects, certifications.
    """
    try:
        text = extract_text_from_pdf(file)
        if not text:
            logger.error("No text extracted from resume")
            return {"error": "Failed to extract text from resume"}

        model = genai.GenerativeModel('gemini-2.0-flash-001')
        prompt = f"""
        You are a resume parser. Extract the following information from the resume text in JSON format:
        {{
            "personal_info": {{"name": "", "email": "", "phone": "", "linkedin": "", "job_role": "", "location": "", "github": ""}},
            "skills": [],
            "education": [{{"degree": "", "institution": "", "graduation_date": "", "gpa": ""}}],
            "experience": [{{"title": "", "company": "", "duration": "", "description": []}}],
            "projects": [{{"name": "", "description": "", "technologies": []}}],
            "certifications": []
        }}
        
        - For skills, include programming languages, frameworks, tools, and core subjects.
        - For experience, include internships and jobs with duration (e.g., 'Sept 2024 - Feb 2025').
        - For education, include all degrees and diplomas with institution and dates.
        - If a field is missing, use empty strings or lists as appropriate.
        - Ensure skills are unique and case-normalized (e.g., 'Python' not 'python').
        
        Resume Text:
        {text}
        
        Respond ONLY with the JSON object, nothing else.
        """
        
        for attempt in range(3):
            try:
                response = model.generate_content(prompt)
                response_text = response.text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    parsed_data = json.loads(json_str)
                    # Normalize skills to title case and remove duplicates
                    parsed_data["skills"] = [skill.title() for skill in parsed_data["skills"]]
                    parsed_data["skills"] = list(set(parsed_data["skills"]))
                    logger.debug("Successfully parsed resume with Gemini")
                    return parsed_data
                else:
                    logger.warning(f"Invalid JSON response from Gemini API, attempt {attempt + 1}")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Error parsing resume with Gemini, attempt {attempt + 1}: {e}")
                time.sleep(2)

        logger.warning("Gemini parsing failed, falling back to regex")
        # Regex fallback
        parsed_data = {
            "personal_info": {"name": "", "email": "", "phone": "", "linkedin": "", "job_role": "", "location": "", "github": ""},
            "skills": [],
            "education": [],
            "experience": [],
            "projects": [],
            "certifications": []
        }

        # Name
        name_pattern = r"^[A-Z][a-zA-Z\s]+[A-Z][a-zA-Z\s]+$"
        for line in text.split('\n')[:5]:
            if re.match(name_pattern, line.strip()):
                parsed_data['personal_info']['name'] = line.strip()
                break
        else:
            parsed_data['personal_info']['name'] = "N/A"

        # Email
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        email = re.search(email_pattern, text)
        parsed_data['personal_info']['email'] = email.group(0) if email else "N/A"

        # Phone
        phone_pattern = r"\+?\d{1,3}[-.\s]?\d{10}"
        phone = re.search(phone_pattern, text)
        parsed_data['personal_info']['phone'] = phone.group(0) if phone else "N/A"

        # LinkedIn
        linkedin_pattern = r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+"
        linkedin = re.search(linkedin_pattern, text)
        parsed_data['personal_info']['linkedin'] = linkedin.group(0) if linkedin else ""

        # Education
        education_pattern = r"(?:Education|EDUCATION)[\s\S]*?(?=\n\n|\Z)"
        education_match = re.search(education_pattern, text, re.IGNORECASE)
        if education_match:
            education_text = education_match.group(0).strip()
            for line in education_text.split('\n')[1:]:
                if 'CGPA' in line or '%' in line:
                    degree_info = line.split('CGPA')[0].strip() if 'CGPA' in line else line.split('%')[0].strip()
                    gpa = re.search(r'CGPA\s*([\d.]+)|([\d.]+)%', line)
                    institution = re.search(r'(K J Somaiya Institute|Government Polytechnic|St Ann’s School|[A-Za-z\s]+(?:Institute|University|College|School))', education_text)
                    date = re.search(r'(\w+\s+\d{4}\s*-\s*\w+\s+\d{4}|\d{4}\s*-\s*\d{4})', line)
                    parsed_data['education'].append({
                        "degree": degree_info,
                        "institution": institution.group(0) if institution else "N/A",
                        "graduation_date": date.group(0) if date else "N/A",
                        "gpa": gpa.group(1) or gpa.group(2) if gpa else "N/A"
                    })
        if not parsed_data['education']:
            parsed_data['education'] = [{"degree": "N/A", "institution": "N/A", "graduation_date": "N/A", "gpa": "N/A"}]

        # Skills
        skills_pattern = r"(?:Skills|SKILLS)[\s\S]*?(?=\n\n|\Z)"
        skills_match = re.search(skills_pattern, text, re.IGNORECASE)
        if skills_match:
            skills_text = skills_match.group(0)
            known_skills = {
                'C', 'C++', 'Java', 'Python', 'HTML', 'CSS', 'JavaScript', 'Django',
                'MongoDB', 'ReactJS', 'NodeJS', 'Data Structure And Algorithm',
                'Operating System', 'Database Management System', 'Software Engineering',
                'Software Testing', 'Computer Network'
            }
            for line in skills_text.split('\n')[1:]:
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    skill_list = [s.strip().title() for s in line.split(':', 1)[1].split(',')]
                    parsed_data['skills'].extend([s for s in skill_list if s in known_skills])
                elif line.title() in known_skills and len(line.split()) < 5:
                    parsed_data['skills'].append(line.title())
            parsed_data['skills'] = list(set(parsed_data['skills']))

        # Experience
        experience_pattern = r"(?:Experience|EXPERIENCE)[\s\S]*?(?=\n\n|\Z)"
        experience_match = re.search(experience_pattern, text, re.IGNORECASE)
        if experience_match:
            experience_text = experience_match.group(0).strip()
            for line in experience_text.split('\n')[1:]:
                if 'Intern' in line or '-' in line:
                    match = re.match(r'(.+?)\s+((?:\w+\s+)?\d{4}\s*-\s*(?:\w+\s+)?\d{4}.*)', line)
                    if match:
                        title = match.group(1).strip()
                        duration = match.group(2).strip()
                        parsed_data['experience'].append({
                            "title": title,
                            "company": "N/A",
                            "duration": duration,
                            "description": []
                        })
        if not parsed_data['experience']:
            parsed_data['experience'] = [{"title": "N/A", "company": "N/A", "duration": "N/A", "description": []}]

        # Projects
        projects_pattern = r"(?:Projects|PROJECTS)[\s\S]*?(?=\n\n|\Z)"
        projects_match = re.search(projects_pattern, text, re.IGNORECASE)
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
                        parsed_data['projects'].append(current_project)
                        current_project = None
            if current_project:
                parsed_data['projects'].append(current_project)
        if not parsed_data['projects']:
            parsed_data['projects'] = [{"name": "N/A", "description": "", "technologies": []}]

        logger.debug(f"Fallback parsed resume data: {parsed_data}")
        return parsed_data
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        return {"error": f"Resume parsing failed: {e}"}

def analyze_resume(resume_text, job_role=""):
    """
    Analyze resume for ATS compatibility and relevance using Gemini with NLTK fallback.
    Returns detailed analysis including ATS score, skills, and feedback.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-001')
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
                response = model.generate_content(prompt)
                response_text = response.text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    feedback = json.loads(json_str)
                    logger.debug("Successfully analyzed resume with Gemini")
                    break
                else:
                    logger.warning(f"Invalid JSON response from Gemini API, attempt {attempt + 1}")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Error analyzing resume with Gemini, attempt {attempt + 1}: {e}")
                time.sleep(2)
        else:
            logger.warning("Gemini analysis failed, using default feedback")
            feedback = {
                "score": 70,
                "strengths": ["Could not extract specific strengths"],
                "improvements": ["Could not extract specific improvements"],
                "ats_suggestions": ["Ensure resume is in a standard PDF format"],
                "missing_skills": ["Could not determine missing skills"]
            }

        # Extract skills with regex as fallback
        skills = []
        skills_pattern = r"(?:Skills|SKILLS)[\s\S]*?(?=\n\n|\Z)"
        skills_match = re.search(skills_pattern, resume_text, re.IGNORECASE)
        if skills_match:
            skills_text = skills_match.group(0)
            known_skills = {
                'C', 'C++', 'Java', 'Python', 'HTML', 'CSS', 'JavaScript', 'Django',
                'MongoDB', 'ReactJS', 'NodeJS', 'Data Structure And Algorithm',
                'Operating System', 'Database Management System', 'Software Engineering',
                'Software Testing', 'Computer Network'
            }
            for line in skills_text.split('\n')[1:]:
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    skill_list = [s.strip().title() for s in line.split(':', 1)[1].split(',')]
                    skills.extend([s for s in skill_list if s in known_skills])
                elif line.title() in known_skills and len(line.split()) < 5:
                    skills.append(line.title())
        skills = list(set(skills))
        skills_freq = dict(Counter(skills))

        # Calculate ATS score with NLTK fallback
        ats_score = feedback.get('score', 70)
        if feedback.get('score', 70) == 70:
            logger.warning("Using NLTK fallback for ATS score")
            try:
                resume_tokens = set(word_tokenize(resume_text.lower()))
                job_keywords = set(word_tokenize(job_role.lower())) if job_role else set()
                if job_keywords:
                    matched_keywords = resume_tokens.intersection(job_keywords)
                    ats_score = (len(matched_keywords) / len(job_keywords)) * 100
                else:
                    ats_score = 70.0
            except Exception as e:
                logger.error(f"NLTK ATS score calculation failed: {e}")
                ats_score = 70.0

        # Collect keywords
        keywords = skills[:]
        if job_role:
            keywords.extend(word_tokenize(job_role.lower()))
        keywords = list(set(keywords))[:10]

        return {
            'ats_score': round(ats_score, 2),
            'word_count': len(resume_text.split()),
            'skills': skills,
            'skills_freq': skills_freq,
            'feedback': feedback,
            'keywords': keywords
        }
    except Exception as e:
        logger.error(f"Error in resume analysis: {e}")
        return {
            'ats_score': 0.0,
            'word_count': len(resume_text.split()) if resume_text else 0,
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

def generate_recommendations(analysis, job_role):
    """
    Generate clear, job-role-specific recommendations based on analysis.
    """
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
    """
    Chat with resume reviewer for specific questions using Gemini API.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        prompt = f"""
        You are an ATS and resume optimization expert. Based on the resume text and job role ({job_role}), answer the user's query: "{user_query}".
        Provide a concise and relevant response in plain text, focusing on ATS compatibility and job-role relevance.
        
        Resume Text:
        {resume_text[:1000]}...
        """
        
        response = model.generate_content(prompt)
        answer = response.text.strip()
        logger.debug("Successfully responded to chat query")
        return answer
    except Exception as e:
        logger.error(f"Error in chat with resume: {e}")
        return "Error in chat response: Please check your Gemini API key or network connection."

def generate_ats_chart(analysis):
    """
    Generate a doughnut pie chart for ATS score, consistent with job seeker UI.
    """
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
        return go.Figure()