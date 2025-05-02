import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Test the API
try:
    model = genai.GenerativeModel('gemini-2.0-flash-001')
    response = model.generate_content("Test")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")