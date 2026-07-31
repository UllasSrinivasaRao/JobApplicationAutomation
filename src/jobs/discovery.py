# discovery.py
"""Orchestrates the discovery run: search -> enrich -> filter -> score -> store."""

from src.jobs import arbeitsagentur, websearch
from src.jobs.fetch import fetch_job_description
from src.jobs.extract import extract_job_fields
from src.jobs.scoring import score_job
from src.jobs.schema import Job, load_criteria, passes_keyword_filter, make_job_id
from src.jobs.store import load_jobs, save_jobs, merge_jobs


def collect(criteria: dict) -> list[Job]:
    """Stage 1 — ask every enabled source for candidate postings."""
    jobs: list[Job] = []
    sources = criteria.get("sources", {})

    if sources.get("arbeitsagentur", {}).get("enabled", True):
        print("\n📡 Searching Arbeitsagentur...")
        jobs.extend(arbeitsagentur.search_all(criteria))

    if sources.get("websearch", {}).get("enabled", False):
        print("\n📡 Searching the web...")
        jobs.extend(websearch.search_all(criteria))

    return jobs


def deduplicate(jobs: list[Job]) -> list[Job]:
    unique: dict[str, Job] = {}
    for job in jobs:
        current = unique.get(job.id)
        if current is None or len(job.description) > len(current.description):
            unique[job.id] = job
    return list(unique.values())


def enrich(job: Job, use_llm_extraction: bool = True) -> Job:
    """Stage 2 — fetch the posting page to get the real description."""
    result = fetch_job_description(job.url)
    description = result.get("description", "")

    # Structured JSON-LD gives us clean fields directly.
    if result.get("title") and not job.title:
        job.title = result["title"]
    if result.get("company") and not job.company:
        job.company = result["company"]
    if result.get("location") and not job.location:
        job.location = result["location"]
    if result.get("posted_at") and not job.posted_at:
        job.posted_at = result["posted_at"]

    # No structured data? Let the LLM read the page text instead.
    needs_llm = use_llm_extraction and description and not result.get("title")
    if needs_llm:
        extracted = extract_job_fields(description)
        if extracted is None:
            job.description = ""       # not a real job posting — will be filtered out
            return job
        job.title = job.title or extracted.get("title", "")
        job.company = job.company or extracted.get("company", "")
        job.location = job.location or extracted.get("location", "")
        description = extracted.get("description") or description

    if len(description) > len(job.description):
        job.description = description

    # Company/title may have only just been discovered — recompute the dedupe key.
    job.id = make_job_id(job.company, job.title, job.url)
    return job


def run(criteria_path: str | None = None, skip_scoring: bool = False, limit: int | None = None) -> dict:
    """Full discovery run. Returns a summary dict of what happened."""
    criteria = load_criteria(criteria_path)

    discovered = deduplicate(collect(criteria))
    print(f"\n✅ Found {len(discovered)} unique postings across all sources.")

    known = load_jobs()
    fresh = [job for job in discovered if job.id not in known]
    print(f"   {len(discovered) - len(fresh)} already in your store, {len(fresh)} new.")

    if limit is not None:
        fresh = fresh[:limit]
        print(f"   Limiting this run to {len(fresh)} postings.")

    if not fresh:
        print("\nNothing new to process.")
        return {"discovered": len(discovered), "new": 0, "kept": 0}

    print(f"\n📄 Fetching descriptions for {len(fresh)} postings...")
    kept: list[Job] = []
    for index, job in enumerate(fresh, start=1):
        label = job.title[:55] or job.url[:55]
        print(f"   [{index}/{len(fresh)}] {label}")

        job = enrich(job)
        if len(job.description) < 200:
            print("        ↳ no usable description, dropping")
            continue

        allowed, why = passes_keyword_filter(job, criteria)
        if not allowed:
            print(f"        ↳ {why}, dropping")
            continue

        kept.append(job)

    print(f"\n✅ {len(kept)} postings survived filtering.")

    if kept and not skip_scoring:
        print(f"\n🤖 Scoring {len(kept)} postings against your resume...")
        min_score = criteria.get("min_score", 0.0)
        for index, job in enumerate(kept, start=1):
            job.score, job.score_reason = score_job(job)
            flag = "✅" if job.score >= min_score else "  "
            print(f"   {flag} [{index}/{len(kept)}] {job.score:.2f} — {job.title[:50]}")

    store = load_jobs()
    store, added = merge_jobs(store, kept)
    save_jobs(store)

    print(f"\n💾 Saved. {added} new jobs added, {len(store)} total in data/jobs.jsonl")
    return {"discovered": len(discovered), "new": len(fresh), "kept": len(kept), "added": added}
