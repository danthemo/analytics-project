package analysis

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

type AnalyzeResponse struct {
	SentimentClass string             `json:"sentiment_class"`
	Confidence     float64            `json:"confidence"`
	Probabilities  map[string]float64 `json:"probabilities"`
}

func New(baseURL string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: 15 * time.Second,
		},
	}
}

func (c *Client) AnalyzeText(ctx context.Context, text string) (AnalyzeResponse, error) {
	requestBody := map[string]string{
		"text": text,
	}

	payload, err := json.Marshal(requestBody)
	if err != nil {
		return AnalyzeResponse{}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/api/v1/analyze", bytes.NewReader(payload))
	if err != nil {
		return AnalyzeResponse{}, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return AnalyzeResponse{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= http.StatusBadRequest {
		return AnalyzeResponse{}, fmt.Errorf("analysis service returned status %d", resp.StatusCode)
	}

	var result AnalyzeResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return AnalyzeResponse{}, err
	}

	return result, nil
}
