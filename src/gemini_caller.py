import os
import json
import time
import typing
from typing import Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions

from src.resume_json_gen import resume_prompt_generator
from src.cover_letter_json_gen import cover_letter_prompt_generator

# Load key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY missing!")

genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"

def call_gemini_with_retry(system_prompt: str, user_prompt: str, configurations: Dict[str, Any], max_retries: int = 3) -> typing.Optional[typing.Dict[str, typing.Any]]:

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=configurations,
        system_instruction=system_prompt
    )

    for attempt in range(max_retries):
        try:
            response = model.generate_content(user_prompt)
            # Parse JSON directly from the response text
            return json.loads(response.text)

        except (exceptions.GoogleAPICallError, json.JSONDecodeError, ValueError) as e:
            # Handle API errors or if the model returned malformed JSON
            print(f"⚠️ Error (attempt {attempt+1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("❌ Final failure after maximum retries.")
                return None

def gemini_caller_func(job_desc):
    # Go up one level to the project root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")

    with open(os.path.join(ASSETS_DIR, "resume.json"), "r", encoding="utf-8") as f:
        base_resume = json.load(f)

    with open(os.path.join(ASSETS_DIR, "cover_letter.json"), "r", encoding="utf-8") as f:
        base_cover_letter = json.load(f)

    # --- Tailor Resume ---
    resume_payload = resume_prompt_generator(base_resume, job_desc)

    system_prompt = resume_payload["system_prompt"]
    user_prompt = resume_payload["user_prompt"]
    resume_configs = resume_payload["config"]

    tailored_resume = call_gemini_with_retry(system_prompt, user_prompt, resume_configs)

    # resume_as_args = json.dumps(tailored_resume, indent=2, ensure_ascii=False)
    
    # --- Tailor Cover Letter ---
    cover_payload = cover_letter_prompt_generator(
        tailored_resume,
        job_desc,
        base_cover_letter
    )

    system_prompt = cover_payload["system_prompt"]
    user_prompt = cover_payload["user_prompt"]
    cover_configs = cover_payload["config"]

    tailored_cover_letter = call_gemini_with_retry(system_prompt, user_prompt, cover_configs)

    return tailored_resume ,tailored_cover_letter
