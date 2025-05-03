import os
import zipfile
import sqlite3
import json
import logging
import re
import pdfplumber
from resume_analyzer import parse_resume, analyze_resume, extract_text_from_pdf
import google.generativeai as genai
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure Gemini API
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    logger.debug("Gemini API configured for recruiter_utils")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    raise Exception("Gemini API configuration failed")

# Fallback mapping for common job roles
JOB_ROLE_DEFAULTS = {
    "data scientist": {
        "skills": ["Python", "R", "SQL", "Machine Learning", "TensorFlow", "Pandas", "NumPy", "Data Visualization"],
        "experience": "2-5 years in data science or related field",
        "education": "Bachelor's or Master's in Data Science, Computer Science, Statistics, or related field"
    },
    "software engineer": {
        "skills": ["Python", "Java", "C++", "JavaScript", "SQL", "Git", "Docker", "AWS"],
        "experience": "2-5 years in software development",
        "education": "Bachelor's in Computer Science, Software Engineering, or related field"
    },
    "machine learning engineer": {
        "skills": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "Deep Learning", "SQL", "Cloud Computing"],
        "experience": "3-6 years in machine learning or AI development",
        "education": "Master's or PhD in Computer Science, AI, or related field"
    }
}

def process_bulk_resumes(uploaded_files, username):
    """
    Process multiple resumes (PDFs or ZIP) and store in database, updating existing entries.
    Returns list of processed resume data.
    """
    resume_data = []
    os.makedirs("uploads/resumes", exist_ok=True)
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Clear previous resumes for this user to keep only current session data
        cursor.execute("DELETE FROM resumes WHERE username = ?", (username,))
        logger.debug(f"Cleared previous resume data for user {username}")
        
        for file in uploaded_files:
            if file.name.endswith(".pdf"):
                # Handle single PDF
                file_path = f"uploads/resumes/{file.name}"
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                resume_data.append(process_single_resume(file_path, username, cursor))
            
            elif file.name.endswith(".zip"):
                # Handle ZIP file
                zip_path = f"uploads/{file.name}"
                with open(zip_path, "wb") as f:
                    f.write(file.getbuffer())
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall("uploads/resumes")
                    for pdf_file in zip_ref.namelist():
                        if pdf_file.endswith(".pdf"):
                            pdf_path = f"uploads/resumes/{pdf_file}"
                            resume_data.append(process_single_resume(pdf_path, username, cursor))
        
        conn.commit()
        logger.debug(f"Processed and stored {len(resume_data)} resumes for user {username}")
    except Exception as e:
        logger.error(f"Error processing bulk resumes: {e}")
        raise
    finally:
        conn.close()
    
    return resume_data

def process_single_resume(file_path, username, cursor):
    """Process a single resume, update if exists, and store in database."""
    try:
        file_name = os.path.basename(file_path)
        
        # Check if resume already exists for this user
        cursor.execute("""
            SELECT id FROM resumes WHERE username = ? AND file_name = ?
        """, (username, file_name))
        existing_resume = cursor.fetchone()
        
        parsed_data = parse_resume(file_path)
        if "error" in parsed_data:
            logger.warning(f"Failed to parse resume {file_path}: {parsed_data['error']}")
            return {
                "file_name": file_name,
                "file_path": file_path,
                "parsed_data": {},
                "ats_score": 0.0,
                "job_role": ""
            }
        
        text = extract_text_from_pdf(file_path)
        job_role = parsed_data.get("personal_info", {}).get("job_role", "")
        analysis = analyze_resume(text, job_role)
        
        # Update or insert resume data
        if existing_resume:
            cursor.execute("""
                UPDATE resumes SET file_path = ?, job_role = ?, ats_score = ?, parsed_data = ?
                WHERE username = ? AND file_name = ?
            """, (
                file_path,
                job_role,
                analysis["ats_score"],
                json.dumps(parsed_data),
                username,
                file_name
            ))
            logger.debug(f"Updated existing resume: {file_name} for user {username}")
        else:
            cursor.execute("""
                INSERT INTO resumes (username, file_name, file_path, job_role, ats_score, parsed_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                username,
                file_name,
                file_path,
                job_role,
                analysis["ats_score"],
                json.dumps(parsed_data)
            ))
            logger.debug(f"Inserted new resume: {file_name} for user {username}")
        
        return {
            "file_name": file_name,
            "file_path": file_path,
            "parsed_data": parsed_data,
            "ats_score": analysis["ats_score"],
            "job_role": job_role
        }
    except Exception as e:
        logger.error(f"Error processing resume {file_path}: {e}")
        return {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "parsed_data": {},
            "ats_score": 0.0,
            "job_role": ""
        }

def parse_job_description(jd_text):
    """
    Parse job description from text using Gemini API with fallback for short inputs.
    Returns structured JD data.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        
        # Check if input is a short job title (e.g., "Data Scientist")
        jd_text_lower = jd_text.lower().strip()
        if len(jd_text.split()) <= 3 and jd_text_lower in JOB_ROLE_DEFAULTS:
            logger.debug(f"Short job title detected: {jd_text_lower}, using default values")
            return JOB_ROLE_DEFAULTS[jd_text_lower]
        
        # Prompt for detailed job descriptions or longer inputs
        prompt = f"""
        You are a job description parser. Extract the following information from the provided job description in JSON format:
        {{
            "skills": [],
            "experience": "",
            "education": ""
        }}
        
        If the input is a brief job title (e.g., "Data Scientist"), infer typical skills, experience, and education for that role based on industry standards.
        
        Job Description:
        {jd_text}
        
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
                    jd_data = json.loads(json_str)
                    # Check if response is empty and fallback to defaults if applicable
                    if not jd_data["skills"] and not jd_data["experience"] and not jd_data["education"] and jd_text_lower in JOB_ROLE_DEFAULTS:
                        logger.debug(f"Empty API response for {jd_text_lower}, using default values")
                        return JOB_ROLE_DEFAULTS[jd_text_lower]
                    logger.debug("Successfully parsed job description")
                    return jd_data
                else:
                    logger.warning(f"JD parsing: JSON not found in response, attempt {attempt + 1}")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"JD parsing error, attempt {attempt + 1}: {e}")
                time.sleep(2)
        
        logger.warning("JD parsing: All retries failed")
        # Fallback to defaults if input matches a known role
        if jd_text_lower in JOB_ROLE_DEFAULTS:
            logger.debug(f"Using default values for {jd_text_lower} after API failure")
            return JOB_ROLE_DEFAULTS[jd_text_lower]
        return {
            "skills": [],
            "experience": "",
            "education": ""
        }
    except Exception as e:
        logger.error(f"Error parsing job description: {e}")
        # Fallback to defaults if input matches a known role
        if jd_text_lower in JOB_ROLE_DEFAULTS:
            logger.debug(f"Using default values for {jd_text_lower} after error")
            return JOB_ROLE_DEFAULTS[jd_text_lower]
        return {
            "skills": [],
            "experience": "",
            "education": ""
        }

def match_resumes(resume_data, jd_data):
    """
    Match resumes against JD and return ranked list with scores.
    """
    try:
        ranked_resumes = []
        
        # Extract and normalize JD requirements
        jd_skills = set(skill.lower() for skill in jd_data.get("skills", []))
        jd_experience = jd_data.get("experience", "").lower()
        jd_education = jd_data.get("education", "").lower()
        
        # Parse JD experience for numerical comparison (e.g., "2-5 years" -> (2, 5))
        experience_range = (0, float('inf'))
        if jd_experience:
            match = re.search(r'(\d+)(?:-(\d+))?\s*(?:years?|yrs?)', jd_experience)
            if match:
                min_years = int(match.group(1))
                max_years = int(match.group(2)) if match.group(2) else min_years
                experience_range = (min_years, max_years)
        
        for resume in resume_data:
            try:
                # Extract resume data
                parsed_data = resume.get("parsed_data", {})
                resume_skills = set(skill.lower() for skill in parsed_data.get("skills", []))
                resume_experience = parsed_data.get("experience", [])
                resume_education = parsed_data.get("education", [])
                ats_score = resume.get("ats_score", 0.0)
                
                # Log parsed data for debugging
                logger.debug(f"Resume {resume['file_name']}: skills={resume_skills}, experience={resume_experience}, education={resume_education}")
                
                # Skills match (50% weight)
                if jd_skills:
                    matched_skills = jd_skills & resume_skills
                    skill_overlap = len(matched_skills) / len(jd_skills)
                else:
                    matched_skills = set()
                    skill_overlap = 0.0
                skill_score = skill_overlap * 50
                
                # Experience match (30% weight)
                experience_score = 0.0
                total_years = 0.0
                for exp in resume_experience:
                    duration = exp.get("duration", "").lower()
                    # Handle formats like "Sept 2024 - Feb 2025" or "1 year"
                    if "present" in duration or "ongoing" in duration:
                        start_date = re.search(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*\d{4}', duration)
                        if start_date:
                            start_year = int(start_date.group().split()[-1])
                            total_years += (2025 - start_year + 0.5)  # Assume current year 2025
                    else:
                        match = re.search(r'(\d+)(?:\.(\d+))?\s*(?:years?|yrs?)|(\d+)\s*months?', duration)
                        if match:
                            if match.group(1):  # Years
                                years = float(match.group(1))
                                if match.group(2):  # Decimal (e.g., 1.5 years)
                                    years += float(f"0.{match.group(2)}")
                                total_years += years
                            elif match.group(3):  # Months
                                total_years += int(match.group(3)) / 12
                if total_years >= experience_range[0] and total_years <= experience_range[1]:
                    experience_score = 30.0
                elif total_years > 0:
                    # Partial score for close matches
                    closeness = min(total_years / experience_range[0] if experience_range[0] > 0 else 1.0, 
                                  experience_range[1] / total_years if total_years > 0 else 1.0)
                    experience_score = 30.0 * closeness
                
                # Education match (20% weight)
                education_score = 0.0
                resume_edu_keywords = []
                for edu in resume_education:
                    degree = edu.get("degree", "").lower()
                    resume_edu_keywords.append(degree)
                    # Check for relevant degrees
                    if any(keyword in degree for keyword in ["bachelor", "master", "phd", "doctorate", "diploma"]):
                        if any(keyword in jd_education for keyword in ["bachelor", "master", "phd", "doctorate", "diploma"]):
                            if any(field in degree for field in ["data science", "artificial intelligence", "computer science", "statistics"]):
                                education_score = 20.0
                                break
                
                # ATS score bonus (scaled to 0-5 points)
                ats_bonus = (ats_score / 100) * 5
                
                # Total score
                total_score = skill_score + experience_score + education_score + ats_bonus
                
                ranked_resumes.append({
                    "file_name": resume["file_name"],
                    "matching_score": round(total_score, 2),
                    "matched_skills": [skill.title() for skill in matched_skills],
                    "experience": f"{total_years:.1f} years" if total_years > 0 else "N/A",
                    "education": ", ".join(resume_edu_keywords) or "N/A",
                    "ats_score": ats_score,
                    "total_years": total_years  # Added for filtering
                })
            except Exception as e:
                logger.error(f"Error matching resume {resume['file_name']}: {e}")
                ranked_resumes.append({
                    "file_name": resume["file_name"],
                    "matching_score": 0.0,
                    "matched_skills": [],
                    "experience": "N/A",
                    "education": "N/A",
                    "ats_score": resume.get("ats_score", 0.0),
                    "total_years": 0.0
                })
        
        # Sort by matching score (descending)
        ranked_resumes.sort(key=lambda x: x["matching_score"], reverse=True)
        logger.debug(f"Matched and ranked {len(ranked_resumes)} resumes")
        return ranked_resumes
    except Exception as e:
        logger.error(f"Error in match_resumes: {e}")
        return []

def filter_resumes(ranked_resumes, selected_skills=None, min_experience=0, max_experience=float('inf'), education_level=None):
    """
    Filter ranked resumes based on skills, experience, and education.
    Returns filtered list of resumes.
    """
    try:
        filtered_resumes = []
        selected_skills = set(skill.lower() for skill in (selected_skills or []))
        education_level = education_level.lower() if education_level else None

        for resume in ranked_resumes:
            try:
                # Extract resume data
                matched_skills = set(skill.lower() for skill in resume.get("matched_skills", []))
                total_years = resume.get("total_years", 0.0)
                education = resume.get("education", "").lower()

                # Skills filter
                if selected_skills and not selected_skills.issubset(matched_skills):
                    continue

                # Experience filter
                if total_years < min_experience or total_years > max_experience:
                    continue

                # Education filter
                if education_level:
                    education_keywords = {
                        "bachelor": ["bachelor", "b.sc", "b.tech", "b.e"],
                        "master": ["master", "m.sc", "m.tech", "m.e"],
                        "phd": ["phd", "doctorate"],
                        "diploma": ["diploma"]
                    }
                    if education_level in education_keywords:
                        if not any(keyword in education for keyword in education_keywords[education_level]):
                            continue
                    else:
                        continue

                filtered_resumes.append(resume)
            except Exception as e:
                logger.error(f"Error filtering resume {resume['file_name']}: {e}")
                continue

        logger.debug(f"Filtered {len(filtered_resumes)} resumes")
        return filtered_resumes
    except Exception as e:
        logger.error(f"Error in filter_resumes: {e}")
        return []

def recruiter_chat(filtered_resumes, query, jd_data):
    """
    Chat with recruiter agent to query candidate data using Gemini API.
    Returns a plain text response.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        
        # Prepare candidate data summary
        candidate_summary = []
        for resume in filtered_resumes:
            candidate_info = (
                f"File: {resume.get('file_name', 'N/A')}\n"
                f"Matching Score: {resume.get('matching_score', 0):.2f}%\n"
                f"Skills: {', '.join(resume.get('matched_skills', [])) or 'None'}\n"
                f"Experience: {resume.get('experience', 'N/A')}\n"
                f"Education: {resume.get('education', 'N/A')}\n"
                f"ATS Score: {resume.get('ats_score', 0):.2f}\n"
            )
            candidate_summary.append(candidate_info)
        candidates_text = "\n\n".join(candidate_summary)
        
        # Prepare job description summary
        jd_summary = (
            f"Skills: {', '.join(jd_data.get('skills', [])) or 'None'}\n"
            f"Experience: {jd_data.get('experience', 'N/A')}\n"
            f"Education: {jd_data.get('education', 'N/A')}"
        )
        
        prompt = f"""
        You are a recruiter assistant analyzing candidate resumes for a job role.
        Based on the filtered candidates and job description below, answer the query: "{query}".
        Provide a concise and relevant response in plain text, focusing on candidate qualifications and job requirements.
        If the query asks for specific skills or attributes, identify matching candidates by file name.
        If the query asks for a summary, provide a brief overview of the top candidates.
        
        Job Description:
        {jd_summary}
        
        Filtered Candidates:
        {candidates_text}
        
        Respond ONLY with the plain text answer, nothing else.
        """
        
        response = model.generate_content(prompt)
        answer = response.text.strip()
        logger.debug(f"Recruiter chat response: {answer}")
        return answer
    except Exception as e:
        logger.error(f"Error in recruiter chat: {e}")
        return "Error in chat response: Please check your Gemini API key or network connection."