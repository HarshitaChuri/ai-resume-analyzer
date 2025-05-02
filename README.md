AI Resume Analyzer
AI Resume Analyzer is a Streamlit-based web application designed to help job seekers optimize their resumes. It allows users to upload PDF resumes, parse key information (personal info, education, experience, skills, projects, certifications), calculate an ATS (Applicant Tracking System) score, provide tailored recommendations, offer a chat assistant powered by Gemini AI, and generate a PDF report. The app features an engaging UI with gradient cards, Lottie animations, and a responsive layout.
This project was inspired by Smart-AI-Resume-Analyzer (replace with actual repo URL if available). While we drew inspiration from its concept and features, this implementation is original, with custom code and enhancements tailored to our requirements.
Features

User Authentication: Login and signup for Job Seekers and Recruiters, with password hashing using bcrypt.
Resume Parsing: Extracts structured data from PDF resumes using pdfplumber and Gemini-2.0-flash-001.
ATS Score: Displays a doughnut chart (#4CAF50 score, transparent background) with an ATS compatibility score (~75/100).
Recommendations: Provides job-role-specific tips, ATS optimization advice, and missing skills in white text (#FFFFFF).
Chat Assistant: Powered by Gemini-2.0-flash-001, answers resume-related queries in white text.
PDF Report: Generates a downloadable report with analysis and recommendations using reportlab.
UI: Gradient cards (#d4f4e2 to #a3e4c1), header (#c8e6c9 to #a5d6a7), #2563EB buttons, #81c784 text, #4CAF50 metrics, Lottie animations.

Prerequisites

Python 3.8+
Git
GitHub account
Streamlit Community Cloud account
Google Gemini API key

Installation

Clone the Repository:git clone https://github.com/bhavishachuri/ai-resume-analyzer.git
cd ai-resume-analyzer


Create a Virtual Environment:python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux


Install Dependencies:pip install -r requirements.txt


Set Up Environment Variables:
Create a .env file in the root directory:GEMINI_API_KEY=your-api-key


Obtain a Gemini API key from Google AI Studio.


Download NLTK Data:python -c "import nltk; nltk.download('punkt_tab')"


Run Locally:streamlit run app.py


Open http://localhost:8501 in your browser.



Deployment on Streamlit Community Cloud

Push to GitHub:
Ensure all files (except .env, users.db) are committed:git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main




Sign Up for Streamlit Community Cloud:
Visit share.streamlit.io and sign in with GitHub.
Authorize Streamlit to access your public repositories.


Deploy the App:
Click "New app" in your Streamlit Cloud dashboard.
Select your repository: bhavishachuri/ai-resume-analyzer.
Choose branch: main.
Set main file path: app.py.
Click "Advanced settings":
Add a secret for GEMINI_API_KEY (paste your Gemini API key).


Click "Deploy".
Wait ~5-10 minutes for deployment. You’ll get a URL like https://bhavishachuri-ai-resume-analyzer.streamlit.app.


Note:
The users.db file is recreated on Streamlit Cloud (empty initially).
Users must sign up again to use the app.
The free tier allows up to 3 apps.



Usage

Login/Sign Up:
Use credentials (e.g., bhavisha/password123) or create a new account.


Upload Resume:
Upload a PDF resume (e.g., Chanchal Budhadeo.pdf).


Enter Job Role:
Input a target job role, e.g., “Data Scientist: Proficient in Python, SQL, machine learning, data visualization”.


View Analysis:
ATS Score: ~75/100 in a doughnut chart.
Parsed Data: Name, email, education, experience, skills, projects, certifications.
Recommendations: Job-specific tips, ATS advice, missing skills (e.g., Pandas, TensorFlow).
Chat: Ask questions like “How to improve for machine learning roles?”.
PDF Report: Download analysis and recommendations.



Limitations

Supports only PDF resumes (no DOCX).
No course suggestions or resume draft export.
Recruiter dashboard is under development.

Credits

Inspired by Smart-AI-Resume-Analyzer (replace with actual repo URL).
Built with Streamlit, Gemini AI, and other open-source libraries.

License
MIT License. See LICENSE for details.
Contributing
Feel free to fork, submit issues, or create pull requests. Please follow the contributing guidelines.
