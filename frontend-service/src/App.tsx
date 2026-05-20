import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";

const CatalogPage = lazy(async () => {
  const module = await import("./pages/CatalogPage");
  return { default: module.CatalogPage };
});

const AddProductPage = lazy(async () => {
  const module = await import("./pages/AddProductPage");
  return { default: module.AddProductPage };
});

const ProductPage = lazy(async () => {
  const module = await import("./pages/ProductPage");
  return { default: module.ProductPage };
});


export default function App() {
  return (
    <Layout>
      <Suspense fallback={<div className="card">Загрузка страницы...</div>}>
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/products" element={<Navigate to="/" replace />} />
          <Route path="/products/new" element={<AddProductPage />} />
          <Route path="/products/:productId" element={<ProductPage />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
