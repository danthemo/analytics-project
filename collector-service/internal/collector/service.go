package collector

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sort"
	"strings"
	"sync"
	"time"
	"unicode"
)

var ErrEmptyQuery = errors.New("query is required")

var defaultSourceOrder = []string{"wildberries", "ozon", "yandex_market"}

type Service struct {
	sources       map[string]SourceCollector
	defaultOrder  []string
	sourceTimeout time.Duration
	logger        *log.Logger
}

type sourceResult struct {
	name    string
	reviews []Review
	err     error
}

func New(collectors []SourceCollector, sourceTimeout time.Duration, logger *log.Logger) *Service {
	sourceMap := make(map[string]SourceCollector, len(collectors))
	for _, source := range collectors {
		sourceMap[source.Name()] = source
	}

	return &Service{
		sources:       sourceMap,
		defaultOrder:  append([]string(nil), defaultSourceOrder...),
		sourceTimeout: sourceTimeout,
		logger:        logger,
	}
}

func (s *Service) Collect(ctx context.Context, query string, requestedSources []string) (CollectResponse, error) {
	query = strings.TrimSpace(query)
	if query == "" {
		return CollectResponse{}, ErrEmptyQuery
	}

	selectedSources, sourceErrors := s.resolveSources(requestedSources)
	results := make(map[string]sourceResult, len(selectedSources))

	var wg sync.WaitGroup
	resultCh := make(chan sourceResult, len(selectedSources))

	for _, sourceName := range selectedSources {
		source := s.sources[sourceName]
		wg.Add(1)

		go func(name string, collector SourceCollector) {
			defer wg.Done()

			sourceCtx, cancel := context.WithTimeout(ctx, s.sourceTimeout)
			defer cancel()

			s.logger.Printf("source=%s event=start query=%q", name, query)
			reviews, err := collector.Collect(sourceCtx, query)
			if err != nil {
				s.logger.Printf("source=%s event=error query=%q error=%v", name, query, err)
				resultCh <- sourceResult{name: name, err: err}
				return
			}

			s.logger.Printf("source=%s event=collected query=%q reviews=%d", name, query, len(reviews))
			resultCh <- sourceResult{name: name, reviews: reviews}
		}(sourceName, source)
	}

	go func() {
		wg.Wait()
		close(resultCh)
	}()

	for result := range resultCh {
		results[result.name] = result
	}

	merged := make([]Review, 0)
	for _, sourceName := range selectedSources {
		result, ok := results[sourceName]
		if !ok {
			continue
		}
		if result.err != nil {
			sourceErrors = append(sourceErrors, SourceError{
				Source: sourceName,
				Error:  result.err.Error(),
			})
			continue
		}
		merged = append(merged, result.reviews...)
	}

	filtered := filterAndDedupeReviews(merged)
	sort.SliceStable(sourceErrors, func(i, j int) bool {
		return sourceIndex(sourceErrors[i].Source) < sourceIndex(sourceErrors[j].Source)
	})

	return CollectResponse{
		Query:        query,
		ReviewsCount: len(filtered),
		Reviews:      filtered,
		Errors:       sourceErrors,
	}, nil
}

func (s *Service) resolveSources(requestedSources []string) ([]string, []SourceError) {
	if len(requestedSources) == 0 {
		return append([]string(nil), s.defaultOrder...), nil
	}

	seen := make(map[string]struct{}, len(requestedSources))
	selected := make([]string, 0, len(requestedSources))
	errors := make([]SourceError, 0)

	for _, sourceName := range requestedSources {
		normalized := strings.TrimSpace(strings.ToLower(sourceName))
		if normalized == "" {
			continue
		}
		if _, exists := seen[normalized]; exists {
			continue
		}
		seen[normalized] = struct{}{}

		if _, ok := s.sources[normalized]; !ok {
			errors = append(errors, SourceError{
				Source: normalized,
				Error:  fmt.Sprintf("unsupported source: %s", normalized),
			})
			continue
		}

		selected = append(selected, normalized)
	}

	if len(selected) == 0 {
		if len(errors) == 0 {
			return append([]string(nil), s.defaultOrder...), nil
		}
		return nil, errors
	}

	return selected, errors
}

func filterAndDedupeReviews(reviews []Review) []Review {
	filtered := make([]Review, 0, len(reviews))
	seen := make(map[string]struct{}, len(reviews))

	for _, review := range reviews {
		text := sanitizeReviewText(review.Text)
		if !isUsefulReviewText(text) {
			continue
		}

		key := review.Source + "|" + normalizeForDedupe(text)
		if _, exists := seen[key]; exists {
			continue
		}
		seen[key] = struct{}{}

		review.Text = text
		filtered = append(filtered, review)
	}

	return filtered
}

func sanitizeReviewText(text string) string {
	return strings.Join(strings.Fields(strings.TrimSpace(text)), " ")
}

func isUsefulReviewText(text string) bool {
	if utf8Len(text) < 5 {
		return false
	}

	letters := 0
	for _, r := range text {
		if unicode.IsLetter(r) {
			letters++
		}
	}

	return letters >= 3
}

func normalizeForDedupe(text string) string {
	text = strings.ToLower(strings.TrimSpace(text))
	text = strings.ReplaceAll(text, "ё", "е")
	return strings.Join(strings.Fields(text), " ")
}

func utf8Len(value string) int {
	count := 0
	for range value {
		count++
	}
	return count
}

func sourceIndex(source string) int {
	for idx, name := range defaultSourceOrder {
		if name == source {
			return idx
		}
	}
	return len(defaultSourceOrder)
}
