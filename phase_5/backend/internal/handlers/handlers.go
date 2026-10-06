package handlers

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/firestore"
	"google.golang.org/api/iterator"

	"phase_5/backend/internal/auth"
	"phase_5/backend/internal/config"
	"phase_5/backend/internal/models"
	"phase_5/backend/internal/services"
)

type APIHandler struct {
	cfg        *config.Config
	db         *firestore.Client
	executor   *services.PythonExecutor
	worker     *services.IngestionWorkerService
	taskWorker *services.TaskWorkerService
	urlChecker *services.URLCheckerService
}

func NewAPIHandler(cfg *config.Config, db *firestore.Client, executor *services.PythonExecutor, worker *services.IngestionWorkerService, taskWorker *services.TaskWorkerService) *APIHandler {
	return &APIHandler{
		cfg:        cfg,
		db:         db,
		executor:   executor,
		worker:     worker,
		taskWorker: taskWorker,
		urlChecker: services.NewURLCheckerService(),
	}
}


// ── HEALTH & CONFIG ENDPOINTS ──────────────────────────────────────────────

func (h *APIHandler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	h.sendJSON(w, http.StatusOK, true, map[string]string{"status": "ok"}, nil)
}

func (h *APIHandler) AuthConfig(w http.ResponseWriter, r *http.Request) {
	// Expose public Firebase configuration to front-end for initializing Auth client
	configData := map[string]interface{}{
		"apiKey":            os.Getenv("FIREBASE_API_KEY"),
		"authDomain":        os.Getenv("FIREBASE_AUTH_DOMAIN"),
		"projectId":         h.cfg.FirebaseProjectID,
		"storageBucket":     os.Getenv("FIREBASE_STORAGE_BUCKET"),
		"messagingSenderId": os.Getenv("FIREBASE_MESSAGING_SENDER_ID"),
		"appId":             os.Getenv("FIREBASE_APP_ID"),
		"singleUserMode":    h.cfg.SingleUserMode,
	}
	h.sendJSON(w, http.StatusOK, true, configData, nil)
}

// ── PROFILE CRUD HANDLERS ───────────────────────────────────────────────────

func (h *APIHandler) GetProfile(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	docRef := h.db.Collection("profiles").Doc(h.getProfileID())

	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Profile not found")
		return
	}

	var p models.Profile
	if err := docSnap.DataTo(&p); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing profile data")
		return
	}

	// Filter by UID in multi-user mode
	if !h.cfg.SingleUserMode && p.UserID != "" && p.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access to profile")
		return
	}

	h.sendJSON(w, http.StatusOK, true, p, nil)
}

func (h *APIHandler) UpdateProfile(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	var p models.Profile
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	if p.Name == "" || p.Email == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Name and Email are required fields")
		return
	}

	if !h.cfg.SingleUserMode {
		p.UserID = uid
	}

	docRef := h.db.Collection("profiles").Doc(h.getProfileID())
	_, err := docRef.Set(r.Context(), p)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to update profile: %v", err))
		return
	}

	h.sendJSON(w, http.StatusOK, true, p, nil)
}

// ── PROJECTS CRUD HANDLERS ───────────────────────────────────────────────────

func (h *APIHandler) ListProjects(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	colRef := h.db.Collection("projects")

	var q firestore.Query = colRef.Query
	if !h.cfg.SingleUserMode {
		q = colRef.Where("user_id", "==", uid)
	}
	// Fallback/Default sorting by priority
	q = q.OrderBy("priority", firestore.Asc)

	iter := q.Documents(r.Context())
	defer iter.Stop()

	var projects []models.Project
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Error fetching projects: %v", err))
			return
		}

		var p models.Project
		if err := doc.DataTo(&p); err != nil {
			continue
		}
		p.ID = doc.Ref.ID
		projects = append(projects, p)
	}

	h.sendJSON(w, http.StatusOK, true, projects, nil)
}

func (h *APIHandler) CreateProject(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	var p models.Project
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	if p.Name == "" || p.Description == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Name and Description are required")
		return
	}

	if !h.cfg.SingleUserMode {
		p.UserID = uid
	}

	ref, _, err := h.db.Collection("projects").Add(r.Context(), p)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to create project: %v", err))
		return
	}

	p.ID = ref.ID
	h.sendJSON(w, http.StatusCreated, true, p, nil)
}

func (h *APIHandler) UpdateProject(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "projects")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing project ID")
		return
	}

	docRef := h.db.Collection("projects").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Project not found")
		return
	}

	var existing models.Project
	if err := docSnap.DataTo(&existing); err == nil && !h.cfg.SingleUserMode && existing.UserID != "" && existing.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	var p models.Project
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	if p.Name == "" || p.Description == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Name and Description are required")
		return
	}

	if !h.cfg.SingleUserMode {
		p.UserID = uid
	}

	_, err = docRef.Set(r.Context(), p)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to update project: %v", err))
		return
	}

	p.ID = id
	h.sendJSON(w, http.StatusOK, true, p, nil)
}

func (h *APIHandler) DeleteProject(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "projects")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing project ID")
		return
	}

	docRef := h.db.Collection("projects").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err == nil {
		var existing models.Project
		if err := docSnap.DataTo(&existing); err == nil && !h.cfg.SingleUserMode && existing.UserID != "" && existing.UserID != uid {
			h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
			return
		}
	}

	_, err = docRef.Delete(r.Context())
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to delete project: %v", err))
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]string{"id": id}, nil)
}

// ── SKILLS CRUD HANDLERS ────────────────────────────────────────────────────

func (h *APIHandler) ListSkills(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	colRef := h.db.Collection("skills")

	var q firestore.Query = colRef.Query
	if !h.cfg.SingleUserMode {
		q = colRef.Where("user_id", "==", uid)
	}
	q = q.OrderBy("sort_order", firestore.Asc)

	iter := q.Documents(r.Context())
	defer iter.Stop()

	var skills []models.Skill
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Error fetching skills: %v", err))
			return
		}

		var s models.Skill
		if err := doc.DataTo(&s); err != nil {
			continue
		}
		s.ID = doc.Ref.ID
		skills = append(skills, s)
	}

	h.sendJSON(w, http.StatusOK, true, skills, nil)
}

func (h *APIHandler) CreateSkill(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	var s models.Skill
	if err := json.NewDecoder(r.Body).Decode(&s); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	if s.Name == "" || s.Category == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Name and Category are required")
		return
	}

	if !h.cfg.SingleUserMode {
		s.UserID = uid
	}

	ref, _, err := h.db.Collection("skills").Add(r.Context(), s)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to create skill: %v", err))
		return
	}

	s.ID = ref.ID
	h.sendJSON(w, http.StatusCreated, true, s, nil)
}

func (h *APIHandler) DeleteSkill(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "skills")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing skill ID")
		return
	}

	docRef := h.db.Collection("skills").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err == nil {
		var existing models.Skill
		if err := docSnap.DataTo(&existing); err == nil && !h.cfg.SingleUserMode && existing.UserID != "" && existing.UserID != uid {
			h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
			return
		}
	}

	_, err = docRef.Delete(r.Context())
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to delete skill: %v", err))
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]string{"id": id}, nil)
}

// ── JOBS CRUD & PIPELINE HANDLERS ───────────────────────────────────────────

func (h *APIHandler) ListJobs(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	colRef := h.db.Collection("jobs")

	var q firestore.Query = colRef.Query
	if !h.cfg.SingleUserMode {
		q = colRef.Where("user_id", "==", uid)
	}
	q = q.OrderBy("created_at", firestore.Desc)

	iter := q.Documents(r.Context())
	defer iter.Stop()

	var jobs []models.Job
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Error fetching jobs: %v", err))
			return
		}

		var j models.Job
		if err := doc.DataTo(&j); err != nil {
			continue
		}
		j.JobID = doc.Ref.ID
		jobs = append(jobs, j)
	}

	h.sendJSON(w, http.StatusOK, true, jobs, nil)
}

func (h *APIHandler) GetJob(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing job ID")
		return
	}

	docSnap, err := h.db.Collection("jobs").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job data")
		return
	}
	j.JobID = docSnap.Ref.ID

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access to job")
		return
	}

	h.sendJSON(w, http.StatusOK, true, j, nil)
}

// validateApplicationURL performs strict URL validation: requires http or https scheme.
// Used by UpdateJob, source URLs, and tested directly as a standalone helper.
func validateApplicationURL(rawURL string) string {
	if rawURL == "" {
		return "" // Optional field — empty is allowed
	}
	u, err := url.ParseRequestURI(rawURL)
	if err != nil {
		return "ApplicationURL is not a valid URL"
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return fmt.Sprintf("ApplicationURL scheme '%s' is not allowed. Only http and https are permitted", u.Scheme)
	}
	if u.Host == "" {
		return "ApplicationURL must include a host name"
	}
	return ""
}

// rejectDangerousURL blocks explicitly dangerous URL schemes at job-creation time.
// Syntactically-invalid URLs (e.g. bare strings without a scheme) are stored as-is
// and classified by the /check-url endpoint.
func rejectDangerousURL(rawURL string) string {
	if rawURL == "" {
		return ""
	}
	lower := strings.ToLower(strings.TrimSpace(rawURL))
	dangerousSchemes := []string{"javascript:", "file:", "data:", "vbscript:"}
	for _, scheme := range dangerousSchemes {
		if strings.HasPrefix(lower, scheme) {
			return fmt.Sprintf("ApplicationURL scheme '%s' is not permitted", scheme)
		}
	}
	return ""
}

func (h *APIHandler) CreateJob(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	var j models.Job
	if err := json.NewDecoder(r.Body).Decode(&j); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	// Validation
	if j.Company == "" || j.JobTitle == "" || j.JDText == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Company, JobTitle, and JDText are required fields")
		return
	}

	// Block explicitly dangerous URL schemes at creation time.
	// Syntactically-weird but non-dangerous URLs (e.g. bare strings) are stored
	// and classified lazily by the /jobs/{id}/check-url endpoint.
	if urlErr := rejectDangerousURL(j.ApplicationURL); urlErr != "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", urlErr)
		return
	}

	j.UserID = uid
	j.Status = "NEW"
	if j.Source == "" {
		j.Source = "manual"
	}
	j.CreatedAt = time.Now()
	j.UpdatedAt = time.Now()

	ref, _, err := h.db.Collection("jobs").Add(r.Context(), j)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to save job: %v", err))
		return
	}

	j.JobID = ref.ID
	// Automatically save ID to document too
	_, _ = ref.Update(r.Context(), []firestore.Update{{Path: "job_id", Value: ref.ID}})

	h.sendJSON(w, http.StatusCreated, true, j, nil)
}

func (h *APIHandler) UpdateJob(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing job ID")
		return
	}

	docRef := h.db.Collection("jobs").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var existing models.Job
	if err := docSnap.DataTo(&existing); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && existing.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	var j models.Job
	if err := json.NewDecoder(r.Body).Decode(&j); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	if j.Company == "" || j.JobTitle == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Company and JobTitle are required")
		return
	}

	// Validate URL scheme on update — same rules as create
	if urlErr := validateApplicationURL(j.ApplicationURL); urlErr != "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", urlErr)
		return
	}

	// Update fields safely, preserve status & generated IDs if they aren't provided
	if j.Status == "" {
		j.Status = existing.Status
	}
	if j.JDDocumentID == "" {
		j.JDDocumentID = existing.JDDocumentID
	}
	if j.MatchID == "" {
		j.MatchID = existing.MatchID
	}
	if j.TailoredResumeID == "" {
		j.TailoredResumeID = existing.TailoredResumeID
	}
	j.UserID = uid
	j.JobID = id
	j.CreatedAt = existing.CreatedAt
	j.UpdatedAt = time.Now()

	_, err = docRef.Set(r.Context(), j)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to update job: %v", err))
		return
	}

	h.sendJSON(w, http.StatusOK, true, j, nil)
}

func (h *APIHandler) DeleteJob(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing job ID")
		return
	}

	docRef := h.db.Collection("jobs").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err == nil {
		var existing models.Job
		if err := docSnap.DataTo(&existing); err == nil && !h.cfg.SingleUserMode && existing.UserID != uid {
			h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
			return
		}
	}

	_, err = docRef.Delete(r.Context())
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to delete job: %v", err))
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]string{"id": id}, nil)
}

// UpdateJobStatus handles manually updating job status (APPLIED, INTERVIEW, etc.)
func (h *APIHandler) UpdateJobStatus(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing job ID")
		return
	}

	var statusPayload struct {
		Status string `json:"status"`
	}
	if err := json.NewDecoder(r.Body).Decode(&statusPayload); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	validStatuses := map[string]bool{
		"NEW": true, "ANALYZING": true, "ANALYZED": true,
		"MATCHING": true, "MATCHED": true, "RESUME_GENERATING": true,
		"RESUME_READY": true, "APPLIED": true, "INTERVIEW": true,
		"REJECTED": true, "OFFER": true, "WITHDRAWN": true, "FAILED": true,
	}

	statusPayload.Status = strings.ToUpper(statusPayload.Status)
	if !validStatuses[statusPayload.Status] {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", fmt.Sprintf("Invalid status transition: %s", statusPayload.Status))
		return
	}

	docRef := h.db.Collection("jobs").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	_, err = docRef.Update(r.Context(), []firestore.Update{
		{Path: "status", Value: statusPayload.Status},
		{Path: "updated_at", Value: time.Now()},
	})
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Failed to update status")
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]string{"job_id": id, "status": statusPayload.Status}, nil)
}

// ── ORCHESTRATION / PYTHON RUNNER SUBPROCESS ENDPOINTS ──────────────────────

func (h *APIHandler) AnalyzeJobJD(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")

	docRef := h.db.Collection("jobs").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	// Guard against duplicate execution: return 409 if already in-progress
	if j.Status == "ANALYZING" {
		h.sendError(w, http.StatusConflict, "OPERATION_IN_PROGRESS", "JD analysis is already in progress for this job")
		return
	}

	// Update status to ANALYZING
	_, _ = docRef.Update(r.Context(), []firestore.Update{
		{Path: "status", Value: "ANALYZING"},
		{Path: "updated_at", Value: time.Now()},
	})

	log.Printf("Starting Phase 2 analysis for job: %s", id)

	// Call Phase 2 script synchronously (with http timeout)
	jdDocID, err := h.executor.AnalyzeJD(r.Context(), j.JDText)
	if err != nil {
		log.Printf("Phase 2 JD Analysis failed: %v", err)
		_, _ = docRef.Update(r.Context(), []firestore.Update{
			{Path: "status", Value: "FAILED"},
			{Path: "updated_at", Value: time.Now()},
		})
		h.sendError(w, http.StatusInternalServerError, "SUBPROCESS_ERROR", fmt.Sprintf("JD Analysis failed: %v", err))
		return
	}

	// Update Job record with jd_document_id and set status to ANALYZED
	_, err = docRef.Update(r.Context(), []firestore.Update{
		{Path: "jd_document_id", Value: jdDocID},
		{Path: "status", Value: "ANALYZED"},
		{Path: "updated_at", Value: time.Now()},
	})
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Failed to update job metadata in Firestore")
		return
	}

	h.sendJSON(w, http.StatusOK, true, models.OperationResponse{
		JobID:  id,
		Status: "ANALYZED",
		ID:     jdDocID,
	}, nil)
}

func (h *APIHandler) MatchJobProfile(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")

	docRef := h.db.Collection("jobs").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if j.JDDocumentID == "" {
		h.sendError(w, http.StatusConflict, "CONFLICT", "Job description must be analyzed first")
		return
	}

	// Guard against duplicate execution: return 409 if already in-progress
	if j.Status == "MATCHING" {
		h.sendError(w, http.StatusConflict, "OPERATION_IN_PROGRESS", "Profile matching is already in progress for this job")
		return
	}

	// Update status to MATCHING
	_, _ = docRef.Update(r.Context(), []firestore.Update{
		{Path: "status", Value: "MATCHING"},
		{Path: "updated_at", Value: time.Now()},
	})

	log.Printf("Starting Phase 3 Matching for job: %s, JDDoc: %s", id, j.JDDocumentID)

	// Call Phase 3 matching
	matchID, err := h.executor.MatchJDProfile(r.Context(), j.JDDocumentID)
	if err != nil {
		log.Printf("Phase 3 matching failed: %v", err)
		_, _ = docRef.Update(r.Context(), []firestore.Update{
			{Path: "status", Value: "FAILED"},
			{Path: "updated_at", Value: time.Now()},
		})
		h.sendError(w, http.StatusInternalServerError, "SUBPROCESS_ERROR", fmt.Sprintf("JD Matching failed: %v", err))
		return
	}

	// Update Job record with match_id and set status to MATCHED
	_, err = docRef.Update(r.Context(), []firestore.Update{
		{Path: "match_id", Value: matchID},
		{Path: "status", Value: "MATCHED"},
		{Path: "updated_at", Value: time.Now()},
	})
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Failed to update match metadata in Firestore")
		return
	}

	h.sendJSON(w, http.StatusOK, true, models.OperationResponse{
		JobID:  id,
		Status: "MATCHED",
		ID:     matchID,
	}, nil)
}

func (h *APIHandler) GenerateJobResume(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")

	docRef := h.db.Collection("jobs").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if j.MatchID == "" {
		h.sendError(w, http.StatusConflict, "CONFLICT", "Job matching must be complete first")
		return
	}

	// Guard against duplicate execution: return 409 if already in-progress
	if j.Status == "RESUME_GENERATING" {
		h.sendError(w, http.StatusConflict, "OPERATION_IN_PROGRESS", "Resume generation is already in progress for this job")
		return
	}

	// Update status to RESUME_GENERATING
	_, _ = docRef.Update(r.Context(), []firestore.Update{
		{Path: "status", Value: "RESUME_GENERATING"},
		{Path: "updated_at", Value: time.Now()},
	})

	log.Printf("Starting Phase 4 tailoring for job: %s, MatchID: %s", id, j.MatchID)

	// Call Phase 4 tailoring
	resumeID, err := h.executor.TailorResume(r.Context(), j.MatchID)
	if err != nil {
		log.Printf("Phase 4 tailoring failed: %v", err)
		_, _ = docRef.Update(r.Context(), []firestore.Update{
			{Path: "status", Value: "FAILED"},
			{Path: "updated_at", Value: time.Now()},
		})
		h.sendError(w, http.StatusInternalServerError, "SUBPROCESS_ERROR", fmt.Sprintf("Resume tailoring failed: %v", err))
		return
	}

	// Update Job record with tailored_resume_id and set status to RESUME_READY
	_, err = docRef.Update(r.Context(), []firestore.Update{
		{Path: "tailored_resume_id", Value: resumeID},
		{Path: "status", Value: "RESUME_READY"},
		{Path: "updated_at", Value: time.Now()},
	})
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Failed to update tailored resume metadata in Firestore")
		return
	}

	h.sendJSON(w, http.StatusOK, true, models.OperationResponse{
		JobID:  id,
		Status: "RESUME_READY",
		ID:     resumeID,
	}, nil)
}

func (h *APIHandler) GetJobMatchResult(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")

	docSnap, err := h.db.Collection("jobs").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if j.MatchID == "" {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "No match result generated for this job")
		return
	}

	// Fetch actual match result from Firestore `job_matches` collection
	matchSnap, err := h.db.Collection("job_matches").Doc(j.MatchID).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Match result document not found in database")
		return
	}

	h.sendJSON(w, http.StatusOK, true, matchSnap.Data(), nil)
}

func (h *APIHandler) GetJobResumeResult(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")

	docSnap, err := h.db.Collection("jobs").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if j.TailoredResumeID == "" {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "No resume tailored for this job")
		return
	}

	// Fetch tailored resume metadata record from Firestore
	resumeSnap, err := h.db.Collection("tailored_resumes").Doc(j.TailoredResumeID).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Tailored resume record not found in database")
		return
	}

	h.sendJSON(w, http.StatusOK, true, resumeSnap.Data(), nil)
}

// ServeResumePDF streams the generated PDF file safely with authentication
func (h *APIHandler) ServeResumePDF(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")

	docSnap, err := h.db.Collection("jobs").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access to file")
		return
	}

	if j.TailoredResumeID == "" {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Resume PDF not generated yet")
		return
	}

	// Fetch resume metadata to get the path
	resumeSnap, err := h.db.Collection("tailored_resumes").Doc(j.TailoredResumeID).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Tailored resume record not found")
		return
	}

	pdfPathVal, ok := resumeSnap.Data()["pdf_path"].(string)
	if !ok || pdfPathVal == "" {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Tailored PDF file path not registered")
		return
	}

	// Clean path to prevent path traversal
	pdfPath := filepath.Clean(pdfPathVal)
	if !filepath.IsAbs(pdfPath) {
		pdfPath = filepath.Join(h.cfg.ProjectRoot, pdfPath)
	}

	// Ensure the file is inside the tailored output dir for safety
	expectedDir := filepath.Clean(filepath.Join(h.cfg.ProjectRoot, "latex", "output", "tailored"))
	if !strings.HasPrefix(strings.ToLower(pdfPath), strings.ToLower(expectedDir)) {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Access denied: file path lies outside sandbox")
		return
	}


	if _, err := os.Stat(pdfPath); os.IsNotExist(err) {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "PDF file does not exist on disk")
		return
	}

	// Serve the PDF
	w.Header().Set("Content-Type", "application/pdf")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"resume_%s_%s.pdf\"", cleanFilename(j.Company), cleanFilename(j.JobTitle)))
	http.ServeFile(w, r, pdfPath)
}

// ── UTILITY HELPERS ─────────────────────────────────────────────────────────

func (h *APIHandler) getProfileID() string {
	profID := os.Getenv("FIRESTORE_PROFILE_ID")
	if profID == "" {
		return "main"
	}
	return profID
}

// sendJSON writes a structured REST envelope
func (h *APIHandler) sendJSON(w http.ResponseWriter, statusCode int, success bool, data interface{}, err interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	envelope := map[string]interface{}{
		"success": success,
	}
	if data != nil {
		envelope["data"] = data
	}
	if err != nil {
		envelope["error"] = err
	}

	_ = json.NewEncoder(w).Encode(envelope)
}

func (h *APIHandler) sendError(w http.ResponseWriter, statusCode int, code string, message string) {
	h.sendJSON(w, statusCode, false, nil, map[string]string{
		"code":    code,
		"message": message,
	})
}

// getURLParam extracts :id from /api/v1/resource/:id URL
func (h *APIHandler) getURLParam(urlPath string, resource string) string {
	parts := strings.Split(urlPath, "/")
	for i, part := range parts {
		if part == resource && i+1 < len(parts) {
			// Return next segment (which is ID), ignore trailing query params
			id := parts[i+1]
			if idx := strings.Index(id, "?"); idx != -1 {
				id = id[:idx]
			}
			return id
		}
	}
	return ""
}

func cleanFilename(s string) string {
	// Remove characters unsafe for filename headers
	reg := strings.NewReplacer(" ", "_", "/", "", "\\", "", "\"", "", "'", "")
	return reg.Replace(strings.ToLower(s))
}

// ── GENERATED OTHER PROFILE SUB-COLLECTIONS BOILERPLATE CRUD ────────────────

func (h *APIHandler) CreateGenericCRUD(w http.ResponseWriter, r *http.Request, collectionName string) {
	uid := auth.GetUser(r.Context())
	var raw map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON")
		return
	}

	if !h.cfg.SingleUserMode {
		raw["user_id"] = uid
	}

	ref, _, err := h.db.Collection(collectionName).Add(r.Context(), raw)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
		return
	}

	raw["id"] = ref.ID
	h.sendJSON(w, http.StatusCreated, true, raw, nil)
}

func (h *APIHandler) ListGenericCRUD(w http.ResponseWriter, r *http.Request, collectionName string) {
	uid := auth.GetUser(r.Context())
	colRef := h.db.Collection(collectionName)

	var q firestore.Query = colRef.Query
	if !h.cfg.SingleUserMode {
		q = colRef.Where("user_id", "==", uid)
	}

	iter := q.Documents(r.Context())
	defer iter.Stop()

	var list []map[string]interface{}
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
			return
		}

		raw := doc.Data()
		raw["id"] = doc.Ref.ID
		list = append(list, raw)
	}

	h.sendJSON(w, http.StatusOK, true, list, nil)
}

func (h *APIHandler) UpdateGenericCRUD(w http.ResponseWriter, r *http.Request, collectionName string) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, collectionName)
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing item ID")
		return
	}

	docRef := h.db.Collection(collectionName).Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Item not found")
		return
	}

	if !h.cfg.SingleUserMode && docSnap.Data()["user_id"] != nil && docSnap.Data()["user_id"].(string) != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	var raw map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON")
		return
	}

	if !h.cfg.SingleUserMode {
		raw["user_id"] = uid
	}

	_, err = docRef.Set(r.Context(), raw, firestore.MergeAll)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
		return
	}

	raw["id"] = id
	h.sendJSON(w, http.StatusOK, true, raw, nil)
}

func (h *APIHandler) DeleteGenericCRUD(w http.ResponseWriter, r *http.Request, collectionName string) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, collectionName)
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing item ID")
		return
	}

	docRef := h.db.Collection(collectionName).Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err == nil {
		if !h.cfg.SingleUserMode && docSnap.Data()["user_id"] != nil && docSnap.Data()["user_id"].(string) != uid {
			h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
			return
		}
	}

	_, err = docRef.Delete(r.Context())
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]string{"id": id}, nil)
}

// ── JOB OPPORTUNITIES INGESTION HANDLERS ────────────────────────────────────

func (h *APIHandler) ListOpportunities(w http.ResponseWriter, r *http.Request) {
	// List discovered job opportunities
	colRef := h.db.Collection("job_opportunities")
	
	// Order by discovered_at descending
	q := colRef.OrderBy("discovered_at", firestore.Desc).Limit(100)
	
	iter := q.Documents(r.Context())
	defer iter.Stop()
	
	var opportunities []models.JobOpportunity
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Error fetching opportunities: %v", err))
			return
		}
		
		var op models.JobOpportunity
		if err := doc.DataTo(&op); err != nil {
			continue
		}
		op.ID = doc.Ref.ID
		opportunities = append(opportunities, op)
	}
	
	h.sendJSON(w, http.StatusOK, true, opportunities, nil)
}

func (h *APIHandler) ImportOpportunity(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "opportunities")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing opportunity ID")
		return
	}

	// 1. Fetch the opportunity
	opRef := h.db.Collection("job_opportunities").Doc(id)
	opSnap, err := opRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Opportunity not found")
		return
	}

	var op models.JobOpportunity
	if err := opSnap.DataTo(&op); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing opportunity")
		return
	}

	// 2. Map to Job model and insert into jobs collection
	// Use description as JDText; fall back to raw_text if description is empty
	jdText := op.Description
	if jdText == "" {
		jdText = op.RawText
	}
	if jdText == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Opportunity has no description or raw text to analyze as a job description")
		return
	}

	newJob := models.Job{
		UserID:         uid,
		Company:        op.Company,
		JobTitle:       op.JobTitle,
		ApplicationURL: op.ApplicationURL,
		JDText:         jdText,
		Location:       op.Location,
		Source:         op.Source,
		Status:         "NEW",
		CreatedAt:      time.Now(),
		UpdatedAt:      time.Now(),
	}

	jobRef, _, err := h.db.Collection("jobs").Add(r.Context(), newJob)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to create job: %v", err))
		return
	}

	newJob.JobID = jobRef.ID
	_, _ = jobRef.Update(r.Context(), []firestore.Update{{Path: "job_id", Value: jobRef.ID}})

	// 3. Mark the opportunity as IMPORTED
	_, _ = opRef.Update(r.Context(), []firestore.Update{
		{Path: "ingestion_status", Value: "IMPORTED"},
		{Path: "updated_at", Value: time.Now()},
	})

	h.sendJSON(w, http.StatusCreated, true, newJob, nil)
}

// ── JOB SOURCES CONFIGURATION HANDLERS ──────────────────────────────────────

func (h *APIHandler) ListSources(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	colRef := h.db.Collection("job_sources")

	var q firestore.Query = colRef.Query
	if !h.cfg.SingleUserMode {
		q = colRef.Where("user_id", "==", uid)
	}

	iter := q.Documents(r.Context())
	defer iter.Stop()

	var sources []models.JobSource
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Error fetching sources: %v", err))
			return
		}

		var s models.JobSource
		if err := doc.DataTo(&s); err != nil {
			continue
		}
		s.ID = doc.Ref.ID
		sources = append(sources, s)
	}

	h.sendJSON(w, http.StatusOK, true, sources, nil)
}

func (h *APIHandler) CreateSource(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	var s models.JobSource
	if err := json.NewDecoder(r.Body).Decode(&s); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	// Validation
	if s.Name == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Name is required")
		return
	}
	if s.Type != "telegram" && s.Type != "website" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Type must be either 'telegram' or 'website'")
		return
	}

	if s.Type == "telegram" {
		if s.Identifier == "" {
			h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Identifier is required for telegram sources")
			return
		}
		if s.AdapterMode == "" {
			s.AdapterMode = "public_web"
		}
		if s.AdapterMode != "public_web" && s.AdapterMode != "api" {
			h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Adapter mode must be either 'public_web' or 'api'")
			return
		}
		if !strings.HasPrefix(s.Identifier, "@") {
			// Must start with @ or be a valid numeric ID (which is also allowed)
			isNumeric := true
			for _, char := range s.Identifier {
				if char < '0' || char > '9' {
					isNumeric = false
					break
				}
			}
			if !isNumeric && s.Identifier != "" {
				s.Identifier = "@" + s.Identifier
			}
		}
	}

	if s.Type == "website" {
		if s.URL == "" {
			h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "URL is required for website sources")
			return
		}
		u, err := url.ParseRequestURI(s.URL)
		if err != nil || (u.Scheme != "http" && u.Scheme != "https") {
			h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "URL must be a valid http or https URL")
			return
		}
	}

	s.UserID = uid
	s.Enabled = true
	s.State = "ENABLED"
	s.CreatedAt = time.Now().UTC().Format(time.RFC3339)
	s.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	if s.Configuration == nil {
		s.Configuration = make(map[string]interface{})
	}

	ref, _, err := h.db.Collection("job_sources").Add(r.Context(), s)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to create source: %v", err))
		return
	}

	s.ID = ref.ID
	h.sendJSON(w, http.StatusCreated, true, s, nil)
}

func (h *APIHandler) GetSource(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "sources")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing source ID")
		return
	}

	docSnap, err := h.db.Collection("job_sources").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Source not found")
		return
	}

	var s models.JobSource
	if err := docSnap.DataTo(&s); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing source configuration")
		return
	}
	s.ID = docSnap.Ref.ID

	if !h.cfg.SingleUserMode && s.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	h.sendJSON(w, http.StatusOK, true, s, nil)
}

func (h *APIHandler) UpdateSource(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "sources")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing source ID")
		return
	}

	docRef := h.db.Collection("job_sources").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Source not found")
		return
	}

	var existing models.JobSource
	if err := docSnap.DataTo(&existing); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing source config")
		return
	}

	if !h.cfg.SingleUserMode && existing.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	var s models.JobSource
	if err := json.NewDecoder(r.Body).Decode(&s); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	// Validation
	if s.Name == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Name is required")
		return
	}
	if s.Type != "telegram" && s.Type != "website" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Type must be either 'telegram' or 'website'")
		return
	}

	if s.Type == "telegram" {
		if s.Identifier == "" {
			h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Identifier is required for telegram sources")
			return
		}
		if s.AdapterMode == "" {
			s.AdapterMode = "public_web"
		}
		if s.AdapterMode != "public_web" && s.AdapterMode != "api" {
			h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Adapter mode must be either 'public_web' or 'api'")
			return
		}
	}


	s.UserID = uid
	s.ID = id
	s.CreatedAt = existing.CreatedAt
	s.UpdatedAt = time.Now().UTC().Format(time.RFC3339)

	if s.State == "" {
		s.State = existing.State
	}
	if s.LastRunAt == "" {
		s.LastRunAt = existing.LastRunAt
	}
	if s.LastSuccessAt == "" {
		s.LastSuccessAt = existing.LastSuccessAt
	}
	if s.LastError == "" {
		s.LastError = existing.LastError
	}
	if s.LastProcessedMarker == nil {
		s.LastProcessedMarker = existing.LastProcessedMarker
	}
	if s.Configuration == nil {
		s.Configuration = existing.Configuration
	}

	_, err = docRef.Set(r.Context(), s)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to update source: %v", err))
		return
	}

	h.sendJSON(w, http.StatusOK, true, s, nil)
}

func (h *APIHandler) DeleteSource(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "sources")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing source ID")
		return
	}

	docRef := h.db.Collection("job_sources").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err == nil {
		var existing models.JobSource
		if err := docSnap.DataTo(&existing); err == nil && !h.cfg.SingleUserMode && existing.UserID != uid {
			h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
			return
		}
	}

	_, err = docRef.Delete(r.Context())
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to delete source: %v", err))
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]string{"id": id}, nil)
}

func (h *APIHandler) EnableSource(w http.ResponseWriter, r *http.Request) {
	h.setSourceEnabled(w, r, true)
}

func (h *APIHandler) DisableSource(w http.ResponseWriter, r *http.Request) {
	h.setSourceEnabled(w, r, false)
}

func (h *APIHandler) setSourceEnabled(w http.ResponseWriter, r *http.Request, enabled bool) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "sources")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing source ID")
		return
	}

	docRef := h.db.Collection("job_sources").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Source not found")
		return
	}

	var existing models.JobSource
	if err := docSnap.DataTo(&existing); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing source")
		return
	}

	if !h.cfg.SingleUserMode && existing.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	state := "ENABLED"
	if !enabled {
		state = "DISABLED"
	}

	_, err = docRef.Update(r.Context(), []firestore.Update{
		{Path: "enabled", Value: enabled},
		{Path: "state", Value: state},
		{Path: "updated_at", Value: time.Now().UTC().Format(time.RFC3339)},
	})
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Failed to update status")
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]interface{}{"id": id, "enabled": enabled, "state": state}, nil)
}

func (h *APIHandler) TestSource(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "sources")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing source ID")
		return
	}

	docRef := h.db.Collection("job_sources").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Source not found")
		return
	}

	var existing models.JobSource
	if err := docSnap.DataTo(&existing); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing source")
		return
	}

	if !h.cfg.SingleUserMode && existing.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	log.Printf("Testing source config: %s (Type: %s)", existing.Name, existing.Type)

	// Call Ingestion module in dry-run mode for testing
	output, err := h.executor.RunIngestion(r.Context(), id, true)
	if err != nil {
		log.Printf("Source test connection failed: %v", err)
		h.sendJSON(w, http.StatusOK, true, map[string]interface{}{
			"success":      false,
			"accessible":   false,
			"message":      fmt.Sprintf("Connection/fetch failed: %v", err),
			"last_checked": time.Now().UTC().Format(time.RFC3339),
		}, nil)
		return
	}

	h.sendJSON(w, http.StatusOK, true, map[string]interface{}{
		"success":      true,
		"source_name":  existing.Name,
		"source_type":  existing.Type,
		"accessible":   true,
		"message":      "Source is active and reachable",
		"last_checked": time.Now().UTC().Format(time.RFC3339),
		"details":      output,
	}, nil)
}

func (h *APIHandler) RunSource(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "sources")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing source ID")
		return
	}

	docRef := h.db.Collection("job_sources").Doc(id)
	docSnap, err := docRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Source not found")
		return
	}

	var existing models.JobSource
	if err := docSnap.DataTo(&existing); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing source")
		return
	}
	existing.ID = docSnap.Ref.ID

	if !h.cfg.SingleUserMode && existing.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if !existing.Enabled {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Cannot run a disabled source. Enable it first.")
		return
	}

	if existing.State == "RUNNING" || existing.State == "QUEUED" {
		h.sendError(w, http.StatusConflict, "CONFLICT", "Source ingestion is already running or queued")
		return
	}

	// Double check active run in ingestion_runs
	activeRuns, err := h.db.Collection("ingestion_runs").
		Where("source_id", "==", id).
		Where("status", "in", []string{"QUEUED", "RUNNING"}).
		Documents(r.Context()).GetAll()
	if err == nil && len(activeRuns) > 0 {
		h.sendError(w, http.StatusConflict, "CONFLICT", "Source ingestion is already running or queued")
		return
	}

	log.Printf("Queuing background Run Now ingestion for source: %s", existing.Name)

	if h.worker == nil {
		h.sendError(w, http.StatusInternalServerError, "WORKER_UNAVAILABLE", "Worker service is not initialized")
		return
	}

	runRecord, err := h.worker.QueueRun(r.Context(), &existing, uid)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "QUEUE_ERROR", fmt.Sprintf("Failed to queue ingestion run: %v", err))
		return
	}

	h.sendJSON(w, http.StatusAccepted, true, map[string]interface{}{
		"run_id":    runRecord.ID,
		"source_id": id,
		"status":    "QUEUED",
		"message":   "Ingestion run enqueued successfully",
	}, nil)
}

func (h *APIHandler) ListIngestionRuns(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	sourceID := r.URL.Query().Get("source_id")

	if h.worker == nil {
		h.sendError(w, http.StatusInternalServerError, "WORKER_UNAVAILABLE", "Worker service is not initialized")
		return
	}

	runs, err := h.worker.ListRuns(r.Context(), uid, sourceID, 50)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to fetch ingestion runs: %v", err))
		return
	}

	if runs == nil {
		runs = []models.IngestionRun{}
	}

	h.sendJSON(w, http.StatusOK, true, runs, nil)
}

// ── PHASE 7 — APPLICATION MANAGEMENT HANDLERS ────────────────────────────────

func (h *APIHandler) ListApplications(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	colRef := h.db.Collection("applications")

	var q firestore.Query = colRef.Query
	if !h.cfg.SingleUserMode {
		q = colRef.Where("user_id", "==", uid)
	}

	// Filter by status if query parameter provided
	if statusParam := r.URL.Query().Get("status"); statusParam != "" && statusParam != "ALL" {
		q = q.Where("status", "==", statusParam)
	}

	q = q.OrderBy("created_at", firestore.Desc)

	iter := q.Documents(r.Context())
	defer iter.Stop()

	var apps []models.Application
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Error fetching applications: %v", err))
			return
		}

		var app models.Application
		if err := doc.DataTo(&app); err != nil {
			continue
		}
		app.ID = doc.Ref.ID
		apps = append(apps, app)
	}

	if apps == nil {
		apps = []models.Application{}
	}

	h.sendJSON(w, http.StatusOK, true, apps, nil)
}

func (h *APIHandler) GetApplication(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")
	if id == "" {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Missing application ID")
		return
	}

	docSnap, err := h.db.Collection("applications").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := docSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}
	app.ID = docSnap.Ref.ID

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	h.sendJSON(w, http.StatusOK, true, app, nil)
}

func (h *APIHandler) CreateApplication(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())

	var input struct {
		JobID          string `json:"job_id"`
		OpportunityID  string `json:"opportunity_id"`
		ApplicationURL string `json:"application_url"`
		Notes          string `json:"notes"`
	}

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	if input.JobID == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "job_id is required")
		return
	}

	if input.ApplicationURL != "" {
		if urlErr := validateApplicationURL(input.ApplicationURL); urlErr != "" {
			h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", urlErr)
			return
		}
	}

	// 1. Verify underlying Job exists and is owned by user

	jobSnap, err := h.db.Collection("jobs").Doc(input.JobID).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Underlying job not found")
		return
	}
	var j models.Job
	if err := jobSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access to job")
		return
	}

	// 2. Transactional Uniqueness Check: (user_id + job_id)
	colRef := h.db.Collection("applications")
	var existingQuery firestore.Query = colRef.Query
	if !h.cfg.SingleUserMode {
		existingQuery = colRef.Where("user_id", "==", uid).Where("job_id", "==", input.JobID).Limit(1)
	} else {
		existingQuery = colRef.Where("job_id", "==", input.JobID).Limit(1)
	}

	existingIter := existingQuery.Documents(r.Context())
	existingDoc, err := existingIter.Next()
	existingIter.Stop()

	if err == nil && existingDoc != nil {
		// Application ALREADY EXISTS! Return existing application (prevent duplicates)
		var existingApp models.Application
		_ = existingDoc.DataTo(&existingApp)
		existingApp.ID = existingDoc.Ref.ID
		h.sendJSON(w, http.StatusOK, true, existingApp, nil)
		return
	}

	// 3. Application URL validation if provided
	appURL := input.ApplicationURL
	if appURL == "" {
		appURL = j.ApplicationURL
	}
	if urlErr := validateApplicationURL(appURL); urlErr != "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", urlErr)
		return
	}

	// 4. Initial status determination based on current Job pipeline progress
	initialStatus := "DISCOVERED"
	var resumePath string
	var resumeFilename string
	var resumeGeneratedAt *time.Time
	now := time.Now().UTC()

	if j.TailoredResumeID != "" || j.Status == "RESUME_READY" {
		initialStatus = "RESUME_GENERATED"
		resumePath = fmt.Sprintf("latex/output/tailored/%s/resume.pdf", j.MatchID)
		resumeFilename = fmt.Sprintf("resume_%s_%s.pdf", cleanFilename(j.Company), cleanFilename(j.JobTitle))
		resumeGeneratedAt = &now
	} else if j.MatchID != "" || j.Status == "MATCHED" {
		initialStatus = "MATCHED"
	} else if j.JDDocumentID != "" || j.Status == "ANALYZED" {
		initialStatus = "ANALYZED"
	}

	if appURL == "" && initialStatus == "READY_TO_APPLY" {
		initialStatus = "APPLICATION_URL_MISSING"
	}

	// Fetch match score if match exists
	var matchScore float64 = 0.0
	if j.MatchID != "" {
		matchSnap, err := h.db.Collection("job_matches").Doc(j.MatchID).Get(r.Context())
		if err == nil && matchSnap.Exists() {
			if score, ok := matchSnap.Data()["overall_match_score"].(float64); ok {
				matchScore = score
			} else if scoreInt, ok := matchSnap.Data()["overall_match_score"].(int64); ok {
				matchScore = float64(scoreInt)
			}
		}
	}

	newApp := models.Application{
		UserID:            uid,
		JobID:             input.JobID,
		OpportunityID:     input.OpportunityID,
		JobMatchID:        j.MatchID,
		JobTitle:          j.JobTitle,
		Company:           j.Company,
		ApplicationURL:    appURL,
		Status:            initialStatus,
		MatchScore:        matchScore,
		ResumePath:        resumePath,
		ResumeFilename:    resumeFilename,
		ResumeGeneratedAt: resumeGeneratedAt,
		CreatedAt:         now,
		UpdatedAt:         now,
		Notes:             input.Notes,
	}
	newApp.Source.Type = "ingestion"
	newApp.Source.Name = j.Source
	newApp.Source.URL = j.ApplicationURL
	newApp.Submission.Method = "MANUAL"
	newApp.Submission.Confirmation = false

	appRef, _, err := colRef.Add(r.Context(), newApp)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to create application: %v", err))
		return
	}
	newApp.ID = appRef.ID

	// Log event
	_, _, _ = appRef.Collection("events").Add(r.Context(), models.ApplicationEvent{
		Event:     "APPLICATION_CREATED",
		Timestamp: now,
		UserID:    uid,
		Notes:     fmt.Sprintf("Application record created with status %s", initialStatus),
	})

	h.sendJSON(w, http.StatusCreated, true, newApp, nil)
}

func (h *APIHandler) PrepareApplication(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	appRef := h.db.Collection("applications").Doc(id)
	appSnap, err := appRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := appSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}
	app.ID = appSnap.Ref.ID

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if app.Status == "SUBMITTED" {
		h.sendError(w, http.StatusConflict, "INVALID_STATE", "Application has already been submitted")
		return
	}

	// 1. Validate Job ID exists
	if app.JobID == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "JOB_MISSING", "Associated Job ID is missing")
		return
	}

	// 2. Validate application URL
	if app.ApplicationURL == "" {
		_, _ = appRef.Update(r.Context(), []firestore.Update{
			{Path: "status", Value: "APPLICATION_URL_MISSING"},
			{Path: "updated_at", Value: time.Now().UTC()},
		})
		h.sendError(w, http.StatusUnprocessableEntity, "APPLICATION_URL_MISSING", "Application URL is missing")
		return
	}

	if urlErr := validateApplicationURL(app.ApplicationURL); urlErr != "" {
		h.sendError(w, http.StatusUnprocessableEntity, "APPLICATION_URL_INVALID", urlErr)
		return
	}

	// 3. Validate tailored resume path and artifact existence
	if app.ResumePath == "" {
		// Check underlying Job
		jobSnap, err := h.db.Collection("jobs").Doc(app.JobID).Get(r.Context())
		if err == nil && jobSnap.Exists() {
			var j models.Job
			_ = jobSnap.DataTo(&j)
			if j.MatchID != "" {
				app.JobMatchID = j.MatchID
				app.ResumePath = fmt.Sprintf("latex/output/tailored/%s/resume.pdf", j.MatchID)
				app.ResumeFilename = fmt.Sprintf("resume_%s_%s.pdf", cleanFilename(app.Company), cleanFilename(app.JobTitle))
			}
		}
	}

	if app.ResumePath == "" {
		h.sendError(w, http.StatusConflict, "RESUME_NOT_READY", "Tailored resume has not been generated for this application yet. Please generate a tailored resume first.")
		return
	}


	// 3. Update status to READY_TO_APPLY
	now := time.Now().UTC()
	_, _ = appRef.Update(r.Context(), []firestore.Update{
		{Path: "job_match_id", Value: app.JobMatchID},
		{Path: "resume_path", Value: app.ResumePath},
		{Path: "resume_filename", Value: app.ResumeFilename},
		{Path: "status", Value: "READY_TO_APPLY"},
		{Path: "updated_at", Value: now},
	})

	// Log event
	_, _, _ = appRef.Collection("events").Add(r.Context(), models.ApplicationEvent{
		Event:     "APPLICATION_PREPARED",
		Timestamp: now,
		UserID:    uid,
		From:      app.Status,
		To:        "READY_TO_APPLY",
		Notes:     "Application package prepared and validated",
	})

	h.sendJSON(w, http.StatusOK, true, map[string]interface{}{
		"application_id":  id,
		"status":          "READY_TO_APPLY",
		"application_url": app.ApplicationURL,
		"resume":          app.ResumePath,
		"match_score":     app.MatchScore,
	}, nil)
}

func (h *APIHandler) GenerateApplicationResume(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	appRef := h.db.Collection("applications").Doc(id)
	appSnap, err := appRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := appSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if app.Status == "SUBMITTED" {
		h.sendError(w, http.StatusConflict, "INVALID_STATE", "Cannot regenerate resume for already submitted application")
		return
	}

	if h.taskWorker == nil {
		h.sendError(w, http.StatusInternalServerError, "WORKER_UNAVAILABLE", "Task worker service is not initialized")
		return
	}

	// Queue background tailoring task
	task, err := h.taskWorker.QueueTask(r.Context(), "generate-resume", id, uid)
	if err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Failed to queue resume generation: %v", err))
		return
	}

	// Update status to RESUME_GENERATING
	now := time.Now().UTC()
	_, _ = appRef.Update(r.Context(), []firestore.Update{
		{Path: "status", Value: "RESUME_GENERATING"},
		{Path: "updated_at", Value: now},
	})

	h.sendJSON(w, http.StatusAccepted, true, map[string]string{
		"task_id": task.ID,
		"status":  "QUEUED",
		"message": "Resume generation queued in background",
	}, nil)
}

func (h *APIHandler) OpenApplication(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	appRef := h.db.Collection("applications").Doc(id)
	appSnap, err := appRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := appSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	if urlErr := validateApplicationURL(app.ApplicationURL); urlErr != "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", urlErr)
		return
	}

	now := time.Now().UTC()
	updates := []firestore.Update{
		{Path: "updated_at", Value: now},
	}

	// Transition to APPLICATION_STARTED if READY_TO_APPLY or RESUME_GENERATED
	newStatus := app.Status
	if app.Status == "READY_TO_APPLY" || app.Status == "RESUME_GENERATED" {
		newStatus = "APPLICATION_STARTED"
		updates = append(updates,
			firestore.Update{Path: "status", Value: "APPLICATION_STARTED"},
			firestore.Update{Path: "started_at", Value: now},
		)
	}

	_, _ = appRef.Update(r.Context(), updates)

	// Log event
	_, _, _ = appRef.Collection("events").Add(r.Context(), models.ApplicationEvent{
		Event:     "APPLICATION_OPENED",
		Timestamp: now,
		UserID:    uid,
		From:      app.Status,
		To:        newStatus,
		Notes:     fmt.Sprintf("Application URL opened: %s", app.ApplicationURL),
	})

	h.sendJSON(w, http.StatusOK, true, map[string]interface{}{
		"application_id":  id,
		"application_url": app.ApplicationURL,
		"status":          newStatus,
	}, nil)
}

func (h *APIHandler) SubmitApplication(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	var payload struct {
		Confirmation bool   `json:"confirmation"`
		Notes        string `json:"notes"`
	}

	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	// Require explicit user confirmation!
	if !payload.Confirmation {
		h.sendError(w, http.StatusUnprocessableEntity, "CONFIRMATION_REQUIRED", "Explicit user confirmation is required to mark an application as submitted")
		return
	}

	appRef := h.db.Collection("applications").Doc(id)
	appSnap, err := appRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := appSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	// Duplicate-submission protection: return immediately if already submitted
	if app.Status == "SUBMITTED" {
		app.ID = appSnap.Ref.ID
		h.sendJSON(w, http.StatusOK, true, app, nil)
		return
	}

	// Lifecycle validation: Cannot transition directly from DISCOVERED or ANALYZED without starting application
	if app.Status == "DISCOVERED" || app.Status == "ANALYZED" {
		h.sendError(w, http.StatusUnprocessableEntity, "INVALID_STATE_TRANSITION", fmt.Sprintf("Cannot submit application from status %s. Must prepare application and open portal first.", app.Status))
		return
	}

	now := time.Now().UTC()
	_, _ = appRef.Update(r.Context(), []firestore.Update{
		{Path: "status", Value: "SUBMITTED"},
		{Path: "submitted_at", Value: now},
		{Path: "updated_at", Value: now},
		{Path: "submission_confirmed", Value: true},
		{Path: "submission_confirmed_at", Value: now},
		{Path: "submission_confirmed_by", Value: uid},
		{Path: "submission_method", Value: "manual_confirmation"},
		{Path: "submission.confirmation", Value: true},
		{Path: "submission.method", Value: "manual_confirmation"},
	})


	// Also update underlying Job status to APPLIED
	if app.JobID != "" {
		_, _ = h.db.Collection("jobs").Doc(app.JobID).Update(r.Context(), []firestore.Update{
			{Path: "status", Value: "APPLIED"},
			{Path: "updated_at", Value: now},
		})
	}

	// Log audit event
	_, _, _ = appRef.Collection("events").Add(r.Context(), models.ApplicationEvent{
		Event:     "SUBMISSION_CONFIRMED",
		Timestamp: now,
		UserID:    uid,
		From:      app.Status,
		To:        "SUBMITTED",
		Notes:     payload.Notes,
	})

	app.Status = "SUBMITTED"
	app.SubmittedAt = &now
	app.UpdatedAt = now
	app.SubmissionConfirmed = true
	app.Submission.Confirmation = true
	app.Submission.Method = "MANUAL"
	app.ID = appSnap.Ref.ID

	h.sendJSON(w, http.StatusOK, true, app, nil)
}

func (h *APIHandler) UpdateApplicationStatus(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	var payload struct {
		Status string `json:"status"`
		Notes  string `json:"notes"`
	}

	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	newStatus := strings.ToUpper(strings.TrimSpace(payload.Status))
	validStatuses := map[string]bool{
		"DISCOVERED": true, "ANALYZING": true, "ANALYZED": true, "MATCHED": true,
		"RESUME_GENERATED": true, "READY_TO_APPLY": true, "APPLICATION_STARTED": true,
		"SUBMITTED": true, "INTERVIEW": true, "OFFER": true, "REJECTED": true,
		"WITHDRAWN": true, "SKIPPED": true, "FAILED": true, "APPLICATION_URL_MISSING": true,
	}

	if !validStatuses[newStatus] {
		h.sendError(w, http.StatusUnprocessableEntity, "INVALID_STATUS", fmt.Sprintf("Unknown application status '%s'", newStatus))
		return
	}

	appRef := h.db.Collection("applications").Doc(id)
	appSnap, err := appRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := appSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	// Validate status transition rules
	if app.Status == "SUBMITTED" && (newStatus == "DISCOVERED" || newStatus == "ANALYZED" || newStatus == "MATCHED") {
		h.sendError(w, http.StatusConflict, "INVALID_TRANSITION", fmt.Sprintf("Cannot transition submitted application back to %s", newStatus))
		return
	}

	now := time.Now().UTC()
	updates := []firestore.Update{
		{Path: "status", Value: newStatus},
		{Path: "updated_at", Value: now},
	}
	if payload.Notes != "" {
		updates = append(updates, firestore.Update{Path: "notes", Value: payload.Notes})
	}

	_, _ = appRef.Update(r.Context(), updates)

	// Log audit event
	_, _, _ = appRef.Collection("events").Add(r.Context(), models.ApplicationEvent{
		Event:     "STATUS_CHANGED",
		Timestamp: now,
		UserID:    uid,
		From:      app.Status,
		To:        newStatus,
		Notes:     payload.Notes,
	})

	app.Status = newStatus
	app.UpdatedAt = now
	app.ID = appSnap.Ref.ID

	h.sendJSON(w, http.StatusOK, true, app, nil)
}

func (h *APIHandler) AddApplicationNote(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	var payload struct {
		Notes string `json:"notes"`
	}

	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		h.sendError(w, http.StatusBadRequest, "BAD_REQUEST", "Invalid JSON payload")
		return
	}

	if strings.TrimSpace(payload.Notes) == "" {
		h.sendError(w, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "Notes field cannot be empty")
		return
	}

	appRef := h.db.Collection("applications").Doc(id)
	appSnap, err := appRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := appSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	now := time.Now().UTC()
	updatedNotes := app.Notes
	if updatedNotes != "" {
		updatedNotes += "\n" + payload.Notes
	} else {
		updatedNotes = payload.Notes
	}

	_, _ = appRef.Update(r.Context(), []firestore.Update{
		{Path: "notes", Value: updatedNotes},
		{Path: "updated_at", Value: now},
	})

	// Log audit event
	_, _, _ = appRef.Collection("events").Add(r.Context(), models.ApplicationEvent{
		Event:     "NOTE_ADDED",
		Timestamp: now,
		UserID:    uid,
		Notes:     payload.Notes,
	})

	app.Notes = updatedNotes
	app.UpdatedAt = now
	app.ID = appSnap.Ref.ID

	h.sendJSON(w, http.StatusOK, true, app, nil)
}

func (h *APIHandler) ListApplicationEvents(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	appRef := h.db.Collection("applications").Doc(id)
	appSnap, err := appRef.Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := appSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	eventsRef := appRef.Collection("events").OrderBy("timestamp", firestore.Asc)
	iter := eventsRef.Documents(r.Context())
	defer iter.Stop()

	var events []models.ApplicationEvent
	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", fmt.Sprintf("Error fetching events: %v", err))
			return
		}

		var evt models.ApplicationEvent
		if err := doc.DataTo(&evt); err != nil {
			continue
		}
		evt.ID = doc.Ref.ID
		events = append(events, evt)
	}

	if events == nil {
		events = []models.ApplicationEvent{}
	}

	h.sendJSON(w, http.StatusOK, true, events, nil)
}

// ── APPLICATION LINK HEALTH HANDLERS ────────────────────────────────────────

func (h *APIHandler) CheckJobURL(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "jobs")

	docSnap, err := h.db.Collection("jobs").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Job not found")
		return
	}

	var j models.Job
	if err := docSnap.DataTo(&j); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing job")
		return
	}

	if !h.cfg.SingleUserMode && j.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	checkRes := h.urlChecker.CheckURL(r.Context(), j.ApplicationURL)

	// Save check result to Firestore
	_, _ = h.db.Collection("jobs").Doc(id).Update(r.Context(), []firestore.Update{
		{Path: "application_url_status", Value: checkRes.Status},
		{Path: "application_url_http_status", Value: checkRes.HTTPStatus},
		{Path: "application_url_final_url", Value: checkRes.FinalURL},
		{Path: "application_url_checked_at", Value: checkRes.CheckedAt},
		{Path: "application_url_error", Value: checkRes.Error},
		{Path: "updated_at", Value: time.Now().UTC()},
	})

	h.sendJSON(w, http.StatusOK, true, checkRes, nil)
}

func (h *APIHandler) CheckApplicationURL(w http.ResponseWriter, r *http.Request) {
	uid := auth.GetUser(r.Context())
	id := h.getURLParam(r.URL.Path, "applications")

	docSnap, err := h.db.Collection("applications").Doc(id).Get(r.Context())
	if err != nil {
		h.sendError(w, http.StatusNotFound, "NOT_FOUND", "Application not found")
		return
	}

	var app models.Application
	if err := docSnap.DataTo(&app); err != nil {
		h.sendError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "Error parsing application")
		return
	}

	if !h.cfg.SingleUserMode && app.UserID != uid {
		h.sendError(w, http.StatusForbidden, "FORBIDDEN", "Unauthorized access")
		return
	}

	checkRes := h.urlChecker.CheckURL(r.Context(), app.ApplicationURL)

	// Save check result to Firestore
	_, _ = h.db.Collection("applications").Doc(id).Update(r.Context(), []firestore.Update{
		{Path: "application_url_status", Value: checkRes.Status},
		{Path: "application_url_http_status", Value: checkRes.HTTPStatus},
		{Path: "application_url_final_url", Value: checkRes.FinalURL},
		{Path: "application_url_checked_at", Value: checkRes.CheckedAt},
		{Path: "application_url_error", Value: checkRes.Error},
		{Path: "updated_at", Value: time.Now().UTC()},
	})

	h.sendJSON(w, http.StatusOK, true, checkRes, nil)
}


