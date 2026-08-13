"""
seed_projects.py — Bulk-upload all of Saish Aher's projects to Firestore.

Usage:
    python scripts/seed_projects.py

This script is idempotent — it checks if a project with the same name already
exists before uploading to avoid duplicates. Run any time you want to add or
update projects.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resume_engine.firebase_client import get_firestore_client


# ════════════════════════════════════════════════════════════════
# PROJECTS  (all 5 projects from the resume)
# priority: lower number = shown first on resume
# ════════════════════════════════════════════════════════════════

PROJECTS = [
    {
        "name": "InventIQ – ML-Powered Inventory Demand Forecasting System",
        "year": "2026",
        "description": (
            "Flask application using Random Forest and XGBoost on 73K+ records "
            "with forecasting dashboard, low-stock alerts and restock recommendations."
        ),
        "technologies": ["Python", "Flask", "Scikit-learn", "XGBoost", "Pandas"],
        "categories":   ["machine_learning", "backend", "data_science"],
        "keywords":     ["inventory", "forecasting", "random forest", "xgboost", "flask", "ml"],
        "resume_bullets": [
            "Built Flask application using Random Forest and XGBoost on 73K+ records "
            "with forecasting dashboard, low-stock alerts and restock recommendations.",
        ],
        "resume_content": {
            "general":          [],
            "machine_learning": [
                "Trained Random Forest and XGBoost models on 73K+ inventory records to "
                "forecast demand with high accuracy.",
                "Built low-stock alert system and automated restock recommendation engine.",
            ],
            "data_science":     [],
            "backend":          [
                "Developed Flask-based forecasting dashboard with interactive visualizations.",
            ],
            "frontend":         [],
            "cloud":            [],
            "devops":           [],
        },
        "github_url":  "",
        "project_url": "",
        "priority":    1,
        "enabled":     True,
    },
    {
        "name": "CloudReport Pipeline – Automated AWS Reporting System",
        "year": "2026",
        "description": (
            "Fully automated serverless pipeline that reads raw data from an S3 bucket, "
            "processes it using Lambda, generates structured reports, and delivers them "
            "via SES email — triggered on a scheduled time using EventBridge."
        ),
        "technologies": ["AWS", "S3", "Lambda", "EventBridge", "SES", "IAM", "Python"],
        "categories":   ["cloud", "backend", "devops"],
        "keywords":     ["aws", "serverless", "lambda", "s3", "ses", "eventbridge", "automation"],
        "resume_bullets": [
            "Built a fully automated serverless pipeline that reads raw data from an S3 bucket, "
            "processes it using Lambda, generates structured reports, and delivers them via SES "
            "email — triggered on a scheduled time using EventBridge.",
        ],
        "resume_content": {
            "general":          [],
            "machine_learning": [],
            "data_science":     [],
            "backend":          [],
            "frontend":         [],
            "cloud":            [
                "Designed end-to-end serverless AWS pipeline using S3, Lambda, EventBridge, and SES.",
                "Configured IAM roles and policies for least-privilege access across all pipeline components.",
                "Automated scheduled report delivery via SES without any manual intervention.",
            ],
            "devops":           [],
        },
        "github_url":  "",
        "project_url": "",
        "priority":    2,
        "enabled":     True,
    },
    {
        "name": "Cybersecurity Threat Analyser",
        "year": "2025",
        "description": (
            "Flask-based threat detection system that identifies brute-force attacks, "
            "unauthorized access, data exfiltration, and suspicious IP activity using "
            "log pattern analysis and rule-based classification on preprocessed CSV data."
        ),
        "technologies": ["Python", "Flask", "Pandas", "NumPy", "HTML", "CSS"],
        "categories":   ["backend", "machine_learning", "web"],
        "keywords":     [
            "cybersecurity", "threat detection", "brute force", "log analysis",
            "rule-based", "flask", "security analytics",
        ],
        "resume_bullets": [
            "Built a Flask-based threat detection system that identifies brute-force attacks, "
            "unauthorized access, data exfiltration, and suspicious IP activity using log "
            "pattern analysis and rule-based classification on preprocessed CSV data.",
        ],
        "resume_content": {
            "general":          [],
            "machine_learning": [
                "Implemented rule-based classification to detect brute-force attacks, "
                "unauthorized access, and data exfiltration from log data.",
            ],
            "data_science":     [],
            "backend":          [
                "Built Flask web interface for real-time log upload and threat report visualization.",
            ],
            "frontend":         [],
            "cloud":            [],
            "devops":           [],
        },
        "github_url":  "",
        "project_url": "",
        "priority":    3,
        "enabled":     True,
    },
    {
        "name": "Customer Churn Analysis – Supervised vs Unsupervised Learning",
        "year": "2026",
        "description": (
            "Predicts telecom customer churn using Random Forest algorithm (93.65% accuracy) "
            "and segments customers into risk groups using KMeans clustering, combining both "
            "into a hybrid retention strategy for preventative churn."
        ),
        "technologies": ["Python", "Scikit-learn", "Pandas", "NumPy", "Matplotlib"],
        "categories":   ["machine_learning", "data_science"],
        "keywords":     [
            "churn prediction", "random forest", "kmeans", "clustering",
            "telecom", "retention", "supervised learning", "unsupervised learning",
        ],
        "resume_bullets": [
            "Predicted telecom customer churn using Random Forest algorithm (93.65% accuracy) "
            "and segmented customers into risk groups using KMeans clustering algorithm, "
            "combining both into a hybrid retention strategy for preventative churn.",
        ],
        "resume_content": {
            "general":          [],
            "machine_learning": [
                "Achieved 93.65% accuracy in churn prediction using Random Forest classifier.",
                "Applied KMeans clustering to segment customers into risk groups for targeted retention.",
                "Designed hybrid supervised + unsupervised strategy combining both model outputs.",
            ],
            "data_science":     [
                "Performed EDA and feature engineering on telecom customer dataset.",
                "Visualized churn patterns and cluster distributions using Matplotlib.",
            ],
            "backend":          [],
            "frontend":         [],
            "cloud":            [],
            "devops":           [],
        },
        "github_url":  "",
        "project_url": "",
        "priority":    4,
        "enabled":     True,
    },
    {
        "name": "Transportation Shipment Management App",
        "year": "2025",
        "description": (
            "Web-based solution for managing truck transport records, streamlining operations "
            "for logistics companies using React and Firebase."
        ),
        "technologies": ["React", "Firebase", "Authentication", "Firestore", "Material-UI"],
        "categories":   ["frontend", "web"],
        "keywords":     [
            "react", "firebase", "logistics", "transport", "management", "material-ui", "full-stack",
        ],
        "resume_bullets": [
            "Built a web-based solution for managing truck transport records, "
            "streamlining operations for logistics companies.",
        ],
        "resume_content": {
            "general":          [],
            "machine_learning": [],
            "data_science":     [],
            "backend":          [],
            "frontend":         [
                "Built React frontend with Material-UI components for managing transport records.",
                "Integrated Firebase Authentication for secure user login and role-based access.",
                "Used Firestore as real-time database for shipment tracking and record management.",
            ],
            "cloud":            [],
            "devops":           [],
        },
        "github_url":  "",
        "project_url": "",
        "priority":    5,
        "enabled":     True,
    },
]


# ════════════════════════════════════════════════════════════════
# SEEDING LOGIC
# ════════════════════════════════════════════════════════════════

def seed_projects() -> None:
    print()
    print("=" * 60)
    print("  Seeding Firestore -- Projects")
    print("=" * 60)
    print()

    db = get_firestore_client()
    collection = db.collection("projects")

    # Build a map of existing project names → document IDs to avoid duplicates
    existing: dict[str, str] = {}
    for doc in collection.stream():
        data = doc.to_dict()
        if data.get("name"):
            existing[data["name"]] = doc.id

    uploaded = 0
    updated  = 0

    for project in PROJECTS:
        name = project["name"]
        if name in existing:
            # Update existing document
            doc_id = existing[name]
            collection.document(doc_id).set(project, merge=True)
            print(f"  ↺  Updated: {name}")
            print(f"     ID: {doc_id}")
            updated += 1
        else:
            # Create new document with auto-generated ID
            _, doc_ref = collection.add(project)
            print(f"  ✓  Uploaded: {name}")
            print(f"     ID: {doc_ref.id}")
            uploaded += 1

    print()
    print(f"  Done — {uploaded} new, {updated} updated, {len(PROJECTS)} total projects.")
    print()
    print("  Next step:")
    print("    python -m resume_engine.main")
    print()


if __name__ == "__main__":
    seed_projects()
