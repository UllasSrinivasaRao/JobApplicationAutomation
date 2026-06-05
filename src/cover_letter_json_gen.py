# cover_letter_json_gen.py
import json
from datetime import datetime
from langdetect import detect

def cover_letter_prompt_generator(updated_resume_json: dict, job_description: str, base_cover_letter: dict, feedback: str = ""):
    """
    Generates system + user prompts for Gemini to produce
    an ATS-optimized cover letter JSON (using the corrected SDK format).
    """

    # --- Detect language of the JD ---
    try:
        lang = detect(job_description)
    except Exception:
        lang = "en"

    lang_text = "German" if lang == "de" else "English"

    # --- Today's date ---
    current_date = datetime.now().strftime("%d.%m.%Y")

    # --- SYSTEM PROMPT ---
    system_prompt = (f"""
        f"You are an expert in writing professional, localized ({lang_text}) cover letters "
        "for software, AI, and tech roles. Generate a tailored cover letter JSON based on "
        "the provided job description and tailored resume, keeping all applicant details unchanged.\n\n"
        "=== RULES ===\n"
        "1️⃣ Maintain the same JSON structure and all field names as the base JSON.\n"
        "2️⃣ DO NOT modify:\n"
        "   - cover_letter.applicant\n"
        "   - cover_letter.location\n"
        "   - cover_letter.signature\n"
        "3️⃣ From the job description, automatically detect and update:\n"
        "   - cover_letter.company.name → Extract the company name.\n"
        "   - cover_letter.company.contact_person → Extract the contact person.\n"
        "4️⃣ Rewrite and tailor:\n"
        "   - cover_letter.subject → Reflect the job title.\n"
        "   - cover_letter.date → Replace with today's date (DD.MM.YYYY).\n"
        "   - All text inside cover_letter.body (introduction, desired_role, skills, motivation, closing).\n"
        "5️⃣ STRICT WORD LIMIT: The *entire body section* (introduction + desired_role + skills + "
        "motivation + closing) MUST NOT exceed **300 words total**.\n"
        "6️⃣ Use the tailored resume naturally to support the content.\n"
        "7️⃣ Write in the same language as the job description.\n"
        "8️⃣ Maintain a formal, confident, concise tone.\n"
        "9️⃣ Output must be valid JSON only — no comments, no extra text."
    """)

    feedback_section = ""
    if feedback:
        feedback_section = f"\n        === FEEDBACK FROM PREVIOUS ATTEMPT ===\n        The previous generated documents had the following issues. Please fix any issues relevant to the Cover Letter:\n        {feedback}\n"

    # --- USER PROMPT ---
    user_prompt = (f"""
        === JOB DESCRIPTION ===
        {job_description}

        === TAILORED RESUME JSON ===
        {json.dumps(updated_resume_json, indent=2)}

        === BASE COVER LETTER TEMPLATE JSON ===
        {json.dumps(base_cover_letter, indent=2)}
        {feedback_section}

        Your tasks:
        - Update the cover letter JSON.
        - Apply the rules strictly.
        - Use today's date: {current_date}
        - DO NOT modify applicant, location, or signature fields.
        - Return ONLY valid JSON. No commentary.
    """)

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "config": {
            "temperature": 0.4,
            "top_p": 0.9,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json"
        }
    }
