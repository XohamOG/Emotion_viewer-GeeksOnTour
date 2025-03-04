import json
import fitz  # PyMuPDF for extracting text from PDF
import google.generativeai as genai
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re
from fpdf import FPDF

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

@csrf_exempt
def upload_resume(request):
    """Handles resume upload, extracts structured information, and sends questions to frontend."""
    if request.method == "POST" and request.FILES.get("resume"):
        uploaded_file = request.FILES["resume"].read()

        # Extract text from PDF
        extracted_text = extract_text_from_pdf(uploaded_file)
        if not extracted_text:
            return JsonResponse({"error": "Failed to extract text from resume"}, status=400)

        # Process text with Gemini AI
        structured_data = parse_resume_with_gemini(extracted_text)

        # Generate interview questions (list)
        interview_questions = generate_interview_questions(structured_data)
        print(interview_questions)

        # ✅ Send questions as JSON array (list)
        return JsonResponse({"questions": interview_questions}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


def extract_text_from_pdf(pdf_bytes):
    """Extracts text from a PDF file using PyMuPDF."""
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text("text") for page in pdf_document)

    return text.strip() if text else None

def parse_resume_with_gemini(text):
    """Extracts structured resume data using Gemini API."""
    model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")

    prompt = f"""
    Extract structured data from the following resume. Identify 'Skills' and 'Experience' separately.
    Return a valid JSON output in this format:
    {{
      "Skills": ["Python", "Machine Learning", "Django"],
      "Experience": ["Software Engineer at XYZ", "Intern at ABC"]
    }}
    
    Resume:
    {text}
    """

    response = model.generate_content(prompt)

    if response and response.text:
        try:
            # Ensure valid JSON extraction (handling Gemini's extra text)
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())  # Extract only the JSON part
        except json.JSONDecodeError:
            pass  # If JSON parsing fails, return empty data

    return {"Skills": [], "Experience": []}  # Default if parsing fails

def generate_interview_questions(data):
    """Generates interview questions based on extracted resume data."""
    skills = ", ".join(data.get("Skills", []))
    experience = ", ".join(data.get("Experience", []))

    if not skills and not experience:
        return ["Describe your background and strengths."]

    prompt = f"""
    Generate 5 interview questions based on these details:
    - Skills: {skills}
    - Experience: {experience}
    
    Ensure the questions are relevant to the candidate's expertise and job role.
    Return the questions in a simple list format.
    """

    model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
    response = model.generate_content(prompt)

    return response.text.split("\n") if response and response.text else ["What are your strengths?"]