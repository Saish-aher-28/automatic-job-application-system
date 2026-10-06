package services

import (
	"context"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// URLCheckResult holds classified result of application URL health check
type URLCheckResult struct {
	Status     string    `json:"application_url_status" firestore:"application_url_status"`
	HTTPStatus int       `json:"application_url_http_status" firestore:"application_url_http_status"`
	FinalURL   string    `json:"application_url_final_url" firestore:"application_url_final_url"`
	CheckedAt  time.Time `json:"application_url_checked_at" firestore:"application_url_checked_at"`
	Error      string    `json:"application_url_error,omitempty" firestore:"application_url_error,omitempty"`
}

type URLCheckerService struct{}

func NewURLCheckerService() *URLCheckerService {
	return &URLCheckerService{}
}

func (s *URLCheckerService) CheckURL(ctx context.Context, rawURL string) URLCheckResult {
	now := time.Now().UTC()
	trimmed := strings.TrimSpace(rawURL)

	if trimmed == "" {
		return URLCheckResult{
			Status:    "INVALID_URL",
			CheckedAt: now,
			Error:     "URL is empty",
		}
	}

	parsed, err := url.Parse(trimmed)
	if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" {
		return URLCheckResult{
			Status:    "INVALID_URL",
			CheckedAt: now,
			Error:     "Malformed URL or unsupported scheme",
		}
	}

	// Configure HTTP client with 7-second timeout and redirect tracking
	var finalURL string = trimmed
	isRedirected := false

	client := &http.Client{
		Timeout: 7 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 10 {
				return http.ErrUseLastResponse
			}
			isRedirected = true
			finalURL = req.URL.String()
			return nil
		},
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, trimmed, nil)
	if err != nil {
		return URLCheckResult{
			Status:    "INVALID_URL",
			CheckedAt: now,
			Error:     err.Error(),
		}
	}

	// Custom browser User-Agent to avoid immediate Cloudflare bot blocks
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		netErr, isNetErr := err.(net.Error)
		if isNetErr && netErr.Timeout() {
			return URLCheckResult{
				Status:    "TIMEOUT",
				CheckedAt: now,
				Error:     "Connection timed out after 7 seconds",
			}
		}
		if strings.Contains(err.Error(), "no such host") || strings.Contains(err.Error(), "Lookup") {
			return URLCheckResult{
				Status:    "DNS_ERROR",
				CheckedAt: now,
				Error:     "DNS resolution failed (host not found)",
			}
		}
		return URLCheckResult{
			Status:    "HTTP_ERROR",
			CheckedAt: now,
			Error:     err.Error(),
		}
	}
	defer resp.Body.Close()

	if isRedirected || (resp.Request != nil && resp.Request.URL != nil && resp.Request.URL.String() != trimmed) {
		if resp.Request != nil && resp.Request.URL != nil {
			finalURL = resp.Request.URL.String()
		}
	}

	statusCode := resp.StatusCode
	res := URLCheckResult{
		HTTPStatus: statusCode,
		FinalURL:   finalURL,
		CheckedAt:  now,
	}

	// Classify status
	switch {
	case statusCode == http.StatusNotFound:
		res.Status = "NOT_FOUND"
		res.Error = "404 Not Found"
	case statusCode == http.StatusForbidden:
		res.Status = "BLOCKED"
		res.Error = "403 Access Restricted / Blocked"
	case statusCode == http.StatusTooManyRequests:
		res.Status = "RATE_LIMITED"
		res.Error = "429 Rate Limited"
	case statusCode == http.StatusUnauthorized:
		res.Status = "LOGIN_REQUIRED"
		res.Error = "401 Unauthorized / Login Required"
	case statusCode >= 500:
		res.Status = "HTTP_ERROR"
		res.Error = http.StatusText(statusCode)
	case statusCode >= 200 && statusCode < 300:
		lowerFinal := strings.ToLower(finalURL)
		if strings.Contains(lowerFinal, "/login") || strings.Contains(lowerFinal, "/signin") || strings.Contains(lowerFinal, "/auth") {
			res.Status = "LOGIN_REQUIRED"
		} else if isRedirected && finalURL != trimmed {
			res.Status = "REDIRECTED"
		} else {
			res.Status = "WORKING"
		}
	case statusCode >= 300 && statusCode < 400:
		res.Status = "REDIRECTED"
	default:
		res.Status = "UNKNOWN"
	}

	return res
}
