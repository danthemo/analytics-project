package sources

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"

	"collector-service/internal/collector"
)

const (
	wildberriesSearchBaseURL   = "https://u-search.wb.ru/exactmatch/ru/common/v18/search"
	wildberriesFeedbackBaseURL = "https://feedbacks1.wb.ru/feedbacks/v2/"
)

type WildberriesCollector struct {
	client *http.Client
}

type wildberriesProduct struct {
	ID   int64  `json:"id"`
	Root int64  `json:"root"`
	Name string `json:"name"`
}

type wildberriesSearchResponse struct {
	Data struct {
		Products []wildberriesProduct `json:"products"`
	} `json:"data"`
	Products []wildberriesProduct `json:"products"`
}

type wildberriesFeedback struct {
	Text string `json:"text"`
}

type wildberriesFeedbackResponse struct {
	Data struct {
		Feedbacks []wildberriesFeedback `json:"feedbacks"`
	} `json:"data"`
	Feedbacks []wildberriesFeedback `json:"feedbacks"`
}

func NewWildberriesCollector(client *http.Client) *WildberriesCollector {
	return &WildberriesCollector{client: client}
}

func (c *WildberriesCollector) Name() string {
	return "wildberries"
}

func (c *WildberriesCollector) Collect(ctx context.Context, query string) ([]collector.Review, error) {
	product, err := c.findFirstProduct(ctx, query)
	if err != nil {
		return nil, err
	}

	if product.Root == 0 {
		return nil, fmt.Errorf("wildberries product root is missing")
	}

	feedbacks, err := c.fetchFeedbacks(ctx, product.Root)
	if err != nil {
		return nil, err
	}

	productURL := fmt.Sprintf("https://www.wildberries.ru/catalog/%d/detail.aspx", product.ID)
	reviews := make([]collector.Review, 0, len(feedbacks))
	for _, feedback := range feedbacks {
		reviews = append(reviews, collector.Review{
			Source:     c.Name(),
			ProductURL: productURL,
			Text:       feedback.Text,
		})
	}

	return reviews, nil
}

func (c *WildberriesCollector) findFirstProduct(ctx context.Context, query string) (wildberriesProduct, error) {
	searchURL, err := buildWildberriesSearchURL(query)
	if err != nil {
		return wildberriesProduct{}, fmt.Errorf("build wildberries search url: %w", err)
	}

	body, _, err := c.getJSON(ctx, searchURL)
	if err != nil {
		return wildberriesProduct{}, err
	}

	var parsed wildberriesSearchResponse
	if err := json.Unmarshal(body, &parsed); err != nil {
		return wildberriesProduct{}, fmt.Errorf("decode wildberries search response: %w", err)
	}

	products := parsed.Data.Products
	if len(products) == 0 {
		products = parsed.Products
	}
	if len(products) == 0 {
		return wildberriesProduct{}, fmt.Errorf("wildberries returned no products")
	}

	return products[0], nil
}

func (c *WildberriesCollector) fetchFeedbacks(ctx context.Context, root int64) ([]wildberriesFeedback, error) {
	feedbackURL := wildberriesFeedbackBaseURL + strconv.FormatInt(root, 10)
	body, _, err := c.getJSON(ctx, feedbackURL)
	if err != nil {
		return nil, err
	}

	var parsed wildberriesFeedbackResponse
	if err := json.Unmarshal(body, &parsed); err != nil {
		return nil, fmt.Errorf("decode wildberries feedback response: %w", err)
	}

	feedbacks := parsed.Data.Feedbacks
	if len(feedbacks) == 0 {
		feedbacks = parsed.Feedbacks
	}

	return feedbacks, nil
}

func (c *WildberriesCollector) getJSON(ctx context.Context, targetURL string) ([]byte, string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, targetURL, nil)
	if err != nil {
		return nil, "", fmt.Errorf("build wildberries request: %w", err)
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "application/json, text/plain, */*")
	req.Header.Set("Accept-Language", "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7")
	req.Header.Set("Referer", "https://www.wildberries.ru/")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, "", fmt.Errorf("request wildberries: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, "", fmt.Errorf("read wildberries response: %w", err)
	}

	contentType := strings.ToLower(resp.Header.Get("Content-Type"))
	if strings.Contains(contentType, "text/html") {
		return nil, contentType, fmt.Errorf("expected JSON, got HTML/anti-bot")
	}
	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		return nil, contentType, fmt.Errorf("wildberries returned status %d", resp.StatusCode)
	}
	if !json.Valid(body) {
		return nil, contentType, fmt.Errorf("expected JSON, got %s", contentType)
	}

	return body, contentType, nil
}

func buildWildberriesSearchURL(query string) (string, error) {
	values := url.Values{}
	values.Set("ab_testid", "catboost_exp_2")
	values.Set("appType", "1")
	values.Set("curr", "rub")
	values.Set("dest", "1259570983")
	values.Set("hide_vflags", "4294967296")
	values.Set("inheritFilters", "false")
	values.Set("lang", "ru")
	values.Set("locale", "ru")
	values.Set("resultset", "catalog")
	values.Set("sort", "popular")
	values.Set("spp", "30")
	values.Set("suppressSpellcheck", "false")
	values.Set("query", query)

	searchURL, err := url.Parse(wildberriesSearchBaseURL)
	if err != nil {
		return "", err
	}

	searchURL.RawQuery = values.Encode()
	return searchURL.String(), nil
}
