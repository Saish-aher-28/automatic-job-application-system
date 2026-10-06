package services

import (
	"errors"
	"testing"
)

func TestWorkerErrorClassification(t *testing.T) {
	ws := &IngestionWorkerService{}

	t.Run("Transient error detection", func(t *testing.T) {
		timeoutErr := errors.New("subprocess execution timed out")
		if !ws.isTransientError(timeoutErr) {
			t.Errorf("Expected timeout error to be classified as transient")
		}

		connErr := errors.New("connection refused by remote host")
		if !ws.isTransientError(connErr) {
			t.Errorf("Expected connection refused to be classified as transient")
		}
	})

	t.Run("Non-transient error detection", func(t *testing.T) {
		invalidConfigErr := errors.New("invalid configuration: missing source URL")
		if ws.isTransientError(invalidConfigErr) {
			t.Errorf("Expected invalid config error to be non-transient")
		}
	})

	t.Run("Clean sensitive errors", func(t *testing.T) {
		raw := "Failed with GEMINI_API_KEY=secret_key_12345 in process environment"
		cleaned := ws.cleanError(raw)

		if cleaned == raw {
			t.Errorf("Expected sensitive token to be redacted")
		}
	})
}
