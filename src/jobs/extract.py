# extract.py
"""Turn raw job-page text into structured fields using Groq."""

import os
import json

from dotenv import load_dotenv
from groq import Groq

MODEL_NAME = "llama-3.3-70b-versatile"
MAX_INPUT_CHARS = 8000

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("❌ GROQ_API_KEY missing! Please add it to your .env file.")
        _client = Groq(api_key=api_key)
    return _client


SYSTEM_PROMPT = """
You extract job posting details from raw web page text.

Return ONLY a JSON object with exactly these keys:
{
  "is_job_posting": true or false,
  "title": "the job title, or empty string",
  "company": "the hiring company name, or empty string",
  "location": "city and/or country, or empty string",
  "description": "the full job description: responsibilities and requirements, cleaned up"
}

RULES
- Set is_job_posting to false if the text is a job LIST, a search results page,
  a company homepage, or anything that is not one specific job advert.
- Never invent details. If a field is not in the text, use an empty string.
- Keep the description in its original language (German stays German).
- The description should be plain prose, no HTML, no navigation text.
"""


def extract_job_fields(page_text: str) -> dict | None:
    """Return structured fields, or None if this page isn't a single job posting."""
    if not page_text or len(page_text) < 200:
        return None

    try:
        completion = _get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": page_text[:MAX_INPUT_CHARS]},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(completion.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"   ⚠️ Extraction returned invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"   ⚠️ Extraction call failed: {e}")
        return None

    if not data.get("is_job_posting"):
        return None
    return data
