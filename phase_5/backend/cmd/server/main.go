package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"

	"syscall"
	"time"

	"phase_5/backend/internal/auth"
	"phase_5/backend/internal/config"
	"phase_5/backend/internal/firestore"
	"phase_5/backend/internal/handlers"
	"phase_5/backend/internal/services"
)

func main() {
	log.Println("Starting Automatic Job Application System — Go Backend")

	// 1. Load Configurations
	cfg := config.Load()

	// 2. Initialize Firestore
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	fsClient, err := firestore.New(ctx, cfg)
	if err != nil {
		log.Fatalf("Critical error initializing Firestore client: %v", err)
	}
	defer fsClient.Close()

	// 3. Initialize services
	executor := services.NewPythonExecutor(cfg)
	worker := services.NewIngestionWorkerService(cfg, fsClient.DB, executor)
	defer worker.Stop()

	intervalStr := os.Getenv("INGESTION_INTERVAL_MINUTES")
	intervalMinutes := 15
	if intervalStr != "" {
		if parsed, err := strconv.Atoi(intervalStr); err == nil && parsed > 0 {
			intervalMinutes = parsed
		}
	}
	worker.StartScheduler(intervalMinutes)


	taskWorker := services.NewTaskWorkerService(cfg, fsClient.DB, executor)
	defer taskWorker.Stop()

	apiHandler := handlers.NewAPIHandler(cfg, fsClient.DB, executor, worker, taskWorker)


	// 4. Setup Routes and Multiplexer
	mux := http.NewServeMux()

	// Public routes
	mux.HandleFunc("/health", apiHandler.HealthCheck)
	mux.HandleFunc("/api/v1/auth/config", apiHandler.AuthConfig)

	// Setup Authentication middleware
	authMiddleware := auth.Middleware(fsClient.App, cfg.SingleUserMode)

	// Register authenticated endpoints with middleware
	mux.Handle("/api/v1/profile", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			apiHandler.GetProfile(w, r)
		} else if r.Method == http.MethodPut || r.Method == http.MethodPost {
			apiHandler.UpdateProfile(w, r)
		} else {
			http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
		}
	})))

	// CRUD Helper registering function
	registerCRUD := func(resource string) {
		mux.Handle("/api/v1/"+resource, authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.Method == http.MethodGet {
				if resource == "projects" {
					apiHandler.ListProjects(w, r)
				} else if resource == "skills" {
					apiHandler.ListSkills(w, r)
				} else {
					apiHandler.ListGenericCRUD(w, r, resource)
				}
			} else if r.Method == http.MethodPost {
				if resource == "projects" {
					apiHandler.CreateProject(w, r)
				} else if resource == "skills" {
					apiHandler.CreateSkill(w, r)
				} else {
					apiHandler.CreateGenericCRUD(w, r, resource)
				}
			} else {
				http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
			}
		})))

		mux.Handle("/api/v1/"+resource+"/", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.Method == http.MethodPut || r.Method == http.MethodPost {
				if resource == "projects" {
					apiHandler.UpdateProject(w, r)
				} else {
					apiHandler.UpdateGenericCRUD(w, r, resource)
				}
			} else if r.Method == http.MethodDelete {
				if resource == "projects" {
					apiHandler.DeleteProject(w, r)
				} else if resource == "skills" {
					apiHandler.DeleteSkill(w, r)
				} else {
					apiHandler.DeleteGenericCRUD(w, r, resource)
				}
			} else {
				http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
			}
		})))
	}

	// Register CRUD resources
	registerCRUD("projects")
	registerCRUD("skills")
	registerCRUD("education")
	registerCRUD("experience")
	registerCRUD("certifications")
	registerCRUD("languages")
	registerCRUD("interests")

	// Job Handlers
	mux.Handle("/api/v1/jobs", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			apiHandler.ListJobs(w, r)
		} else if r.Method == http.MethodPost {
			apiHandler.CreateJob(w, r)
		} else {
			http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
		}
	})))

	mux.Handle("/api/v1/jobs/", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Specific pipeline post actions
		if r.Method == http.MethodPost {
			if strings.HasSuffix(r.URL.Path, "/analyze") {
				apiHandler.AnalyzeJobJD(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/match") {
				apiHandler.MatchJobProfile(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/generate-resume") {
				apiHandler.GenerateJobResume(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/check-url") {
				apiHandler.CheckJobURL(w, r)
				return
			}

		}
		if r.Method == http.MethodPatch && strings.HasSuffix(r.URL.Path, "/status") {
			apiHandler.UpdateJobStatus(w, r)
			return
		}

		if r.Method == http.MethodGet {
			if strings.HasSuffix(r.URL.Path, "/resume") {
				apiHandler.ServeResumePDF(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/match-result") {
				apiHandler.GetJobMatchResult(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/resume-result") {
				apiHandler.GetJobResumeResult(w, r)
				return
			}
			apiHandler.GetJob(w, r)
			return
		}

		if r.Method == http.MethodPut {
			apiHandler.UpdateJob(w, r)
			return
		}

		if r.Method == http.MethodDelete {
			apiHandler.DeleteJob(w, r)
			return
		}

		http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
	})))

	// Job Ingestion Opportunities Handlers
	mux.Handle("/api/v1/opportunities", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			apiHandler.ListOpportunities(w, r)
		} else {
			http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
		}
	})))

	mux.Handle("/api/v1/opportunities/", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost && strings.HasSuffix(r.URL.Path, "/import") {
			apiHandler.ImportOpportunity(w, r)
		} else {
			http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
		}
	})))

	// Job Sources Handlers
	mux.Handle("/api/v1/sources", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			apiHandler.ListSources(w, r)
		} else if r.Method == http.MethodPost {
			apiHandler.CreateSource(w, r)
		} else {
			http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
		}
	})))

	mux.Handle("/api/v1/sources/", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			if strings.HasSuffix(r.URL.Path, "/enable") {
				apiHandler.EnableSource(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/disable") {
				apiHandler.DisableSource(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/test") {
				apiHandler.TestSource(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/run") {
				apiHandler.RunSource(w, r)
				return
			}
		}

		if r.Method == http.MethodGet {
			apiHandler.GetSource(w, r)
			return
		}

		if r.Method == http.MethodPut {
			apiHandler.UpdateSource(w, r)
			return
		}

		if r.Method == http.MethodDelete {
			apiHandler.DeleteSource(w, r)
			return
		}

		http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
	})))

	// Ingestion Runs Handlers
	mux.Handle("/api/v1/runs", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			apiHandler.ListIngestionRuns(w, r)
		} else {
			http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
		}
	})))

	// Phase 7 Application Management Handlers
	mux.Handle("/api/v1/applications", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			apiHandler.ListApplications(w, r)
		} else if r.Method == http.MethodPost {
			apiHandler.CreateApplication(w, r)
		} else {
			http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
		}
	})))

	mux.Handle("/api/v1/applications/", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			if strings.HasSuffix(r.URL.Path, "/prepare") {
				apiHandler.PrepareApplication(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/generate-resume") {
				apiHandler.GenerateApplicationResume(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/open") {
				apiHandler.OpenApplication(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/submit") {
				apiHandler.SubmitApplication(w, r)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/check-url") {
				apiHandler.CheckApplicationURL(w, r)
				return
			}

		}

		if r.Method == http.MethodPatch && strings.HasSuffix(r.URL.Path, "/status") {
			apiHandler.UpdateApplicationStatus(w, r)
			return
		}

		if r.Method == http.MethodGet {
			if strings.HasSuffix(r.URL.Path, "/events") {
				apiHandler.ListApplicationEvents(w, r)
				return
			}
			apiHandler.GetApplication(w, r)
			return
		}

		http.Error(w, `{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed"}}`, http.StatusMethodNotAllowed)
	})))

	// Setup CORS wrapping handler

	corsHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", cfg.FrontendURL)
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.Header().Set("Access-Control-Max-Age", "3600")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		mux.ServeHTTP(w, r)
	})

	// Start server
	serverAddr := fmt.Sprintf(":%s", cfg.Port)
	srv := &http.Server{
		Addr:         serverAddr,
		Handler:      corsHandler,
		WriteTimeout: 310 * time.Second, // Timeout to accommodate 5-minute subprocess executor limit
		ReadTimeout:  15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	log.Printf("Go Server listening on %s (CORS matching: %s)", serverAddr, cfg.FrontendURL)

	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen error: %s\n", err)
		}
	}()

	// Setup Graceful Shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down Go server...")

	ctxShut, cancelShut := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelShut()

	if err := srv.Shutdown(ctxShut); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Go Server stopped cleanly")
}
