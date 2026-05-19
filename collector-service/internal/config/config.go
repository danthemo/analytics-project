package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	AppName               string
	ServerPort            string
	OzonParserURL         string
	YandexMarketParserURL string
	SourceTimeout         time.Duration
}

func Load() Config {
	timeoutSeconds := getEnvInt("SOURCE_TIMEOUT_SECONDS", 60)
	if timeoutSeconds <= 0 {
		timeoutSeconds = 60
	}

	return Config{
		AppName:               getEnv("APP_NAME", "collector-service"),
		ServerPort:            getEnv("SERVER_PORT", "8080"),
		OzonParserURL:         getEnv("OZON_PARSER_URL", "http://localhost:8001/parse/ozon"),
		YandexMarketParserURL: getEnv("YANDEX_MARKET_PARSER_URL", "http://localhost:8002/parse/yandex-market"),
		SourceTimeout:         time.Duration(timeoutSeconds) * time.Second,
	}
}

func (c Config) Address() string {
	return ":" + c.ServerPort
}

func getEnv(name, fallback string) string {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	return value
}

func getEnvInt(name string, fallback int) int {
	raw := os.Getenv(name)
	if raw == "" {
		return fallback
	}

	value, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}

	return value
}
