# websearch.py
"""DuckDuckGo search — free, no API key, finds career pages the APIs miss.

Results are just candidate URLs; the real job data gets extracted later by
fetching each page (fetch.py) and, when the page has no structured data,
handing the text to Groq (extract.py).
"""

import time

from src.jobs.schema import build_job, Job

SEARCH_DELAY_SECONDS = 2.0

# Domains whose terms don't permit automated access, or that block fetching anyway.
# We never follow these — job data comes from sources that allow it.
BLOCKED_DOMAINS = (
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "xing.com",
    "facebook.com",
)


def _get_ddgs():
    """The package was renamed from duckduckgo-search to ddgs; support both."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return None
    return DDGS


def _is_allowed(url: str) -> bool:
    lowered = (url or "").lower()
    return bool(lowered) and not any(domain in lowered for domain in BLOCKED_DOMAINS)


def search(query: str, max_results: int = 10) -> list[Job]:
    DDGS = _get_ddgs()
    if DDGS is None:
        print("   ⚠️ ddgs not installed — skipping web search. Run: uv add ddgs")
        return []

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, region="de-de", max_results=max_results))
    except Exception as e:
        print(f"   ⚠️ Web search failed for '{query}': {e}")
        return []

    jobs: list[Job] = []
    for item in raw_results:
        url = item.get("href") or item.get("url", "")
        if not _is_allowed(url):
            continue
        jobs.append(
            build_job(
                title=item.get("title", ""),
                company="",           # filled in later from the page itself
                location="",
                url=url,
                source="websearch",
                description=item.get("body", ""),   # snippet only, replaced after fetch
            )
        )

    time.sleep(SEARCH_DELAY_SECONDS)
    return jobs


def search_all(criteria: dict) -> list[Job]:
    config = criteria.get("sources", {}).get("websearch", {})
    if not config.get("enabled", False):
        return []

    templates = config.get("query_templates", ["{title} {city} Stellenanzeige"])
    max_results = config.get("max_results_per_query", 10)

    jobs: list[Job] = []
    for title in criteria.get("titles", []):
        for location in criteria.get("locations", []):
            city = location.get("city")
            if not city:
                continue
            for template in templates:
                query = template.format(title=title, city=city)
                found = search(query, max_results)
                print(f"   🔎 '{query}': {len(found)} results")
                jobs.extend(found)

    return jobs
