package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestSourceValidationCases(t *testing.T) {
	h := newSingleUserHandler()

	tests := []struct {
		name           string
		payload        map[string]interface{}
		expectedStatus int
	}{
		{
			name: "Valid Telegram Source with @ prefix",
			payload: map[string]interface{}{
				"name":       "Golang Channel",
				"type":       "telegram",
				"identifier": "@golangjobs",
			},
			expectedStatus: http.StatusCreated, // will try to hit DB in this test if valid, but we mock or catch nil panic
		},
		{
			name: "Missing Name",
			payload: map[string]interface{}{
				"type":       "telegram",
				"identifier": "@golangjobs",
			},
			expectedStatus: http.StatusUnprocessableEntity,
		},
		{
			name: "Invalid Type",
			payload: map[string]interface{}{
				"name":       "My Channel",
				"type":       "slack",
				"identifier": "general",
			},
			expectedStatus: http.StatusUnprocessableEntity,
		},
		{
			name: "Telegram Missing Identifier",
			payload: map[string]interface{}{
				"name": "My Channel",
				"type": "telegram",
			},
			expectedStatus: http.StatusUnprocessableEntity,
		},
		{
			name: "Website Missing URL",
			payload: map[string]interface{}{
				"name": "My Website",
				"type": "website",
			},
			expectedStatus: http.StatusUnprocessableEntity,
		},
		{
			name: "Website Malformed URL",
			payload: map[string]interface{}{
				"name": "My Website",
				"type": "website",
				"url":  "not-a-url",
			},
			expectedStatus: http.StatusUnprocessableEntity,
		},
		{
			name: "Website Invalid Scheme",
			payload: map[string]interface{}{
				"name": "My Website",
				"type": "website",
				"url":  "ftp://example.com/jobs",
			},
			expectedStatus: http.StatusUnprocessableEntity,
		},
		{
			name: "Website Javascript URL",
			payload: map[string]interface{}{
				"name": "My Website",
				"type": "website",
				"url":  "javascript:alert(1)",
			},
			expectedStatus: http.StatusUnprocessableEntity,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			body, _ := json.Marshal(tc.payload)
			req := httptest.NewRequest(http.MethodPost, "/api/v1/sources", bytes.NewReader(body)).WithContext(ctxWithMockUser())
			w := httptest.NewRecorder()

			defer func() {
				// Catch the expected nil panic from h.db when validation succeeds
				if r := recover(); r != nil {
					if tc.expectedStatus != http.StatusCreated {
						t.Errorf("unexpected panic for case '%s': %v", tc.name, r)
					}
				}
			}()

			h.CreateSource(w, req)
			if w.Code != tc.expectedStatus {
				t.Errorf("CreateSource returned code %d; expected %d", w.Code, tc.expectedStatus)
			}
		})
	}
}
