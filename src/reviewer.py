import os
import json
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

def review_cv(cv_data, job_description):
    load_dotenv()
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise ValueError("❌ CEREBRAS_API_KEY missing! Please add it to your .env file.")
        
    client = Cerebras(api_key=api_key)
    
    # Convert dict to JSON string if necessary
    if isinstance(cv_data, dict):
        cv_json = json.dumps(cv_data, indent=2)
    else:
        cv_json = str(cv_data)

    system_message = """
    You are a Senior Technical Recruiter. Your task is to review a CV (provided in JSON) 
    against a Job Description. 
    
    CRITERIA:
    1. Does the CV use quantifiable results (numbers, %)?
    2. Does it match the key skills in the Job Description?
    3. Is the tone professional and action-oriented?

    OUTPUT RULES:
    - If the CV is great, start your response with [APPROVED].
    - If it needs changes, start with [REVISE] and list bullet points of EXACTLY what to fix.
    """

    user_message = f"JOB DESCRIPTION:\n{job_description}\n\nCV JSON:\n{cv_json}"

    response = client.chat.completions.create(
        model="llama3.1-8b",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content

def review_cover_letter(cv_data, cover_letter_data, job_description):
    load_dotenv()
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise ValueError("❌ CEREBRAS_API_KEY missing! Please add it to your .env file.")
        
    client = Cerebras(api_key=api_key)
    
    if isinstance(cv_data, dict):
        cv_json = json.dumps(cv_data, indent=2)
    else:
        cv_json = str(cv_data)

    if isinstance(cover_letter_data, dict):
        cl_json = json.dumps(cover_letter_data, indent=2)
    else:
        cl_json = str(cover_letter_data)

    system_message = """
    You are a Senior Technical Recruiter. Your task is to review a Cover Letter (provided in JSON) 
    against a Job Description and the candidate's CV.
    
    CRITERIA:
    1. Does the cover letter match the key skills in the Job Description and CV?
    2. Is the tone professional, action-oriented, and confident?
    3. Is the cover letter tailored specifically to the company and role, not generic?

    OUTPUT RULES:
    - If the Cover Letter is great, start your response with [APPROVED].
    - If it needs changes, start with [REVISE] and list bullet points of EXACTLY what to fix in the Cover Letter.
    """

    user_message = f"JOB DESCRIPTION:\n{job_description}\n\nCV JSON:\n{cv_json}\n\nCOVER LETTER JSON:\n{cl_json}"

    response = client.chat.completions.create(
        model="llama3.1-8b",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content
