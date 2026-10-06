# AWS Lightsail Production Deployment Guide

This guide outlines the production deployment strategy for the Automatic Job Application System on AWS Lightsail.

## 1. Instance Sizing Recommendations

The system involves two components:
- Go Backend: High CPU during resume tailoring (Python semantic matcher calls, Gemini parsing, and Tectonic LaTeX PDF compilations).
- Frontend: Served as a lightweight static site via Nginx.

### Recommended Tier
- **Size**: **2 GB RAM, 2 vCPUs**
- **Storage**: **60 GB SSD**
- **Monthly Cost**: ~$10 USD
- **Rationale**: Tectonic compilation and python genai libraries require at least 1.5 GB of free memory to compile PDFs quickly without running out of memory. 1 vCPU instances will face throttling during multi-page compilations, so 2 vCPUs is recommended.

## 2. Setting Up Firebase and Environment

Ensure the following credentials are provided to the Lightsail Container Service or set up in the `.env` file:
1. `GEMINI_API_KEY`: API key for Gemini Flash-Lite.
2. `FIREBASE_PROJECT_ID`: Target Firebase project.
3. `GOOGLE_APPLICATION_CREDENTIALS`: Path to Firestore credentials JSON file.
4. `SINGLE_USER_MODE`: `false` for multi-user production SaaS, `true` for single developer dashboard.

## 3. Deploying using Docker Compose

To deploy on a Lightsail virtual instance (VPS):
1. Install Docker and Docker Compose on the Lightsail VPS.
2. Clone the repository and navigate to `phase_5`.
3. Create `backend-credentials.json` containing the Firestore service account credentials.
4. Create `.env` file containing:
   ```env
   GEMINI_API_KEY=your-gemini-key
   FIREBASE_PROJECT_ID=your-firebase-project-id
   ```
5. Run:
   ```bash
   docker-compose up -d --build
   ```
6. The app will be available on:
   - Frontend: Port 3000
   - Go REST API: Port 8080
