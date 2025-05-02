import streamlit as st
from auth import login, signup
from utils import load_lottie_animation
from db import initialize_database
from resume_analyzer import extract_text_from_pdf, parse_resume, analyze_resume, generate_recommendations, chat_with_resume, generate_ats_chart
from reports import generate_pdf_report
import sqlite3
import bcrypt
import logging
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Streamlit app configuration
try:
    st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")
    logger.debug("Streamlit page configuration set")
except Exception as e:
    logger.error(f"Failed to set page config: {e}")
    st.error(f"Failed to initialize app: {e}")

# Custom CSS for engaging UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2e7d32;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #c8e6c9 0%, #a5d6a7 100%);
        padding: 10px;
        border-radius: 8px;
    }
    .card {
        background: linear-gradient(135deg, #d4f4e2 0%, #a3e4c1 100%);
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        padding: 15px;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .card:hover {
        transform: translateY(-5px);
    }
    .subheader {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1F2937;
        margin-bottom: 1rem;
    }
    .text {
        color: #81c784;
        font-size: 1rem;
    }
    .highlight {
        color: #4CAF50;
        font-size: 1.1rem;
        font-weight: bold;
    }
    .recommendation {
        color: #FFFFFF;
        font-size: 1.1rem;
        font-weight: normal;
    }
    .button {
        background-color: #2563EB;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
        display: inline-block;
        cursor: pointer;
    }
    .button:hover {
        background-color: #1E40AF;
    }
    .sidebar .text {
        text-align: center;
        color: #81c784;
    }
    .stSpinner > div {
        display: flex;
        justify-content: center;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
try:
    initialize_database()
    logger.debug("Database initialized")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    st.error(f"Database initialization failed: {e}")

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None
logger.debug("Session state initialized")

def reset_password(username, new_password):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        username_lower = username.lower()
        c.execute('SELECT username FROM users WHERE username = ?', (username_lower,))
        if c.fetchone():
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            c.execute('UPDATE users SET password = ? WHERE username = ?', (hashed, username_lower))
            conn.commit()
            logger.debug(f"Password reset for user: {username_lower}")
            return True
        else:
            logger.error(f"User not found: {username_lower}")
            return False
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")
        return False
    finally:
        conn.close()

def display_auth_page():
    try:
        st.markdown('<div class="main-header">AI Resume Analyzer</div>', unsafe_allow_html=True)
        
        with st.sidebar:
            try:
                load_lottie_animation("https://assets5.lottiefiles.com/packages/lf20_xyadoh9h.json")
            except Exception as e:
                st.warning(f"Failed to load animation: {e}")
            st.markdown('<div class="text">Welcome to the AI Resume Analyzer!</div>', unsafe_allow_html=True)
        
        with st.container():
            role = st.selectbox("Select Your Role", ["Job Seeker", "Recruiter"], key="role_select")
            st.markdown(f'<div class="text">You are signing up or logging in as a <b>{role}</b>. Ensure your account matches this role.</div>', unsafe_allow_html=True)
        
        auth_option = st.radio("Choose an option", ["Login", "Sign Up", "Reset Password"], key="auth_option")
        
        if auth_option == "Sign Up":
            with st.container():
                st.markdown(f'<div class="card"><div class="subheader">Sign Up as {role}</div>', unsafe_allow_html=True)
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                if st.button("Sign Up", key="signup_button"):
                    if not username or not password or not confirm_password:
                        st.error("All fields are required")
                    elif password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        try:
                            role_lower = role.lower().replace(" ", "_")
                            if role_lower not in ["job_seeker", "recruiter"]:
                                st.error("Invalid role selected")
                                logger.error(f"Invalid role: {role_lower}")
                            else:
                                signup(username, password, role_lower)
                                st.success(f"Account created for {username}! Please log in.")
                                logger.debug(f"User {username} signed up as {role}")
                        except Exception as e:
                            st.error(f"Error in signup: {e}")
                            logger.error(f"Signup error: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        elif auth_option == "Login":
            with st.container():
                st.markdown(f'<div class="card"><div class="subheader">Login as {role}</div>', unsafe_allow_html=True)
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Login", key="login_button"):
                    try:
                        authentication_status, username, user_role = login(username, password)
                        if authentication_status:
                            expected_role = role.lower().replace(" ", "_")
                            if user_role == expected_role:
                                st.session_state['authenticated'] = True
                                st.session_state['username'] = username
                                st.session_state['role'] = user_role
                                st.success(f"Welcome, {username}!")
                                logger.debug(f"User {username} logged in as {user_role}")
                                st.rerun()
                            else:
                                st.warning(f"Role mismatch: Your account is registered as {user_role.replace('_', ' ').title()}. Proceeding as {user_role.replace('_', ' ').title()}.")
                                st.session_state['authenticated'] = True
                                st.session_state['username'] = username
                                st.session_state['role'] = user_role
                                logger.debug(f"User {username} logged in with role mismatch, proceeding as {user_role}")
                                st.rerun()
                        else:
                            st.error("Username or password is incorrect. Usernames are case-insensitive.")
                            logger.error("Login failed: incorrect username/password")
                    except Exception as e:
                        st.error(f"Error in login: {e}")
                        logger.error(f"Login error: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        elif auth_option == "Reset Password":
            with st.container():
                st.markdown(f'<div class="card"><div class="subheader">Reset Password</div>', unsafe_allow_html=True)
                username = st.text_input("Username", key="reset_username")
                new_password = st.text_input("New Password", type="password", key="reset_password")
                confirm_password = st.text_input("Confirm New Password", type="password", key="reset_confirm_password")
                if st.button("Reset Password", key="reset_button"):
                    if not username or not new_password or not confirm_password:
                        st.error("All fields are required")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        if reset_password(username, new_password):
                            st.success(f"Password reset for {username}! Please log in.")
                            logger.debug(f"Password reset for {username}")
                        else:
                            st.error("Username not found. Usernames are case-insensitive.")
                            logger.error(f"Password reset failed: Username {username} not found")
                st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error in auth page: {e}")
        st.error(f"Failed to render auth page: {e}")

def format_recommendations(recommendations, job_role):
    """Format recommendations to avoid repeating job role and use bullets"""
    try:
        # Split recommendations into lines
        lines = recommendations.split('\n')
        formatted = []
        job_role_prefix = f"For {job_role}:"
        for line in lines:
            line = line.strip()
            if line.startswith(job_role_prefix):
                # Remove the job role prefix
                formatted.append(f"- {line[len(job_role_prefix):].strip()}")
            elif line.startswith("ATS Tip:") or line.startswith("Add for"):
                # Keep ATS Tip and Add lines as is
                formatted.append(f"- {line}")
            elif line:
                # Include any other non-empty lines
                formatted.append(f"- {line}")
        return '\n'.join(formatted) if formatted else recommendations
    except Exception as e:
        logger.error(f"Error formatting recommendations: {e}")
        return recommendations

def display_dashboard():
    try:
        st.markdown(f'<div class="main-header">Welcome, {st.session_state["username"]}!</div>', unsafe_allow_html=True)
        
        with st.sidebar:
            try:
                load_lottie_animation("https://assets5.lottiefiles.com/packages/lf20_xyadoh9h.json")
            except Exception as e:
                st.warning(f"Failed to load animation: {e}")
            st.markdown(f'<div class="text">Logged in as {st.session_state["username"]} ({st.session_state["role"].replace("_", " ").title()})</div>', unsafe_allow_html=True)
            if st.button("Logout"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state['authenticated'] = False
                st.session_state['username'] = None
                st.session_state['role'] = None
                logger.debug("User logged out")
                st.rerun()
        
        if st.session_state['role'] == "job_seeker":
            st.markdown('<div class="card"><div class="subheader">Job Seeker Dashboard</div>', unsafe_allow_html=True)
            col1, col2 = st.columns([3, 1])
            with col1:
                uploaded_file = st.file_uploader("Upload Your Resume (PDF)", type="pdf")
            with col2:
                st.markdown('<div class="text mt-4">Supported formats: PDF</div>', unsafe_allow_html=True)
            
            if uploaded_file:
                try:
                    with st.spinner("Analyzing resume..."):
                        logger.debug("Processing uploaded resume")
                        text = extract_text_from_pdf(uploaded_file)
                        parsed_data = parse_resume(uploaded_file)
                        st.markdown('<div class="card"><div class="subheader">Target Job Role</div>', unsafe_allow_html=True)
                        st.markdown('<div class="text">This helps tailor recommendations and chat responses to your job goals.</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        job_role = st.text_area("Enter the job role or job description you are targeting (optional):", height=100)
                        analysis = analyze_resume(text, job_role)
                        
                        if "error" in parsed_data:
                            st.warning(f"Resume parsing failed: {parsed_data['error']}. Proceeding with text-based analysis.")
                            parsed_data = {
                                "personal_info": {"name": "N/A", "email": "N/A"},
                                "skills": [],
                                "education": [{"degree": "N/A", "institution": "N/A", "graduation_date": "N/A", "gpa": "N/A"}],
                                "experience": [{"title": "N/A", "company": "N/A", "duration": "N/A", "description": []}],
                                "projects": [{"name": "N/A", "description": "", "technologies": []}],
                                "certifications": []
                            }
                        
                        st.markdown('<div class="card"><div class="subheader">Resume Analysis</div>', unsafe_allow_html=True)
                        st.markdown(f"""
                        - <span class="highlight">ATS Score</span>: {analysis['ats_score']:.2f}
                        - <span class="highlight">Word Count</span>: {analysis['word_count']}
                        - <span class="highlight">Skills Detected</span>: {', '.join(analysis['skills'])}
                        """, unsafe_allow_html=True)
                        st.plotly_chart(generate_ats_chart(analysis), use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="card"><div class="subheader">Parsed Resume Data</div>', unsafe_allow_html=True)
                        st.markdown(f"- <span class=\"highlight\">Name</span>: {parsed_data['personal_info'].get('name', 'N/A')}", unsafe_allow_html=True)
                        st.markdown(f"- <span class=\"highlight\">Email</span>: {parsed_data['personal_info'].get('email', 'N/A')}", unsafe_allow_html=True)
                        st.markdown("<span class=\"highlight\">Education</span>:", unsafe_allow_html=True)
                        for edu in parsed_data['education']:
                            st.markdown(f"  - {edu.get('degree', 'N/A')} at {edu.get('institution', 'N/A')}, {edu.get('graduation_date', 'N/A')} (GPA: {edu.get('gpa', 'N/A')})", unsafe_allow_html=True)
                        st.markdown("<span class=\"highlight\">Experience</span>:", unsafe_allow_html=True)
                        for exp in parsed_data['experience']:
                            st.markdown(f"  - {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('duration', 'N/A')})", unsafe_allow_html=True)
                            for desc in exp.get('description', []):
                                st.markdown(f"    - {desc}", unsafe_allow_html=True)
                        st.markdown(f"- <span class=\"highlight\">Skills</span>: {', '.join(parsed_data['skills']) if parsed_data['skills'] else 'None'}", unsafe_allow_html=True)
                        st.markdown("<span class=\"highlight\">Projects</span>:", unsafe_allow_html=True)
                        for proj in parsed_data['projects']:
                            st.markdown(f"  - {proj.get('name', 'N/A')}: {proj.get('description', 'No description')}", unsafe_allow_html=True)
                            st.markdown(f"    Technologies: {', '.join(proj.get('technologies', []))}", unsafe_allow_html=True)
                        st.markdown(f"- <span class=\"highlight\">Certifications</span>: {', '.join(parsed_data['certifications']) if parsed_data['certifications'] else 'None'}", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        recommendations = generate_recommendations(analysis, job_role)
                        formatted_recommendations = format_recommendations(recommendations, job_role if job_role else "the job role")
                        st.markdown('<div class="card"><div class="subheader">Recommendations</div>', unsafe_allow_html=True)
                        st.markdown(f'<span class="recommendation">{formatted_recommendations}</span>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="card"><div class="subheader">Chat with Resume Reviewer</div>', unsafe_allow_html=True)
                        user_query = st.text_input("Ask a question about your resume:")
                        if user_query:
                            with st.spinner("Generating response..."):
                                response = chat_with_resume(text, user_query, job_role)
                                st.markdown(f'<span class="recommendation">{response}</span>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="card"><div class="subheader">Download Report</div>', unsafe_allow_html=True)
                        pdf_buffer = generate_pdf_report(analysis, recommendations)
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_buffer,
                            file_name="resume_analysis_report.pdf",
                            mime="application/pdf",
                            key="download_button",
                            help="Click to download your resume analysis report"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error processing resume: {e}")
                    logger.error(f"Resume processing error: {e}")
            else:
                st.markdown('<div class="text">Upload your resume to get started!</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state['role'] == "recruiter":
            st.markdown('<div class="card"><div class="subheader">Recruiter Dashboard</div>', unsafe_allow_html=True)
            st.markdown('<div class="text">Upload job description and resumes to screen candidates! (Coming soon)</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        st.error(f"Failed to render dashboard: {e}")

try:
    if not st.session_state['authenticated']:
        display_auth_page()
    else:
        display_dashboard()
    logger.debug("Page rendered successfully")
except Exception as e:
    logger.error(f"Failed to render page: {e}")
    st.error(f"Application error: {e}")