import type { Review } from "../types/domain";
import { mockGetProductReviews } from "../mocks/server";
import { apiRequest, USE_MOCK_API } from "./client";


export async function getProductReviews(productId: string) {
  if (USE_MOCK_API) {
    return mockGetProductReviews(productId);
  }
  return apiRequest<Review[]>(`/products/${productId}/reviews`);
}
