import type { ProductStats } from "../types/domain";
import { mockGetProductStats } from "../mocks/server";
import { apiRequest, USE_MOCK_API } from "./client";


export async function getProductStats(productId: string) {
  if (USE_MOCK_API) {
    return mockGetProductStats(productId);
  }
  return apiRequest<ProductStats>(`/products/${productId}/stats`);
}
