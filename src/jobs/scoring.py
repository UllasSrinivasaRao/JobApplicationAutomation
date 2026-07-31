# scoring.py
"""Score how well a job fits your actual resume, using Groq.

This is the step that makes discovery useful: keyword filters let through a lot
of noise, but an LLM reading the JD against your real experience can tell the
difference between "Werkstudent Softwareentwicklung" and "Werkstudent Vertrieb
with a website to maintain".
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from src.jobs.schema import Job, BASE_DIR

MODEL_NAME = "llama-3.3-70b-versatile"
MAX_JD_CHARS = 6000

_client: Groq | None = None
_resume_summary: str | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("❌ GROQ_API_KEY missing! Please add it to your .env file.")
        _client = Groq(api_key=api_key)
    return _client


def _get_resume_summary() -> str:
    """A compact profile built from resume.json — cheaper than sending the whole thing."""
    global _resume_summary
    if _resume_summary is not None:
        return _resume_summary

    resume_path = Path(BASE_DIR) / "assets" / "resume.json"
    with open(resume_path, "r", encoding="utf-8") as f:
        resume = json.load(f)

    skills = []
    for category, items in resume.get("technical_skills", {}).items():
        skills.append(f"{category}: {', '.join(items)}")

    roles = [
        f"{job.get('role')} at {job.get('company')} ({job.get('time_period')})"
        for job in resume.get("work_experience", [])
    ]

    education = [
        f"{edu.get('degree')} — {edu.get('institution')} ({edu.get('time_period')})"
        for edu in resume.get("education", [])
    ]

    languages = [f"{l.get('name')} ({l.get('level')})" for l in resume.get("languages", [])]

    _resume_summary = (
        f"SUMMARY:\n{resume.get('professional_summary', '')}\n\n"
        f"SKILLS:\n" + "\n".join(skills) + "\n\n"
        f"EXPERIENCE:\n" + "\n".join(roles) + "\n\n"
        f"EDUCATION:\n" + "\n".join(education) + "\n\n"
        f"LANGUAGES: {', '.join(languages)}"
    )
    return _resume_summary


SYSTEM_PROMPT = """
You assess how well a candidate fits a job posting.

Return ONLY a JSON object:
{
  "score": a number between 0.0 and 1.0,
  "reason": "one short sentence explaining the score"
}

SCORING GUIDE
- 0.8-1.0: strong match. The core tech and the seniority both fit.
- 0.6-0.8: good match. Most requirements fit; some gaps are learnable.
- 0.4-0.6: partial match. Right field, but notable mismatch in stack or level.
- 0.0-0.4: poor match. Wrong field, or requires seniority/qualifications the candidate lacks.

IMPORTANT
- The candidate is a Master's student seeking working-student / junior roles.
  A posting demanding 5+ years or a team lead should score low.
- German language requirement matters: the candidate is B1 German, C1 English.
  A role requiring fluent/native German for client-facing work should score lower.
- Judge on substance, not on how nicely the posting is written.
"""


def score_job(job: Job) -> tuple[float, str]:
    """Return (score, reason). Falls back to a neutral score if the call fails."""
    if not job.description or len(job.description) < 150:
        return 0.0, "no usable job description available"

    user_message = (
        f"CANDIDATE PROFILE:\n{_get_resume_summary()}\n\n"
        f"JOB POSTING:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n\n"
        f"{job.description[:MAX_JD_CHARS]}"
    )

    try:
        completion = _get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        data = json.loads(completion.choices[0].message.content)
        score = float(data.get("score", 0.0))
        reason = str(data.get("reason", "")).strip()
        return max(0.0, min(1.0, score)), reason
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"   ⚠️ Could not parse score for '{job.title}': {e}")
        return 0.0, "scoring failed"
    except Exception as e:
        print(f"   ⚠️ Scoring call failed for '{job.title}': {e}")
        return 0.0, "scoring failed"
