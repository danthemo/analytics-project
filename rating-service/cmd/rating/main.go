package main

import (
	"context"
	"log"
	"net/http"
	"time"

	"rating-service/internal/analysis"
	"rating-service/internal/config"
	"rating-service/internal/db"
	"rating-service/internal/httpapi"
	"rating-service/internal/service"
)

func main() {
	cfg := config.Load()

	store, err := db.Open(cfg)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	analysisClient := analysis.New(cfg.AnalysisServiceURL)
	ratingService := service.New(store, analysisClient)
	handler := httpapi.New(ratingService)

	server := &http.Server{
		Addr:              cfg.Address(),
		Handler:           handler.Register(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       30 * time.Second,
	}

	log.Printf("starting %s on %s", cfg.AppName, cfg.Address())
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("http server: %v", err)
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = server.Shutdown(shutdownCtx)
}
