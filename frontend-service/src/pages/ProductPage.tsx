import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { deleteProduct, getProduct, refreshProduct } from "../api/products";
import { getProductReviews } from "../api/reviews";
import { getProductStats } from "../api/stats";
import { Filters } from "../components/Filters";
import { MarketplaceComparisonChart } from "../components/MarketplaceComparisonChart";
import { RatingBadge } from "../components/RatingBadge";
import { ReviewsTable } from "../components/ReviewsTable";
import { SentimentPieChart } from "../components/SentimentPieChart";
import { SentimentSummary } from "../components/SentimentSummary";
import { StatusBadge } from "../components/StatusBadge";
import type { Product, ProductStats, Review, ReviewFiltersState } from "../types/domain";
import { formatDate, formatPercent } from "../utils/format";


const initialFilters: ReviewFiltersState = {
  marketplace: "",
  sentiment: "",
  search: "",
};


export function ProductPage() {
  const { productId = "" } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [stats, setStats] = useState<ProductStats | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [filters, setFilters] = useState<ReviewFiltersState>(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function loadProductData() {
      setLoading(true);
      setError("");
      try {
        const [productData, statsData, reviewsData] = await Promise.all([
          getProduct(productId),
          getProductStats(productId),
          getProductReviews(productId),
        ]);

        if (!mounted) {
          return;
        }

        setProduct(productData);
        setStats(statsData);
        setReviews(reviewsData);
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : "Не удалось загрузить товар");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void loadProductData();

    return () => {
      mounted = false;
    };
  }, [productId]);

  const filteredReviews = useMemo(() => {
    return reviews.filter((review) => {
      const matchesMarketplace = !filters.marketplace || review.marketplace === filters.marketplace;
      const matchesSentiment = !filters.sentiment || review.sentiment === filters.sentiment;
      const matchesSearch =
        !filters.search ||
        review.text.toLowerCase().includes(filters.search.trim().toLowerCase());
      return matchesMarketplace && matchesSentiment && matchesSearch;
    });
  }, [reviews, filters]);

  const reloadProductData = async () => {
    const [productData, statsData, reviewsData] = await Promise.all([
      getProduct(productId),
      getProductStats(productId),
      getProductReviews(productId),
    ]);
    setProduct(productData);
    setStats(statsData);
    setReviews(reviewsData);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setActionError("");
    setActionMessage("");

    try {
      await refreshProduct(productId);
      await reloadProductData();
      setActionMessage("Статистика и рейтинг пересобраны.");
    } catch (refreshError) {
      setActionError(
        refreshError instanceof Error ? refreshError.message : "Не удалось пересобрать статистику",
      );
    } finally {
      setRefreshing(false);
    }
  };

  const handleDelete = async () => {
    const confirmed = window.confirm(
      "Удалить товар и все связанные отзывы, анализ и рейтинг из базы данных?",
    );
    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setActionError("");
    setActionMessage("");

    try {
      await deleteProduct(productId);
      navigate("/");
    } catch (deleteError) {
      setActionError(
        deleteError instanceof Error ? deleteError.message : "Не удалось удалить товар",
      );
      setDeleting(false);
    }
  };

  if (loading) {
    return <div className="card">Загрузка карточки товара...</div>;
  }

  if (error || !product || !stats) {
    return (
      <div className="page-stack">
        <div className="alert alert--error">{error || "Товар не найден"}</div>
        <Link to="/" className="button button--secondary">
          Вернуться к каталогу
        </Link>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <section className="card product-overview">
        <div className="product-overview__header">
          <div>
            <Link to="/" className="text-link">
              Назад к каталогу
            </Link>
            <h1 className="page-title">{product.name}</h1>
            <p className="page-subtitle">
              Последний анализ: {formatDate(product.lastAnalyzedAt)}
            </p>
          </div>
          <div className="product-overview__badges">
            <RatingBadge rating={product.rating} />
            <StatusBadge status={product.status} />
          </div>
        </div>

        <div className="product-actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={handleRefresh}
            disabled={refreshing || deleting}
          >
            {refreshing ? "Пересбор..." : "Пересобрать статистику"}
          </button>
          <button
            type="button"
            className="button button--danger"
            onClick={handleDelete}
            disabled={refreshing || deleting}
          >
            {deleting ? "Удаление..." : "Удалить товар"}
          </button>
        </div>

        {actionMessage ? <div className="alert alert--info">{actionMessage}</div> : null}
        {actionError ? <div className="alert alert--error">{actionError}</div> : null}

        <div className="overview-grid">
          <div className="stat-card">
            <span className="stat-card__label">Количество отзывов</span>
            <strong className="stat-card__value">{product.reviewsCount}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Положительные</span>
            <strong className="stat-card__value">{stats.sentiment.positive}</strong>
            <span className="stat-card__meta">{formatPercent(stats.sentimentPercentages.positive)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Нейтральные</span>
            <strong className="stat-card__value">{stats.sentiment.neutral}</strong>
            <span className="stat-card__meta">{formatPercent(stats.sentimentPercentages.neutral)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Отрицательные</span>
            <strong className="stat-card__value">{stats.sentiment.negative}</strong>
            <span className="stat-card__meta">{formatPercent(stats.sentimentPercentages.negative)}</span>
          </div>
        </div>
      </section>

      <SentimentSummary sentiment={stats.sentiment} percentages={stats.sentimentPercentages} />

      <div className="charts-grid">
        <SentimentPieChart sentiment={stats.sentiment} />
        <MarketplaceComparisonChart
          title="Количество отзывов по площадкам"
          stats={stats.marketplaces}
          variant="reviews"
        />
        <MarketplaceComparisonChart
          title="Сравнение рейтинга по площадкам"
          stats={stats.marketplaces}
          variant="rating"
        />
      </div>

      <section className="card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Сравнение площадок</h2>
            <p className="section-subtitle">
              Ozon, Wildberries и Яндекс Маркет показаны отдельными строками для демонстрации
              различий в отзывах и рейтинге.
            </p>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="reviews-table">
            <thead>
              <tr>
                <th>Площадка</th>
                <th>Отзывы</th>
                <th>Рейтинг</th>
                <th>Положительные</th>
                <th>Нейтральные</th>
                <th>Отрицательные</th>
              </tr>
            </thead>
            <tbody>
              {stats.marketplaces.map((marketplace) => {
                const total = marketplace.positive + marketplace.neutral + marketplace.negative || 1;
                return (
                  <tr key={marketplace.marketplace}>
                    <td>{marketplace.marketplace}</td>
                    <td>{marketplace.reviewsCount}</td>
                    <td>{marketplace.rating.toFixed(2)}</td>
                    <td>
                      {marketplace.positive} ({formatPercent((marketplace.positive / total) * 100)})
                    </td>
                    <td>
                      {marketplace.neutral} ({formatPercent((marketplace.neutral / total) * 100)})
                    </td>
                    <td>
                      {marketplace.negative} ({formatPercent((marketplace.negative / total) * 100)})
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Отзывы</h2>
            <p className="section-subtitle">
              Фильтруйте отзывы по площадке, тональности и тексту, не обращаясь напрямую к
              парсерам или сервисам анализа.
            </p>
          </div>
        </div>

        <Filters
          filters={filters}
          marketplaces={stats.marketplaces.map((marketplace) => marketplace.marketplace)}
          onChange={setFilters}
        />
        <ReviewsTable reviews={filteredReviews} />
      </section>
    </div>
  );
}
