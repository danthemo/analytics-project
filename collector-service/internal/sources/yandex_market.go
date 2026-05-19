package sources

import (
	"context"
	"net/http"

	"collector-service/internal/collector"
)

type YandexMarketCollector struct {
	parser *pythonParserCollector
}

func NewYandexMarketCollector(client *http.Client, parserURL string) *YandexMarketCollector {
	return &YandexMarketCollector{
		parser: newPythonParserCollector("yandex_market", parserURL, client, nil),
	}
}

func (c *YandexMarketCollector) Name() string {
	return c.parser.Name()
}

func (c *YandexMarketCollector) Collect(ctx context.Context, query string) ([]collector.Review, error) {
	return c.parser.Collect(ctx, query)
}
