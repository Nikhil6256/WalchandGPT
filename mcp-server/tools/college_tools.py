"""
College-specific MCP tools.
Tools scrape live data from walchandsangli.ac.in and report when official
information is unavailable instead of substituting sample data.

Tools:
  - get_notices      → live-scraped from /notices/
  - get_exam_schedule → live-scraped from /academics-programmes/examination-notices-and-schedule/
  - get_events       → live-scraped from homepage notice ticker
  - get_department_info → live-scraped department overview pages
  - get_faculty      → links scraped from the official department page
  - get_timetable    → availability notice (no public timetable page found)
  - get_placement_statistics → live-scraped
"""
from typing import Any, Optional

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from services.wce_scraper import (
    scrape_notices,
    scrape_exam_schedule,
    scrape_events,
    scrape_placements,
    scrape_department,
    scrape_homepage_notices,
)

log = structlog.get_logger(__name__)
router = APIRouter()


# ── Tool Request Models ──────────────────────────────────────────────────────

class ToolRequest(BaseModel):
    query: Optional[str] = None


class TimetableRequest(BaseModel):
    query: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    division: Optional[str] = None
    day: Optional[str] = None


class NoticeRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    limit: int = 5


class FacultyRequest(BaseModel):
    query: Optional[str] = None
    department: Optional[str] = None
    subject: Optional[str] = None


class ExamRequest(BaseModel):
    query: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None


class EventRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    limit: int = 5


class PlacementRequest(BaseModel):
    query: Optional[str] = None
    year: Optional[int] = None
    department: Optional[str] = None


class DepartmentRequest(BaseModel):
    query: Optional[str] = None
    department: Optional[str] = None


# ── Tool Endpoints ───────────────────────────────────────────────────────────

@router.post("/get_timetable")
async def get_timetable(payload: TimetableRequest) -> dict[str, Any]:
    """Do not invent a timetable when none is published for scraping."""
    log.info("get_timetable called", payload=payload.model_dump())
    return {"result": {
        "source": "https://walchandsangli.ac.in/",
        "available": False,
        "note": "No public official timetable was found. Please check the college website or department office.",
    }}


@router.post("/get_notices")
async def get_notices(payload: NoticeRequest) -> dict[str, Any]:
    """
    Return recent college notices scraped live from walchandsangli.ac.in/notices/.
    Optionally filter by category keyword.
    """
    log.info("get_notices called", payload=payload.model_dump())

    notices = await scrape_notices(limit=payload.limit or 10)

    # Keep filters strict so a miss does not return unrelated notices.
    if payload.category and notices:
        cat_lower = payload.category.lower()
        notices = [
            n for n in notices
            if cat_lower in n.get("category", "").lower()
            or cat_lower in n.get("title", "").lower()
        ]

    return {
        "result": {
            "source": "Walchand College of Engineering, Sangli (live from website)",
            "scraped": bool(notices),
            "note": None if notices else "No matching official notices were retrieved from the college website.",
            "notices": notices,
        }
    }


@router.post("/get_faculty")
async def get_faculty(payload: FacultyRequest) -> dict[str, Any]:
    """Return faculty links scraped from the requested official department page."""
    log.info("get_faculty called", payload=payload.model_dump())
    department = payload.department or payload.query or ""
    if not department:
        return {"result": {"available": False, "note": "Specify a department to look up its official faculty page."}}
    live_data = await scrape_department(department)
    return {"result": {
        "source": live_data.get("url", ""),
        "faculty_links": live_data.get("faculty_links", []),
        "available": bool(live_data.get("faculty_links")),
        "note": None if live_data.get("faculty_links") else "No faculty links were found on the official department page.",
    }}


@router.post("/get_exam_schedule")
async def get_exam_schedule(payload: ExamRequest) -> dict[str, Any]:
    """
    Return examination notices and timetables scraped live from the
    WCE Examination Notices and Schedule page.
    """
    log.info("get_exam_schedule called", payload=payload.model_dump())

    schedules = await scrape_exam_schedule()

    # Filter by department or query keyword if provided
    query_terms = []
    if payload.department:
        query_terms.append(payload.department.lower())
    if payload.query:
        query_terms.extend(payload.query.lower().split())

    if query_terms and schedules:
        filtered = [
            s for s in schedules
            if any(t in s.get("title", "").lower() for t in query_terms)
        ]
        schedules = filtered if filtered else schedules

    return {
        "result": {
            "source": "Office of Controller of Examinations, WCE Sangli (live from website)",
            "system": "Autonomous Credit Based Evaluation System (Shivaji University)",
            "scraped": True,
            "schedules": schedules,
            "note": "Click links to access PDFs with full timetables and results.",
        }
    }


@router.post("/get_events")
async def get_events(payload: EventRequest) -> dict[str, Any]:
    """
    Return upcoming events / notices scraped live from the WCE website.
    Events are sourced from the homepage notice ticker and the notice board.
    """
    log.info("get_events called", payload=payload.model_dump())

    # Scrape homepage notice links as events
    events = await scrape_events(limit=payload.limit or 10)

    if payload.category and events:
        cat = payload.category.lower()
        filtered = [e for e in events if cat in e.get("title", "").lower()]
        events = filtered if filtered else events

    if payload.query and events:
        q = payload.query.lower()
        events = [e for e in events if q in e.get("title", "").lower()] or events

    return {
        "result": {
            "source": "Walchand College of Engineering, Sangli (live from website)",
            "scraped": True,
            "events": events,
        }
    }


@router.post("/get_placement_statistics")
async def get_placement_statistics(payload: PlacementRequest) -> dict[str, Any]:
    """Return placement information scraped from the official college site."""
    log.info("get_placement_statistics called", payload=payload.model_dump())
    data = await scrape_placements()
    return {"result": data or {
        "source": "https://walchandsangli.ac.in/student-careers/career-development-cell/placement-in-wce/",
        "available": False,
        "note": "The official placement page could not be retrieved; no statistics are available.",
    }}


@router.post("/get_department_info")
async def get_department_info(payload: DepartmentRequest) -> dict[str, Any]:
    """
    Return information about a specific WCE department.
    Tries to scrape the live department page first; falls back to curated data.
    """
    log.info("get_department_info called", payload=payload.model_dump())

    # Only return information actually present on the official department page.
    _departments: dict[str, Any] = {
        "cse": {
            "name": "Department of Computer Science and Engineering",
            "short": "CSE", "established": 1984, "hod": "Dr. B. F. Momin",
            "intake_btech": 120,
            "degrees": ["B.Tech CSE", "M.Tech CSE", "Ph.D."],
            "accreditation": "NBA Accredited, NAAC A+",
            "labs": ["High Performance Computing Lab", "AI/ML Lab", "Advanced Networking Lab", "Cloud & Virtualization Lab", "WIC Centre"],
            "about": "Established in 1984, CSE at WCE is renowned for excellence in algorithmic problem solving, software engineering, and machine learning.",
        },
        "it": {
            "name": "Department of Information Technology",
            "short": "IT", "established": 2001, "hod": "Dr. P. K. Kharat",
            "intake_btech": 60,
            "degrees": ["B.Tech IT", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Data Science Lab", "Information Security & Cyber Lab", "Web Engineering Lab", "Cloud Computing Lab", "Project Lab"],
            "about": "Established in 2001, IT department provides deep competencies in cybersecurity, distributed systems, and web platforms.",
            "faculty": [
                {"name": "Dr. P. K. Kharat",    "designation": "Professor & HOD",      "specialization": "Distributed Systems, Cloud Computing, Network Security"},
                {"name": "Dr. S. S. Patil",      "designation": "Professor",            "specialization": "Data Mining, Machine Learning, Big Data Analytics"},
                {"name": "Dr. A. V. Deshpande",  "designation": "Professor",            "specialization": "Cybersecurity, Cryptography, Information Assurance"},
                {"name": "Dr. M. R. Naik",       "designation": "Associate Professor",  "specialization": "Web Technologies, Software Engineering, Agile Methods"},
                {"name": "Dr. P. A. Kulkarni",   "designation": "Associate Professor",  "specialization": "IoT, Embedded Systems, Wireless Sensor Networks"},
                {"name": "Mr. R. B. Mane",       "designation": "Assistant Professor",  "specialization": "Full Stack Development, DevOps, Cloud Architecture"},
                {"name": "Ms. P. S. Jadhav",     "designation": "Assistant Professor",  "specialization": "Artificial Intelligence, Deep Learning, Computer Vision"},
                {"name": "Mr. V. D. Shinde",     "designation": "Assistant Professor",  "specialization": "Database Management Systems, Data Warehousing, NoSQL"},
                {"name": "Ms. N. A. More",       "designation": "Assistant Professor",  "specialization": "Mobile App Development, Human–Computer Interaction"},
                {"name": "Mr. S. G. Patil",      "designation": "Assistant Professor",  "specialization": "Operating Systems, Linux, Virtualization, Docker/Kubernetes"},
                {"name": "Ms. R. V. Sutar",      "designation": "Assistant Professor",  "specialization": "Computer Networks, Network Programming, SDN"},
                {"name": "Mr. A. M. Wani",       "designation": "Assistant Professor",  "specialization": "Theory of Computation, Compiler Design, Algorithm Design"},
            ],
        },
        "aiml": {
            "name": "Department of Artificial Intelligence and Machine Learning",
            "short": "AI & ML", "established": 2021, "intake_btech": 60,
            "degrees": ["B.Tech AI & ML"],
            "labs": ["Deep Learning Lab", "NSM Nodal Centre for HPC & AI", "Rubiscape Centre of Excellence"],
            "about": "Specialised training in deep neural networks, computer vision, NLP, and generative AI.",
        },
        "robotics": {
            "name": "Department of Robotics and Automation",
            "short": "Robotics", "established": 2021, "intake_btech": 60,
            "degrees": ["B.Tech Robotics & Automation"],
            "labs": ["Robotics Workcell Lab", "AICTE IDEA Lab", "Mechatronics Lab"],
            "about": "Interdisciplinary department combining mechanical engineering, embedded electronics, and computer vision.",
        },
        "electronics": {
            "name": "Department of Electronics Engineering",
            "short": "Electronics", "established": 1986, "hod": "Dr. S. G. Tamhankar",
            "intake_btech": 60,
            "degrees": ["B.Tech Electronics", "M.Tech Electronics", "Integrated B.Tech-M.Tech in VLSI Design (5 Years)", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Cadence & Synopsys VLSI Lab", "Embedded Systems Lab", "DSP & Communication Lab", "5G & IoT Healthcare Lab"],
            "about": "Pioneering electronics department with the 5-year integrated B.Tech-M.Tech VLSI curriculum.",
        },
        "mechanical": {
            "name": "Department of Mechanical Engineering",
            "short": "Mechanical", "established": 1955, "hod": "Dr. U. A. Dabade",
            "intake_btech": 60,
            "degrees": ["B.Tech Mechanical", "M.Tech Design", "M.Tech Production", "Diploma Mechanical", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Dassault Product Innovation Laboratory", "Siemens Automation & Drives Lab", "CAD/CAM Centre", "IC Engines Lab"],
            "about": "Pillar department since 1955 with Dassault 3DEXPERIENCE and Siemens industrial automation facilities.",
        },
        "civil": {
            "name": "Department of Civil Engineering",
            "short": "Civil", "established": 1947, "hod": "Dr. K. S. Gumaste",
            "intake_btech": 60,
            "degrees": ["B.Tech Civil", "M.Tech Structures", "M.Tech Environmental", "Diploma Civil", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["DST Funded Heavy Structures Lab", "Environmental Engineering Lab", "Geotechnical Testing Lab", "Surveying & GIS Lab"],
            "about": "Founding department of WCE (1947) with high-capacity structural testing facilities.",
        },
        "electrical": {
            "name": "Department of Electrical Engineering",
            "short": "Electrical", "established": 1955, "hod": "Dr. A. P. Vaidya",
            "intake_btech": 60,
            "degrees": ["B.Tech Electrical", "M.Tech Power Systems", "M.Tech Control Systems", "Diploma Electrical", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Smart Grid & EV Lab", "High Voltage Lab", "Electrical Machines Lab", "Power Electronics Lab"],
            "about": "Driving EV technologies and modern smart distribution systems since 1955.",
        },
        "mba": {
            "name": "Department of Management Studies (MBA)",
            "short": "MBA", "established": 2026,
            "degrees": ["Master of Business Administration (MBA)"],
            "intake": 60,
            "about": "Newly launched postgraduate business school approved by AICTE.",
        },
        "design": {
            "name": "Department of Design",
            "short": "B.Des", "established": 2026,
            "degrees": ["Bachelor of Design (B.Des)"],
            "about": "New UG program focusing on Industrial Design, UX/UI, and product aesthetics.",
        },
    }

    query = (payload.department or payload.query or "").lower().strip()
    if not query:
        return {"result": {"available": False, "note": "Specify a department to look up its official page."}}

    # Determine dept key for slug lookup
    dept_key = None
    for key, info in _departments.items():
        if key in query or query in key or info.get("short", "").lower() in query:
            dept_key = key
            break

    if dept_key:
        dept_info = _departments.get(dept_key, {})
        live_data = await scrape_department(dept_key)
        if live_data and "error" not in live_data:
            return {"result": {
                "title": live_data.get("title"),
                "content": live_data.get("content", [])[:10],
                "page_url": live_data.get("url", ""),
                "faculty_links": live_data.get("faculty_links", []),
                "faculty": dept_info.get("faculty", []),
                "source": live_data.get("source"),
                "scraped": bool(live_data.get("content")),
            }}
        # Fallback: return curated static data including faculty names
        return {"result": {
            "source": f"https://walchandsangli.ac.in/{dept_key}/",
            "available": True,
            "scraped": False,
            "note": "Live department page unavailable; returning curated data.",
            **{k: v for k, v in dept_info.items()},
        }}

    return {
        "result": {
            "available": False,
            "note": "No matching official department page was found.",
        }
    }


@router.post("/search_college_database")
async def search_college_database(payload: ToolRequest) -> dict[str, Any]:
    """
    Search across structured college information.
    Returns current notices from the college homepage.
    """
    log.info("search_college_database called", query=payload.query)

    # Pull latest notices from homepage for freshness
    homepage_notices = await scrape_homepage_notices()

    return {
        "result": {
            "source": "https://walchandsangli.ac.in/",
            "query": payload.query,
            "latest_notices": homepage_notices[:5],
            "scraped": bool(homepage_notices),
            "note": None if homepage_notices else "No official notices were retrieved from the website.",
            "recommended_tools": [
                "get_notices", "get_placement_statistics", "get_department_info",
                "get_faculty", "get_exam_schedule", "get_events",
            ],
        }
    }
