export type AnalysisStatus = "pending" | "in_progress" | "completed" | "failed";

export type SentimentLabel = "positive" | "neutral" | "negative";

export type MarketplaceName = "Ozon" | "Wildberries" | "Яндекс Маркет";

export type SentimentTotals = {
  positive: number;
  neutral: number;
  negative: number;
};

export type SentimentPercentages = {
  positive: number;
  neutral: number;
  negative: number;
};

export type Product = {
  id: string;
  name: string;
  rating: number;
  reviewsCount: number;
  status: AnalysisStatus;
  lastAnalyzedAt: string;
  sentiment: SentimentTotals;
};

export type ProductStats = {
  productId: string;
  rating: number;
  reviewsCount: number;
  sentiment: SentimentTotals;
  sentimentPercentages: SentimentPercentages;
  marketplaces: MarketplaceStats[];
};

export type MarketplaceStats = {
  marketplace: MarketplaceName;
  reviewsCount: number;
  rating: number;
  positive: number;
  neutral: number;
  negative: number;
};

export type Review = {
  id: string;
  marketplace: MarketplaceName;
  text: string;
  sentiment: SentimentLabel;
  confidence?: number;
  createdAt?: string;
};

export type AnalyzeProductPayload = {
  name: string;
};

export type ReviewFiltersState = {
  marketplace: string;
  sentiment: string;
  search: string;
};
