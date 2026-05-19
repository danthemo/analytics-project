package collector

import "context"

type Review struct {
	Source     string `json:"source"`
	ProductURL string `json:"product_url"`
	Text       string `json:"text"`
}

type SourceError struct {
	Source string `json:"source"`
	Error  string `json:"error"`
}

type CollectRequest struct {
	Query   string   `json:"query"`
	Sources []string `json:"sources"`
}

type CollectResponse struct {
	Query        string        `json:"query"`
	ReviewsCount int           `json:"reviews_count"`
	Reviews      []Review      `json:"reviews"`
	Errors       []SourceError `json:"errors"`
}

type SourceCollector interface {
	Name() string
	Collect(ctx context.Context, query string) ([]Review, error)
}
