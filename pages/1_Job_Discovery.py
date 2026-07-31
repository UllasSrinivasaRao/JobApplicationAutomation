# pages/1_Job_Discovery.py
"""Review queue for discovered jobs — approve one and it prefills the generator."""

import streamlit as st

from src.jobs.schema import STATUS_APPROVED, STATUS_SKIPPED, STATUS_NEW, load_criteria
from src.jobs.store import load_jobs, save_jobs

st.set_page_config(page_title="Job Discovery", page_icon="🔎", layout="wide")
st.title("🔎 Job Discovery")

jobs = load_jobs()

if not jobs:
    st.info(
        "No jobs discovered yet.\n\n"
        "Run a discovery pass first:\n\n"
        "```\nuv run python discover_jobs.py --limit 10\n```"
    )
    st.stop()

try:
    min_score_default = load_criteria().get("min_score", 0.55)
except FileNotFoundError:
    min_score_default = 0.55

# ---------------------------
# Filters
# ---------------------------

col1, col2, col3 = st.columns([2, 2, 3])

with col1:
    status_filter = st.selectbox(
        "Status",
        ["new", "approved", "skipped", "applied", "all"],
        index=0,
    )

with col2:
    min_score = st.slider("Minimum score", 0.0, 1.0, float(min_score_default), 0.05)

with col3:
    search_text = st.text_input("Filter by title or company", "")

visible = []
for job in jobs.values():
    if status_filter != "all" and job.status != status_filter:
        continue
    if job.score is not None and job.score < min_score:
        continue
    if search_text:
        haystack = f"{job.title} {job.company}".lower()
        if search_text.lower() not in haystack:
            continue
    visible.append(job)

visible.sort(key=lambda j: (j.score if j.score is not None else -1.0), reverse=True)

counts = {}
for job in jobs.values():
    counts[job.status] = counts.get(job.status, 0) + 1

st.caption(
    f"Showing {len(visible)} of {len(jobs)} jobs · "
    + " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
)

st.divider()

if not visible:
    st.warning("No jobs match these filters. Try lowering the minimum score.")
    st.stop()


# ---------------------------
# Job cards
# ---------------------------

def set_status(job_id: str, status: str) -> None:
    store = load_jobs()
    if job_id in store:
        store[job_id].status = status
        save_jobs(store)


for job in visible:
    score_label = f"{job.score:.2f}" if job.score is not None else "—"
    header = f"**{score_label}** · {job.title or '(untitled)'}"
    if job.company:
        header += f" · {job.company}"

    with st.expander(header, expanded=False):
        meta_col, action_col = st.columns([3, 1])

        with meta_col:
            if job.location:
                st.caption(f"📍 {job.location}")
            if job.posted_at:
                st.caption(f"🗓️ Posted {job.posted_at}")
            st.caption(f"🔗 [{job.source}]({job.url})")
            if job.score_reason:
                st.info(f"**Why this score:** {job.score_reason}")

        with action_col:
            if st.button("✅ Use this job", key=f"use_{job.id}", use_container_width=True):
                st.session_state.prefill_title = job.title
                st.session_state.prefill_jd = job.description
                set_status(job.id, STATUS_APPROVED)
                st.success("Loaded! Open the main page to generate documents.")

            if st.button("⏭️ Skip", key=f"skip_{job.id}", use_container_width=True):
                set_status(job.id, STATUS_SKIPPED)
                st.rerun()

            if job.status != STATUS_NEW:
                if st.button("↩️ Reset", key=f"reset_{job.id}", use_container_width=True):
                    set_status(job.id, STATUS_NEW)
                    st.rerun()

        st.text_area(
            "Job description",
            value=job.description,
            height=280,
            key=f"desc_{job.id}",
            disabled=True,
        )
