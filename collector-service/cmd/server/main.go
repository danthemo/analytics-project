package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"collector-service/internal/collector"
	"collector-service/internal/config"
	httptransport "collector-service/internal/http"
	"collector-service/internal/sources"
)

func main() {
	cfg := config.Load()
	logger := log.New(os.Stdout, "", log.LstdFlags)
	client := &http.Client{}

	collectors := []collector.SourceCollector{
		sources.NewWildberriesCollector(client),
		sources.NewOzonCollector(client, cfg.OzonParserURL),
		sources.NewYandexMarketCollector(client, cfg.YandexMarketParserURL),
	}

	service := collector.New(collectors, cfg.SourceTimeout, logger)
	handler := httptransport.New(service)

	server := &http.Server{
		Addr:              cfg.Address(),
		Handler:           handler.Register(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      cfg.SourceTimeout + 10*time.Second,
		IdleTimeout:       30 * time.Second,
	}

	logger.Printf("starting %s on %s", cfg.AppName, cfg.Address())
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Fatalf("http server: %v", err)
	}
}
