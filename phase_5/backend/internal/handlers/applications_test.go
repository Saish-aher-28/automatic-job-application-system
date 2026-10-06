package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// ── TEST: Application creation input validation ─────────────────────────────

func TestCreateApplicationValidation(t *testing.T) {
	h := newSingleUserHandler()

	tests := []struct {
		name       string
		payload    map[string]interface{}
		wantStatus int
		wantCode   string
	}{
		{
			name:       "missing job_id",
			payload:    map[string]interface{}{"opportunity_id": "opp123"},
			wantStatus: http.StatusUnprocessableEntity,
			wantCode:   "VALIDATION_ERROR",
		},
		{
			name:       "invalid application URL scheme (javascript)",
			payload:    map[string]interface{}{"job_id": "job123", "application_url": "javascript:alert(1)"},
			wantStatus: http.StatusUnprocessableEntity,
			wantCode:   "VALIDATION_ERROR",
		},
		{
			name:       "invalid application URL scheme (file)",
			payload:    map[string]interface{}{"job_id": "job123", "application_url": "file:///etc/passwd"},
			wantStatus: http.StatusUnprocessableEntity,
			wantCode:   "VALIDATION_ERROR",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			body, _ := json.Marshal(tc.payload)
			req := httptest.NewRequest("POST", "/api/v1/applications", bytes.NewReader(body))
			req = req.WithContext(ctxWithMockUser())
			w := httptest.NewRecorder()

			h.CreateApplication(w, req)

			if w.Code != tc.wantStatus {
				t.Errorf("CreateApplication() status = %d; want %d (body: %s)", w.Code, tc.wantStatus, w.Body.String())
			}

			var resp struct {
				Success bool `json:"success"`
				Error   struct {
					Code string `json:"code"`
				} `json:"error"`
			}
			_ = json.Unmarshal(w.Body.Bytes(), &resp)

			if resp.Error.Code != tc.wantCode {
				t.Errorf("CreateApplication() error code = %q; want %q", resp.Error.Code, tc.wantCode)
			}
		})
	}
}

// ── TEST: Application submit confirmation required ─────────────────────────

func TestSubmitApplicationConfirmationRequired(t *testing.T) {
	h := newSingleUserHandler()

	// Missing explicit confirmation flag
	payload := map[string]interface{}{
		"confirmation": false,
		"notes":        "Submitted via portal",
	}

	body, _ := json.Marshal(payload)
	req := httptest.NewRequest("POST", "/api/v1/applications/app123/submit", bytes.NewReader(body))
	req = req.WithContext(ctxWithMockUser())
	w := httptest.NewRecorder()

	h.SubmitApplication(w, req)

	if w.Code != http.StatusUnprocessableEntity {
		t.Errorf("SubmitApplication() status = %d; want %d", w.Code, http.StatusUnprocessableEntity)
	}

	var resp struct {
		Success bool `json:"success"`
		Error   struct {
			Code string `json:"code"`
		} `json:"error"`
	}
	_ = json.Unmarshal(w.Body.Bytes(), &resp)

	if resp.Error.Code != "CONFIRMATION_REQUIRED" {
		t.Errorf("SubmitApplication() error code = %q; want 'CONFIRMATION_REQUIRED'", resp.Error.Code)
	}
}

// ── TEST: Application status update invalid status ──────────────────────────

func TestUpdateApplicationStatusInvalid(t *testing.T) {
	h := newSingleUserHandler()

	payload := map[string]interface{}{
		"status": "NONEXISTENT_STATUS",
	}

	body, _ := json.Marshal(payload)
	req := httptest.NewRequest("PATCH", "/api/v1/applications/app123/status", bytes.NewReader(body))
	req = req.WithContext(ctxWithMockUser())
	w := httptest.NewRecorder()

	h.UpdateApplicationStatus(w, req)

	if w.Code != http.StatusUnprocessableEntity {
		t.Errorf("UpdateApplicationStatus() status = %d; want %d", w.Code, http.StatusUnprocessableEntity)
	}
}

// ── TEST: Application note validation ──────────────────────────────────────

func TestAddApplicationNoteValidation(t *testing.T) {
	h := newSingleUserHandler()

	payload := map[string]interface{}{
		"notes": "   ",
	}

	body, _ := json.Marshal(payload)
	req := httptest.NewRequest("POST", "/api/v1/applications/app123/notes", bytes.NewReader(body))
	req = req.WithContext(ctxWithMockUser())
	w := httptest.NewRecorder()

	h.AddApplicationNote(w, req)

	if w.Code != http.StatusUnprocessableEntity {
		t.Errorf("AddApplicationNote() status = %d; want %d", w.Code, http.StatusUnprocessableEntity)
	}
}
