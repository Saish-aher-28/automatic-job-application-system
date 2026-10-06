package firestore

import (
	"context"
	"fmt"
	"log"

	"cloud.google.com/go/firestore"
	firebase "firebase.google.com/go/v4"
	"google.golang.org/api/option"

	"phase_5/backend/internal/config"
)

type Client struct {
	App *firebase.App
	DB  *firestore.Client
}

func New(ctx context.Context, cfg *config.Config) (*Client, error) {
	var app *firebase.App
	var err error

	// Initialize Firebase App
	if cfg.GoogleApplicationCredentials != "" {
		opt := option.WithCredentialsFile(cfg.GoogleApplicationCredentials)
		app, err = firebase.NewApp(ctx, &firebase.Config{ProjectID: cfg.FirebaseProjectID}, opt)
	} else {
		// Attempt default credentials loading (e.g. metadata server on AWS Lightsail)
		app, err = firebase.NewApp(ctx, &firebase.Config{ProjectID: cfg.FirebaseProjectID})
	}

	if err != nil {
		return nil, fmt.Errorf("error initializing firebase app: %w", err)
	}

	// Initialize Firestore Client
	var dbClient *firestore.Client
	if cfg.GoogleApplicationCredentials != "" {
		opt := option.WithCredentialsFile(cfg.GoogleApplicationCredentials)
		dbClient, err = firestore.NewClient(ctx, cfg.FirebaseProjectID, opt)
	} else {
		dbClient, err = firestore.NewClient(ctx, cfg.FirebaseProjectID)
	}

	if err != nil {
		return nil, fmt.Errorf("error initializing firestore client: %w", err)
	}

	log.Printf("Firestore client initialized for project: %s", cfg.FirebaseProjectID)

	return &Client{
		App: app,
		DB:  dbClient,
	}, nil
}

func (c *Client) Close() {
	if c.DB != nil {
		c.DB.Close()
	}
}
