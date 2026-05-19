package sources

import (
	"context"
	"net/http"

	"collector-service/internal/collector"
)

type OzonCollector struct {
	parser *pythonParserCollector
}

func NewOzonCollector(client *http.Client, parserURL string) *OzonCollector {
	headless := false

	return &OzonCollector{
		parser: newPythonParserCollector("ozon", parserURL, client, &headless),
	}
}

func (c *OzonCollector) Name() string {
	return c.parser.Name()
}

func (c *OzonCollector) Collect(ctx context.Context, query string) ([]collector.Review, error) {
	return c.parser.Collect(ctx, query)
}
