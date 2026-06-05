import os
import json
import time
import typing
from typing import Dict, Any
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

from src.resume_json_gen import resume_prompt_generator
from src.cover_letter_json_gen import cover_letter_prompt_generator

# Load key
load_dotenv()
API_KEY = os.getenv("CEREBRAS_API_KEY")

if not API_KEY:
    raise ValueError("❌ CEREBRAS_API_KEY missing! Please add it to your .env file.")

client = Cerebras(api_key=API_KEY)

MODEL_NAME = "llama3.1-8b"

def call_cerebras_with_retry(system_prompt: str, user_prompt: str, configurations: Dict[str, Any], max_retries: int = 3) -> typing.Optional[typing.Dict[str, typing.Any]]:

    for attempt in range(max_retries):
        try:
            # If using JSON object response format, the prompt must explicitly ask to output JSON
            response_format = None
            if configurations.get("response_mime_type") == "application/json":
                response_format = {"type": "json_object"}
                
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                model=MODEL_NAME,
                temperature=configurations.get("temperature", 0.3),
                top_p=configurations.get("top_p", 0.9),
                max_completion_tokens=configurations.get("max_output_tokens", 8192),
                response_format=response_format,
            )
            response_text = chat_completion.choices[0].message.content
            
            # Find the JSON block in the response if markdown formatting is present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            return json.loads(response_text)

        except Exception as e:
            print(f"⚠️ Error (attempt {attempt+1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("❌ Final failure after maximum retries.")
                return None

def generate_tailored_resume(job_desc, feedback=""):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")

    with open(os.path.join(ASSETS_DIR, "resume.json"), "r", encoding="utf-8") as f:
        base_resume = json.load(f)

    # --- Tailor Resume ---
    resume_payload = resume_prompt_generator(base_resume, job_desc, feedback)

    system_prompt = resume_payload["system_prompt"]
    user_prompt = resume_payload["user_prompt"]
    resume_configs = resume_payload["config"]

    tailored_resume = call_cerebras_with_retry(system_prompt, user_prompt, resume_configs)

    if not tailored_resume:
        raise Exception("Failed to generate tailored resume.")

    return tailored_resume

def generate_tailored_cover_letter(tailored_resume, job_desc, feedback=""):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")

    with open(os.path.join(ASSETS_DIR, "cover_letter.json"), "r", encoding="utf-8") as f:
        base_cover_letter = json.load(f)

    # --- Tailor Cover Letter ---
    cover_payload = cover_letter_prompt_generator(
        tailored_resume,
        job_desc,
        base_cover_letter,
        feedback
    )

    system_prompt = cover_payload["system_prompt"]
    user_prompt = cover_payload["user_prompt"]
    cover_configs = cover_payload["config"]

    tailored_cover_letter = call_cerebras_with_retry(system_prompt, user_prompt, cover_configs)
    
    if not tailored_cover_letter:
        raise Exception("Failed to generate tailored cover letter.")

    return tailored_cover_letter
