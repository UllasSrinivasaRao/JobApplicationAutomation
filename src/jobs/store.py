# store.py
"""jobs.jsonl persistence — one JSON object per line, keyed by Job.id."""

import json
import tempfile
from pathlib import Path

from src.jobs.schema import Job, BASE_DIR

DATA_DIR = BASE_DIR / "data"
JOBS_PATH = DATA_DIR / "jobs.jsonl"


def load_jobs(path: Path | None = None) -> dict[str, Job]:
    """Return {job_id: Job}. Missing file is not an error — it's just an empty store."""
    path = path or JOBS_PATH
    jobs: dict[str, Job] = {}
    if not path.exists():
        return jobs

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                job = Job.from_dict(json.loads(line))
                jobs[job.id] = job
            except (json.JSONDecodeError, TypeError) as e:
                print(f"⚠️ Skipping malformed row at {path.name}:{line_no} — {e}")
    return jobs


def save_jobs(jobs: dict[str, Job], path: Path | None = None) -> None:
    """Atomic rewrite so an interrupted run can't truncate the store."""
    path = path or JOBS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered = sorted(
        jobs.values(),
        key=lambda j: (j.score if j.score is not None else -1.0),
        reverse=True,
    )

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            for job in ordered:
                f.write(json.dumps(job.to_dict(), ensure_ascii=False) + "\n")
        Path(tmp_name).replace(path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def merge_jobs(existing: dict[str, Job], discovered: list[Job]) -> tuple[dict[str, Job], int]:
    """Add newly discovered jobs, preserving your review decisions on ones already seen."""
    added = 0
    for job in discovered:
        current = existing.get(job.id)
        if current is None:
            existing[job.id] = job
            added += 1
            continue

        # Already known: keep status/score, but fill in a description if we finally got one.
        if len(job.description) > len(current.description):
            current.description = job.description
        if not current.posted_at and job.posted_at:
            current.posted_at = job.posted_at
    return existing, added


def update_status(job_id: str, status: str, path: Path | None = None) -> bool:
    jobs = load_jobs(path)
    if job_id not in jobs:
        return False
    jobs[job_id].status = status
    save_jobs(jobs, path)
    return True
