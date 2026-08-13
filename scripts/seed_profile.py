"""
seed_profile.py — Seed Saish Aher's profile data into Firestore.

Usage:
    python scripts/seed_profile.py

This script is idempotent — running it again updates existing documents.
"""

import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resume_engine.profile_service import upsert_profile
from resume_engine.firebase_client import get_firestore_client


# ════════════════════════════════════════════════════════════════
# PROFILE
# ════════════════════════════════════════════════════════════════

PROFILE = {
    "name":         "Saish Aher",
    "degree_title": "B.Tech Information Technology | Honors in AI & ML",
    "email":        "saishaher28@gmail.com",
    "phone":        "+91 9699703471",
    "location":     "Kopargaon, Maharashtra, India",
    "linkedin":     "https://linkedin.com/in/saish-aher-28",
    "github":       "https://github.com/Saish-aher-28",
    "portfolio":    "",
    "summary": (
        "Results-driven B.Tech Information Technology student (CGPA: 8.4) "
        "with Honors in Artificial Intelligence and Machine Learning. "
        "Skilled in Python, Java, React, Flask, AWS, Machine Learning, "
        "Cloud Computing, Linux, and Data Analytics. "
        "Hands-on experience developing AI-powered, cloud-native, and full-stack applications. "
        "Strong foundation in Data Structures, OOP, DBMS, and problem solving. "
        "Seeking Software Engineer opportunities."
    ),
}


# ════════════════════════════════════════════════════════════════
# SKILLS  (exactly as on the resume)
# ════════════════════════════════════════════════════════════════

SKILLS = [
    # Web Development
    {"name": "HTML",               "category": "Web Development",        "sort_order": 1},
    {"name": "CSS",                "category": "Web Development",        "sort_order": 2},
    {"name": "JavaScript",         "category": "Web Development",        "sort_order": 3},
    {"name": "React",              "category": "Web Development",        "sort_order": 4},

    # Programming Languages
    {"name": "Python",             "category": "Programming Languages",  "sort_order": 1},
    {"name": "C",                  "category": "Programming Languages",  "sort_order": 2},
    {"name": "C++",                "category": "Programming Languages",  "sort_order": 3},
    {"name": "Java (OOP)",         "category": "Programming Languages",  "sort_order": 4},

    # Databases
    {"name": "MySQL",              "category": "Databases",              "sort_order": 1},
    {"name": "MongoDB",            "category": "Databases",              "sort_order": 2},
    {"name": "Firebase",           "category": "Databases",              "sort_order": 3},

    # AI/ML
    {"name": "Scikit-learn",       "category": "AI/ML",                  "sort_order": 1},
    {"name": "Pandas",             "category": "AI/ML",                  "sort_order": 2},
    {"name": "NumPy",              "category": "AI/ML",                  "sort_order": 3},
    {"name": "Matplotlib",         "category": "AI/ML",                  "sort_order": 4},
    {"name": "Seaborn",            "category": "AI/ML",                  "sort_order": 5},
    {"name": "Security Analytics", "category": "AI/ML",                  "sort_order": 6},
    {"name": "Rule-based Classification", "category": "AI/ML",           "sort_order": 7},

    # Other
    {"name": "Git",                "category": "Other",                  "sort_order": 1},
    {"name": "GitHub",             "category": "Other",                  "sort_order": 2},
    {"name": "Linux/OS Internals", "category": "Other",                  "sort_order": 3},
    {"name": "Docker",             "category": "Other",                  "sort_order": 4},
    {"name": "Kubernetes",         "category": "Other",                  "sort_order": 5},
    {"name": "GitHub Actions",     "category": "Other",                  "sort_order": 6},
]


# ════════════════════════════════════════════════════════════════
# EDUCATION
# ════════════════════════════════════════════════════════════════

EDUCATION = [
    {
        "degree":          "B.Tech",
        "field":           "Information Technology",
        "specialization":  "Honors in Artificial Intelligence and Machine Learning",
        "institution":     "Sanjivani College of Engineering",
        "location":        "Kopargaon",
        "start_year":      2023,
        "graduation_year": None,          # Present / ongoing
        "details": [
            "CGPA: 8.4",
            "HSC: 65%",
            "SSC: 88%",
        ],
        "sort_order": 1,
    },
]


# ════════════════════════════════════════════════════════════════
# CERTIFICATIONS  (exactly as on the resume)
# ════════════════════════════════════════════════════════════════

CERTIFICATIONS = [
    {
        "name":           "Amazon Cloud Operations",
        "issuer":         "AWS Training and Certification",
        "date":           "",
        "credential_url": "",
        "skills":         ["AWS", "Cloud Operations"],
        "enabled":        True,
        "sort_order":     1,
    },
    {
        "name":           "Google Cloud Career Launchpad – Data Analytics Track",
        "issuer":         "Google Cloud",
        "date":           "",
        "credential_url": "",
        "skills":         ["Data management", "Cloud storage", "Data transformation", "Visualization"],
        "enabled":        True,
        "sort_order":     2,
    },
    {
        "name":           "Programming in Java",
        "issuer":         "NPTEL",
        "date":           "",
        "credential_url": "",
        "skills":         ["Java", "OOP"],
        "enabled":        True,
        "sort_order":     3,
    },
    {
        "name":           "The Joy of Computing using Python",
        "issuer":         "NPTEL",
        "date":           "",
        "credential_url": "",
        "skills":         ["Python"],
        "enabled":        True,
        "sort_order":     4,
    },
    {
        "name":           "Employment Communication",
        "issuer":         "NPTEL",
        "date":           "",
        "credential_url": "",
        "skills":         [],
        "enabled":        True,
        "sort_order":     5,
    },
    {
        "name":           "Data Science Methods and Algorithm",
        "issuer":         "Udemy",
        "date":           "2026",
        "credential_url": "",
        "skills":         ["Data Science", "Machine Learning"],
        "enabled":        True,
        "sort_order":     6,
    },
]


# ════════════════════════════════════════════════════════════════
# LANGUAGES
# ════════════════════════════════════════════════════════════════

LANGUAGES = [
    {"name": "English", "proficiency": "Professional working fluency", "sort_order": 1},
    {"name": "Hindi",   "proficiency": "Full professional fluency",    "sort_order": 2},
    {"name": "Marathi", "proficiency": "Native speaker",               "sort_order": 3},
]


# ════════════════════════════════════════════════════════════════
# INTERESTS
# ════════════════════════════════════════════════════════════════

INTERESTS = [
    {"name": "Reading Books",               "sort_order": 1},
    {"name": "Exploring Places and New Things", "sort_order": 2},
]


# ════════════════════════════════════════════════════════════════
# SEEDING LOGIC — do not modify below this line
# ════════════════════════════════════════════════════════════════

def seed_all() -> None:
    print()
    print("=" * 60)
    print("  Seeding Firestore -- Saish Aher's Profile")
    print("=" * 60)
    print()

    db = get_firestore_client()

    # Profile
    print("  Seeding profile...")
    upsert_profile(PROFILE)

    # Skills
    print("  Seeding skills...")
    for skill in SKILLS:
        skill_id = (
            skill["name"]
            .lower()
            .replace(" ", "_")
            .replace("+", "plus")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
        )
        db.collection("skills").document(skill_id).set(
            {**skill, "enabled": True}, merge=True
        )
        print(f"    ✓ {skill['category']}: {skill['name']}")

    # Education
    print("  Seeding education...")
    for i, edu in enumerate(EDUCATION):
        doc_id = f"edu_{i+1:03d}"
        db.collection("education").document(doc_id).set(edu, merge=True)
        print(f"    ✓ {edu.get('institution', 'Unknown')} — {edu.get('field', '')}")

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
        db.collection("languages").document(doc_id).set(
            {**lang, "enabled": True}, merge=True
        )
        print(f"    ✓ {lang['name']} — {lang['proficiency']}")

    # Interests
    print("  Seeding interests...")
    for i, interest in enumerate(INTERESTS):
        doc_id = f"interest_{i+1:03d}"
        db.collection("interests").document(doc_id).set(
            {**interest, "enabled": True}, merge=True
        )
        print(f"    ✓ {interest['name']}")

    print()
    print("  ✓  All profile data seeded successfully.")
    print()
    print("  Next steps:")
    print("    1. Seed projects:  python scripts/seed_projects.py")
    print("    2. Generate resume: python -m resume_engine.main")
    print()


if __name__ == "__main__":
    seed_all()
