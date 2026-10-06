package config

import (
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/joho/godotenv"
)

type Config struct {
	Port                         string
	FrontendURL                  string
	FirebaseProjectID            string
	GoogleApplicationCredentials string
	GeminiAPIKey                 string
	// SingleUserMode enables a dev-only bypass where requests without an auth
	// token are accepted and attributed to a mock user. This is ONLY allowed
	// when ENVIRONMENT=development. In production this is always false.
	SingleUserMode bool
	Environment    string
	PythonPath     string
	ProjectRoot    string
}

func Load() *Config {
	// Locate project root by searching for requirements.txt or go.mod
	execDir, err := os.Getwd()
	if err != nil {
		log.Printf("Warning: failed to get working dir: %v", err)
	}

	// Simple heuristic: search upwards for "requirements.txt" to find project root
	projectRoot := execDir
	for {
		if _, err := os.Stat(filepath.Join(projectRoot, "requirements.txt")); err == nil {
			break
		}
		parent := filepath.Dir(projectRoot)
		if parent == projectRoot {
			projectRoot = execDir // Fallback
			break
		}
		projectRoot = parent
	}

	// Load root .env file if it exists
	envPath := filepath.Join(projectRoot, ".env")
	if _, err := os.Stat(envPath); err == nil {
		if err := godotenv.Load(envPath); err != nil {
			log.Printf("Warning: error loading .env file: %v", err)
		}
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	frontendURL := os.Getenv("FRONTEND_URL")
	if frontendURL == "" {
		frontendURL = "http://localhost:5173" // Default React/Vite dev url
	}

	firebaseProjectID := os.Getenv("FIREBASE_PROJECT_ID")
	if firebaseProjectID == "" {
		// Try parsing from credentials json if needed, or default
		firebaseProjectID = "automatic-job-applicatio-7b237"
	}

	googleApplicationCredentials := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")
	if googleApplicationCredentials == "" {
		googleApplicationCredentials = filepath.Join(projectRoot, "firebase-credentials", "automatic-job-applicatio-7b237-firebase-adminsdk-fbsvc-a5c2b6fd17.json")
	}

	geminiAPIKey := os.Getenv("GEMINI_API_KEY")

	// ENVIRONMENT controls the security posture of the server.
	// Default is "production" — the most restrictive/secure setting.
	// Set ENVIRONMENT=development explicitly to enable dev conveniences.
	environment := strings.ToLower(strings.TrimSpace(os.Getenv("ENVIRONMENT")))
	if environment == "" {
		environment = "production"
	}

	// SECURITY: SingleUserMode is ONLY permitted in development environments.
	// Even if SINGLE_USER_MODE=true is set, it is ignored in production.
	// This prevents accidental auth bypass in deployed environments.
	singleUserMode := false
	if environment == "development" {
		rawVal := strings.ToLower(strings.TrimSpace(os.Getenv("SINGLE_USER_MODE")))
		singleUserMode = (rawVal == "true" || rawVal == "1" || rawVal == "yes")
	}

	if singleUserMode {
		log.Printf("⚠️  WARNING: SINGLE_USER_MODE is enabled. All requests will be attributed to the dev mock user. NEVER use this in production.")
	}

	pythonPath := os.Getenv("PYTHON_PATH")
	if pythonPath == "" {
		// Detect local venv path
		venvPython := filepath.Join(projectRoot, "venv", "Scripts", "python.exe")
		if _, err := os.Stat(venvPython); err == nil {
			pythonPath = venvPython
		} else {
			// Unix fallback
			venvPythonUnix := filepath.Join(projectRoot, "venv", "bin", "python")
			if _, err := os.Stat(venvPythonUnix); err == nil {
				pythonPath = venvPythonUnix
			} else {
				pythonPath = "python" // Global fallback
			}
		}
	}

	return &Config{
		Port:                         port,
		FrontendURL:                  strings.TrimRight(frontendURL, "/"),
		FirebaseProjectID:            firebaseProjectID,
		GoogleApplicationCredentials: googleApplicationCredentials,
		GeminiAPIKey:                 geminiAPIKey,
		SingleUserMode:               singleUserMode,
		Environment:                  environment,
		PythonPath:                   pythonPath,
		ProjectRoot:                  projectRoot,
	}
}
