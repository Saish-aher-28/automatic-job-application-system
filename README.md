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
19. [Phase 2 -- Job Description Analysis Engine](#19-phase-2---job-description-analysis-engine)
20. [Phase 3 — JD ↔ User Profile Matching Engine](#20-phase-3--jd--user-profile-matching-engine)

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

---

## 19. Phase 2 -- Job Description Analysis Engine

### Overview
Phase 2 implements a standalone Job Description (JD) Analysis system. It extracts structured information from any raw job description using Gemini Flash-Lite and persists both the raw text and the structured analysis to Firestore.

This phase is completely decoupled from the Phase 1 resume generation pipeline.

### Architecture

```
                    JOB DESCRIPTION
                           │
                           ▼
                      JD INPUT
                           │
                           ▼
                  GEMINI FLASH-LITE (gemini-3.1-flash-lite)
                           │
                           ▼
                   STRUCTURED JSON
                           │
                           ▼
                  PYTHON VALIDATOR (Pydantic v2)
                           │
                    ┌──────┴──────┐
                    │             │
                  VALID        INVALID
                    │             │
                    ▼             ▼
               FIRESTORE       RETRY/
                    │            ERROR
                    ▼
             job_descriptions
                    │
                    ▼
             STRUCTURED JD
```

### Environment Variables
Add these to your existing `.env` file at the root:

```env
# Gemini API Key -- get yours at https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key-here

# Gemini model to use
GEMINI_MODEL=gemini-3.1-flash-lite

# Maximum retries on transient Gemini API errors (default: 3)
GEMINI_MAX_RETRIES=3

# Gemini API timeout in seconds (default: 60)
GEMINI_TIMEOUT_SECONDS=60
```

### Structured Schema
The parsed JD is validated against the following Pydantic model (`JDAnalysis`):

```json
{
  "job_title": "string or null",
  "company": "string or null",
  "role_category": "string or null",
  "experience_level": "string or null",
  "employment_type": "string or null",
  "location": "string or null",
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "technologies": ["string"],
  "responsibilities": ["string"],
  "education_requirements": ["string"],
  "experience_requirements": ["string"],
  "keywords": ["string"]
}
```

### Firestore Collection
- **Collection name:** `job_descriptions`
- **Document structure:**
  - `raw_text`: the exact un-modified JD text submitted.
  - `analysis`: the validated structured analysis object (matching schema above).
  - `model`: the Gemini model identifier used.
  - `created_at`: ISO-8601 server timestamp.
  - `analysis_version`: `"1.0"`.

### CLI Usage
Run the analyzer on any text file containing a job description:

```bash
python -m phase_2.jd_analyzer.main "phase_2/input/sample_jd.txt"
```

#### Output
- Displays the structured analysis on stdout (in clean ASCII).
- Saves the validated JSON locally to: `phase_2/output/<document_id>.json`.
- Saves to Firestore under the collection `job_descriptions/` with an auto-generated document ID.

### Testing
Offline unit/mocked tests can be run without an API key or Firestore connection. Real integration tests run automatically when `GEMINI_API_KEY` is present.

#### Run Phase 2 Tests
```bash
python -m pytest "phase_2/tests/" -c "phase_2/pytest.ini" -v
```

#### Run All Tests (Phase 1 + Phase 2)
```bash
python -m pytest tests/ -c pytest.ini -q
python -m pytest "phase_2/tests/" -c "phase_2/pytest.ini" -q
```

### Phase 2 Limitations
- **No Scraping:** URLs are not supported as inputs yet. JDs must be supplied as text files or raw text.
- **No Matching:** Does not select, rank, or filter resume projects (matching is part of Phase 3).
- **No Tailoring:** Does not modify the resume or rewrite bullets (tailoring is part of Phase 3).

---

## 20. Phase 3 — JD ↔ User Profile Matching Engine

### Overview
Phase 3 builds a Job Description ↔ User Profile Matching Engine. It maps a structured Job Description (produced by Phase 2) against the user's Firestore profile data (projects, skills, education, certifications, and experience) from Phase 1. It calculates deterministic match scores, ranks project relevance using a two-stage approach, and saves the matches to Firestore.

Phase 3 is read-only with respect to the user's profile and does not modify the LaTeX template or compile resumes.

### Architecture

```
                    STRUCTURED JD
                         │
                         ▼
                 ┌───────────────┐
                 │  JD Matcher   │
                 └───────────────┘
                         ▲
                         │
                  USER PROFILE
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
          Skills      Projects    Experience
            │            │            │
            └────────────┼────────────┘
                         ▼
                   NORMALIZATION
                         │
                         ▼
              DETERMINISTIC MATCHING
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
       Skill Matching         Project Filtering
             │                       │
             │                       ▼
             │                Project Candidates
             │                       │
             │                       ▼
             │                Gemini Semantic
             │                  Relevance
             │                       │
             └───────────┬───────────┘
                         ▼
                  FINAL SCORING
                         │
                         ▼
                  RANKED RESULTS
                         │
                         ▼
                     FIRESTORE
```

### Configurable Weights
Scoring weights are configured in `phase_3/matcher/config.py` and must sum to 1.0.

#### Overall Match Score Weights
*   `REQUIRED_SKILL_WEIGHT = 0.50` (50%)
*   `PREFERRED_SKILL_WEIGHT = 0.15` (15%)
*   `TECHNOLOGY_WEIGHT = 0.15` (15%)
*   `PROJECT_WEIGHT = 0.20` (20%)

$$\text{Overall Score} = (S_{\text{req}} \times 0.50) + (S_{\text{pref}} \times 0.15) + (T \times 0.15) + (P \times 0.20)$$
where $P$ is the average score of the top 3 ranked projects.

#### Project Deterministic Scoring Weights
*   `PROJECT_REQUIRED_WEIGHT = 0.40` (40%)
*   `PROJECT_PREFERRED_WEIGHT = 0.15` (15%)
*   `PROJECT_TECHNOLOGY_WEIGHT = 0.20` (20%)
*   `PROJECT_KEYWORD_WEIGHT = 0.15` (15%)
*   `PROJECT_CATEGORY_WEIGHT = 0.10` (10%)

#### Project Final Score Blending
If a project is within the top $N$ candidates (configured by `SEMANTIC_PROJECT_CANDIDATES = 5`), it is evaluated semantically using Gemini, and its score is blended:
$$\text{Project Final Score} = (\text{Deterministic Score} \times 0.30) + (\text{Semantic Score} \times 0.70)$$
Projects outside the top $N$ candidates retain their deterministic score.

### Safety & Hallucination Protection
An active evidence validation layer matches Gemini's returned claims against actual project details. If Gemini claims a technology match that does not exist in the project's technologies list, keywords, categories, or description/bullets, the validation layer:
1. Filters it out of `matched_requirements`.
2. Adds it to `missing_requirements`.
3. Reduces the project relevance score proportionally.

### Firestore Collections
*   **Reads:** `job_descriptions`, `profiles`, `skills`, `projects`, `experience`, `certifications`.
*   **Writes:** `job_matches` (auto-generated ID).

### CLI Usage
Run the matching engine using a Firestore JD document ID:

```bash
python -m phase_3.matcher.main <jd_document_id>
```

Add the `--json` flag to print the full validated JSON schema:
```bash
python -m phase_3.matcher.main <jd_document_id> --json
```

#### Output
- Prints a clean, CP1252-safe ASCII match summary to stdout.
- Saves the validated JSON locally to: `phase_3/output/<match_id>.json`.
- Uploads the match to Firestore under the collection `job_matches/`.

### Testing
To run the Phase 3 test suite:
```bash
python -m pytest "phase_3/tests/" -c "phase_3/pytest.ini" -v
```

To run all tests (Phase 1 + Phase 2 + Phase 3):
```bash
python -m pytest tests/ -c pytest.ini -q
python -m pytest "phase_2/tests/" -c "phase_2/pytest.ini" -q
python -m pytest "phase_3/tests/" -c "phase_3/pytest.ini" -q
```

