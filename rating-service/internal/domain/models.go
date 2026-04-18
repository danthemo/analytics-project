package domain

import "time"

type ReviewAnalysis struct {
	ReviewID       int64
	ReviewText     string
	SentimentClass string
}

type ProductRatingResponse struct {
	ProductID      int64     `json:"product_id"`
	ProductName    string    `json:"product_name"`
	ReviewsCount   int       `json:"reviews_count"`
	PositiveCount  int       `json:"positive_count"`
	NeutralCount   int       `json:"neutral_count"`
	NegativeCount  int       `json:"negative_count"`
	LocalScore     float64   `json:"local_score"`
	AvgScore       float64   `json:"avg_score"`
	Rating10       float64   `json:"rating_10"`
	GlobalMean     float64   `json:"global_mean"`
	Confidence     float64   `json:"confidence"`
	SummaryText    string    `json:"summary_text"`
	ProsText       string    `json:"pros_text"`
	ConsText       string    `json:"cons_text"`
	LastCalculated time.Time `json:"last_calculated,omitempty"`
}
