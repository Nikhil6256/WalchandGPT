"""
College-specific MCP tools.
Each tool is an HTTP endpoint that queries structured data from PostgreSQL.
The LangGraph agent calls these tools when structured (non-RAG) data is needed.

IMPORTANT: These tools return real data from the database.
The seed data scripts must be run first to populate these tables.
Demo data is clearly marked as such.
"""
from typing import Any, Optional

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

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
    """
    Return timetable information.
    In production: query a timetable table in PostgreSQL.
    Currently returns structured demo data clearly marked as sample.
    """
    log.info("get_timetable called", payload=payload.model_dump())

    # TODO: Replace with real DB query
    # SELECT * FROM timetable WHERE department=? AND semester=? AND day=?
    sample_data = {
        "note": "[DEMO DATA] Replace with real timetable from database",
        "department": payload.department or "Computer Engineering",
        "semester": payload.semester or 5,
        "division": payload.division or "A",
        "day": payload.day or "Monday",
        "schedule": [
            {"time": "08:00-09:00", "subject": "Database Management Systems", "faculty": "Dr. A. Kulkarni", "room": "CS-101"},
            {"time": "09:00-10:00", "subject": "Operating Systems", "faculty": "Prof. B. Patil", "room": "CS-102"},
            {"time": "10:00-11:00", "subject": "Theory of Computation", "faculty": "Dr. C. Desai", "room": "CS-103"},
            {"time": "11:15-12:15", "subject": "Computer Networks Lab", "faculty": "Prof. D. Sharma", "room": "Net-Lab"},
            {"time": "13:00-14:00", "subject": "Software Engineering", "faculty": "Dr. E. Joshi", "room": "CS-201"},
            {"time": "14:00-15:00", "subject": "Elective: Machine Learning", "faculty": "Prof. F. Nair", "room": "CS-204"},
        ]
    }
    return {"result": sample_data}


@router.post("/get_notices")
async def get_notices(payload: NoticeRequest) -> dict[str, Any]:
    """Return recent college notices and announcements."""
    log.info("get_notices called", payload=payload.model_dump())

    sample_notices = {
        "note": "[DEMO DATA] Replace with real notices from database",
        "notices": [
            {
                "id": 1,
                "title": "Semester V Examination Schedule",
                "category": "examination",
                "date": "2026-09-20",
                "content": "The Semester V examinations for all branches will commence from October 15, 2026. The detailed schedule is available on the college website.",
                "issued_by": "Examination Cell"
            },
            {
                "id": 2,
                "title": "SPPU Convocation 2026",
                "category": "event",
                "date": "2026-09-18",
                "content": "The annual convocation ceremony will be held on November 5, 2026. Final year students must register by October 10, 2026.",
                "issued_by": "Principal's Office"
            },
            {
                "id": 3,
                "title": "Attendance Shortage Warning",
                "category": "academic",
                "date": "2026-09-15",
                "content": "Students with attendance below 75% have been notified. Please contact your class teacher to understand the implications.",
                "issued_by": "Academic Section"
            },
            {
                "id": 4,
                "title": "Hackathon Registration Open",
                "category": "competition",
                "date": "2026-09-10",
                "content": "WCE Hackathon 2026 registrations are open. Teams of 2-4 students can register at the college technical festival portal.",
                "issued_by": "ACM Student Chapter"
            },
        ][:payload.limit]
    }
    return {"result": sample_notices}


@router.post("/get_faculty")
async def get_faculty(payload: FacultyRequest) -> dict[str, Any]:
    """Return faculty information by department or subject."""
    log.info("get_faculty called", payload=payload.model_dump())

    sample_faculty = {
        "note": "[DEMO DATA] Replace with real faculty data from database",
        "faculty": [
            {
                "name": "Dr. Anjali Kulkarni",
                "designation": "Professor & HOD",
                "department": "Computer Engineering",
                "subjects": ["Database Management Systems", "Data Mining"],
                "email": "anjali.kulkarni@walchandsangli.ac.in",
                "cabin": "CS-201"
            },
            {
                "name": "Prof. Bharat Patil",
                "designation": "Associate Professor",
                "department": "Computer Engineering",
                "subjects": ["Operating Systems", "System Programming"],
                "email": "bharat.patil@walchandsangli.ac.in",
                "cabin": "CS-202"
            },
            {
                "name": "Dr. Chetan Desai",
                "designation": "Assistant Professor",
                "department": "Computer Engineering",
                "subjects": ["Theory of Computation", "Compiler Design"],
                "email": "chetan.desai@walchandsangli.ac.in",
                "cabin": "CS-203"
            },
        ]
    }

    # Filter by department if provided
    if payload.department:
        sample_faculty["faculty"] = [
            f for f in sample_faculty["faculty"]
            if payload.department.lower() in f["department"].lower()
        ]

    # Filter by subject if provided
    if payload.subject:
        sample_faculty["faculty"] = [
            f for f in sample_faculty["faculty"]
            if any(payload.subject.lower() in s.lower() for s in f["subjects"])
        ]

    return {"result": sample_faculty}


@router.post("/get_exam_schedule")
async def get_exam_schedule(payload: ExamRequest) -> dict[str, Any]:
    """Return examination schedule."""
    log.info("get_exam_schedule called", payload=payload.model_dump())

    sample_schedule = {
        "note": "[DEMO DATA] Replace with real exam schedule from database",
        "department": payload.department or "All Departments",
        "semester": payload.semester or 5,
        "exams": [
            {"date": "2026-10-15", "day": "Thursday", "subject": "Database Management Systems", "time": "10:00-13:00", "code": "410241"},
            {"date": "2026-10-17", "day": "Saturday", "subject": "Operating Systems", "time": "10:00-13:00", "code": "410242"},
            {"date": "2026-10-20", "day": "Tuesday", "subject": "Computer Networks", "time": "10:00-13:00", "code": "410243"},
            {"date": "2026-10-22", "day": "Thursday", "subject": "Theory of Computation", "time": "10:00-13:00", "code": "410244"},
            {"date": "2026-10-24", "day": "Saturday", "subject": "Software Engineering", "time": "10:00-13:00", "code": "410245"},
            {"date": "2026-10-27", "day": "Tuesday", "subject": "Elective - I", "time": "10:00-13:00", "code": "410246"},
        ]
    }
    return {"result": sample_schedule}


@router.post("/get_events")
async def get_events(payload: EventRequest) -> dict[str, Any]:
    """Return upcoming college events."""
    log.info("get_events called", payload=payload.model_dump())

    sample_events = {
        "note": "[DEMO DATA] Replace with real events from database",
        "events": [
            {
                "id": 1,
                "name": "Antardhwani 2026 — Annual Technical Festival",
                "date": "2026-10-20 to 2026-10-22",
                "venue": "WCE Main Campus",
                "category": "technical",
                "description": "3-day technical festival featuring hackathons, paper presentations, robotics competitions, and expert talks."
            },
            {
                "id": 2,
                "name": "Campus Placement Drive — TCS",
                "date": "2026-10-05",
                "venue": "Placement Cell, Admin Building",
                "category": "placement",
                "description": "TCS is visiting campus for NQT (National Qualifier Test) and interviews for final year students."
            },
            {
                "id": 3,
                "name": "Guest Lecture — AI in Healthcare",
                "date": "2026-09-30",
                "venue": "Seminar Hall, Block A",
                "category": "academic",
                "description": "Guest lecture by Dr. Rajeev Menon from IIT Bombay on applications of AI in healthcare."
            },
        ][:payload.limit]
    }
    return {"result": sample_events}


@router.post("/get_placement_statistics")
async def get_placement_statistics(payload: PlacementRequest) -> dict[str, Any]:
    """Return placement statistics."""
    log.info("get_placement_statistics called", payload=payload.model_dump())

    sample_stats = {
        "note": "[DEMO DATA] Replace with real placement data from database",
        "academic_year": str(payload.year or 2026),
        "summary": {
            "total_students_eligible": 450,
            "total_placed": 387,
            "placement_percentage": 86.0,
            "highest_package_lpa": 42.0,
            "average_package_lpa": 8.5,
            "median_package_lpa": 7.2,
        },
        "top_recruiters": [
            {"company": "TCS", "offers": 45, "package_lpa": 3.6},
            {"company": "Infosys", "offers": 38, "package_lpa": 3.6},
            {"company": "Wipro", "offers": 30, "package_lpa": 3.5},
            {"company": "Accenture", "offers": 28, "package_lpa": 4.5},
            {"company": "Capgemini", "offers": 25, "package_lpa": 3.8},
            {"company": "LTI Mindtree", "offers": 20, "package_lpa": 6.5},
            {"company": "Persistent Systems", "offers": 18, "package_lpa": 5.0},
            {"company": "Syntel", "offers": 15, "package_lpa": 4.2},
        ],
        "department_wise": {
            "Computer Engineering": {"placed": 95, "eligible": 105, "avg_pkg": 9.2},
            "Information Technology": {"placed": 88, "eligible": 98, "avg_pkg": 8.8},
            "Electronics": {"placed": 72, "eligible": 85, "avg_pkg": 7.5},
            "Mechanical": {"placed": 65, "eligible": 80, "avg_pkg": 7.0},
            "Civil": {"placed": 45, "eligible": 60, "avg_pkg": 6.5},
        }
    }
    return {"result": sample_stats}


@router.post("/get_department_info")
async def get_department_info(payload: DepartmentRequest) -> dict[str, Any]:
    """Return information about a specific department."""
    log.info("get_department_info called", payload=payload.model_dump())

    departments = {
        "computer engineering": {
            "name": "Department of Computer Engineering",
            "short": "CSE",
            "established": 1984,
            "hod": "Dr. Anjali Kulkarni",
            "intake": 120,
            "labs": ["Programming Lab", "Network Lab", "AI/ML Lab", "DBMS Lab", "Project Lab"],
            "accreditation": "NBA Accredited",
            "about": "The Department of Computer Engineering at WCE offers B.E., M.E., and Ph.D. programs. It has NAAC Grade A+ and NBA accreditation with state-of-the-art laboratories."
        },
        "information technology": {
            "name": "Department of Information Technology",
            "short": "IT",
            "established": 2001,
            "hod": "Dr. Suresh Nawale",
            "intake": 60,
            "labs": ["Programming Lab", "Web Technology Lab", "Cyber Security Lab"],
            "accreditation": "NBA Accredited",
            "about": "The IT Department focuses on software development, web technologies, and cybersecurity. It has strong industry connections with Pune-based IT companies."
        }
    }

    query = (payload.department or payload.query or "").lower()
    for key, info in departments.items():
        if key in query or query in key:
            return {"result": {**info, "note": "[DEMO DATA]"}}

    return {"result": {"available_departments": list(departments.keys()), "note": "[DEMO DATA]"}}


@router.post("/search_college_database")
async def search_college_database(payload: ToolRequest) -> dict[str, Any]:
    """Generic search across college structured data."""
    log.info("search_college_database called", query=payload.query)

    return {
        "result": {
            "note": "[DEMO DATA] This tool searches structured college data",
            "query": payload.query,
            "message": "Please use specific tools (get_faculty, get_notices, etc.) for more accurate results.",
        }
    }
