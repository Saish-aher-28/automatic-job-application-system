package services

import (
	"context"
	"fmt"
	"log"
	"regexp"
	"strings"
	"sync"
	"time"

	"cloud.google.com/go/firestore"
	"phase_5/backend/internal/config"
	"phase_5/backend/internal/models"
)

type TaskRunJob struct {
	TaskRunID string
	UserID    string
}

type TaskWorkerService struct {
	cfg      *config.Config
	db       *firestore.Client
	executor *PythonExecutor
	queue    chan *TaskRunJob
	wg       sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
}

func NewTaskWorkerService(cfg *config.Config, db *firestore.Client, executor *PythonExecutor) *TaskWorkerService {
	ctx, cancel := context.WithCancel(context.Background())
	ts := &TaskWorkerService{
		cfg:      cfg,
		db:       db,
		executor: executor,
		queue:    make(chan *TaskRunJob, 100),
		ctx:      ctx,
		cancel:   cancel,
	}

	ts.wg.Add(1)
	go ts.workerLoop()

	return ts
}

func (ts *TaskWorkerService) Stop() {
	ts.cancel()
	close(ts.queue)
	ts.wg.Wait()
}

func (ts *TaskWorkerService) QueueTask(ctx context.Context, taskType, targetID, userID string) (*models.TaskRun, error) {
	now := time.Now().UTC()
	task := models.TaskRun{
		UserID:    userID,
		Type:      taskType,
		TargetID:  targetID,
		Status:    "QUEUED",
		CreatedAt: now,
	}
	ref, _, err := ts.db.Collection("task_runs").Add(ctx, task)
	if err != nil {
		return nil, fmt.Errorf("failed to create task_runs record: %w", err)
	}
	task.ID = ref.ID

	ts.queue <- &TaskRunJob{
		TaskRunID: ref.ID,
		UserID:    userID,
	}
	return &task, nil
}

func (ts *TaskWorkerService) workerLoop() {
	defer ts.wg.Done()
	log.Printf("[TaskWorker] Background worker loop started")

	for {
		select {
		case <-ts.ctx.Done():
			log.Printf("[TaskWorker] Background worker loop shutting down")
			return
		case job, ok := <-ts.queue:
			if !ok {
				return
			}
			ts.executeTask(job)
		}
	}
}

func (ts *TaskWorkerService) executeTask(job *TaskRunJob) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	taskRef := ts.db.Collection("task_runs").Doc(job.TaskRunID)
	
	// Update status to RUNNING
	_, _ = taskRef.Update(ctx, []firestore.Update{
		{Path: "status", Value: "RUNNING"},
	})

	snap, err := taskRef.Get(ctx)
	if err != nil {
		log.Printf("[TaskWorker] TaskRun %s not found: %v", job.TaskRunID, err)
		return
	}
	var task models.TaskRun
	_ = snap.DataTo(&task)

	if task.Type == "generate-resume" {
		appRef := ts.db.Collection("applications").Doc(task.TargetID)
		appSnap, err := appRef.Get(ctx)
		if err != nil {
			ts.failTask(ctx, taskRef, fmt.Sprintf("Application %s not found", task.TargetID))
			return
		}
		var app models.Application
		_ = appSnap.DataTo(&app)

		// 1. Fetch Job Match ID
		jobSnap, err := ts.db.Collection("jobs").Doc(app.JobID).Get(ctx)
		if err != nil {
			ts.failTask(ctx, taskRef, fmt.Sprintf("Job %s not found", app.JobID))
			return
		}
		var j models.Job
		_ = jobSnap.DataTo(&j)

		if j.MatchID == "" {
			log.Printf("[TaskWorker] MatchID is empty for Job %s. Running automatic Analysis & Matching pipeline...", app.JobID)
			
			jdDocID := j.JDDocumentID
			if jdDocID == "" {
				if strings.TrimSpace(j.JDText) == "" {
					ts.failTask(ctx, taskRef, "Job description text is empty. Cannot perform JD analysis or matching.")
					_, _ = appRef.Update(ctx, []firestore.Update{
						{Path: "status", Value: "FAILED"},
						{Path: "updated_at", Value: time.Now().UTC()},
					})
					return
				}
				analyzedID, err := ts.executor.AnalyzeJD(ctx, j.JDText)
				if err != nil {
					ts.failTask(ctx, taskRef, fmt.Sprintf("Automatic JD analysis failed: %v", err))
					_, _ = appRef.Update(ctx, []firestore.Update{
						{Path: "status", Value: "FAILED"},
						{Path: "updated_at", Value: time.Now().UTC()},
					})
					return
				}
				jdDocID = analyzedID
				_, _ = ts.db.Collection("jobs").Doc(app.JobID).Update(ctx, []firestore.Update{
					{Path: "jd_document_id", Value: jdDocID},
					{Path: "status", Value: "ANALYZED"},
					{Path: "updated_at", Value: time.Now().UTC()},
				})
			}


			matchedID, err := ts.executor.MatchJDProfile(ctx, jdDocID)
			if err != nil {
				ts.failTask(ctx, taskRef, fmt.Sprintf("Automatic JD profile matching failed: %v", err))
				_, _ = appRef.Update(ctx, []firestore.Update{
					{Path: "status", Value: "FAILED"},
					{Path: "updated_at", Value: time.Now().UTC()},
				})
				return
			}

			j.MatchID = matchedID
			_, _ = ts.db.Collection("jobs").Doc(app.JobID).Update(ctx, []firestore.Update{
				{Path: "match_id", Value: matchedID},
				{Path: "status", Value: "MATCHED"},
				{Path: "updated_at", Value: time.Now().UTC()},
			})
		}


		// 2. Call Phase 4 Resume Tailoring script
		log.Printf("[TaskWorker] Executing Phase 4 resume tailoring for MatchID: %s", j.MatchID)
		resumeID, err := ts.executor.TailorResume(ctx, j.MatchID)
		if err != nil {
			log.Printf("[TaskWorker] Resume tailoring failed: %v", err)
			ts.failTask(ctx, taskRef, err.Error())
			
			// Set Application status to FAILED
			_, _ = appRef.Update(ctx, []firestore.Update{
				{Path: "status", Value: "FAILED"},
				{Path: "updated_at", Value: time.Now().UTC()},
			})
			return
		}

		// 3. Update application and job details
		now := time.Now().UTC()
		resumePath := fmt.Sprintf("latex/output/tailored/%s/resume.pdf", j.MatchID)
		cleanedCompany := cleanFilename(app.Company)
		cleanedTitle := cleanFilename(app.JobTitle)
		resumeFilename := fmt.Sprintf("resume_%s_%s.pdf", cleanedCompany, cleanedTitle)

		var matchScore float64 = 0.0
		if j.MatchID != "" {
			if matchSnap, err := ts.db.Collection("job_matches").Doc(j.MatchID).Get(ctx); err == nil {
				if scores, ok := matchSnap.Data()["scores"].(map[string]interface{}); ok {
					if overall, ok := scores["overall"].(float64); ok {
						matchScore = overall
					}
				}
			}
		}

		_, _ = appRef.Update(ctx, []firestore.Update{
			{Path: "job_match_id", Value: j.MatchID},
			{Path: "match_score", Value: matchScore},
			{Path: "resume_path", Value: resumePath},
			{Path: "resume_filename", Value: resumeFilename},
			{Path: "resume_generated_at", Value: now},
			{Path: "status", Value: "RESUME_GENERATED"},
			{Path: "updated_at", Value: now},
		})


		_, _ = ts.db.Collection("jobs").Doc(app.JobID).Update(ctx, []firestore.Update{
			{Path: "tailored_resume_id", Value: resumeID},
			{Path: "status", Value: "RESUME_READY"},
			{Path: "updated_at", Value: now},
		})

		// 4. Log event in subcollection
		_, _, _ = appRef.Collection("events").Add(ctx, models.ApplicationEvent{
			Event:     "RESUME_GENERATED",
			Timestamp: now,
			UserID:    task.UserID,
			Notes:     fmt.Sprintf("Tailored resume generated. Resume ID: %s", resumeID),
		})


		// 5. Complete task
		ts.completeTask(ctx, taskRef)
	}
}

func (ts *TaskWorkerService) failTask(ctx context.Context, ref *firestore.DocumentRef, errMsg string) {
	now := time.Now().UTC()
	_, _ = ref.Update(ctx, []firestore.Update{
		{Path: "status", Value: "FAILED"},
		{Path: "error", Value: ts.cleanError(errMsg)},
		{Path: "completed_at", Value: now},
	})
}

func (ts *TaskWorkerService) completeTask(ctx context.Context, ref *firestore.DocumentRef) {
	now := time.Now().UTC()
	_, _ = ref.Update(ctx, []firestore.Update{
		{Path: "status", Value: "SUCCESS"},
		{Path: "completed_at", Value: now},
	})
}

func (ts *TaskWorkerService) cleanError(raw string) string {
	cleaned := raw
	for _, key := range []string{"GEMINI_API_KEY", "TELEGRAM_API_HASH", "FIREBASE_API_KEY"} {
		if idx := strings.Index(cleaned, key); idx >= 0 {
			cleaned = cleaned[:idx] + "[REDACTED]"
		}
	}
	if len(cleaned) > 500 {
		cleaned = cleaned[:500] + "... (truncated)"
	}
	return cleaned
}

func cleanFilename(s string) string {
	re := regexp.MustCompile(`[^a-zA-Z0-9]+`)
	cleaned := strings.Trim(re.ReplaceAllString(strings.ToLower(s), "_"), "_")
	if cleaned == "" {
		return "application"
	}
	return cleaned
}
