package services

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"

	"math"
	"strings"
	"sync"
	"time"

	"cloud.google.com/go/firestore"
	"google.golang.org/api/iterator"

	"phase_5/backend/internal/config"
	"phase_5/backend/internal/models"
)

type IngestionTask struct {
	RunID      string
	SourceID   string
	UserID     string
	RetryCount int
}

type IngestionWorkerService struct {
	cfg      *config.Config
	db       *firestore.Client
	executor *PythonExecutor
	taskChan chan *IngestionTask
	wg       sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
}

func NewIngestionWorkerService(cfg *config.Config, db *firestore.Client, executor *PythonExecutor) *IngestionWorkerService {
	ctx, cancel := context.WithCancel(context.Background())
	ws := &IngestionWorkerService{
		cfg:      cfg,
		db:       db,
		executor: executor,
		taskChan: make(chan *IngestionTask, 100),
		ctx:      ctx,
		cancel:   cancel,
	}

	// Start 2 worker goroutines
	for i := 0; i < 2; i++ {
		ws.wg.Add(1)
		go ws.workerLoop(i)
	}

	return ws
}

func (ws *IngestionWorkerService) StartScheduler(intervalMinutes int) {
	if intervalMinutes <= 0 {
		intervalMinutes = 15
	}
	log.Printf("[WorkerService] Background ingestion scheduler initialized (interval: %d minutes)", intervalMinutes)
	ws.wg.Add(1)
	go ws.schedulerLoop(time.Duration(intervalMinutes) * time.Minute)
}

func (ws *IngestionWorkerService) schedulerLoop(interval time.Duration) {
	defer ws.wg.Done()
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ws.ctx.Done():
			log.Printf("[WorkerService] Ingestion scheduler shutting down")
			return
		case <-ticker.C:
			log.Printf("[WorkerService] Ingestion scheduler tick triggered")
			ws.runScheduledIngestions()
		}
	}
}

func (ws *IngestionWorkerService) runScheduledIngestions() {
	ctx, cancel := context.WithTimeout(ws.ctx, 2*time.Minute)
	defer cancel()

	iter := ws.db.Collection("job_sources").Where("enabled", "==", true).Documents(ctx)
	defer iter.Stop()

	for {
		doc, err := iter.Next()
		if errors.Is(err, iterator.Done) {
			break
		}
		if err != nil {
			log.Printf("[WorkerService] Error fetching enabled job sources for scheduler: %v", err)
			break
		}

		var src models.JobSource
		if err := doc.DataTo(&src); err != nil {
			continue
		}
		src.ID = doc.Ref.ID

		// Overlap protection: skip if QUEUED or RUNNING
		if src.State == "QUEUED" || src.State == "RUNNING" {
			log.Printf("[WorkerService] Skipping scheduled run for source %s (%s): current state is %s", src.ID, src.Name, src.State)
			continue
		}

		log.Printf("[WorkerService] Triggering scheduled ingestion for source %s (%s)", src.ID, src.Name)
		_, err = ws.QueueRun(ctx, &src, src.UserID)
		if err != nil {
			log.Printf("[WorkerService] Failed to queue scheduled run for source %s: %v", src.ID, err)
		}
	}
}

func (ws *IngestionWorkerService) Stop() {
	ws.cancel()
	close(ws.taskChan)
	ws.wg.Wait()
}


// QueueRun creates an ingestion_runs record in status QUEUED and dispatches to task queue.
func (ws *IngestionWorkerService) QueueRun(ctx context.Context, source *models.JobSource, userID string) (*models.IngestionRun, error) {
	nowStr := time.Now().UTC().Format(time.RFC3339)
	runRecord := models.IngestionRun{
		SourceID:          source.ID,
		UserID:            userID,
		SourceType:        source.Type,
		SourceName:        source.Name,
		Status:            "QUEUED",
		CreatedAt:         nowStr,
		MessagesScanned:   0,
		JobsDetected:      0,
		JobsCreated:       0,
		DuplicatesSkipped: 0,
		NonJobsSkipped:    0,
		RetryCount:        0,
	}

	ref, _, err := ws.db.Collection("ingestion_runs").Add(ctx, runRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create ingestion run document: %w", err)
	}
	runRecord.ID = ref.ID

	// Update source state to QUEUED
	_, _ = ws.db.Collection("job_sources").Doc(source.ID).Update(ctx, []firestore.Update{
		{Path: "state", Value: "QUEUED"},
		{Path: "updated_at", Value: nowStr},
	})

	task := &IngestionTask{
		RunID:      runRecord.ID,
		SourceID:   source.ID,
		UserID:     userID,
		RetryCount: 0,
	}

	select {
	case ws.taskChan <- task:
		log.Printf("[WorkerService] Enqueued ingestion task runID=%s sourceID=%s", runRecord.ID, source.ID)
	default:
		// Queue full, process in goroutine directly
		go ws.processTask(task)
	}

	return &runRecord, nil
}

func (ws *IngestionWorkerService) workerLoop(workerID int) {
	defer ws.wg.Done()
	log.Printf("[WorkerService] Worker %d started", workerID)

	for {
		select {
		case <-ws.ctx.Done():
			log.Printf("[WorkerService] Worker %d shutting down", workerID)
			return
		case task, ok := <-ws.taskChan:
			if !ok {
				return
			}
			ws.processTask(task)
		}
	}
}

func (ws *IngestionWorkerService) processTask(task *IngestionTask) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()

	runRef := ws.db.Collection("ingestion_runs").Doc(task.RunID)
	sourceRef := ws.db.Collection("job_sources").Doc(task.SourceID)

	nowStr := time.Now().UTC().Format(time.RFC3339)

	// Set RUNNING status
	_, _ = runRef.Update(ctx, []firestore.Update{
		{Path: "status", Value: "RUNNING"},
		{Path: "started_at", Value: nowStr},
	})
	_, _ = sourceRef.Update(ctx, []firestore.Update{
		{Path: "state", Value: "RUNNING"},
		{Path: "last_run_at", Value: nowStr},
		{Path: "updated_at", Value: nowStr},
	})

	log.Printf("[WorkerService] Starting execution of task runID=%s sourceID=%s (retry %d)", task.RunID, task.SourceID, task.RetryCount)

	// Execute Python ingestion with --json flag
	output, err := ws.executor.RunIngestionWithJSON(ctx, task.SourceID)
	completedAt := time.Now().UTC().Format(time.RFC3339)

	if err != nil {
		isTransient := ws.isTransientError(err)
		log.Printf("[WorkerService] Ingestion failed for runID=%s: %v (transient: %v)", task.RunID, err, isTransient)

		if isTransient && task.RetryCount < 2 {
			task.RetryCount++
			backoffSec := time.Duration(math.Pow(2, float64(task.RetryCount))*5) * time.Second
			log.Printf("[WorkerService] Retrying task runID=%s in %v (attempt %d/2)", task.RunID, backoffSec, task.RetryCount)

			_, _ = runRef.Update(ctx, []firestore.Update{
				{Path: "retry_count", Value: task.RetryCount},
				{Path: "status", Value: "QUEUED"},
			})

			time.Sleep(backoffSec)
			ws.processTask(task)
			return
		}

		// Non-transient or max retries reached
		safeErrMsg := ws.cleanError(err.Error())
		_, _ = runRef.Update(ctx, []firestore.Update{
			{Path: "status", Value: "FAILED"},
			{Path: "completed_at", Value: completedAt},
			{Path: "error", Value: safeErrMsg},
			{Path: "retry_count", Value: task.RetryCount},
		})
		_, _ = sourceRef.Update(ctx, []firestore.Update{
			{Path: "state", Value: "ERROR"},
			{Path: "last_error", Value: safeErrMsg},
			{Path: "updated_at", Value: completedAt},
		})
		return
	}

	// Success: parse stats
	stats := ws.parseStats(output)

	scanned := stats.Telegram.Scanned + stats.Website.Scanned
	detected := stats.Telegram.Detected + stats.Website.Detected
	stored := stats.Telegram.Stored + stats.Website.Stored
	duplicates := stats.Telegram.Duplicates + stats.Website.Duplicates
	nonJobs := stats.Telegram.NonJobs + stats.Website.NonJobs

	_, _ = runRef.Update(ctx, []firestore.Update{
		{Path: "status", Value: "SUCCESS"},
		{Path: "completed_at", Value: completedAt},
		{Path: "messages_scanned", Value: scanned},
		{Path: "jobs_detected", Value: detected},
		{Path: "jobs_created", Value: stored},
		{Path: "duplicates_skipped", Value: duplicates},
		{Path: "non_jobs_skipped", Value: nonJobs},
		{Path: "error", Value: ""},
	})

	_, _ = sourceRef.Update(ctx, []firestore.Update{
		{Path: "state", Value: "ENABLED"},
		{Path: "last_success_at", Value: completedAt},
		{Path: "last_error", Value: ""},
		{Path: "updated_at", Value: completedAt},
	})

	log.Printf("[WorkerService] Successfully completed runID=%s (jobs_created=%d)", task.RunID, stored)
}

type ingestionStatsJSON struct {
	Telegram struct {
		Scanned    int `json:"scanned"`
		Detected   int `json:"detected"`
		Extracted  int `json:"extracted"`
		NonJobs    int `json:"non_jobs"`
		Stored     int `json:"stored"`
		Duplicates int `json:"duplicates"`
		Failed     int `json:"failed"`
	} `json:"telegram"`
	Website struct {
		Scanned    int `json:"scanned"`
		Detected   int `json:"detected"`
		Extracted  int `json:"extracted"`
		NonJobs    int `json:"non_jobs"`
		Stored     int `json:"stored"`
		Duplicates int `json:"duplicates"`
		Failed     int `json:"failed"`
	} `json:"website"`
}

func (ws *IngestionWorkerService) parseStats(output string) ingestionStatsJSON {
	var stats ingestionStatsJSON
	// Try parsing raw JSON
	if err := json.Unmarshal([]byte(output), &stats); err == nil {
		return stats
	}

	// Try parsing JSON block inside text output
	startIdx := strings.Index(output, "{")
	endIdx := strings.LastIndex(output, "}")
	if startIdx >= 0 && endIdx > startIdx {
		jsonStr := output[startIdx : endIdx+1]
		_ = json.Unmarshal([]byte(jsonStr), &stats)
	}
	return stats
}

func (ws *IngestionWorkerService) isTransientError(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	if strings.Contains(msg, "timed out") || strings.Contains(msg, "timeout") || strings.Contains(msg, "connection refused") || strings.Contains(msg, "temporary failure") || strings.Contains(msg, "503") || strings.Contains(msg, "429") {
		return true
	}
	return false
}

func (ws *IngestionWorkerService) cleanError(raw string) string {
	// Strip API keys and sensitive tokens
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

// ListRuns retrieves ingestion_runs for a user
func (ws *IngestionWorkerService) ListRuns(ctx context.Context, userID string, sourceID string, limit int) ([]models.IngestionRun, error) {
	colRef := ws.db.Collection("ingestion_runs")
	var q firestore.Query = colRef.Query

	if !ws.cfg.SingleUserMode && userID != "" {
		q = q.Where("user_id", "==", userID)
	}
	if sourceID != "" {
		q = q.Where("source_id", "==", sourceID)
	}

	q = q.OrderBy("created_at", firestore.Desc)
	if limit > 0 {
		q = q.Limit(limit)
	}

	iter := q.Documents(ctx)
	defer iter.Stop()

	var runs []models.IngestionRun
	for {
		doc, err := iter.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, err
		}
		var r models.IngestionRun
		if err := doc.DataTo(&r); err != nil {
			continue
		}
		r.ID = doc.Ref.ID
		runs = append(runs, r)
	}

	return runs, nil
}
