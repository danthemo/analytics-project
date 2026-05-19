package sources

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"collector-service/internal/collector"
)

type pythonParserCollector struct {
	name      string
	parserURL string
	client    *http.Client
	headless  *bool
}

type parserRequest struct {
	Query    string `json:"query"`
	Headless *bool  `json:"headless,omitempty"`
}

type parserResponse struct {
	Product struct {
		URL string `json:"url"`
	} `json:"product"`
	Reviews []struct {
		Text string `json:"text"`
	} `json:"reviews"`
}

func newPythonParserCollector(name, parserURL string, client *http.Client, headless *bool) *pythonParserCollector {
	return &pythonParserCollector{
		name:      name,
		parserURL: parserURL,
		client:    client,
		headless:  headless,
	}
}

func (c *pythonParserCollector) Name() string {
	return c.name
}

func (c *pythonParserCollector) Collect(ctx context.Context, query string) ([]collector.Review, error) {
	payload, err := json.Marshal(parserRequest{
		Query:    query,
		Headless: c.headless,
	})
	if err != nil {
		return nil, fmt.Errorf("marshal parser request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.parserURL, bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("build parser request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request parser: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read parser response: %w", err)
	}

	contentType := resp.Header.Get("Content-Type")
	if strings.Contains(strings.ToLower(contentType), "text/html") {
		return nil, fmt.Errorf("expected JSON, got HTML/anti-bot")
	}

	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		return nil, fmt.Errorf("parser returned status %d: %s", resp.StatusCode, parserErrorMessage(body))
	}

	var parsed parserResponse
	if err := json.Unmarshal(body, &parsed); err != nil {
		return nil, fmt.Errorf("decode parser response: %w", err)
	}

	reviews := make([]collector.Review, 0, len(parsed.Reviews))
	for _, review := range parsed.Reviews {
		reviews = append(reviews, collector.Review{
			Source:     c.name,
			ProductURL: parsed.Product.URL,
			Text:       review.Text,
		})
	}

	return reviews, nil
}

func parserErrorMessage(body []byte) string {
	var payload struct {
		Detail string `json:"detail"`
		Error  string `json:"error"`
	}

	if err := json.Unmarshal(body, &payload); err == nil {
		if payload.Detail != "" {
			return payload.Detail
		}
		if payload.Error != "" {
			return payload.Error
		}
	}

	message := strings.TrimSpace(string(body))
	if message == "" {
		return "empty error body"
	}
	if len(message) > 300 {
		return message[:300]
	}
	return message
}
