# Automatic Job Application System — Phase 1

> **Data-driven dynamic resume generation from Firebase Firestore using your existing LaTeX template.**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Phase 1 Architecture](#2-phase-1-architecture)
3. [Python Setup](#3-python-setup)
4. [Firebase Setup](#4-firebase-setup)
5. [Firestore Setup](#5-firestore-setup)
6. [Authentication](#6-authentication)
7. [Environment Variables](#7-environment-variables)
8. [Firestore Collections](#8-firestore-collections)
9. [How to Add Profile Information](#9-how-to-add-profile-information)
10. [How to Add a Project](#10-how-to-add-a-project)
11. [How to Import a Project](#11-how-to-import-a-project)
12. [How to Generate the Resume](#12-how-to-generate-the-resume)
13. [How to Install LaTeX](#13-how-to-install-latex)
14. [How to Compile PDF](#14-how-to-compile-pdf)
15. [How Page Count is Validated](#15-how-page-count-is-validated)
16. [How to Run Tests](#16-how-to-run-tests)
17. [Security Requirements](#17-security-requirements)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Project Overview

Phase 1 establishes the foundation for an automatic job application system. It allows you to:

- **Store** your complete professional profile in Firebase Firestore (projects, skills, education, experience, certifications, languages, interests).
- **Add** new projects, skills, or certifications dynamically — no code changes required.
- **Generate** a resume from Firestore data using your existing LaTeX template.
- **Compile** the generated `.tex` file to PDF.
- **Validate** that the generated resume does not exceed 2 pages.

The system is completely **data-driven**:
- Adding a new project = creating one new Firestore document.
- No Python code, LaTeX template, or database schema changes are needed.

---

## 2. Phase 1 Architecture

```
Firebase Firestore
        │
        ▼
  Master Profile
        │
  ┌─────┴───────────────────┐
  │         │               │
Projects  Skills       Education
  │         │               │
  └─────┬───┴───────────────┘
        │
  ┌─────┴───────────────────┐
  │         │               │
Experience Certifications  Languages
  │         │               │
  └─────┬───┴───────────────┘
        │
        ▼
Python Resume Engine
        │
        ▼
Existing LaTeX Template  ← DESIGN SOURCE OF TRUTH (never modified)
        │
        ▼
Generated .tex  (latex/output/resume.tex)
        │
        ▼
     PDF
        │
        ▼
   ≤ 2 Pages ✓
```

**Core principle:** Firestore = data truth. LaTeX template = design truth. Python = bridge.

---

## 3. Python Setup

### Requirements
- Python 3.11+
- `pip`

### Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Project structure

```
Phase 1/
├── resume_engine/       # Core Python engine
│   ├── main.py          # Entry point: python -m resume_engine.main
│   ├── config.py        # Configuration loader
│   ├── firebase_client.py
│   ├── validators.py    # LaTeX escaping + field validation
│   ├── profile_service.py
│   ├── project_service.py
│   ├── skill_service.py
│   ├── education_service.py
│   ├── experience_service.py
│   ├── certification_service.py
│   ├── language_service.py
│   ├── interest_service.py
│   ├── resume_generator.py
│   ├── latex_renderer.py
│   ├── add_project.py   # CLI: python -m resume_engine.add_project
│   └── import_project.py# CLI: python -m resume_engine.import_project
├── latex/
│   ├── resume_tex.tex   # Master LaTeX template (NEVER modified by engine)
│   └── output/          # Generated files (gitignored)
├── scripts/
│   └── seed_profile.py  # Seed initial Firestore data
├── profile/
│   └── projects/        # Example project JSON files
├── tests/               # pytest test suite
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 4. Firebase Setup

### Step 1: Create a Firebase project

1. Go to [https://console.firebase.google.com](https://console.firebase.google.com)
2. Click **Add project**
3. Enter a project name (e.g. `auto-resume`)
4. Disable Google Analytics (not needed for Phase 1)
5. Click **Create project**

### Step 2: Enable Firestore

1. In the Firebase Console, click **Firestore Database**
2. Click **Create database**
3. Select **Start in production mode** (recommended) or test mode
4. Choose a location (e.g. `asia-south1` for India)
5. Click **Enable**

---

## 5. Firestore Setup

Once Firestore is enabled, the collections are created automatically when you seed data. No manual Firestore setup is required beyond enabling the database.

The `seed_profile.py` script will create:
- `profiles/main` — your main profile document
- `skills/*` — one document per skill
- `education/*` — one document per education record
- `certifications/*` — one document per certification
- `languages/*` — one document per language
- `interests/*` — one document per interest

Projects are added separately via `add_project` or `import_project`.

---

## 6. Authentication

### Download your service account key

1. Firebase Console → **Project Settings** (gear icon)
2. Click the **Service accounts** tab
3. Click **Generate new private key**
4. Download the JSON file
5. Save it somewhere **outside** the project directory (e.g. `C:\Users\you\firebase\serviceAccount.json`)

> ⚠️ **Never put this file inside the project directory.** It is excluded by `.gitignore`, but keeping it outside is safer.

### Set the credentials path

In your `.env` file (see next section):

```
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\you\firebase\serviceAccount.json
```

---

## 7. Environment Variables

### Create your `.env` file

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Then edit `.env`:

```env
# Required: path to your Firebase service account JSON
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\serviceAccount.json

# Firestore document ID for your profile (default: main)
FIRESTORE_PROFILE_ID=main

# Maximum projects to display on the resume (others remain in Firestore)
RESUME_PROJECT_LIMIT=3

# LaTeX template path (default: latex/resume_tex.tex)
LATEX_TEMPLATE_PATH=latex/resume_tex.tex

# Output directory for generated files (default: latex/output)
LATEX_OUTPUT_DIR=latex/output
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | **Yes** | — | Path to Firebase service account JSON |
| `FIRESTORE_PROFILE_ID` | No | `main` | Profile document ID in `profiles/` collection |
| `RESUME_PROJECT_LIMIT` | No | `3` | Projects shown on resume (others stay in Firestore) |
| `LATEX_TEMPLATE_PATH` | No | `latex/resume_tex.tex` | Path to the master LaTeX template |
| `LATEX_OUTPUT_DIR` | No | `latex/output` | Directory for `.tex` and `.pdf` output |

---

## 8. Firestore Collections

| Collection | Purpose | Key fields |
|---|---|---|
| `profiles/{id}` | Your contact info and summary | `name`, `email`, `phone`, `linkedin`, `github`, `summary` |
| `projects/{auto}` | All your projects | `name`, `description`, `technologies`, `resume_bullets`, `enabled` |
| `skills/{id}` | Skills grouped by category | `name`, `category`, `sort_order`, `enabled` |
| `education/{auto}` | Education records | `degree`, `field`, `institution`, `graduation_year`, `details` |
| `experience/{auto}` | Work experience | `company`, `role`, `start_date`, `end_date`, `resume_bullets` |
| `certifications/{auto}` | Certifications and awards | `name`, `issuer`, `date`, `credential_url`, `enabled` |
| `languages/{auto}` | Languages you speak | `name`, `proficiency`, `enabled` |
| `interests/{auto}` | Personal interests | `name`, `enabled` |

### Dynamic design

- Each entity (project, skill, certification, etc.) is its **own Firestore document**.
- Adding a new project = adding a new document in `projects/`.
- **No schema changes, no code changes, no template changes** are needed.
- Documents have an `enabled` field — set to `false` to hide from resume without deleting.

### RESUME_PROJECT_LIMIT

The database can contain unlimited projects. `RESUME_PROJECT_LIMIT` controls how many appear on the generated resume. The rest remain in Firestore for future job-description matching.

```
Firestore: 10 projects
RESUME_PROJECT_LIMIT=3
Generated resume: 3 projects (top by priority, then name)
Other 7 projects: safely stored in Firestore
```

---

## 9. How to Add Profile Information

### Edit and run the seed script

1. Open `scripts/seed_profile.py`
2. Fill in all `"YOUR_VALUE_HERE"` fields with your real information
3. Activate your virtual environment
4. Run:

```bash
python scripts/seed_profile.py
```

This script is **idempotent** — running it again updates existing data without creating duplicates.

> ⚠️ Do not invent data. Only fill in information that accurately represents you.

---

## 10. How to Add a Project

### Interactive CLI

```bash
python -m resume_engine.add_project
```

You will be prompted for:

```
Project name: My Portfolio Website
Year: 2024
Description: A personal portfolio built with React and Firebase.
Technologies (comma-separated): React, Firebase, CSS
Categories (comma-separated): frontend, web
Keywords (comma-separated): portfolio, react
GitHub URL: https://github.com/yourname/portfolio
Project URL:
Resume bullets (one per line, press Enter on empty line when done):
  > Built responsive UI with React achieving 98 Lighthouse score.
  > Deployed to Firebase Hosting with CI/CD pipeline.
  >
```

After confirmation, the project is created in Firestore with an auto-generated ID.

**No code changes. No template changes. No schema changes needed.**

To regenerate the resume with the new project:

```bash
python -m resume_engine.main
```

---

## 11. How to Import a Project

### JSON import

Create a JSON file (see `profile/projects/example_project.json` for the full schema):

```json
{
    "name": "My Project",
    "description": "What it does.",
    "technologies": ["Python", "Flask"],
    "resume_bullets": ["Achieved X by doing Y."],
    "categories": ["backend"],
    "keywords": ["api", "flask"],
    "enabled": true
}
```

Then import it:

```bash
python -m resume_engine.import_project profile/projects/my_project.json
```

The script validates the JSON, uploads it to Firestore, and prints the new document ID.

---

## 12. How to Generate the Resume

```bash
python -m resume_engine.main
```

Example output:

```
╔══════════════════════════════════════════════════════════╗
║          Automatic Job Application System                ║
║          Phase 1 — Resume Generator                      ║
╚══════════════════════════════════════════════════════════╝

  Connecting to Firestore...
  ✓  Connected.

  Generating resume...

  Loading profile... ✓
  Loading projects... ✓  (3/7 selected for resume, limit=3)
  Loading skills... ✓  (18 skills in 5 categories)
  Loading education... ✓  (1 records)
  Loading experience... ✓  (0 records)
  Loading certifications... ✓  (6 records)
  Loading languages... ✓  (3 records)
  Loading interests... ✓  (2 records)
  Rendering LaTeX... ✓
  Writing .tex file... ✓  latex/output/resume.tex
  Compiling PDF...
  PDF compiled successfully.
  Counting pages... ✓  2 page(s) — within 2-page limit.

────────────────────────────────────────────────────────────
  ✓  Resume generation successful.

  Output:
    .tex → latex/output/resume.tex
    .pdf → latex/output/resume.pdf
    ✓ Pages: 2 / 2 max
```

### Override project limit for a single run

```bash
python -m resume_engine.main --limit 5
```

---

## 13. How to Install LaTeX

`pdflatex` is required to compile `.tex` to PDF. If it's not installed, the `.tex` file is still generated but PDF compilation is skipped with clear instructions.

### Windows (MiKTeX — Recommended)

1. Download MiKTeX from: [https://miktex.org/download](https://miktex.org/download)
2. Run the installer
3. Choose "Install missing packages on the fly" → Yes
4. Restart your terminal/PowerShell
5. Verify: `pdflatex --version`

### Windows (TeX Live)

1. Download from: [https://tug.org/texlive/](https://tug.org/texlive/)
2. Follow the installer instructions

### macOS

```bash
brew install --cask mactex
```

### Ubuntu/Debian

```bash
sudo apt-get install texlive-full
```

---

## 14. How to Compile PDF

PDF compilation happens automatically when you run:

```bash
python -m resume_engine.main
```

If `pdflatex` is installed, the PDF is generated at `latex/output/resume.pdf`.

You can also compile manually:

```bash
pdflatex -output-directory latex/output latex/output/resume.tex
```

The master template (`latex/resume_tex.tex`) is **never touched**. Only `latex/output/resume.tex` is modified.

---

## 15. How Page Count is Validated

After PDF generation, the engine uses `PyMuPDF` to count the pages:

- **≤ 2 pages** → ✓ Pass
- **> 2 pages** → ⚠ Warning (non-zero exit code)

If the resume exceeds 2 pages:
- The engine reports the problem clearly.
- It identifies the likely cause (too many projects).
- It suggests lowering `RESUME_PROJECT_LIMIT`.
- **No information is silently deleted.**
- **No sections are removed.**
- **The design is not changed.**

Example warning:
```
  ⚠  Resume is 3 pages — exceeds the 2-page limit.
     Suggestion: lower RESUME_PROJECT_LIMIT (currently 5) in your .env file.
     Projects in Firestore remain untouched.
```

---

## 16. How to Run Tests

### Run all offline tests (no Firebase needed)

```bash
python -m pytest tests/ --ignore=tests/test_firebase.py -v
```

### Run Firebase connection tests (requires credentials)

```bash
python -m pytest tests/test_firebase.py -v
```

### Run all tests

```bash
python -m pytest tests/ -v
```

### Test coverage by file

| Test file | What it tests | Requires Firebase |
|---|---|---|
| `test_validators.py` | LaTeX escaping (all 10 chars), field validation | No |
| `test_latex_renderer.py` | Section rendering, placeholder replacement, template immutability | No |
| `test_projects.py` | Dynamic project CRUD, **critical A→B→C→D test** | No (mocked) |
| `test_profile.py` | Profile get/upsert | No (mocked) |
| `test_resume_generator.py` | End-to-end pipeline, template unchanged after generation | No (mocked) |
| `test_firebase.py` | Real Firestore connection | **Yes** |

### The Critical Dynamic Project Test

`tests/test_projects.py::TestCriticalDynamicProjectTest::test_dynamic_project_addition` verifies:

1. Start with 3 projects (A, B, C) → `get_all_projects()` returns 3
2. Add Project D (simulated, no code/schema/template changes)
3. `get_all_projects()` returns 4
4. Project D is in the results

---

## 17. Security Requirements

**Never commit:**
- `.env` (contains your credentials path)
- Firebase service account JSON files
- Any file matching `serviceAccount*.json` or `*credentials*.json`
- Private keys of any kind

All of the above are excluded by `.gitignore`.

**Best practices:**
- Store your service account JSON **outside** the project directory
- Use environment variables — never hardcode credentials
- Do not print credentials in logs (the engine never does this)
- Regularly rotate your Firebase service account key

**Before every `git push`:**

```bash
git status
```

Verify that no `.json` credential files or `.env` appear in the staged files.

---

## 18. Troubleshooting

### `Firebase credentials not configured`

**Cause:** `GOOGLE_APPLICATION_CREDENTIALS` is not set in `.env`.

**Fix:**
1. Copy `.env.example` to `.env`
2. Set `GOOGLE_APPLICATION_CREDENTIALS=C:\full\path\to\serviceAccount.json`
3. Verify the file exists at that path

### `Service account file not found`

**Cause:** The path in `GOOGLE_APPLICATION_CREDENTIALS` is wrong.

**Fix:** Check the path is absolute and the file exists:
```bash
ls "C:\path\to\serviceAccount.json"
```

### `pdflatex not found`

**Cause:** LaTeX is not installed.

**Fix:** Install MiKTeX (see [Section 13](#13-how-to-install-latex)). The `.tex` file is still generated even without `pdflatex`.

### `Profile not found in Firestore`

**Cause:** The seed script hasn't been run yet.

**Fix:**
1. Edit `scripts/seed_profile.py` with your real data
2. Run `python scripts/seed_profile.py`

### `Unfilled placeholders remaining in template`

**Cause:** A placeholder like `{{NAME}}` was not replaced — the profile field is missing.

**Fix:** Run `python scripts/seed_profile.py` to ensure all profile fields are set.

### Resume exceeds 2 pages

**Cause:** Too many projects are being displayed.

**Fix:** Lower `RESUME_PROJECT_LIMIT` in `.env`:
```
RESUME_PROJECT_LIMIT=2
```
Your other projects remain safely in Firestore.

### Tests fail with import errors

**Cause:** Virtual environment not activated or dependencies not installed.

**Fix:**
```bash
venv\Scripts\activate      # Windows
pip install -r requirements.txt
python -m pytest tests/ -v
```
