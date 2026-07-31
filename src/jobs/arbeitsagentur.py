# arbeitsagentur.py
"""Bundesagentur für Arbeit — public Jobsuche API.

Free, official, no account needed, and it covers the German market (including
Werkstudent roles) far better than anything you'd get by scraping a job board.

Note: the /jobdetails endpoint rejects this public key (HTTP 403), so the search
results only give us metadata. Descriptions are filled in later by fetching each
posting's own URL (see discovery.py).
"""

import time
import urllib.parse

import httpx

from src.jobs.schema import build_job, Job

SEARCH_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
API_KEY = "jobboerse-jobsuche"  # public client key used by the official Jobsuche app
PUBLIC_DETAIL_URL = "https://www.arbeitsagentur.de/jobsuche/jobdetail/"
REQUEST_DELAY_SECONDS = 1.0


def _posting_url(item: dict) -> str:
    """Prefer the employer's own listing; fall back to the Arbeitsagentur page.

    The public detail page takes the raw refnr in the path — not base64-encoded.
    """
    external = (item.get("externeUrl") or "").strip()
    if external:
        return external

    refnr = (item.get("refnr") or "").strip()
    if not refnr:
        return ""
    return PUBLIC_DETAIL_URL + urllib.parse.quote(refnr, safe="")


def _format_location(arbeitsort: dict) -> str:
    if not isinstance(arbeitsort, dict):
        return ""
    parts = [arbeitsort.get("ort"), arbeitsort.get("region")]
    location = ", ".join(p for p in parts if p)
    distance = arbeitsort.get("entfernung")
    if distance:
        location += f" ({distance} km)"
    return location


def search(
    what: str,
    where: str,
    radius_km: int = 50,
    size: int = 25,
    published_within_days: int | None = 30,
) -> list[Job]:
    params = {
        "was": what,
        "wo": where,
        "umkreis": radius_km,
        "size": size,
        "page": 1,
    }
    if published_within_days:
        params["veroeffentlichtseit"] = published_within_days

    try:
        response = httpx.get(
            SEARCH_URL,
            params=params,
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
            timeout=25.0,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as e:
        print(f"   ⚠️ Arbeitsagentur request failed for '{what}' in {where}: {e}")
        return []
    except ValueError as e:
        print(f"   ⚠️ Arbeitsagentur returned invalid JSON: {e}")
        return []

    jobs: list[Job] = []
    for item in payload.get("stellenangebote", []) or []:
        url = _posting_url(item)
        if not url:
            continue
        jobs.append(
            build_job(
                title=item.get("titel") or item.get("beruf", ""),
                company=item.get("arbeitgeber", ""),
                location=_format_location(item.get("arbeitsort", {})),
                url=url,
                source="arbeitsagentur",
                posted_at=item.get("aktuelleVeroeffentlichungsdatum"),
            )
        )

    time.sleep(REQUEST_DELAY_SECONDS)
    return jobs


def search_all(criteria: dict) -> list[Job]:
    """Run every title x location combination from the criteria file."""
    jobs: list[Job] = []
    size = criteria.get("max_jobs_per_query", 25)
    within = criteria.get("published_within_days", 30)

    for title in criteria.get("titles", []):
        for location in criteria.get("locations", []):
            city = location.get("city")
            if not city:
                continue
            radius = location.get("radius_km", 50)
            found = search(title, city, radius, size, within)
            print(f"   🔎 '{title}' near {city}: {len(found)} results")
            jobs.extend(found)

    return jobs
