# schema.py
"""Common Job record shared by every source, plus criteria loading."""

import re
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config" / "criteria.json"

# Job lifecycle: discovered -> reviewed by you -> documents generated
STATUS_NEW = "new"
STATUS_APPROVED = "approved"
STATUS_SKIPPED = "skipped"
STATUS_APPLIED = "applied"


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    posted_at: str | None = None
    fetched_at: str = ""
    score: float | None = None
    score_reason: str | None = None
    status: str = STATUS_NEW

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        # Ignore unknown keys so older jobs.jsonl rows keep loading after a schema change
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def make_job_id(company: str, title: str, url: str) -> str:
    """Stable ID so the same posting seen twice (or from two sources) collapses."""
    company_key = _clean(company).lower()
    title_key = _clean(title).lower()
    if company_key and title_key:
        key = f"{company_key}|{title_key}"
    else:
        key = _clean(url).lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def build_job(
    title: str,
    company: str,
    location: str,
    url: str,
    source: str,
    description: str = "",
    posted_at: str | None = None,
) -> Job:
    title = _clean(title)
    company = _clean(company)
    return Job(
        id=make_job_id(company, title, url),
        title=title,
        company=company,
        location=_clean(location),
        url=_clean(url),
        source=source,
        description=(description or "").strip(),
        posted_at=posted_at,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def load_criteria(path: Path | str | None = None) -> dict:
    path = Path(path) if path else CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"❌ Criteria file not found at {path}. Copy config/criteria.json and edit it."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def passes_keyword_filter(job: Job, criteria: dict) -> tuple[bool, str]:
    """Cheap pre-filter so we don't spend LLM calls on obvious non-matches."""
    haystack = f"{job.title} {job.description}".lower()

    for bad in criteria.get("keywords_exclude", []):
        if bad.lower() in haystack:
            return False, f"excluded by keyword: {bad}"

    # Only enforce the include-list once we actually have a description to search.
    includes = [k.lower() for k in criteria.get("keywords_include", [])]
    if includes and len(job.description) > 200:
        if not any(k in haystack for k in includes):
            return False, "no matching skill keywords found"

    return True, ""
