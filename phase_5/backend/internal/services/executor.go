package services

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"time"

	"phase_5/backend/internal/config"
)

type PythonExecutor struct {
	cfg *config.Config
}

func NewPythonExecutor(cfg *config.Config) *PythonExecutor {
	return &PythonExecutor{cfg: cfg}
}

// AnalyzeJD runs Phase 2 Analysis
func (pe *PythonExecutor) AnalyzeJD(ctx context.Context, jdText string) (string, error) {
	// Create temp file for JD text in LATEX_OUTPUT_DIR/temp
	tempDir := filepath.Join(pe.cfg.ProjectRoot, "latex", "output", "temp")
	if err := os.MkdirAll(tempDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create temp folder: %w", err)
	}

	tempFile, err := os.CreateTemp(tempDir, "jd_text_*.txt")
	if err != nil {
		return "", fmt.Errorf("failed to create temp file: %w", err)
	}
	defer os.Remove(tempFile.Name())
	defer tempFile.Close()

	if _, err := tempFile.WriteString(jdText); err != nil {
		return "", fmt.Errorf("failed to write temp file: %w", err)
	}

	// Run python -m phase_2.jd_analyzer.main <tempFile>
	stdout, stderr, err := pe.runPythonModule(ctx, "phase_2.jd_analyzer.main", tempFile.Name())
	if err != nil {
		return "", fmt.Errorf("phase_2 execution failed: %w (stderr: %s)", err, stderr)
	}

	// Extract doc_id via regex
	// e.g. "  Firestore Document: job_descriptions/XYZ"
	re := regexp.MustCompile(`Firestore Document:\s*job_descriptions/([a-zA-Z0-9_\-]+)`)
	matches := re.FindStringSubmatch(stdout)
	if len(matches) < 2 {
		return "", fmt.Errorf("failed to extract jd_document_id from output: %s", stdout)
	}

	return matches[1], nil
}

// MatchJDProfile runs Phase 3 Matching
func (pe *PythonExecutor) MatchJDProfile(ctx context.Context, jdDocID string) (string, error) {
	// Run python -m phase_3.matcher.main <jdDocID>
	stdout, stderr, err := pe.runPythonModule(ctx, "phase_3.matcher.main", jdDocID)
	if err != nil {
		return "", fmt.Errorf("phase_3 execution failed: %w (stderr: %s)", err, stderr)
	}

	// Extract match_id via regex
	// e.g. "  Firestore Match ID: job_matches/XYZ"
	re := regexp.MustCompile(`Firestore Match ID:\s*job_matches/([a-zA-Z0-9_\-]+)`)
	matches := re.FindStringSubmatch(stdout)
	if len(matches) < 2 {
		return "", fmt.Errorf("failed to extract match_id from output: %s", stdout)
	}

	return matches[1], nil
}

// TailorResume runs Phase 4 resume tailoring and compilation
func (pe *PythonExecutor) TailorResume(ctx context.Context, matchID string) (string, error) {
	// Run python -m phase_4.resume_tailor.main <matchID>
	stdout, stderr, err := pe.runPythonModule(ctx, "phase_4.resume_tailor.main", matchID)
	if err != nil {
		return "", fmt.Errorf("phase_4 execution failed: %w (stderr: %s)", err, stderr)
	}

	// Extract tailored_resume_id (or resume_id)
	// e.g. "OK  (resume_id: XYZ)" or "Resume ID:    XYZ"
	re := regexp.MustCompile(`resume_id:\s*([a-zA-Z0-9_\-]+)|Resume ID:\s*([a-zA-Z0-9_\-]+)`)
	matches := re.FindStringSubmatch(stdout)
	if len(matches) < 2 {
		return "", fmt.Errorf("failed to extract resume_id from output: %s", stdout)
	}

	// Get first non-empty capture group
	var resumeID string
	for _, m := range matches[1:] {
		if m != "" {
			resumeID = m
			break
		}
	}

	if resumeID == "" {
		return "", fmt.Errorf("failed to parse resume_id from output: %s", stdout)
	}

	return resumeID, nil
}

// RunIngestion runs Phase 6 Ingestion CLI for a specific source configuration ID.
func (pe *PythonExecutor) RunIngestion(ctx context.Context, sourceID string, dryRun bool) (string, error) {
	args := []string{"--source-id", sourceID}
	if dryRun {
		args = append(args, "--dry-run")
	}
	stdout, stderr, err := pe.runPythonModule(ctx, "phase_6.ingestion.main", args...)
	if err != nil {
		return "", fmt.Errorf("phase_6 ingestion failed: %w (stderr: %s)", err, stderr)
	}
	return stdout, nil
}

// RunIngestionWithJSON runs Phase 6 Ingestion CLI with --json output formatting
func (pe *PythonExecutor) RunIngestionWithJSON(ctx context.Context, sourceID string) (string, error) {
	stdout, stderr, err := pe.runPythonModule(ctx, "phase_6.ingestion.main", "--source-id", sourceID, "--json")
	if err != nil {
		return "", fmt.Errorf("phase_6 ingestion failed: %w (stderr: %s)", err, stderr)
	}
	return stdout, nil
}

func (pe *PythonExecutor) runPythonModule(ctx context.Context, module string, args ...string) (string, string, error) {
	cmdArgs := append([]string{"-m", module}, args...)
	cmd := exec.CommandContext(ctx, pe.cfg.PythonPath, cmdArgs...)

	// Execute inside project root directory
	cmd.Dir = pe.cfg.ProjectRoot

	// Pass parent env plus API keys and credentials
	cmd.Env = os.Environ()
	cmd.Env = append(cmd.Env,
		fmt.Sprintf("GEMINI_API_KEY=%s", pe.cfg.GeminiAPIKey),
		fmt.Sprintf("GOOGLE_APPLICATION_CREDENTIALS=%s", pe.cfg.GoogleApplicationCredentials),
		fmt.Sprintf("FIRESTORE_PROFILE_ID=%s", os.Getenv("FIRESTORE_PROFILE_ID")),
	)

	var stdoutBuf, stderrBuf bytes.Buffer
	cmd.Stdout = &stdoutBuf
	cmd.Stderr = &stderrBuf

	log.Printf("Executing Python command: %s %s (Dir: %s)", pe.cfg.PythonPath, module, pe.cfg.ProjectRoot)

	// Set 5-minute timeout for safety
	timeoutCtx, cancel := context.WithTimeout(ctx, 300*time.Second)
	defer cancel()

	err := cmd.Run()
	if timeoutCtx.Err() == context.DeadlineExceeded {
		return "", "", fmt.Errorf("subprocess execution timed out")
	}

	return stdoutBuf.String(), stderrBuf.String(), err
}
