# AutoResume — Automatic Job Application System

> **An end-to-end, AI-powered job application automation platform** — from multi-source job discovery and Gemini-AI analysis to deterministic profile matching, dynamic LaTeX resume tailoring, link health classification, and strict application lifecycle tracking.

[![Go](https://img.shields.io/badge/Go-1.22+-00ADD8?logo=go)](https://go.dev/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)](https://react.dev/)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?logo=firebase)](https://firebase.google.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-4285F4?logo=google)](https://ai.google.dev/)

---

## Overview

AutoResume automates the repetitive work of job applications:

1. **Discovers** jobs automatically from Telegram channels and career websites
2. **Analyzes** job descriptions using Google Gemini AI
3. **Matches** your master profile against each job deterministically
4. **Tailors** your LaTeX resume specifically for each opportunity
5. **Tracks** every application through a full lifecycle — from discovery to offer

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│             React Dashboard (Vite + TypeScript)      │
│  Dashboard │ Applications │ Jobs │ Sources │ Profile  │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────┐
│              Go Backend API (:8080)                  │
│  Auth │ Jobs │ Applications │ Sources │ Task Worker   │
└──────┬───────────────┬────────────────┬─────────────┘
       │               │                │
┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│  Firestore  │ │  Phase 2    │ │  Phase 4    │
│  Database   │ │  JD Analyze │ │  Resume PDF │
└─────────────┘ └──────┬──────┘ └─────────────┘
                       │
                ┌──────▼──────┐
                │  Phase 3    │
                │  Matcher    │
                └─────────────┘
```

---

## Project Phases

### Phase 1 — Resume Engine & Core Infrastructure
- Master profile schema (Firestore)
- LaTeX master template (`latex/resume_tex.tex`) — **immutable**, SHA-256 verified
- PDF compilation via [Tectonic](https://tectonic-typesetting.github.io/) CLI
- Profile data models: personal info, experience, education, projects, skills, certifications

### Phase 2 — Gemini JD Analysis
- Parses raw job descriptions with Google Gemini API
- Extracts: Job Title, Company, Required Skills, Preferred Skills, Technologies, Responsibilities
- Stores structured analysis in Firestore `job_descriptions` collection

### Phase 3 — Hybrid Job ↔ Profile Matching Engine
- **Stage 1 (Deterministic)**: Alias-normalized exact skill matching
  - `k8s` → `Kubernetes`, `react.js` → `React`, `postgres` → `PostgreSQL`
- **Stage 2 (Semantic)**: Gemini-powered project relevance scoring
- **Weighted Formula**:
  ```
  Overall Score = (Required Skills × 0.50)
                + (Preferred Skills × 0.15)
                + (Technologies     × 0.15)
                + (Project Relevance × 0.20)
  ```
- Anti-hallucination controls: Java ≠ JavaScript, React ≠ React Native, PostgreSQL ≠ MongoDB

### Phase 4 — Dynamic Resume Tailoring Pipeline
- Reorders skills to front-load matched required skills
- Selects top-3 most relevant projects for the target job
- Tailors summary section without fabricating technologies
- Page budget enforcement (≤ 2 pages), auto-adjusts on overflow
- Immutable master template (SHA-256 locked)

### Phase 5 — Full-Stack Web Application
- **Go REST API** (`phase_5/backend/`) — `net/http`, Firestore, Firebase Auth
- **React + Vite Dashboard** (`phase_5/frontend/`) — dark glassmorphic UI, vanilla CSS
- **Pages**: Dashboard, Applications Tracker, Job Pipeline, Job Opportunities, Job Sources, Ingestion Runs, Profile, Projects, Skills, Education

### Phase 6 — Multi-Source Job Discovery & Ingestion
- Telegram public channel scrapers
- Generic career website adapters
- 15-minute background scheduler (configurable via `INGESTION_INTERVAL_MINUTES`)
- Pre-Gemini deduplication (avoids redundant API calls)
- Per-source retry logic with exponential backoff

### Phase 7 — Application Management & Tracking
- Full application lifecycle state machine:
  ```
  DISCOVERED → ANALYZED → MATCHED → RESUME_GENERATING
  → RESUME_GENERATED → READY_TO_APPLY → APPLICATION_STARTED
  → SUBMITTED → INTERVIEW / OFFER / REJECTED
  ```
- Asynchronous task queue (`QUEUED → RUNNING → SUCCESS/FAILED`)
- Full audit event logging in `events` sub-collection
- Application event history per application

### Phase 7.1 — System Reliability & Application Truth Audit
- **Application Submission Truth**: Explicit `confirmation: true` required; blocks premature submission from `DISCOVERED` state
- **URL Health Classifier**: 7-state classification — `WORKING`, `REDIRECTED`, `NOT_FOUND`, `BLOCKED`, `RATE_LIMITED`, `TIMEOUT`, `INVALID_URL`
- **Two-tier URL Safety**: Dangerous schemes (`javascript:`, `file:`, `data:`, `vbscript:`) blocked at creation; malformed URLs stored & classified lazily
- **Adversarial Matching Tests**: 15 test cases verifying no false-positive skill matches

---

## Test Results

| Suite | Tests | Result |
|:---|:---:|:---:|
| Phase 1 — Resume Engine | 98 | ✅ 100% |
| Phase 2 — JD Analysis | 54 | ✅ 100% |
| Phase 3 — Matcher | 51 | ✅ 100% |
| Phase 4 — Resume Pipeline | 61 | ✅ 100% |
| Phase 7.1 — E2E Compliance | 7 | ✅ 100% |
| Adversarial Match Suite | 15 | ✅ 100% |
| Go Backend Unit Tests | — | ✅ 0 failures |

---

## Getting Started

### Prerequisites

- [Go 1.22+](https://go.dev/dl/)
- [Python 3.11+](https://python.org/downloads/)
- [Node.js 20.19+](https://nodejs.org/)
- [Tectonic](https://tectonic-typesetting.github.io/) (LaTeX engine)
- Google Cloud Firestore project
- Google Gemini API key

### 1. Clone & Environment Setup

```bash
git clone https://github.com/<your-username>/AutoResume.git
cd AutoResume
cp .env.example .env
# Fill in all values in .env
```

### 2. Python Dependencies

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Go Backend

```bash
cd phase_5/backend
go run ./cmd/server/main.go
# API available at http://localhost:8080
```

### 4. React Frontend

```bash
cd phase_5/frontend
npm install
npm run dev
# Dashboard at http://localhost:5173
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Firebase / Firestore
FIREBASE_PROJECT_ID=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccount.json

# Backend config
PORT=8080
CORS_ORIGIN=http://localhost:5173
SINGLE_USER_MODE=true
INGESTION_INTERVAL_MINUTES=15

# Frontend (Vite)
VITE_API_URL=http://localhost:8080
```

---

## Docker

```bash
# From phase_5/
docker-compose up --build
```

---

## Directory Structure

```
AutoResume/
├── latex/              # Master LaTeX template (immutable)
├── profile/            # Master profile JSON data
├── resume_engine/      # Phase 1: Resume model & Firestore
├── phase_2/            # JD analysis via Gemini
├── phase_3/            # Hybrid matching engine
├── phase_4/            # Resume tailoring pipeline
├── phase_5/
│   ├── backend/        # Go REST API
│   └── frontend/       # React + Vite dashboard
├── phase_6/            # Job discovery & ingestion workers
├── .env.example        # Environment variable template
├── requirements.txt    # Python dependencies
└── pytest.ini          # Test configuration
```

---

## API Overview

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Server health check |
| `GET/POST` | `/api/v1/jobs` | Job pipeline management |
| `POST` | `/api/v1/jobs/:id/check-url` | Classify application URL health |
| `GET/POST` | `/api/v1/applications` | Application tracker |
| `POST` | `/api/v1/applications/:id/submit` | Submit application (requires `confirmation: true`) |
| `GET/POST` | `/api/v1/sources` | Job source management |
| `POST` | `/api/v1/sources/:id/run` | Trigger manual ingestion run |
| `GET` | `/api/v1/runs` | Background ingestion run history |
| `GET` | `/api/v1/opportunities` | Discovered opportunities |
| `POST` | `/api/v1/opportunities/:id/import` | Import opportunity to pipeline |
| `GET/PUT` | `/api/v1/profile` | Master profile |
| `GET/POST/DELETE` | `/api/v1/projects` | Projects CRUD |
| `GET/POST/DELETE` | `/api/v1/skills` | Skills CRUD |

---

## Security

- Firebase service account keys and `.env` are **gitignored by default**
- Dangerous URL schemes (`javascript:`, `file:`, `data:`, `vbscript:`) blocked at job creation
- API keys stripped from error logs before storage
- Application submission requires explicit user confirmation
- All Firestore writes go through typed models — no raw JSON passthrough

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built with Go · Python · React · Gemini AI · Firebase · LaTeX*
