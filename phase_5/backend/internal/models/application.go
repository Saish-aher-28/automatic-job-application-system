package models

import "time"

// ApplicationSource represents embedded metadata about where the job was discovered
type ApplicationSource struct {
	Type string `json:"type" firestore:"type"`
	Name string `json:"name" firestore:"name"`
	URL  string `json:"url" firestore:"url"`
}

// ApplicationSubmission represents details about how the application was submitted
type ApplicationSubmission struct {
	Method       string `json:"method" firestore:"method"` // Default "MANUAL"
	Confirmation bool   `json:"confirmation" firestore:"confirmation"`
}

// Application represents applications/ collection
type Application struct {
	ID                string                `json:"id" firestore:"-"`
	UserID            string                `json:"user_id" firestore:"user_id"`
	JobID             string                `json:"job_id" firestore:"job_id"`
	OpportunityID     string                `json:"opportunity_id,omitempty" firestore:"opportunity_id,omitempty"`
	JobMatchID        string                `json:"job_match_id,omitempty" firestore:"job_match_id,omitempty"`
	JobTitle          string                `json:"job_title" firestore:"job_title"`
	Company           string                `json:"company" firestore:"company"`
	ApplicationURL    string                `json:"application_url" firestore:"application_url"`
	Status            string                `json:"status" firestore:"status"`
	MatchScore        float64               `json:"match_score" firestore:"match_score"`
	ResumePath        string                `json:"resume_path" firestore:"resume_path"`
	ResumeFilename    string                `json:"resume_filename" firestore:"resume_filename"`
	ResumeGeneratedAt *time.Time            `json:"resume_generated_at,omitempty" firestore:"resume_generated_at,omitempty"`
	CreatedAt         time.Time             `json:"created_at" firestore:"created_at"`
	UpdatedAt         time.Time             `json:"updated_at" firestore:"updated_at"`
	StartedAt         *time.Time            `json:"started_at,omitempty" firestore:"started_at,omitempty"`
	SubmittedAt       *time.Time            `json:"submitted_at,omitempty" firestore:"submitted_at,omitempty"`
	Source                ApplicationSource     `json:"source" firestore:"source"`
	Submission            ApplicationSubmission `json:"submission" firestore:"submission"`
	SubmissionConfirmed   bool                  `json:"submission_confirmed" firestore:"submission_confirmed"`
	SubmissionConfirmedAt *time.Time            `json:"submission_confirmed_at,omitempty" firestore:"submission_confirmed_at,omitempty"`
	SubmissionConfirmedBy string                `json:"submission_confirmed_by,omitempty" firestore:"submission_confirmed_by,omitempty"`
	SubmissionMethod      string                `json:"submission_method,omitempty" firestore:"submission_method,omitempty"`
	ApplicationURLStatus  string                `json:"application_url_status,omitempty" firestore:"application_url_status,omitempty"`
	ApplicationURLCheckedAt *time.Time          `json:"application_url_checked_at,omitempty" firestore:"application_url_checked_at,omitempty"`
	Notes                 string                `json:"notes" firestore:"notes"`
}


// ApplicationEvent represents an audit event inside applications/{app_id}/events subcollection
type ApplicationEvent struct {
	ID        string    `json:"id" firestore:"-"`
	Event     string    `json:"event" firestore:"event"`
	Timestamp time.Time `json:"timestamp" firestore:"timestamp"`
	UserID    string    `json:"user_id" firestore:"user_id"`
	From      string    `json:"from,omitempty" firestore:"from,omitempty"`
	To        string    `json:"to,omitempty" firestore:"to,omitempty"`
	Notes     string    `json:"notes,omitempty" firestore:"notes,omitempty"`
}

// TaskRun represents a background task execution in task_runs/ collection
type TaskRun struct {
	ID          string     `json:"id" firestore:"-"`
	UserID      string     `json:"user_id" firestore:"user_id"`
	Type        string     `json:"type" firestore:"type"` // "generate-resume"
	TargetID    string     `json:"target_id" firestore:"target_id"` // application_id or job_id
	Status      string     `json:"status" firestore:"status"` // "QUEUED", "RUNNING", "SUCCESS", "FAILED"
	Error       string     `json:"error,omitempty" firestore:"error,omitempty"`
	CreatedAt   time.Time  `json:"created_at" firestore:"created_at"`
	CompletedAt *time.Time `json:"completed_at,omitempty" firestore:"completed_at,omitempty"`
}
