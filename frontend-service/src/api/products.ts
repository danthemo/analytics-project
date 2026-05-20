import type { AnalyzeProductPayload, Product } from "../types/domain";
import {
  mockAnalyzeProduct,
  mockDeleteProduct,
  mockGetProduct,
  mockListProducts,
  mockRefreshProduct,
} from "../mocks/server";
import { apiRequest, USE_MOCK_API } from "./client";


export async function listProducts() {
  if (USE_MOCK_API) {
    return mockListProducts();
  }
  return apiRequest<Product[]>("/products");
}

export async function getProduct(productId: string) {
  if (USE_MOCK_API) {
    return mockGetProduct(productId);
  }
  return apiRequest<Product>(`/products/${productId}`);
}

export async function analyzeProduct(payload: AnalyzeProductPayload) {
  if (USE_MOCK_API) {
    return mockAnalyzeProduct(payload);
  }
  return apiRequest<Product>("/products/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function refreshProduct(productId: string) {
  if (USE_MOCK_API) {
    return mockRefreshProduct(productId);
  }
  return apiRequest<Product>(`/products/${productId}/refresh`, {
    method: "POST",
  });
}

export async function deleteProduct(productId: string) {
  if (USE_MOCK_API) {
    return mockDeleteProduct(productId);
  }
  return apiRequest<{ status: string; product_id: number }>(`/products/${productId}`, {
    method: "DELETE",
  });
}
