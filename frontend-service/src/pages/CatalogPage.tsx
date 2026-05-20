import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listProducts } from "../api/products";
import { ProductList } from "../components/ProductList";
import type { Product } from "../types/domain";


export function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    void (async () => {
      try {
        const data = await listProducts();
        if (mounted) {
          setProducts(data);
        }
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : "Не удалось загрузить товары");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="page-stack">
      <section className="page-hero">
        <div>
          <h1 className="page-title">Каталог товаров</h1>
          <p className="page-subtitle">
            Добавляйте товары, запускайте анализ отзывов через API Gateway и просматривайте
            агрегированную статистику по маркетплейсам.
          </p>
        </div>
        <Link to="/products/new" className="button button--primary">
          Добавить товар
        </Link>
      </section>

      {loading ? <div className="card">Загрузка каталога...</div> : null}
      {error ? <div className="alert alert--error">{error}</div> : null}

      {!loading && !error && products.length === 0 ? (
        <section className="empty-state card">
          <h2 className="section-title">Товары пока не добавлены</h2>
          <p className="section-subtitle">
            Начните с добавления одного товара, и backend выполнит сбор отзывов, анализ и расчет
            итогового рейтинга.
          </p>
          <div>
            <Link to="/products/new" className="button button--primary">
              Добавить товар
            </Link>
          </div>
        </section>
      ) : null}

      {!loading && !error && products.length > 0 ? <ProductList products={products} /> : null}
    </div>
  );
}
