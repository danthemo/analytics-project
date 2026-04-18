package config

import (
	"fmt"
	"os"
)

type Config struct {
	AppName            string
	HTTPPort           string
	AnalysisServiceURL string
	DBHost             string
	DBPort             string
	DBName             string
	DBUser             string
	DBPassword         string
	DBSSLMode          string
}

func Load() Config {
	return Config{
		AppName:            getEnv("APP_NAME", "rating-service"),
		HTTPPort:           getEnv("HTTP_PORT", "8080"),
		AnalysisServiceURL: getEnv("ANALYSIS_SERVICE_URL", "http://localhost:8000"),
		DBHost:             getEnv("DB_HOST", "localhost"),
		DBPort:             getEnv("DB_PORT", "5432"),
		DBName:             getEnv("DB_NAME", "market_ratings"),
		DBUser:             getEnv("DB_USER", "postgres"),
		DBPassword:         getEnv("DB_PASSWORD", "postgres"),
		DBSSLMode:          getEnv("DB_SSLMODE", "disable"),
	}
}

func (c Config) Address() string {
	return ":" + c.HTTPPort
}

func (c Config) DSN() string {
	return fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=%s",
		c.DBUser,
		c.DBPassword,
		c.DBHost,
		c.DBPort,
		c.DBName,
		c.DBSSLMode,
	)
}

func getEnv(name, fallback string) string {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	return value
}
