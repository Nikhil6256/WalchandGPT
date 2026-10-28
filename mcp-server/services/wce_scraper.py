"""
WCE Website Scraper
====================
Scrapes live data from the Walchand College of Engineering website
(walchandsangli.ac.in) using BeautifulSoup.

All functions are async-friendly via run_in_executor so they don't block
the FastAPI event loop.
"""
import asyncio
import functools
from datetime import datetime
from typing import Optional

import requests
import structlog
from bs4 import BeautifulSoup

log = structlog.get_logger(__name__)

BASE_URL = "https://walchandsangli.ac.in"

# Shared session with SSL verification disabled (site uses self-signed cert)
_session = requests.Session()
_session.verify = False
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (compatible; WalchandGPT/1.0; "
        "+https://walchandsangli.ac.in)"
    )
})

# Suppress InsecureRequestWarning for the self-signed cert
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fetch(url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = _session.get(url, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as exc:
        log.warning("wce_scraper fetch failed", url=url, error=str(exc))
        return None


async def _async_fetch(url: str) -> Optional[BeautifulSoup]:
    """Run _fetch in a thread executor so it's non-blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(_fetch, url))


def _parse_wce_date(raw: str) -> str:
    """
    Normalise various WCE date formats to ISO-8601 (YYYY-MM-DD).
    Handles: '23/09/2026', '29/07/26', '05/03/2026', etc.
    Returns the raw string unchanged if parsing fails.
    """
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw


def _notice_loop_items(soup: BeautifulSoup) -> list:
    """
    Extract notices from the Elementor loop-grid used on /notices/.

    Each loop item is a div with class 'e-loop-item'.
    Its text follows the pattern:
        department | date | notice_id | title | department (repeated)

    The first <a> link in the item is the notice document / page link.
    """
    container = soup.find("div", class_="elementor-loop-container")
    if not container:
        log.warning("wce_scraper: elementor-loop-container not found")
        return []

    notices = []
    items = container.find_all("div", recursive=False)

    for idx, item in enumerate(items, start=1):
        # Split all visible text by a separator to get ordered fields
        parts = [
            p.strip()
            for p in item.get_text(separator="|||", strip=True).split("|||")
            if p.strip()
        ]

        if len(parts) < 4:
            continue  # malformed item

        # Field mapping based on observed Elementor template structure:
        # [0] department/category  [1] date  [2] notice_id  [3] title
        category = parts[0]
        raw_date = parts[1] if len(parts) > 1 else ""
        notice_id = parts[2] if len(parts) > 2 else str(idx)
        title = parts[3] if len(parts) > 3 else parts[-1]

        # Deduplicated links (each link appears twice in the Elementor template)
        links = list(dict.fromkeys(
            a["href"] for a in item.find_all("a", href=True) if a["href"]
        ))
        link = links[0] if links else ""

        notices.append({
            "id": idx,
            "notice_ref": notice_id,
            "title": title,
            "category": category,
            "date": _parse_wce_date(raw_date),
            "link": link,
            "issued_by": category,
        })

    return notices


# ── Public Scraping Functions ─────────────────────────────────────────────────

async def scrape_notices(limit: int = 10) -> list:
    """
    Scrape the official WCE Notice Board at /notices/.
    Returns a list of notice dicts with keys:
        id, notice_ref, title, category, date, link, issued_by
    """
    soup = await _async_fetch(f"{BASE_URL}/notices/")
    if soup is None:
        return []

    notices = _notice_loop_items(soup)
    log.info("scrape_notices", total=len(notices))
    return notices[:limit]


async def scrape_exam_schedule() -> list:
    """
    Scrape the Examination Notices and Schedule page.
    Returns list of dicts: {title, link, source}
    """
    url = f"{BASE_URL}/academics-programmes/examination-notices-and-schedule/"
    soup = await _async_fetch(url)
    if soup is None:
        return []

    schedules = []
    seen = set()

    # Find the main content area — skip the Elementor nav/header sections
    # The exam docs appear as anchor links inside the page's main content widget
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)

        if not title or len(title) < 15:
            continue
        if href in seen:
            continue

        # Must be an actual document or internal exam-page link
        # (not a navigation menu link or department page)
        is_upload = "wp-content/uploads" in href or "wp-content/uploads" in href
        is_walchand_doc = (
            ("walchandsangli.ac.in" in href or href.startswith("/"))
            and ".pdf" in href.lower()
        )
        is_exam_keyword = any(
            kw in title.lower()
            for kw in [
                "exam", "timetable", "time table", "result", "grade",
                "schedule", "provisional", "mse", "ese", "re-exam",
                "re exam", "circular", "revaluation", "notice",
            ]
        )

        # Only include if it looks like an actual exam document
        if (is_upload or is_walchand_doc) and is_exam_keyword:
            seen.add(href)
            schedules.append({
                "title": title,
                "link": href,
                "source": "Office of Controller of Examinations, WCE Sangli",
            })

    log.info("scrape_exam_schedule", total=len(schedules))
    return schedules


async def scrape_placements() -> dict:
    """
    Scrape the Placements page for WCE placement statistics.
    Returns a dict with text content and related links.
    """
    url = f"{BASE_URL}/student-careers/career-development-cell/placement-in-wce/"
    soup = await _async_fetch(url)
    if soup is None:
        return {}

    text_blocks = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        txt = tag.get_text(strip=True)
        if txt and len(txt) > 10:
            text_blocks.append(txt)

    links = []
    for a in soup.find_all("a", href=True):
        txt = a.get_text(strip=True)
        href = a["href"]
        if txt and len(txt) > 5 and "walchand" in href:
            links.append({"text": txt, "url": href})

    log.info("scrape_placements", text_blocks=len(text_blocks))
    return {
        "source": "Training & Placement Cell, Walchand College of Engineering, Sangli",
        "page_url": url,
        "text_content": text_blocks[:30],
        "related_links": links[:10],
    }


async def scrape_events(limit: int = 10) -> list:
    """
    Scrape upcoming events from the WCE homepage notice links.
    Returns list of {title, link, source} dicts.
    """
    soup = await _async_fetch(BASE_URL)
    if soup is None:
        return []

    events = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if not title or len(title) < 15 or href in seen:
            continue
        if "notice_board" in href or "event" in href.lower():
            seen.add(href)
            events.append({
                "title": title,
                "link": href,
                "source": "Walchand College of Engineering, Sangli",
            })

    log.info("scrape_events", total=len(events))
    return events[:limit]


async def scrape_department(dept_slug: str) -> dict:
    """
    Scrape a department overview page.
    dept_slug: 'cse', 'it', 'electronics', 'mechanical', 'civil',
               'electrical', 'robotics', 'aiml', 'design', 'humanities'
    """
    dept_urls = {
        "cse": f"{BASE_URL}/department-of-computer-engineering/overview/",
        "computer": f"{BASE_URL}/department-of-computer-engineering/overview/",
        "it": f"{BASE_URL}/department-of-information-technology/overview-it/",
        "electronics": f"{BASE_URL}/department-of-electronics-engg/overview-electronics/",
        "electrical": f"{BASE_URL}/department-of-electrical-engg/overview-electrical/",
        "mechanical": f"{BASE_URL}/department-of-mechanical-engineering/overview/",
        "civil": f"{BASE_URL}/department-of-civil-engineering/overview-ce/",
        "robotics": f"{BASE_URL}/department-of-robotics-and-automation/overview-ra/",
        "aiml": f"{BASE_URL}/department-of-artificial-intelligence-and-machine-learning/overview-ai/",
        "ai": f"{BASE_URL}/department-of-artificial-intelligence-and-machine-learning/overview-ai/",
        "design": f"{BASE_URL}/department-of-design/overview/",
        "humanities": f"{BASE_URL}/department-of-humanities-and-sciences/overview-hs/",
    }

    url = dept_urls.get(dept_slug.lower().strip())
    if not url:
        url = f"{BASE_URL}/{dept_slug}/overview/"

    soup = await _async_fetch(url)
    if soup is None:
        return {"error": f"Could not fetch department page for '{dept_slug}'"}

    title = soup.title.string.strip() if soup.title else dept_slug

    # On WCE Elementor pages, actual department content is in <p> tags.
    # Navigation/menu text appears in <h2>, <h3>, <li> — so we skip those.
    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all("p")
        if (
            len(p.get_text(strip=True)) > 40
            and "@" not in p.get_text(strip=True)
            and not p.get_text(strip=True).startswith("+91")
        )
    ]
    faculty_links = [
        {"name": a.get_text(strip=True), "url": a["href"]}
        for a in soup.find_all("a", href=True)
        if "faculty" in a.get("href", "").lower()
    ]

    log.info("scrape_department", slug=dept_slug, paragraphs=len(paragraphs))
    return {
        "title": title,
        "url": url,
        "content": paragraphs[:20],
        "faculty_links": faculty_links[:5],
        "source": "Walchand College of Engineering, Sangli",
    }


async def scrape_homepage_notices() -> list:
    """
    Scrape notice links from the WCE homepage ticker section.
    Returns list of {title, link} dicts.
    """
    soup = await _async_fetch(BASE_URL)
    if soup is None:
        return []

    notices = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "notice_board" in href and title and len(title) > 10 and href not in seen:
            seen.add(href)
            notices.append({"title": title, "link": href})

    log.info("scrape_homepage_notices", count=len(notices))
    return notices
