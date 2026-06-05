# resume_json_gen.py
import json
from langdetect import detect

def resume_prompt_generator(master_data: dict, job_description: str, feedback: str = ""):
    """
    Builds system + user prompts for Gemini to generate an
    ATS-optimized, job-tailored resume JSON.
    
    This version is compatible with google.generativeai SDK.
    """

    # --- Detect language of the job description ---
    try:
        lang = detect(job_description)
    except Exception:
        lang = "en"

    lang_text = "German" if lang == "de" else "English"

    # --- SYSTEM PROMPT ---
    system_prompt = (f"""
        You are a professional ATS-optimized resume writer and a domain expert.
        Your job is to tailor the provided resume JSON to match the target Job Description (JD)
        while keeping it truthful, consistent, and structurally identical.

        === RULES ===
        1️⃣ Maintain the EXACT JSON structure — do NOT rename or delete fields.
        2️⃣ You may reorder, edit, add, or remove items INSIDE LISTS only.
           Examples: technical_skills[] categories, contributions[], highlighted_projects[].contributions
        3️⃣ Technical skills rules:
           - Reorder skills based on JD relevance.
           - Remove irrelevant categories.
           - Add realistic skills implied by the JD (e.g., HTML/CSS if React is present).
        4️⃣ Rewrite work experience contributions to fit the JD focus.
        5️⃣ Rewrite project contributions to align with JD requirements (AI, backend, etc.).
        6️⃣ Soft skills may be refined or reordered.
        7️⃣ NEVER modify: personal_details, education, or any static fields.
        8️⃣ Keep everything realistic — no fabricated experience.
        9️⃣ Match the language of the JD: **{lang_text}**
        🔟 Output MUST be a single valid JSON object. No explanations.
    """)

    feedback_section = ""
    if feedback:
        feedback_section = f"\n        === FEEDBACK FROM PREVIOUS ATTEMPT ===\n        The previous generated CV had the following issues. Please fix them:\n        {feedback}\n"

    # --- USER PROMPT ---
    user_prompt = (f"""
        === TARGET JOB DESCRIPTION ===
        {job_description}

        === ORIGINAL RESUME JSON ===
        {json.dumps(master_data, indent=2)}
        {feedback_section}

        Your task:
        - Update ONLY the JSON content, not the structure.
        - Reorder skills, experience, and projects to match the JD.
        - Rewrite contributions for maximum relevance.
        - Return ONLY the updated JSON object.
    """)

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "config": {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json"
        }
    }
