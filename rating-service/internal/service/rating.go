package service

import (
	"context"
	"errors"
	"fmt"
	"math"
	"regexp"
	"sort"
	"strings"

	"rating-service/internal/analysis"
	"rating-service/internal/db"
	"rating-service/internal/domain"
)

const (
	positiveWeight = 5.0
	neutralWeight  = 3.0
	negativeWeight = 1.0
)

var (
	ErrProductNotFound   = errors.New("product not found")
	ErrReviewNotFound    = errors.New("review not found")
	ErrNoAnalyzedReviews = errors.New("no analyzed reviews for product")
	tokenRegex           = regexp.MustCompile(`[а-яёa-z0-9]+`)
	russianStopwords     = map[string]struct{}{
		"а": {}, "без": {}, "более": {}, "бы": {}, "был": {}, "была": {}, "были": {}, "в": {}, "вам": {}, "вас": {},
		"весь": {}, "во": {}, "вот": {}, "все": {}, "всего": {}, "вы": {}, "где": {}, "да": {}, "даже": {}, "для": {},
		"до": {}, "его": {}, "ее": {}, "если": {}, "есть": {}, "еще": {}, "же": {}, "за": {}, "здесь": {}, "и": {},
		"из": {}, "или": {}, "им": {}, "их": {}, "к": {}, "как": {}, "какая": {}, "какой": {}, "когда": {}, "ли": {},
		"мне": {}, "можно": {}, "мой": {}, "мы": {}, "на": {}, "над": {}, "не": {}, "него": {}, "нее": {}, "нет": {},
		"но": {}, "ну": {}, "о": {}, "об": {}, "она": {}, "они": {}, "оно": {}, "от": {}, "очень": {}, "по": {},
		"под": {}, "при": {}, "с": {}, "сам": {}, "себя": {}, "сейчас": {}, "так": {}, "также": {}, "там": {}, "те": {},
		"тем": {}, "то": {}, "тоже": {}, "только": {}, "том": {}, "тут": {}, "ты": {}, "у": {}, "уже": {}, "хорошо": {},
		"что": {}, "чтобы": {}, "эта": {}, "это": {}, "этот": {}, "я": {},
	}
)

type ReviewAnalysisResponse struct {
	ReviewID         int64              `json:"review_id"`
	ReviewText       string             `json:"review_text"`
	SentimentClass   string             `json:"sentiment_class"`
	Confidence       float64            `json:"confidence"`
	Probabilities    map[string]float64 `json:"probabilities"`
	StoredInDatabase bool               `json:"stored_in_database"`
}

type RatingService struct {
	store          *db.Store
	analysisClient *analysis.Client
}

func New(store *db.Store, analysisClient *analysis.Client) *RatingService {
	return &RatingService{
		store:          store,
		analysisClient: analysisClient,
	}
}

func (s *RatingService) AnalyzeReview(ctx context.Context, reviewID int64) (ReviewAnalysisResponse, error) {
	review, err := s.store.GetReviewByID(ctx, reviewID)
	if db.IsNotFound(err) {
		return ReviewAnalysisResponse{}, ErrReviewNotFound
	}
	if err != nil {
		return ReviewAnalysisResponse{}, err
	}

	prediction, err := s.analysisClient.AnalyzeText(ctx, review.ReviewText)
	if err != nil {
		return ReviewAnalysisResponse{}, err
	}

	if err := s.store.UpsertAnalysisResult(ctx, reviewID, prediction.SentimentClass); err != nil {
		return ReviewAnalysisResponse{}, err
	}

	return ReviewAnalysisResponse{
		ReviewID:         review.ID,
		ReviewText:       review.ReviewText,
		SentimentClass:   prediction.SentimentClass,
		Confidence:       prediction.Confidence,
		Probabilities:    prediction.Probabilities,
		StoredInDatabase: true,
	}, nil
}

func (s *RatingService) RecalculateProduct(ctx context.Context, productID int64) (domain.ProductRatingResponse, error) {
	product, err := s.store.GetProductByID(ctx, productID)
	if db.IsNotFound(err) {
		return domain.ProductRatingResponse{}, ErrProductNotFound
	}
	if err != nil {
		return domain.ProductRatingResponse{}, err
	}

	reviews, err := s.store.GetProductAnalyses(ctx, productID)
	if err != nil {
		return domain.ProductRatingResponse{}, err
	}
	if len(reviews) == 0 {
		return domain.ProductRatingResponse{}, ErrNoAnalyzedReviews
	}

	positiveCount, neutralCount, negativeCount := countSentiments(reviews)
	reviewsCount := len(reviews)
	localScore := calculateLocalScore(positiveCount, neutralCount, negativeCount, reviewsCount)

	globalMean, confidence, err := s.fetchGlobalStats(ctx)
	if err != nil {
		return domain.ProductRatingResponse{}, err
	}

	bayesianScore := calculateBayesianRating(localScore, globalMean, confidence, float64(reviewsCount))
	rating10 := convertToTenPointScale(bayesianScore)

	prosKeywords := extractKeywords(filterTextsBySentiment(reviews, "positive"), 5)
	consKeywords := extractKeywords(filterTextsBySentiment(reviews, "negative"), 5)

	response := domain.ProductRatingResponse{
		ProductID:     productID,
		ProductName:   product.Name,
		ReviewsCount:  reviewsCount,
		PositiveCount: positiveCount,
		NeutralCount:  neutralCount,
		NegativeCount: negativeCount,
		LocalScore:    round2(localScore),
		AvgScore:      round2(bayesianScore),
		Rating10:      round2(rating10),
		GlobalMean:    round2(globalMean),
		Confidence:    round2(confidence),
		SummaryText:   buildSummaryText(product.Name, round2(rating10), positiveCount, neutralCount, negativeCount, prosKeywords, consKeywords),
		ProsText:      buildProsText(prosKeywords),
		ConsText:      buildConsText(consKeywords),
	}

	if err := s.store.SaveProductArtifacts(ctx, response); err != nil {
		return domain.ProductRatingResponse{}, err
	}

	return s.GetProductResult(ctx, productID)
}

func (s *RatingService) RecalculateAll(ctx context.Context) ([]domain.ProductRatingResponse, error) {
	productIDs, err := s.store.ListProductIDsWithAnalysis(ctx)
	if err != nil {
		return nil, err
	}

	results := make([]domain.ProductRatingResponse, 0, len(productIDs))
	for _, productID := range productIDs {
		result, err := s.RecalculateProduct(ctx, productID)
		if err != nil {
			return nil, err
		}
		results = append(results, result)
	}

	return results, nil
}

func (s *RatingService) GetProductResult(ctx context.Context, productID int64) (domain.ProductRatingResponse, error) {
	product, err := s.store.GetProductByID(ctx, productID)
	if db.IsNotFound(err) {
		return domain.ProductRatingResponse{}, ErrProductNotFound
	}
	if err != nil {
		return domain.ProductRatingResponse{}, err
	}

	positiveCount, neutralCount, negativeCount, err := s.store.CountSentimentsByProduct(ctx, productID)
	if err != nil {
		return domain.ProductRatingResponse{}, err
	}

	rating, err := s.store.GetProductRating(ctx, productID)
	if err != nil && !db.IsNotFound(err) {
		return domain.ProductRatingResponse{}, err
	}

	summary, err := s.store.GetProductSummary(ctx, productID)
	if err != nil && !db.IsNotFound(err) {
		return domain.ProductRatingResponse{}, err
	}

	globalMean, confidence, err := s.fetchGlobalStats(ctx)
	if err != nil {
		return domain.ProductRatingResponse{}, err
	}

	response := domain.ProductRatingResponse{
		ProductID:      productID,
		ProductName:    product.Name,
		ReviewsCount:   rating.ReviewsCount,
		PositiveCount:  positiveCount,
		NeutralCount:   neutralCount,
		NegativeCount:  negativeCount,
		LocalScore:     round2(calculateLocalScore(positiveCount, neutralCount, negativeCount, rating.ReviewsCount)),
		AvgScore:       round2(rating.AvgScore),
		Rating10:       round2(rating.Rating10),
		GlobalMean:     round2(globalMean),
		Confidence:     round2(confidence),
		SummaryText:    summary.SummaryText,
		ProsText:       summary.ProsText,
		ConsText:       summary.ConsText,
		LastCalculated: rating.UpdatedAt,
	}

	return response, nil
}

func (s *RatingService) fetchGlobalStats(ctx context.Context) (float64, float64, error) {
	totals, err := s.store.GetGlobalSentimentTotals(ctx)
	if err != nil {
		return 0, 0, err
	}

	globalMean := 3.0
	if totals.Total > 0 {
		globalMean = ((totals.Positive * positiveWeight) + (totals.Neutral * neutralWeight) + (totals.Negative * negativeWeight)) / totals.Total
	}

	confidence, err := s.store.GetAverageAnalyzedReviewsPerProduct(ctx)
	if err != nil {
		return 0, 0, err
	}
	if confidence < 1 {
		confidence = 1
	}

	return globalMean, confidence, nil
}

func countSentiments(reviews []domain.ReviewAnalysis) (int, int, int) {
	var positiveCount, neutralCount, negativeCount int
	for _, review := range reviews {
		switch review.SentimentClass {
		case "positive":
			positiveCount++
		case "neutral":
			neutralCount++
		case "negative":
			negativeCount++
		}
	}
	return positiveCount, neutralCount, negativeCount
}

func filterTextsBySentiment(reviews []domain.ReviewAnalysis, sentiment string) []string {
	texts := make([]string, 0)
	for _, review := range reviews {
		if review.SentimentClass == sentiment {
			texts = append(texts, review.ReviewText)
		}
	}
	return texts
}

func calculateLocalScore(positiveCount, neutralCount, negativeCount, total int) float64 {
	if total == 0 {
		return 0
	}
	weightedSum := (float64(positiveCount) * positiveWeight) + (float64(neutralCount) * neutralWeight) + (float64(negativeCount) * negativeWeight)
	return weightedSum / float64(total)
}

func calculateBayesianRating(localScore, globalMean, confidence, totalReviews float64) float64 {
	if totalReviews == 0 {
		return globalMean
	}
	return ((confidence * globalMean) + (totalReviews * localScore)) / (confidence + totalReviews)
}

func convertToTenPointScale(score float64) float64 {
	converted := 1.0 + ((score-1.0)/4.0)*9.0
	if converted < 1 {
		return 1
	}
	if converted > 10 {
		return 10
	}
	return converted
}

func extractKeywords(texts []string, limit int) []string {
	frequencies := make(map[string]int)
	for _, text := range texts {
		normalized := strings.ToLower(text)
		tokens := tokenRegex.FindAllString(normalized, -1)
		for _, token := range tokens {
			if len(token) < 3 {
				continue
			}
			if _, exists := russianStopwords[token]; exists {
				continue
			}
			frequencies[token]++
		}
	}

	type keywordStat struct {
		Token string
		Count int
	}

	keywords := make([]keywordStat, 0, len(frequencies))
	for token, count := range frequencies {
		keywords = append(keywords, keywordStat{Token: token, Count: count})
	}

	sort.Slice(keywords, func(i, j int) bool {
		if keywords[i].Count == keywords[j].Count {
			return keywords[i].Token < keywords[j].Token
		}
		return keywords[i].Count > keywords[j].Count
	})

	top := make([]string, 0, limit)
	for _, keyword := range keywords {
		top = append(top, keyword.Token)
		if len(top) == limit {
			break
		}
	}
	return top
}

func buildSummaryText(productName string, rating10 float64, positiveCount, neutralCount, negativeCount int, prosKeywords, consKeywords []string) string {
	pros := "выраженные преимущества пока не выделяются"
	if len(prosKeywords) > 0 {
		pros = "покупатели чаще всего отмечают " + strings.Join(prosKeywords, ", ")
	}

	cons := "критических замечаний по отзывам немного"
	if len(consKeywords) > 0 {
		cons = "основные замечания связаны с " + strings.Join(consKeywords, ", ")
	}

	return fmt.Sprintf(
		"Товар %q получил итоговую оценку %.2f/10 на основе анализа отзывов. Позитивных отзывов: %d, нейтральных: %d, негативных: %d. По содержанию отзывов %s, а также %s.",
		productName,
		rating10,
		positiveCount,
		neutralCount,
		negativeCount,
		pros,
		cons,
	)
}

func buildProsText(keywords []string) string {
	if len(keywords) == 0 {
		return "Положительные отзывы есть, но устойчивые преимущества по текстам пока не выделяются."
	}
	return "Чаще всего покупатели хвалят: " + strings.Join(keywords, ", ") + "."
}

func buildConsText(keywords []string) string {
	if len(keywords) == 0 {
		return "Существенные повторяющиеся недостатки по отзывам не обнаружены."
	}
	return "Наиболее частые замечания относятся к: " + strings.Join(keywords, ", ") + "."
}

func round2(value float64) float64 {
	return math.Round(value*100) / 100
}
