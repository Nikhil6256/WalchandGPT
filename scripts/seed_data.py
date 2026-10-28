"""
Seed script: populates WalchandGPT database with demo college data.
Run with: python scripts/seed_data.py

All data is DEMO/SAMPLE data. It is NOT official Walchand College data.
Do not present this as official information.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def seed_admin_user(session: AsyncSession):
    """Create a default admin user."""
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    from sqlalchemy import select

    existing = await session.execute(
        select(User).where(User.email == "admin@walchandsangli.ac.in")
    )
    if existing.scalar_one_or_none():
        print("Admin user already exists")
        return

    admin = User(
        name="WalchandGPT Admin",
        email="admin@walchandsangli.ac.in",
        password_hash=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        department=None,
    )
    session.add(admin)

    student = User(
        name="Demo Student",
        email="student@walchandsangli.ac.in",
        password_hash=hash_password("Student@1234"),
        role=UserRole.STUDENT,
        department="Computer Engineering",
        year=3,
    )
    session.add(student)

    faculty = User(
        name="Demo Faculty",
        email="faculty@walchandsangli.ac.in",
        password_hash=hash_password("Faculty@1234"),
        role=UserRole.FACULTY,
        department="Computer Engineering",
    )
    session.add(faculty)

    await session.commit()
    print("✓ Seed users created")
    print("  Admin:   admin@walchandsangli.ac.in / Admin@1234")
    print("  Student: student@walchandsangli.ac.in / Student@1234")
    print("  Faculty: faculty@walchandsangli.ac.in / Faculty@1234")


async def seed_sample_documents(session: AsyncSession):
    """Create placeholder document records (content from seed text files)."""
    from app.models.document import Document, DocumentType, IndexingStatus
    from app.models.user import User
    from sqlalchemy import select

    admin = (await session.execute(
        select(User).where(User.email == "admin@walchandsangli.ac.in")
    )).scalar_one_or_none()

    if not admin:
        print("Admin user not found, skipping document seed")
        return

    sample_docs = [
        {
            "title": "Walchand College of Engineering — Official FAQ & Profile",
            "description": "Comprehensive FAQ covering history (1947), autonomous status, Shivaji University affiliation, library, and campus infrastructure.",
            "file_name": "college_faq.txt",
            "document_type": DocumentType.TXT,
            "document_category": "faq",
        },
        {
            "title": "Academic Departments, Programs & Intake Capacities",
            "description": "Details of B.Tech programs (CSE, IT, AI-ML, Robotics, Electronics, Electrical, Mechanical, Civil), newly introduced B.Des, MBA, and Integrated VLSI (5-Yr), plus Polytechnic Diploma wings.",
            "file_name": "departments_and_programs.txt",
            "document_type": DocumentType.TXT,
            "document_category": "academic",
        },
        {
            "title": "Campus Placements, Recruiters & Distinguished Alumni",
            "description": "Official placement metrics (Highest ₹1.5 Cr/yr, Avg ₹12 LPA, 300+ companies, Rubrik/Google/CRED selections) and alumni leaders (Leena Nair - Chanel CEO, Suumit Shah, IAS/IPS officers).",
            "file_name": "placements_and_alumni.txt",
            "document_type": DocumentType.TXT,
            "document_category": "placement",
        },
        {
            "title": "Current Notices, CAP Admissions & Campus Events (AY 2026-27)",
            "description": "State CET Cell CAP reporting rounds 1-4, MBA option form CAP-2, FDP on Reconfigurable Intelligent Surfaces, Marathi AICTE-VAANI workshop, SMKC Civic Innovation challenge.",
            "file_name": "current_notices_and_admissions.txt",
            "document_type": DocumentType.TXT,
            "document_category": "notice",
        },
        {
            "title": "IT Department Faculty Directory — Department of Information Technology",
            "description": "Full faculty list for the IT branch at Walchand College of Engineering, Sangli. Includes faculty names, designations, specializations, and qualifications.",
            "file_name": "it_faculty.txt",
            "document_type": DocumentType.TXT,
            "document_category": "faculty",
        },
    ]

    for doc_data in sample_docs:
        doc = Document(
            title=doc_data["title"],
            description=doc_data["description"],
            file_path=f"./storage/seed/{doc_data['file_name']}",
            file_name=doc_data["file_name"],
            document_type=doc_data["document_type"],
            document_category=doc_data["document_category"],
            uploaded_by=admin.id,
            indexing_status=IndexingStatus.PENDING,
        )
        session.add(doc)

    await session.commit()
    print("✓ Official WCE document records created in database")


async def main():
    print("=" * 50)
    print("WalchandGPT Seed Data Script")
    print("NOTE: All data is DEMO data, not official WCE data")
    print("=" * 50)

    async with AsyncSessionLocal() as session:
        await seed_admin_user(session)
        await seed_sample_documents(session)

    print("\n✓ Seeding complete!")
    print("\nNext steps:")
    print("  1. Start the backend: docker compose up backend")
    print("  2. Upload real college documents via admin dashboard")
    print("  3. The RAG pipeline will index them automatically")


if __name__ == "__main__":
    asyncio.run(main())
