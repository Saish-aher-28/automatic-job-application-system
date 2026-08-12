"""
seed_profile.py — Seed your profile data into Firestore.

IMPORTANT:
  Fill in every "YOUR_VALUE_HERE" with your real information
  before running this script.

  The system will NEVER invent data. Only what you provide here
  is stored in Firestore.

Usage:
    python scripts/seed_profile.py

This script is idempotent — running it again updates the existing document.
"""

import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resume_engine.profile_service import upsert_profile
from resume_engine.firebase_client import get_firestore_client


# ════════════════════════════════════════════════════════════════
# FILL IN YOUR REAL INFORMATION BELOW
# DO NOT leave "YOUR_VALUE_HERE" when running for real.
# ════════════════════════════════════════════════════════════════

PROFILE = {
    # Your full name as it should appear on the resume
    "name": "YOUR_VALUE_HERE",

    # e.g. "B.E. Computer Science" or "M.Tech Data Science"
    "degree_title": "YOUR_VALUE_HERE",

    # Contact
    "email":    "YOUR_VALUE_HERE",
    "phone":    "YOUR_VALUE_HERE",
    "location": "YOUR_VALUE_HERE",     # e.g. "Mumbai, India"

    # Social links — full URLs
    "linkedin":  "https://linkedin.com/in/YOUR_USERNAME",
    "github":    "https://github.com/YOUR_USERNAME",
    "portfolio": "",                    # Leave empty if not applicable

    # Professional summary (2–4 sentences)
    "summary": "YOUR_VALUE_HERE",
}


# ════════════════════════════════════════════════════════════════
# SKILLS — fill in your real skills
# Format: {document_id: {name, category, sort_order}}
# ════════════════════════════════════════════════════════════════

SKILLS = [
    # Programming Languages
    {"name": "Python",      "category": "Programming Languages", "sort_order": 1},
    {"name": "C++",         "category": "Programming Languages", "sort_order": 2},
    {"name": "Java",        "category": "Programming Languages", "sort_order": 3},

    # Web Development
    {"name": "HTML",        "category": "Web Development", "sort_order": 1},
    {"name": "CSS",         "category": "Web Development", "sort_order": 2},
    {"name": "JavaScript",  "category": "Web Development", "sort_order": 3},
    {"name": "React",       "category": "Web Development", "sort_order": 4},

    # Databases
    {"name": "MySQL",       "category": "Databases", "sort_order": 1},
    {"name": "PostgreSQL",  "category": "Databases", "sort_order": 2},
    {"name": "MongoDB",     "category": "Databases", "sort_order": 3},
    {"name": "Firebase",    "category": "Databases", "sort_order": 4},

    # AI/ML — add your actual skills here
    {"name": "YOUR_SKILL",  "category": "AI/ML", "sort_order": 1},

    # Other
    {"name": "Git",         "category": "Other", "sort_order": 1},
    {"name": "Linux",       "category": "Other", "sort_order": 2},
]


# ════════════════════════════════════════════════════════════════
# EDUCATION — fill in your real education records
# ════════════════════════════════════════════════════════════════

EDUCATION = [
    {
        "degree":          "Bachelor of Engineering",
        "field":           "Computer Science",
        "specialization":  "",
        "institution":     "YOUR_INSTITUTION_HERE",
        "location":        "YOUR_CITY_HERE",
        "start_year":      2021,
        "graduation_year": 2025,
        "details":         [
            "CGPA: YOUR_CGPA/10",
            "HSC: YOUR_HSC%",
            "SSC: YOUR_SSC%",
        ],
        "sort_order": 1,
    },
    # Add more education records as needed
]


# ════════════════════════════════════════════════════════════════
# CERTIFICATIONS — fill in your real certifications
# ════════════════════════════════════════════════════════════════

CERTIFICATIONS = [
    {
        "name":           "YOUR_CERTIFICATION_NAME",
        "issuer":         "YOUR_ISSUER",
        "date":           "2024",
        "credential_url": "",
        "skills":         [],
        "enabled":        True,
        "sort_order":     1,
    },
    # Add more certifications as needed
]


# ════════════════════════════════════════════════════════════════
# LANGUAGES
# ════════════════════════════════════════════════════════════════

LANGUAGES = [
    {"name": "English", "proficiency": "Professional working fluency", "sort_order": 1},
    {"name": "Hindi",   "proficiency": "Full professional fluency",    "sort_order": 2},
    # Add your native language or others as needed
]


# ════════════════════════════════════════════════════════════════
# INTERESTS
# ════════════════════════════════════════════════════════════════

INTERESTS = [
    {"name": "Reading Books",  "sort_order": 1},
    {"name": "YOUR_INTEREST",  "sort_order": 2},
]


# ════════════════════════════════════════════════════════════════
# SEEDING LOGIC — do not modify below this line
# ════════════════════════════════════════════════════════════════

def seed_all() -> None:
    print()
    print("═" * 60)
    print("  Seeding Firestore with profile data")
    print("═" * 60)
    print()

    db = get_firestore_client()

    # Profile
    print("  Seeding profile...")
    upsert_profile(PROFILE)

    # Skills
    print("  Seeding skills...")
    for skill in SKILLS:
        skill_id = skill["name"].lower().replace(" ", "_").replace("+", "plus")
        db.collection("skills").document(skill_id).set({**skill, "enabled": True}, merge=True)
        print(f"    ✓ {skill['category']}: {skill['name']}")

    # Education
    print("  Seeding education...")
    for i, edu in enumerate(EDUCATION):
        doc_id = f"edu_{i+1:03d}"
        db.collection("education").document(doc_id).set(edu, merge=True)
        print(f"    ✓ {edu.get('institution', 'Unknown')}")

    # Certifications
    print("  Seeding certifications...")
    for i, cert in enumerate(CERTIFICATIONS):
        doc_id = f"cert_{i+1:03d}"
        db.collection("certifications").document(doc_id).set(cert, merge=True)
        print(f"    ✓ {cert.get('name', 'Unknown')}")

    # Languages
    print("  Seeding languages...")
    for i, lang in enumerate(LANGUAGES):
        doc_id = f"lang_{i+1:03d}"
        db.collection("languages").document(doc_id).set({**lang, "enabled": True}, merge=True)
        print(f"    ✓ {lang['name']}")

    # Interests
    print("  Seeding interests...")
    for i, interest in enumerate(INTERESTS):
        doc_id = f"interest_{i+1:03d}"
        db.collection("interests").document(doc_id).set({**interest, "enabled": True}, merge=True)
        print(f"    ✓ {interest['name']}")

    print()
    print("  ✓  All data seeded successfully.")
    print()
    print("  Next steps:")
    print("    1. Add your projects: python -m resume_engine.add_project")
    print("    2. Generate resume:   python -m resume_engine.main")
    print()


if __name__ == "__main__":
    seed_all()
