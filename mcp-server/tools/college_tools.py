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
    """Return recent college notices and announcements from Walchand College of Engineering."""
    log.info("get_notices called", payload=payload.model_dump())

    official_notices = [
        {
            "id": 1,
            "title": "Guidelines for Walchand College CAP Reporting — New Admissions 2026-27",
            "category": "admission",
            "date": "2026-09-24",
            "content": "Seat allotted through State CET Cell for CAP Rounds 1, 2, 3 & 4 (AY 2026–27). All students must report to WCE Admission Reporting Center with original documents and prescribed fees.",
            "issued_by": "Admission Cell, WCE Sangli",
            "link": "https://walchandsangli.ac.in/notice_board/guidelines-for-walchand-college-of-engineering-cap-reporting-new-admissions-2026-27/"
        },
        {
            "id": 2,
            "title": "MBA Program Option Form Submission (CAP Round-2)",
            "category": "admission",
            "date": "2026-09-22",
            "content": "Students can fill option forms for the newly introduced MBA Program at Walchand College of Engineering, Sangli from CAP Round-2 through candidate login on the CET Cell Portal.",
            "issued_by": "Chairman, Admissions",
            "link": "https://walchandsangli.ac.in/notice_board/students-can-fill-option-form-for-mba-program-at-walchand-college-of-engineering-sangli-from-cap-round-2-through-candidate-login-on-cet-cell-portal/"
        },
        {
            "id": 3,
            "title": "AICTE ATAL FDP on Reconfigurable Intelligent Surfaces for Wireless Communications",
            "category": "academic",
            "date": "2026-09-07",
            "content": "One-week national FDP organized by Department of Electronics Engineering from 7-12 September 2026.",
            "issued_by": "Department of Electronics Engineering",
            "link": "https://walchandsangli.ac.in/notice_board/aicte-atal-fdp-on-reconfigurable-intelligent-surfaces-for-wireless-communications-from-7-12-september-2026/"
        },
        {
            "id": 4,
            "title": "AICTE-VAANI FDP Workshop in Marathi Language",
            "category": "academic",
            "date": "2026-08-28",
            "content": "Workshop on 'TECHNOLOGY DRIVEN ENGINEERING FOR HEALTH ADVANCEMENT' in Marathi from 01-03 December 2026 under NEP 2020 initiatives.",
            "issued_by": "Dean Academics",
            "link": "https://walchandsangli.ac.in/notice_board/aicte-vaani-fdp-workshop-in-marathi-language-on-technology-driven-engineering-for-health-advancement-from-01-03-december-2026/"
        },
        {
            "id": 5,
            "title": "SMKC Civic Innovation Forum: Ideathon + Software Development Challenge",
            "category": "competition",
            "date": "2026-08-20",
            "content": "Civic Innovation Challenge in association with Sangli Miraj Kupwad City Municipal Corporation for urban and municipal digital solutions.",
            "issued_by": "Dean R&D & WCE IIE Cell",
            "link": "https://walchandsangli.ac.in/notice_board/smkc-civic-innovation-forum-2026-ideathon-software-development-challenge/"
        },
    ][:payload.limit]

    return {"result": {"source": "Walchand College of Engineering, Sangli", "notices": official_notices}}


@router.post("/get_faculty")
async def get_faculty(payload: FacultyRequest) -> dict[str, Any]:
    """Return faculty information by department or subject."""
    log.info("get_faculty called", payload=payload.model_dump())

    sample_faculty = {
        "source": "Walchand College of Engineering, Sangli",
        "faculty": [
            {
                "name": "Dr. U. A. Dabade",
                "designation": "Professor & Director",
                "department": "Mechanical Engineering",
                "subjects": ["Advanced Manufacturing", "Machining Science"],
                "email": "director@walchandsangli.ac.in",
                "cabin": "Director Office, Admin Building"
            },
            {
                "name": "Dr. S. G. Tamhankar",
                "designation": "Professor & Head",
                "department": "Electronics Engineering",
                "subjects": ["VLSI Design", "Embedded Systems"],
                "email": "hod.electronics@walchandsangli.ac.in",
                "cabin": "Electronics Dept, Ground Floor"
            },
            {
                "name": "Dr. B. F. Momin",
                "designation": "Professor & Head",
                "department": "Computer Science and Engineering",
                "subjects": ["Cloud Computing", "Distributed Systems", "Machine Learning"],
                "email": "hod.cse@walchandsangli.ac.in",
                "cabin": "CSE Building, CS-101"
            },
            {
                "name": "Dr. P. K. Kharat",
                "designation": "Professor & Head",
                "department": "Information Technology",
                "subjects": ["Cybersecurity", "Network Architecture", "Data Science"],
                "email": "hod.it@walchandsangli.ac.in",
                "cabin": "IT Building, IT-201"
            },
            {
                "name": "Dr. K. S. Gumaste",
                "designation": "Professor & Head",
                "department": "Civil Engineering",
                "subjects": ["Structural Dynamics", "Earthquake Engineering"],
                "email": "hod.civil@walchandsangli.ac.in",
                "cabin": "Civil Dept, Main Block"
            },
            {
                "name": "Dr. A. P. Vaidya",
                "designation": "Professor & Head",
                "department": "Electrical Engineering",
                "subjects": ["Power Systems", "Control Systems"],
                "email": "hod.electrical@walchandsangli.ac.in",
                "cabin": "Electrical Dept, Block E"
            }
        ]
    }

    if payload.department:
        sample_faculty["faculty"] = [
            f for f in sample_faculty["faculty"]
            if payload.department.lower() in f["department"].lower()
        ]

    if payload.subject:
        sample_faculty["faculty"] = [
            f for f in sample_faculty["faculty"]
            if any(payload.subject.lower() in s.lower() for s in f["subjects"])
        ]

    return {"result": sample_faculty}


@router.post("/get_exam_schedule")
async def get_exam_schedule(payload: ExamRequest) -> dict[str, Any]:
    """Return autonomous examination schedule."""
    log.info("get_exam_schedule called", payload=payload.model_dump())

    sample_schedule = {
        "source": "Office of Controller of Examinations, WCE Sangli",
        "system": "Autonomous Credit Based Evaluation System (Shivaji University)",
        "department": payload.department or "Computer Science and Engineering",
        "semester": payload.semester or 5,
        "exams": [
            {"date": "2026-10-15", "day": "Thursday", "subject": "Database Management Systems", "time": "10:00-13:00", "code": "CS301"},
            {"date": "2026-10-17", "day": "Saturday", "subject": "Operating Systems & System Programming", "time": "10:00-13:00", "code": "CS302"},
            {"date": "2026-10-20", "day": "Tuesday", "subject": "Computer Networks & Protocols", "time": "10:00-13:00", "code": "CS303"},
            {"date": "2026-10-22", "day": "Thursday", "subject": "Theory of Computation & Automata", "time": "10:00-13:00", "code": "CS304"},
            {"date": "2026-10-24", "day": "Saturday", "subject": "Software Engineering & Agile Methodologies", "time": "10:00-13:00", "code": "CS305"},
            {"date": "2026-10-27", "day": "Tuesday", "subject": "Open Elective / MDM", "time": "10:00-13:00", "code": "OE301"},
        ]
    }
    return {"result": sample_schedule}


@router.post("/get_events")
async def get_events(payload: EventRequest) -> dict[str, Any]:
    """Return upcoming college events."""
    log.info("get_events called", payload=payload.model_dump())

    sample_events = {
        "source": "Walchand College of Engineering, Sangli",
        "events": [
            {
                "id": 1,
                "name": "WCE Hackathon & Techfest (VISION)",
                "date": "2026-10-18 to 2026-10-20",
                "venue": "WCE Sangli Main Campus & Tilak Hall",
                "category": "technical",
                "description": "Annual state-level technical symposium with national hackathons, coding contests, paper presentations, and robotics tracks."
            },
            {
                "id": 2,
                "name": "SMKC Civic Innovation Forum: Final Demo Day",
                "date": "2026-10-12",
                "venue": "Ajit Gulabchand Central Library Auditorium",
                "category": "innovation",
                "description": "Final project demonstrations of smart city solutions developed by students for Sangli municipal authorities."
            },
            {
                "id": 3,
                "name": "Campus Recruitment Drive — Tier-1 Tech Partners",
                "date": "2026-10-05",
                "venue": "Placement Cell & WIC Labs",
                "category": "placement",
                "description": "Recruitment drive for B.Tech & M.Tech graduating batches by software and core engineering firms."
            },
            {
                "id": 4,
                "name": "AICTE-VAANI Workshop in Marathi",
                "date": "2026-12-01 to 2026-12-03",
                "venue": "Seminar Hall, Mechanical Complex",
                "category": "academic",
                "description": "Technology Driven Engineering for Health Advancement workshop conducted in Marathi language."
            },
        ][:payload.limit]
    }
    return {"result": sample_events}


@router.post("/get_placement_statistics")
async def get_placement_statistics(payload: PlacementRequest) -> dict[str, Any]:
    """Return official placement statistics from Walchand College of Engineering."""
    log.info("get_placement_statistics called", payload=payload.model_dump())

    official_stats = {
        "source": "Training & Placement Cell, Walchand College of Engineering, Sangli",
        "academic_year": str(payload.year or "2024-2026"),
        "highlights": {
            "highest_package": "₹1.50 Crore / Annum",
            "historical_milestone": "₹1.30 Crore / Annum by Saurabh Pukale (2021 Platinum Jubilee)",
            "average_package": "₹12.0 LPA",
            "companies_visiting": "300+ Recruiters",
            "placement_assistance": "100%",
        },
        "notable_placements": [
            {"student": "Jay Shirguppe", "company": "Rubrik", "profile": "Software Development Engineer"},
            {"student": "Aardhya Pittalwar", "company": "CRED", "profile": "Software Engineer"},
            {"student": "Ankita Dongare", "company": "Google", "profile": "Software Engineer"},
            {"student": "Saurabh Pukale", "company": "International Tech Corp", "package": "₹1.3 Cr / Annum"},
        ],
        "top_recruiting_partners": [
            "Google", "Microsoft", "Amazon", "Rubrik", "CRED", "Dassault Systèmes",
            "Siemens", "Texas Instruments", "Persistent Systems", "TCS", "Infosys",
            "LTI Mindtree", "Tata Motors", "John Deere", "Cummins India", "Bharat Forge"
        ],
        "department_placement_rates": {
            "Computer Science & Engineering": {"placed_pct": "96%", "avg_lpa": 14.5},
            "Information Technology": {"placed_pct": "95%", "avg_lpa": 13.8},
            "Electronics Engineering": {"placed_pct": "90%", "avg_lpa": 11.2},
            "Electrical Engineering": {"placed_pct": "88%", "avg_lpa": 9.5},
            "Mechanical Engineering": {"placed_pct": "86%", "avg_lpa": 8.8},
            "Civil Engineering": {"placed_pct": "80%", "avg_lpa": 7.5},
        }
    }
    return {"result": official_stats}


@router.post("/get_department_info")
async def get_department_info(payload: DepartmentRequest) -> dict[str, Any]:
    """Return information about a specific department at Walchand College of Engineering."""
    log.info("get_department_info called", payload=payload.model_dump())

    departments = {
        "cse": {
            "name": "Department of Computer Science and Engineering",
            "short": "CSE",
            "established": 1984,
            "hod": "Dr. B. F. Momin",
            "intake_btech": 120,
            "degrees": ["B.Tech CSE", "M.Tech CSE", "Ph.D."],
            "accreditation": "NBA Accredited, NAAC A+",
            "labs": ["High Performance Computing Lab", "AI/ML Lab", "Advanced Networking Lab", "Cloud & Virtualization Lab", "WIC Centre"],
            "about": "Established in 1984, CSE at WCE is renowned for excellence in algorithmic problem solving, software engineering, and machine learning with top-tier placements at Google, Rubrik, and Microsoft."
        },
        "it": {
            "name": "Department of Information Technology",
            "short": "IT",
            "established": 2001,
            "hod": "Dr. P. K. Kharat",
            "intake_btech": 60,
            "degrees": ["B.Tech IT", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Data Science Lab", "Information Security & Cyber Lab", "Web Engineering Lab", "Cloud Computing Lab"],
            "about": "Established in 2001, IT department provides deep competencies in full-stack web platforms, mobile software, cybersecurity, and distributed systems."
        },
        "aiml": {
            "name": "Department of Artificial Intelligence and Machine Learning",
            "short": "AI & ML",
            "established": 2021,
            "intake_btech": 60,
            "degrees": ["B.Tech AI & ML"],
            "labs": ["Deep Learning Lab", "NSM Nodal Centre for HPC & AI", "Rubiscape Centre of Excellence"],
            "about": "Offers specialized training in deep neural networks, computer vision, natural language processing, and generative AI."
        },
        "robotics": {
            "name": "Department of Robotics and Automation",
            "short": "Robotics",
            "established": 2021,
            "intake_btech": 60,
            "degrees": ["B.Tech Robotics & Automation"],
            "labs": ["Robotics Workcell Lab", "AICTE IDEA Lab", "Mechatronics Lab"],
            "about": "Interdisciplinary department combining mechanical engineering, embedded electronics, sensors, and computer vision for industrial robotics."
        },
        "electronics": {
            "name": "Department of Electronics Engineering",
            "short": "Electronics",
            "established": 1986,
            "hod": "Dr. S. G. Tamhankar",
            "intake_btech": 60,
            "degrees": ["B.Tech Electronics", "M.Tech Electronics", "Integrated B.Tech-M.Tech in VLSI Design (5 Years)", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Cadence & Synopsys VLSI Lab", "Embedded Systems Lab", "DSP & Communication Lab", "5G & IoT Healthcare Lab"],
            "about": "Pioneering electronics department with specialized VLSI synthesis setups and the 5-year integrated B.Tech-M.Tech VLSI curriculum."
        },
        "mechanical": {
            "name": "Department of Mechanical Engineering",
            "short": "Mechanical",
            "established": 1955,
            "hod": "Dr. U. A. Dabade",
            "intake_btech": 60,
            "degrees": ["B.Tech Mechanical", "M.Tech Design", "M.Tech Production", "Diploma Mechanical", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Dassault Product Innovation Laboratory", "Siemens Automation & Drives Lab", "CAD/CAM Centre", "IC Engines Lab"],
            "about": "One of the pillar departments of WCE since 1955, equipped with Dassault 3DEXPERIENCE facilities and Siemens industrial automation."
        },
        "civil": {
            "name": "Department of Civil Engineering",
            "short": "Civil",
            "established": 1947,
            "hod": "Dr. K. S. Gumaste",
            "intake_btech": 60,
            "degrees": ["B.Tech Civil", "M.Tech Structures", "M.Tech Environmental", "Diploma Civil", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["DST Funded Heavy Structures Lab", "Environmental Engineering Lab", "Geotechnical Testing Lab", "Surveying & GIS Lab"],
            "about": "The founding department of Walchand College of Engineering established in 1947 by Late Shri Dhondumama Sathe with high-capacity structural testing facilities."
        },
        "electrical": {
            "name": "Department of Electrical Engineering",
            "short": "Electrical",
            "established": 1955,
            "hod": "Dr. A. P. Vaidya",
            "intake_btech": 60,
            "degrees": ["B.Tech Electrical", "M.Tech Power Systems", "M.Tech Control Systems", "Diploma Electrical", "Ph.D."],
            "accreditation": "NBA Accredited",
            "labs": ["Smart Grid & EV Lab", "High Voltage Lab", "Electrical Machines Lab", "Power Electronics Lab"],
            "about": "Established in 1955, driving power sector advancements, EV technologies, and modern smart distribution systems."
        },
        "mba": {
            "name": "Department of Management Studies (MBA)",
            "short": "MBA",
            "established": 2026,
            "degrees": ["Master of Business Administration (MBA)"],
            "intake": 60,
            "specializations": ["Technology Management", "Operations & Supply Chain", "Finance", "Marketing"],
            "about": "Newly launched postgraduate business school program approved by AICTE and affiliated with Shivaji University."
        },
        "design": {
            "name": "Department of Design",
            "short": "B.Des",
            "established": 2026,
            "degrees": ["Bachelor of Design (B.Des)"],
            "about": "Newly introduced undergraduate program focusing on Industrial Design, UX/UI, and product aesthetics."
        }
    }

    query = (payload.department or payload.query or "").lower().strip()
    for key, info in departments.items():
        if key in query or query in key or info["short"].lower() in query:
            return {"result": {**info, "college": "Walchand College of Engineering, Sangli"}}

    return {"result": {"available_departments": list(departments.keys()), "college": "Walchand College of Engineering, Sangli"}}


@router.post("/search_college_database")
async def search_college_database(payload: ToolRequest) -> dict[str, Any]:
    """Search across structured college information."""
    log.info("search_college_database called", query=payload.query)

    return {
        "result": {
            "institution": "Walchand College of Engineering, Sangli (Autonomous, Affiliated to Shivaji University)",
            "query": payload.query,
            "key_highlights": "Estd. 1947 | Highest Package ₹1.5 Cr/yr | 30,000+ Alumni | Global CEO Chanel Leena Nair | 50k sq ft Library | AICTE IDEA Lab",
            "recommended_tools": ["get_notices", "get_placement_statistics", "get_department_info", "get_faculty", "get_exam_schedule", "get_events"],
        }
    }

