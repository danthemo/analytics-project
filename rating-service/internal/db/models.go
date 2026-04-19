package db

import "time"

type Product struct {
	ID          int64     `gorm:"primaryKey"`
	Name        string    `gorm:"size:255;not null"`
	Category    string    `gorm:"size:100;not null"`
	Brand       string    `gorm:"size:100;not null"`
	Description string    `gorm:"type:text"`
	CreatedAt   time.Time `gorm:"not null;default:CURRENT_TIMESTAMP"`
	UpdatedAt   time.Time `gorm:"not null;default:CURRENT_TIMESTAMP"`
}

func (Product) TableName() string {
	return "products"
}

type Review struct {
	ID             int64     `gorm:"primaryKey"`
	ProductID      int64     `gorm:"not null;index"`
	AuthorName     string    `gorm:"size:255;not null"`
	ReviewText     string    `gorm:"type:text;not null"`
	ReviewDate     time.Time `gorm:"type:date;not null"`
	SourceName     string    `gorm:"size:100;not null"`
	RatingOriginal *float64  `gorm:"type:numeric(3,1)"`
	Status         string    `gorm:"size:20;not null;default:new;index"`
	CreatedAt      time.Time `gorm:"not null;default:CURRENT_TIMESTAMP"`
	Product        Product   `gorm:"foreignKey:ProductID;constraint:OnDelete:CASCADE"`
}

func (Review) TableName() string {
	return "reviews"
}

type AnalysisResult struct {
	ID             int64     `gorm:"primaryKey"`
	ReviewID       int64     `gorm:"uniqueIndex;not null"`
	SentimentClass string    `gorm:"size:20;not null;index"`
	ProcessedAt    time.Time `gorm:"not null;default:CURRENT_TIMESTAMP"`
	Review         Review    `gorm:"foreignKey:ReviewID;constraint:OnDelete:CASCADE"`
}

func (AnalysisResult) TableName() string {
	return "analysis_results"
}

type ProductRating struct {
	ID           int64     `gorm:"primaryKey"`
	ProductID    int64     `gorm:"uniqueIndex;not null"`
	ReviewsCount int       `gorm:"not null"`
	AvgScore     float64   `gorm:"type:numeric(4,2);not null"`
	Rating10     float64   `gorm:"column:rating10;type:numeric(4,2);not null;index"`
	UpdatedAt    time.Time `gorm:"not null;default:CURRENT_TIMESTAMP"`
	Product      Product   `gorm:"foreignKey:ProductID;constraint:OnDelete:CASCADE"`
}

func (ProductRating) TableName() string {
	return "product_ratings"
}

type ProductSummary struct {
	ID          int64     `gorm:"primaryKey"`
	ProductID   int64     `gorm:"uniqueIndex;not null"`
	SummaryText string    `gorm:"type:text;not null"`
	ProsText    string    `gorm:"type:text;not null"`
	ConsText    string    `gorm:"type:text;not null"`
	UpdatedAt   time.Time `gorm:"not null;default:CURRENT_TIMESTAMP"`
	Product     Product   `gorm:"foreignKey:ProductID;constraint:OnDelete:CASCADE"`
}

func (ProductSummary) TableName() string {
	return "product_summaries"
}
