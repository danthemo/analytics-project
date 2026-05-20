import { useNavigate } from "react-router-dom";

import { analyzeProduct } from "../api/products";
import { AddProductForm } from "../components/AddProductForm";


export function AddProductPage() {
  const navigate = useNavigate();

  const handleSubmit = async (name: string) => {
    const product = await analyzeProduct({ name });
    navigate(`/products/${product.id}`);
  };

  return (
    <div className="page-stack page-stack--narrow">
      <section className="page-hero page-hero--compact">
        <div>
          <h1 className="page-title">Запуск анализа товара</h1>
          <p className="page-subtitle">
            Frontend отправляет только название товара в API Gateway. Дальше backend сам собирает
            отзывы с трех площадок, анализирует их и рассчитывает рейтинг.
          </p>
        </div>
      </section>

      <AddProductForm onSubmit={handleSubmit} />
    </div>
  );
}
