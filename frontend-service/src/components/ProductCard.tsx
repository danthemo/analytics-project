import { Link } from "react-router-dom";

import type { Product } from "../types/domain";
import { formatDate } from "../utils/format";
import { RatingBadge } from "./RatingBadge";
import { SentimentSummary } from "./SentimentSummary";
import { StatusBadge } from "./StatusBadge";


type ProductCardProps = {
  product: Product;
};


export function ProductCard({ product }: ProductCardProps) {
  return (
    <article className="card product-card">
      <div className="product-card__header">
        <div>
          <h3 className="card__title">{product.name}</h3>
          <p className="card__muted">Последний анализ: {formatDate(product.lastAnalyzedAt)}</p>
        </div>
        <div className="product-card__aside">
          <RatingBadge rating={product.rating} />
          <StatusBadge status={product.status} />
        </div>
      </div>

      <div className="product-card__meta">
        <div className="product-card__metric">
          <span>Отзывы</span>
          <strong>{product.reviewsCount}</strong>
        </div>
      </div>

      <SentimentSummary sentiment={product.sentiment} compact />

      <div className="product-card__footer">
        <Link to={`/products/${product.id}`} className="button button--primary">
          Открыть
        </Link>
      </div>
    </article>
  );
}
