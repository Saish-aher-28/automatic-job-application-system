package auth

import (
	"context"
	"net/http"
	"strings"

	firebase "firebase.google.com/go/v4"
)

type contextKey string

const (
	UserIDKey contextKey = "userId"
	EmailKey  contextKey = "email"
)

func Middleware(app *firebase.App, singleUserMode bool) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Handle CORS preflight
			if r.Method == http.MethodOptions {
				next.ServeHTTP(w, r)
				return
			}

			authHeader := r.Header.Get("Authorization")
			var idToken string

			if strings.HasPrefix(authHeader, "Bearer ") {
				idToken = strings.TrimPrefix(authHeader, "Bearer ")
			}

			// Fallback for single-user dev testing if configured and token is absent
			if idToken == "" && singleUserMode {
				ctx := context.WithValue(r.Context(), UserIDKey, "saish-aher-dev")
				ctx = context.WithValue(ctx, EmailKey, "saishaher28@gmail.com")
				next.ServeHTTP(w, r.WithContext(ctx))
				return
			}

			if idToken == "" {
				http.Error(w, `{"success":false,"error":{"code":"UNAUTHENTICATED","message":"Missing authorization token"}}`, http.StatusUnauthorized)
				return
			}

			// Verify token using Firebase Auth
			authClient, err := app.Auth(r.Context())
			if err != nil {
				http.Error(w, `{"success":false,"error":{"code":"INTERNAL_ERROR","message":"Failed to initialize auth client"}}`, http.StatusInternalServerError)
				return
			}

			token, err := authClient.VerifyIDToken(r.Context(), idToken)
			if err != nil {
				http.Error(w, `{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid or expired auth token"}}`, http.StatusUnauthorized)
				return
			}

			// Inject user ID and email into context
			ctx := context.WithValue(r.Context(), UserIDKey, token.UID)
			email, _ := token.Claims["email"].(string)
			ctx = context.WithValue(ctx, EmailKey, email)

			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// GetUser gets UID from request context
func GetUser(ctx context.Context) string {
	uid, _ := ctx.Value(UserIDKey).(string)
	return uid
}

// GetEmail gets email from request context
func GetEmail(ctx context.Context) string {
	email, _ := ctx.Value(EmailKey).(string)
	return email
}
