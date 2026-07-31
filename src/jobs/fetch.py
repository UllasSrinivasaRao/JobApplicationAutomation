# fetch.py
"""Polite page fetching + description extraction.

Order of preference when pulling a job description off a page:
  1. JSON-LD `JobPosting` — structured data the site published for machines to read
  2. Readable text from the main content area
"""

import re
import json
import time
import html
import urllib.robotparser as robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "JobApplicationAutomation/0.1 (personal job search; +https://github.com/AhmedAli288)"
REQUEST_TIMEOUT = 20.0
POLITE_DELAY_SECONDS = 1.5

_robots_cache: dict[str, robotparser.RobotFileParser | None] = {}
_last_request_at: dict[str, float] = {}


def _robots_allows(url: str) -> bool:
    """Check robots.txt before fetching. On any doubt we allow, but we never hammer."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in _robots_cache:
        parser = robotparser.RobotFileParser()
        parser.set_url(f"{origin}/robots.txt")
        try:
            parser.read()
            _robots_cache[origin] = parser
        except Exception:
            # No reachable robots.txt means no stated restriction.
            _robots_cache[origin] = None

    parser = _robots_cache[origin]
    if parser is None:
        return True
    try:
        return parser.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def _throttle(url: str) -> None:
    """One request per host per POLITE_DELAY_SECONDS."""
    host = urlparse(url).netloc
    last = _last_request_at.get(host)
    if last is not None:
        elapsed = time.monotonic() - last
        if elapsed < POLITE_DELAY_SECONDS:
            time.sleep(POLITE_DELAY_SECONDS - elapsed)
    _last_request_at[host] = time.monotonic()


def fetch_page(url: str) -> str | None:
    if not url or not url.startswith(("http://", "https://")):
        return None

    if not _robots_allows(url):
        print(f"   ⏭️  robots.txt disallows fetching {urlparse(url).netloc} — skipping")
        return None

    _throttle(url)
    try:
        response = httpx.get(
            url,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            },
        )
        if response.status_code != 200:
            return None
        if "html" not in response.headers.get("content-type", "").lower():
            return None
        return response.text
    except httpx.HTTPError:
        return None


def _iter_jsonld_objects(soup: BeautifulSoup):
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, AttributeError):
            continue

        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                yield node
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)


def _html_to_text(fragment: str) -> str:
    text = BeautifulSoup(html.unescape(fragment or ""), "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def extract_job_posting(html_text: str) -> dict | None:
    """Pull a schema.org JobPosting out of the page, if the site published one."""
    soup = BeautifulSoup(html_text, "html.parser")

    for node in _iter_jsonld_objects(soup):
        node_type = node.get("@type", "")
        types = node_type if isinstance(node_type, list) else [node_type]
        if "JobPosting" not in types:
            continue

        org = node.get("hiringOrganization") or {}
        company = org.get("name", "") if isinstance(org, dict) else str(org)

        location = ""
        loc = node.get("jobLocation")
        if isinstance(loc, list):
            loc = loc[0] if loc else None
        if isinstance(loc, dict):
            address = loc.get("address")
            if isinstance(address, dict):
                location = ", ".join(
                    str(address.get(k))
                    for k in ("addressLocality", "addressRegion", "addressCountry")
                    if address.get(k)
                )
            elif isinstance(address, str):
                location = address

        return {
            "title": node.get("title", ""),
            "company": company,
            "location": location,
            "description": _html_to_text(node.get("description", "")),
            "posted_at": node.get("datePosted"),
        }
    return None


def extract_readable_text(html_text: str, max_chars: int = 12000) -> str:
    """Fallback: strip chrome and return the page's visible text."""
    soup = BeautifulSoup(html_text, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "svg", "form"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = re.sub(r"\s+", " ", main.get_text(" ")).strip()
    return text[:max_chars]


def fetch_job_description(url: str) -> dict:
    """Return whatever we can learn about a posting from its page.

    Always returns a dict; empty description means the fetch failed or the page
    was JS-rendered with nothing useful in the initial HTML.
    """
    page = fetch_page(url)
    if not page:
        return {"description": ""}

    posting = extract_job_posting(page)
    if posting and len(posting.get("description", "")) > 200:
        return posting

    text = extract_readable_text(page)
    result = posting or {}
    existing = result.get("description", "")
    result["description"] = text if len(text) > len(existing) else existing
    return result
