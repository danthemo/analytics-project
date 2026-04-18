package db

import (
	"context"
	"errors"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
	"gorm.io/gorm/logger"

	"rating-service/internal/config"
	"rating-service/internal/domain"
)

type Store struct {
	DB *gorm.DB
}

type SentimentTotals struct {
	Positive float64
	Neutral  float64
	Negative float64
	Total    float64
}

func Open(cfg config.Config) (*Store, error) {
	gormDB, err := gorm.Open(postgres.Open(cfg.DSN()), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
	if err != nil {
		return nil, err
	}

	sqlDB, err := gormDB.DB()
	if err != nil {
		return nil, err
	}

	sqlDB.SetMaxOpenConns(10)
	sqlDB.SetMaxIdleConns(5)
	sqlDB.SetConnMaxLifetime(30 * time.Minute)
	sqlDB.SetConnMaxIdleTime(5 * time.Minute)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := sqlDB.PingContext(ctx); err != nil {
		return nil, err
	}

	store := &Store{DB: gormDB}
	if err := store.AutoMigrate(ctx); err != nil {
		return nil, err
	}

	return store, nil
}

func (s *Store) Close() error {
	sqlDB, err := s.DB.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

func (s *Store) AutoMigrate(ctx context.Context) error {
	return s.DB.WithContext(ctx).AutoMigrate(
		&Product{},
		&Review{},
		&AnalysisResult{},
		&ProductRating{},
		&ProductSummary{},
	)
}

func (s *Store) GetProductByID(ctx context.Context, productID int64) (Product, error) {
	var product Product
	err := s.DB.WithContext(ctx).First(&product, productID).Error
	return product, err
}

func (s *Store) GetReviewByID(ctx context.Context, reviewID int64) (Review, error) {
	var review Review
	err := s.DB.WithContext(ctx).First(&review, reviewID).Error
	return review, err
}

func (s *Store) UpsertAnalysisResult(ctx context.Context, reviewID int64, sentimentClass string) error {
	return s.DB.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		result := AnalysisResult{
			ReviewID:       reviewID,
			SentimentClass: sentimentClass,
			ProcessedAt:    time.Now().UTC(),
		}

		if err := tx.Clauses(clause.OnConflict{
			Columns:   []clause.Column{{Name: "review_id"}},
			DoUpdates: clause.AssignmentColumns([]string{"sentiment_class", "processed_at"}),
		}).Create(&result).Error; err != nil {
			return err
		}

		return tx.Model(&Review{}).
			Where("id = ?", reviewID).
			Update("status", "processed").Error
	})
}

func (s *Store) GetProductAnalyses(ctx context.Context, productID int64) ([]domain.ReviewAnalysis, error) {
	type row struct {
		ReviewID       int64
		ReviewText     string
		SentimentClass string
	}

	var rows []row
	err := s.DB.WithContext(ctx).
		Table("reviews").
		Select("reviews.id AS review_id, reviews.review_text, analysis_results.sentiment_class").
		Joins("JOIN analysis_results ON analysis_results.review_id = reviews.id").
		Where("reviews.product_id = ?", productID).
		Order("reviews.review_date DESC, reviews.id DESC").
		Scan(&rows).Error
	if err != nil {
		return nil, err
	}

	reviews := make([]domain.ReviewAnalysis, 0, len(rows))
	for _, item := range rows {
		reviews = append(reviews, domain.ReviewAnalysis{
			ReviewID:       item.ReviewID,
			ReviewText:     item.ReviewText,
			SentimentClass: item.SentimentClass,
		})
	}

	return reviews, nil
}

func (s *Store) ListProductIDsWithAnalysis(ctx context.Context) ([]int64, error) {
	var productIDs []int64
	err := s.DB.WithContext(ctx).
		Table("reviews").
		Distinct("reviews.product_id").
		Joins("JOIN analysis_results ON analysis_results.review_id = reviews.id").
		Order("reviews.product_id").
		Pluck("reviews.product_id", &productIDs).Error
	return productIDs, err
}

func (s *Store) CountSentimentsByProduct(ctx context.Context, productID int64) (int, int, int, error) {
	type row struct {
		Positive int
		Neutral  int
		Negative int
	}

	var result row
	err := s.DB.WithContext(ctx).
		Table("analysis_results").
		Select(`
			SUM(CASE WHEN analysis_results.sentiment_class = 'positive' THEN 1 ELSE 0 END) AS positive,
			SUM(CASE WHEN analysis_results.sentiment_class = 'neutral' THEN 1 ELSE 0 END) AS neutral,
			SUM(CASE WHEN analysis_results.sentiment_class = 'negative' THEN 1 ELSE 0 END) AS negative
		`).
		Joins("JOIN reviews ON reviews.id = analysis_results.review_id").
		Where("reviews.product_id = ?", productID).
		Scan(&result).Error
	return result.Positive, result.Neutral, result.Negative, err
}

func (s *Store) GetGlobalSentimentTotals(ctx context.Context) (SentimentTotals, error) {
	type row struct {
		Positive float64
		Neutral  float64
		Negative float64
		Total    float64
	}

	var result row
	err := s.DB.WithContext(ctx).
		Model(&AnalysisResult{}).
		Select(`
			SUM(CASE WHEN sentiment_class = 'positive' THEN 1 ELSE 0 END) AS positive,
			SUM(CASE WHEN sentiment_class = 'neutral' THEN 1 ELSE 0 END) AS neutral,
			SUM(CASE WHEN sentiment_class = 'negative' THEN 1 ELSE 0 END) AS negative,
			COUNT(*) AS total
		`).
		Scan(&result).Error
	if err != nil {
		return SentimentTotals{}, err
	}

	return SentimentTotals(result), nil
}

func (s *Store) GetAverageAnalyzedReviewsPerProduct(ctx context.Context) (float64, error) {
	subquery := s.DB.WithContext(ctx).
		Table("reviews").
		Select("reviews.product_id, COUNT(*) AS reviews_count").
		Joins("JOIN analysis_results ON analysis_results.review_id = reviews.id").
		Group("reviews.product_id")

	type row struct {
		Value *float64
	}

	var result row
	err := s.DB.WithContext(ctx).
		Table("(?) AS product_counts", subquery).
		Select("AVG(reviews_count) AS value").
		Scan(&result).Error
	if err != nil {
		return 0, err
	}
	if result.Value == nil {
		return 0, nil
	}
	return *result.Value, nil
}

func (s *Store) SaveProductArtifacts(ctx context.Context, response domain.ProductRatingResponse) error {
	return s.DB.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		rating := ProductRating{
			ProductID:    response.ProductID,
			ReviewsCount: response.ReviewsCount,
			AvgScore:     response.AvgScore,
			Rating10:     response.Rating10,
			UpdatedAt:    time.Now().UTC(),
		}

		if err := tx.Clauses(clause.OnConflict{
			Columns:   []clause.Column{{Name: "product_id"}},
			DoUpdates: clause.AssignmentColumns([]string{"reviews_count", "avg_score", "rating_10", "updated_at"}),
		}).Create(&rating).Error; err != nil {
			return err
		}

		summary := ProductSummary{
			ProductID:   response.ProductID,
			SummaryText: response.SummaryText,
			ProsText:    response.ProsText,
			ConsText:    response.ConsText,
			UpdatedAt:   time.Now().UTC(),
		}

		return tx.Clauses(clause.OnConflict{
			Columns:   []clause.Column{{Name: "product_id"}},
			DoUpdates: clause.AssignmentColumns([]string{"summary_text", "pros_text", "cons_text", "updated_at"}),
		}).Create(&summary).Error
	})
}

func (s *Store) GetProductRating(ctx context.Context, productID int64) (ProductRating, error) {
	var rating ProductRating
	err := s.DB.WithContext(ctx).
		Where("product_id = ?", productID).
		First(&rating).Error
	return rating, err
}

func (s *Store) GetProductSummary(ctx context.Context, productID int64) (ProductSummary, error) {
	var summary ProductSummary
	err := s.DB.WithContext(ctx).
		Where("product_id = ?", productID).
		First(&summary).Error
	return summary, err
}

func IsNotFound(err error) bool {
	return errors.Is(err, gorm.ErrRecordNotFound)
}
