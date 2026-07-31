# app.py
import streamlit as st
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from io import BytesIO

from src.groq_caller import generate_tailored_resume, generate_tailored_cover_letter
from src.reviewer import review_cv, review_cover_letter

# ---------------------------
# PDF GENERATION FUNCTIONS
# ---------------------------

def render_template(template_file, context):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_file)
    return template.render(context)

def generate_pdf_from_html(html_string):
    pdf_io = BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_io)
    if pisa_status.err:
        raise Exception("Failed to generate PDF.")
    pdf_io.seek(0)
    return pdf_io


# ---------------------------
# STREAMLIT UI
# ---------------------------

st.title("ATS-Tailored Resume Generator")

job_title = st.text_input("Job Title", value=st.session_state.get("prefill_title", ""))
job_desc = st.text_area("Job Description", value=st.session_state.get("prefill_jd", ""), height=250)

# Initialize session state vars
if "resume" not in st.session_state:
    st.session_state.resume = None
if "cover_letter" not in st.session_state:
    st.session_state.cover_letter = None
if "review_history" not in st.session_state:
    st.session_state.review_history = []

if st.button("Generate"):
    if not job_desc:
        st.error("Please enter the job description.")
        st.stop()
        
    st.session_state.review_history = []

    st.info("🤖 AI Agents are working... (This may take a few loops)")

    # --- PHASE 1: THE CV LOOP ---
    attempts = 0
    max_attempts = 3
    feedback = ""
    resume = None
    
    while attempts < max_attempts:
        attempts += 1
        with st.status(f"Phase 1: Tailoring & Reviewing CV (Attempt {attempts})...") as status:
            try:
                # 1. Generate
                resume = generate_tailored_resume(job_desc, feedback=feedback)

                # 2. Review
                review_result = review_cv(resume, job_desc)
                
                # Show feedback
                st.markdown("#### Reviewer Feedback")
                st.markdown(review_result)
                
                st.session_state.review_history.append({
                    "phase": "CV",
                    "attempt": attempts,
                    "feedback": review_result
                })

                if "[APPROVED]" in review_result:
                    status.update(label="✅ CV Review Passed!", state="complete")
                    break
                else:
                    status.update(label=f"❌ CV Revision required (Attempt {attempts})", state="running")
                    feedback = review_result 
            except Exception as e:
                status.update(label=f"❌ Error: {e}", state="error")
                break
        
    if attempts == max_attempts and resume:
        st.warning("Reached max refinements for CV. Using latest version.")
        
    if not resume:
        st.stop()
        
    # Save the resume
    st.session_state.resume = resume

    # --- PHASE 2: THE COVER LETTER LOOP ---
    attempts = 0
    feedback = ""
    cover_letter = None

    while attempts < max_attempts:
        attempts += 1
        with st.status(f"Phase 2: Tailoring & Reviewing Cover Letter (Attempt {attempts})...") as status:
            try:
                # 1. Generate
                cover_letter = generate_tailored_cover_letter(resume, job_desc, feedback=feedback)

                # 2. Review
                review_result = review_cover_letter(resume, cover_letter, job_desc)
                
                # Show feedback
                st.markdown("#### Reviewer Feedback")
                st.markdown(review_result)
                
                st.session_state.review_history.append({
                    "phase": "Cover Letter",
                    "attempt": attempts,
                    "feedback": review_result
                })

                if "[APPROVED]" in review_result:
                    status.update(label="✅ Cover Letter Review Passed!", state="complete")
                    break
                else:
                    status.update(label=f"❌ Cover Letter Revision required (Attempt {attempts})", state="running")
                    feedback = review_result 
            except Exception as e:
                status.update(label=f"❌ Error: {e}", state="error")
                break
        
    if attempts == max_attempts and cover_letter:
        st.warning("Reached max refinements for Cover Letter. Using latest version.")

    if cover_letter:
        st.session_state.cover_letter = cover_letter
    
    if st.session_state.resume and st.session_state.cover_letter:
        st.success("Final documents ready for download!")

st.divider()

# ---------------------------
# Review History Section
# ---------------------------

if st.session_state.review_history:
    st.subheader("🕵️‍♂️ AI Review History")
    st.write("Here is the feedback from the AI Reviewer for each attempt it made to tailor your CV:")
    for review in st.session_state.review_history:
        phase_label = review.get('phase', 'CV')
        with st.expander(f"{phase_label} - Attempt {review['attempt']} Feedback"):
            st.markdown(review['feedback'])

st.divider()

# ---------------------------
# Download Section
# ---------------------------

if st.session_state.resume and st.session_state.cover_letter:
    st.subheader("📄 Download Documents")

    company_name = "Unknown"
    try:
        # Extract company name safely
        if isinstance(st.session_state.cover_letter, dict):
            company_name = st.session_state.cover_letter.get("cover_letter", {}).get("company", {}).get("name", "Unknown")
        
        # Clean up the name for safe file paths
        company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not company_name:
            company_name = "Unknown"
    except Exception:
        pass

    # Resume PDF
    resume_html = render_template(
        "resume_template.html",
        {"resume": st.session_state.resume}
    )
    resume_pdf = generate_pdf_from_html(resume_html)

    st.download_button(
        label="⬇️ Download Resume PDF",
        data=resume_pdf,
        file_name=f"Ahmed_CV_{company_name}.pdf",
        mime="application/pdf",
        key="resume_btn"
    )

    # Cover Letter PDF
    cover_html = render_template(
        "cover_letter_template.html",
        {"cover_letter": st.session_state.cover_letter["cover_letter"]}
    )
    cover_pdf = generate_pdf_from_html(cover_html)

    st.download_button(
        label="⬇️ Download Cover Letter PDF",
        data=cover_pdf,
        file_name=f"Ahmed_Cover_Letter_{company_name}.pdf",
        mime="application/pdf",
        key="cover_btn"
    )
