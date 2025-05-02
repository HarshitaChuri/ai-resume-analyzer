AI Resume Analyzer
AI Resume Analyzer is a Streamlit-based web application designed to help job seekers optimize their resumes. It allows users to upload PDF resumes, parse key information (personal info, education, experience, skills, projects, certifications), calculate an ATS (Applicant Tracking System) score, provide tailored recommendations, offer a chat assistant powered by Gemini AI, and generate a PDF report. The app features an engaging UI with gradient cards, Lottie animations, and a responsive layout.
This project was inspired by Smart-AI-Resume-Analyzer(https://github.com/Hunterdii/Smart-AI-Resume-Analyzer). While we drew inspiration from its concept and features, this implementation is original, with custom code and enhancements tailored to our requirements.

Features :

User Authentication: Login and signup for Job Seekers and Recruiters, with password hashing using bcrypt.
Resume Parsing: Extracts structured data from PDF resumes using pdfplumber and Gemini-2.0-flash-001.
ATS Score: Displays a doughnut chart (#4CAF50 score, transparent background) with an ATS compatibility score .
Recommendations: Provides job-role-specific tips, ATS optimization advice, and missing skills .
Chat Assistant: Powered by Gemini-2.0-flash-001, answers resume-related queries.
PDF Report: Generates a downloadable report with analysis and recommendations using reportlab.
UI: Gradient cards (#d4f4e2 to #a3e4c1), header (#c8e6c9 to #a5d6a7), #2563EB buttons, #81c784 text, #4CAF50 metrics, Lottie animations.
