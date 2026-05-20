import type { AnalyzeProductPayload } from "../types/domain";
import {
  analyzeMockProduct,
  deleteMockProduct,
  getMockProduct,
  getMockProducts,
  getMockProductReviews,
  getMockProductStats,
  refreshMockProduct,
} from "./data";


const DELAY_MS = 600;

function delay<T>(value: T, timeout = DELAY_MS) {
  return new Promise<T>((resolve) => {
    window.setTimeout(() => resolve(value), timeout);
  });
}

export async function mockListProducts() {
  return delay(await getMockProducts());
}

export async function mockGetProduct(productId: string) {
  return delay(await getMockProduct(productId));
}

export async function mockGetProductStats(productId: string) {
  return delay(await getMockProductStats(productId));
}

export async function mockGetProductReviews(productId: string) {
  return delay(await getMockProductReviews(productId));
}

export async function mockAnalyzeProduct(payload: AnalyzeProductPayload) {
  return delay(await analyzeMockProduct(payload), 1400);
}

export async function mockRefreshProduct(productId: string) {
  return delay(await refreshMockProduct(productId), 1200);
}

export async function mockDeleteProduct(productId: string) {
  await delay(null, 700);
  return deleteMockProduct(productId);
}
