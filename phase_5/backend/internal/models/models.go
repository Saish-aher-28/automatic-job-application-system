package models

import "time"

// Profile represents profiles/main collection
type Profile struct {
	Name        string `json:"name" firestore:"name"`
	DegreeTitle string `json:"degree_title" firestore:"degree_title"`
	Email       string `json:"email" firestore:"email"`
	Phone       string `json:"phone" firestore:"phone"`
	Location    string `json:"location" firestore:"location"`
	Linkedin    string `json:"linkedin" firestore:"linkedin"`
	Github      string `json:"github" firestore:"github"`
	Portfolio   string `json:"portfolio" firestore:"portfolio"`
	Summary     string `json:"summary" firestore:"summary"`
	UserID      string `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Project represents projects/ collection
type Project struct {
	ID            string   `json:"_id,omitempty" firestore:"-"`
	Name          string   `json:"name" firestore:"name"`
	Year          string   `json:"year" firestore:"year"`
	Technologies  []string `json:"technologies" firestore:"technologies"`
	Description   string   `json:"description" firestore:"description"`
	ResumeBullets []string `json:"resume_bullets" firestore:"resume_bullets"`
	Keywords      []string `json:"keywords" firestore:"keywords"`
	Categories    []string `json:"categories" firestore:"categories"`
	Enabled       bool     `json:"enabled" firestore:"enabled"`
	Priority      int      `json:"priority" firestore:"priority"`
	UserID        string   `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Skill represents skills/ collection
type Skill struct {
	ID        string `json:"id,omitempty" firestore:"-"`
	Name      string `json:"name" firestore:"name"`
	Category  string `json:"category" firestore:"category"`
	SortOrder int    `json:"sort_order" firestore:"sort_order"`
	UserID    string `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Education represents education/ collection
// Fields aligned with Phase 1 resume_engine/education_service.py schema
type Education struct {
	ID             string   `json:"id,omitempty" firestore:"-"`
	Degree         string   `json:"degree" firestore:"degree"`
	Field          string   `json:"field" firestore:"field"`
	Specialization string   `json:"specialization" firestore:"specialization"`
	Institution    string   `json:"institution" firestore:"institution"`
	Location       string   `json:"location" firestore:"location"`
	StartYear      int      `json:"start_year" firestore:"start_year"`
	GraduationYear *int     `json:"graduation_year" firestore:"graduation_year"`
	Details        []string `json:"details" firestore:"details"`
	SortOrder      int      `json:"sort_order" firestore:"sort_order"`
	// Academic scores — used by Phase 1 LaTeX renderer
	CGPA     *float64 `json:"cgpa" firestore:"cgpa"`
	HSCScore *float64 `json:"hsc_score" firestore:"hsc_score"`
	HSCYear  *int     `json:"hsc_year" firestore:"hsc_year"`
	SSCScore *float64 `json:"ssc_score" firestore:"ssc_score"`
	SSCYear  *int     `json:"ssc_year" firestore:"ssc_year"`
	UserID   string   `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Experience represents experience/ collection
type Experience struct {
	ID          string   `json:"id,omitempty" firestore:"-"`
	Role        string   `json:"role" firestore:"role"`
	Company     string   `json:"company" firestore:"company"`
	Location    string   `json:"location" firestore:"location"`
	StartYear   int      `json:"start_year" firestore:"start_year"`
	EndYear     *int     `json:"end_year" firestore:"end_year"`
	Description string   `json:"description" firestore:"description"`
	Bullets     []string `json:"bullets" firestore:"bullets"`
	Enabled     bool     `json:"enabled" firestore:"enabled"`
	UserID      string   `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Certification represents certifications/ collection
type Certification struct {
	ID        string `json:"id,omitempty" firestore:"-"`
	Name      string `json:"name" firestore:"name"`
	Authority string `json:"authority" firestore:"authority"`
	Year      int    `json:"year" firestore:"year"`
	URL       string `json:"url" firestore:"url"`
	UserID    string `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Language represents languages/ collection
type Language struct {
	ID          string `json:"id,omitempty" firestore:"-"`
	Language    string `json:"language" firestore:"language"`
	Proficiency string `json:"proficiency" firestore:"proficiency"`
	UserID      string `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Interest represents interests/ collection
type Interest struct {
	ID     string `json:"id,omitempty" firestore:"-"`
	Name   string `json:"name" firestore:"name"`
	UserID string `json:"user_id,omitempty" firestore:"user_id,omitempty"`
}

// Job represents jobs/ collection
type Job struct {
	JobID            string    `json:"job_id" firestore:"job_id"`
	UserID           string    `json:"user_id" firestore:"user_id"`
	Company          string    `json:"company" firestore:"company"`
	JobTitle         string    `json:"job_title" firestore:"job_title"`
	ApplicationURL   string    `json:"application_url" firestore:"application_url"`
	JDText           string    `json:"jd_text" firestore:"jd_text"`
	Location         string    `json:"location" firestore:"location"`
	Source           string    `json:"source" firestore:"source"`
	Status           string    `json:"status" firestore:"status"`
	JDDocumentID     string    `json:"jd_document_id" firestore:"jd_document_id"`
	MatchID          string    `json:"match_id" firestore:"match_id"`
	TailoredResumeID string    `json:"tailored_resume_id" firestore:"tailored_resume_id"`
	CreatedAt        time.Time `json:"created_at" firestore:"created_at"`
	UpdatedAt        time.Time `json:"updated_at" firestore:"updated_at"`
}

// OperationResponse holds background task status updates for UI
type OperationResponse struct {
	JobID   string `json:"job_id"`
	Status  string `json:"status"`
	Message string `json:"message,omitempty"`
	ID      string `json:"id,omitempty"` // jd_document_id, match_id, or resume_id
}

// JobOpportunity represents a discovered job opportunity in job_opportunities collection
// Note: discovered_at, created_at, updated_at are stored as ISO-8601 strings by the Python
// ingestion pipeline (phase_6), so we use string here to match the actual Firestore document format.
type JobOpportunity struct {
	ID             string   `json:"id" firestore:"-"`
	Source         string   `json:"source" firestore:"source"`
	SourceType     string   `json:"source_type" firestore:"source_type"`
	SourceName     string   `json:"source_name" firestore:"source_name"`
	SourceURL      string   `json:"source_url" firestore:"source_url"`
	Company        string   `json:"company" firestore:"company"`
	JobTitle       string   `json:"job_title" firestore:"job_title"`
	Description    string   `json:"description" firestore:"description"`
	RawText        string   `json:"raw_text" firestore:"raw_text"`
	ApplicationURL string   `json:"application_url" firestore:"application_url"`
	Location       string   `json:"location" firestore:"location"`
	EmploymentType string   `json:"employment_type" firestore:"employment_type"`
	Experience     string   `json:"experience" firestore:"experience"`
	Salary         string   `json:"salary" firestore:"salary"`
	Skills         []string `json:"skills" firestore:"skills"`
	Technologies   []string `json:"technologies" firestore:"technologies"`
	DiscoveredAt   string   `json:"discovered_at" firestore:"discovered_at"`
	IngestionStatus string  `json:"ingestion_status" firestore:"ingestion_status"`
	CreatedAt      string   `json:"created_at" firestore:"created_at"`
	UpdatedAt      string   `json:"updated_at" firestore:"updated_at"`
}

// JobSource represents a configured Telegram or Website discovery source in job_sources collection
type JobSource struct {
	ID                  string                 `json:"id" firestore:"-"`
	UserID              string                 `json:"user_id" firestore:"user_id"`
	Name                string                 `json:"name" firestore:"name"`
	Type                string                 `json:"type" firestore:"type"` // "telegram" or "website"
	AdapterMode         string                 `json:"adapter_mode" firestore:"adapter_mode"` // "public_web" or "api"
	Identifier          string                 `json:"identifier" firestore:"identifier"` // Telegram channel/group name or ID
	URL                 string                 `json:"url" firestore:"url"` // Website URL
	Enabled             bool                   `json:"enabled" firestore:"enabled"`
	State               string                 `json:"state" firestore:"state"` // "ENABLED", "DISABLED", "RUNNING", "ERROR"
	LastRunAt           string                 `json:"last_run_at" firestore:"last_run_at"`
	LastSuccessAt       string                 `json:"last_success_at" firestore:"last_success_at"`
	LastError           string                 `json:"last_error" firestore:"last_error"`
	LastProcessedMarker interface{}            `json:"last_processed_marker,omitempty" firestore:"last_processed_marker,omitempty"`
	Configuration       map[string]interface{} `json:"configuration" firestore:"configuration"`
	CreatedAt           string                 `json:"created_at" firestore:"created_at"`
	UpdatedAt           string                 `json:"updated_at" firestore:"updated_at"`
}

// IngestionRun represents an asynchronous background ingestion run in ingestion_runs collection
type IngestionRun struct {
	ID                string `json:"id" firestore:"-"`
	SourceID          string `json:"source_id" firestore:"source_id"`
	UserID            string `json:"user_id" firestore:"user_id"`
	SourceType        string `json:"source_type" firestore:"source_type"`
	SourceName        string `json:"source_name" firestore:"source_name"`
	Status            string `json:"status" firestore:"status"` // "QUEUED", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"
	CreatedAt         string `json:"created_at" firestore:"created_at"`
	StartedAt         string `json:"started_at,omitempty" firestore:"started_at,omitempty"`
	CompletedAt       string `json:"completed_at,omitempty" firestore:"completed_at,omitempty"`
	Error             string `json:"error,omitempty" firestore:"error,omitempty"`
	MessagesScanned   int    `json:"messages_scanned" firestore:"messages_scanned"`
	JobsDetected      int    `json:"jobs_detected" firestore:"jobs_detected"`
	JobsCreated       int    `json:"jobs_created" firestore:"jobs_created"`
	DuplicatesSkipped int    `json:"duplicates_skipped" firestore:"duplicates_skipped"`
	NonJobsSkipped    int    `json:"non_jobs_skipped" firestore:"non_jobs_skipped"`
	RetryCount        int    `json:"retry_count" firestore:"retry_count"`
}
