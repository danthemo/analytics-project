import type {
  AnalyzeProductPayload,
  MarketplaceName,
  MarketplaceStats,
  Product,
  ProductStats,
  Review,
} from "../types/domain";


const PRODUCT_SEEDS = [
  {
    id: "1",
    name: "Игровой руль Logitech G29",
    rating: 4.32,
    reviewsCount: 1240,
    status: "completed",
    lastAnalyzedAt: "2026-05-20T12:00:00Z",
    sentiment: {
      positive: 820,
      neutral: 260,
      negative: 160,
    },
    marketplaces: [
      { marketplace: "Wildberries", reviewsCount: 420, rating: 4.25, positive: 280, neutral: 90, negative: 50 },
      { marketplace: "Ozon", reviewsCount: 510, rating: 4.41, positive: 338, neutral: 101, negative: 71 },
      { marketplace: "Яндекс Маркет", reviewsCount: 310, rating: 4.29, positive: 202, neutral: 69, negative: 39 },
    ] satisfies MarketplaceStats[],
  },
  {
    id: "2",
    name: "Пылесос Dreame V11",
    rating: 4.48,
    reviewsCount: 860,
    status: "completed",
    lastAnalyzedAt: "2026-05-19T18:35:00Z",
    sentiment: {
      positive: 594,
      neutral: 171,
      negative: 95,
    },
    marketplaces: [
      { marketplace: "Wildberries", reviewsCount: 280, rating: 4.35, positive: 188, neutral: 57, negative: 35 },
      { marketplace: "Ozon", reviewsCount: 355, rating: 4.57, positive: 254, neutral: 63, negative: 38 },
      { marketplace: "Яндекс Маркет", reviewsCount: 225, rating: 4.51, positive: 152, neutral: 51, negative: 22 },
    ] satisfies MarketplaceStats[],
  },
  {
    id: "3",
    name: "Наушники Sony WH-1000XM5",
    rating: 4.61,
    reviewsCount: 632,
    status: "completed",
    lastAnalyzedAt: "2026-05-18T10:20:00Z",
    sentiment: {
      positive: 462,
      neutral: 108,
      negative: 62,
    },
    marketplaces: [
      { marketplace: "Wildberries", reviewsCount: 204, rating: 4.54, positive: 145, neutral: 36, negative: 23 },
      { marketplace: "Ozon", reviewsCount: 250, rating: 4.67, positive: 188, neutral: 37, negative: 25 },
      { marketplace: "Яндекс Маркет", reviewsCount: 178, rating: 4.60, positive: 129, neutral: 35, negative: 14 },
    ] satisfies MarketplaceStats[],
  },
] as const;

const reviewTemplates = {
  positive: [
    "Хороший товар, качество понравилось.",
    "Удобно пользоваться, ожидания оправдал.",
    "Сборка аккуратная, работает стабильно.",
    "Покупкой доволен, рекомендую.",
  ],
  neutral: [
    "В целом нормально, но без вау-эффекта.",
    "Есть мелкие недостатки, но пользоваться можно.",
    "Обычный вариант за свои деньги.",
  ],
  negative: [
    "Ожидал большего, качество среднее.",
    "Есть проблемы с удобством использования.",
    "Не все работает так, как хотелось бы.",
  ],
} as const;

const marketplaceReviewPhrases: Record<MarketplaceName, string> = {
  Ozon: "Покупал на Ozon.",
  Wildberries: "Брал на Wildberries.",
  "Яндекс Маркет": "Заказывал через Яндекс Маркет.",
};

let productsStore: Product[] = PRODUCT_SEEDS.map((product) => ({
  id: product.id,
  name: product.name,
  rating: product.rating,
  reviewsCount: product.reviewsCount,
  status: product.status,
  lastAnalyzedAt: product.lastAnalyzedAt,
  sentiment: { ...product.sentiment },
}));

let productStatsStore: Record<string, ProductStats> = Object.fromEntries(
  PRODUCT_SEEDS.map((product) => {
    const percentages = toPercentages(product.sentiment);
    return [
      product.id,
      {
        productId: product.id,
        rating: product.rating,
        reviewsCount: product.reviewsCount,
        sentiment: { ...product.sentiment },
        sentimentPercentages: percentages,
        marketplaces: product.marketplaces.map((marketplace) => ({ ...marketplace })),
      },
    ];
  }),
);

let reviewsStore: Record<string, Review[]> = Object.fromEntries(
  PRODUCT_SEEDS.map((product) => [product.id, buildReviews(product.id, product.marketplaces)]),
);

function buildReviews(productId: string, marketplaces: MarketplaceStats[]) {
  const reviews: Review[] = [];
  marketplaces.forEach((marketplaceStats) => {
    const baseDate = new Date("2026-05-20T09:00:00Z");
    const samples = [
      ...repeatReviews("positive", Math.max(4, Math.round(marketplaceStats.positive / 80))),
      ...repeatReviews("neutral", Math.max(2, Math.round(marketplaceStats.neutral / 70))),
      ...repeatReviews("negative", Math.max(2, Math.round(marketplaceStats.negative / 60))),
    ];

    samples.forEach((sentiment, index) => {
      const textPool = reviewTemplates[sentiment];
      const phrase = textPool[index % textPool.length];
      const createdAt = new Date(baseDate.getTime() - (index + Number(productId)) * 86_400_000);
      reviews.push({
        id: `${productId}-${marketplaceStats.marketplace}-${index}`.replace(/ /g, "_"),
        marketplace: marketplaceStats.marketplace,
        text: `${phrase} ${marketplaceReviewPhrases[marketplaceStats.marketplace]}`,
        sentiment,
        confidence: sentiment === "neutral" ? 0.74 : sentiment === "positive" ? 0.91 : 0.83,
        createdAt: createdAt.toISOString(),
      });
    });
  });
  return reviews;
}

function repeatReviews(
  sentiment: "positive" | "neutral" | "negative",
  count: number,
) {
  return Array.from({ length: count }, () => sentiment);
}

function toPercentages(sentiment: Product["sentiment"]) {
  const total = sentiment.positive + sentiment.neutral + sentiment.negative || 1;
  return {
    positive: (sentiment.positive / total) * 100,
    neutral: (sentiment.neutral / total) * 100,
    negative: (sentiment.negative / total) * 100,
  };
}

function createGeneratedProduct(payload: AnalyzeProductPayload) {
  const id = String(productsStore.length + 1);
  const seed = payload.name.length;
  const wildberries = {
    marketplace: "Wildberries" as const,
    reviewsCount: 260 + seed * 3,
    rating: 4.05 + (seed % 6) * 0.08,
    positive: 170 + seed * 2,
    neutral: 58 + (seed % 8),
    negative: 32 + (seed % 6),
  };
  const ozon = {
    marketplace: "Ozon" as const,
    reviewsCount: 310 + seed * 2,
    rating: 4.14 + (seed % 5) * 0.09,
    positive: 214 + seed * 2,
    neutral: 67 + (seed % 5),
    negative: 29 + (seed % 7),
  };
  const yandex = {
    marketplace: "Яндекс Маркет" as const,
    reviewsCount: 190 + seed,
    rating: 4.11 + (seed % 7) * 0.07,
    positive: 128 + seed,
    neutral: 41 + (seed % 4),
    negative: 21 + (seed % 4),
  };

  const marketplaces = [wildberries, ozon, yandex];
  const sentiment = marketplaces.reduce(
    (acc, item) => ({
      positive: acc.positive + item.positive,
      neutral: acc.neutral + item.neutral,
      negative: acc.negative + item.negative,
    }),
    { positive: 0, neutral: 0, negative: 0 },
  );

  const reviewsCount = marketplaces.reduce((sum, item) => sum + item.reviewsCount, 0);
  const rating =
    marketplaces.reduce((sum, item) => sum + item.rating * item.reviewsCount, 0) / reviewsCount;
  const lastAnalyzedAt = new Date().toISOString();

  const product: Product = {
    id,
    name: payload.name,
    rating,
    reviewsCount,
    status: "completed",
    lastAnalyzedAt,
    sentiment,
  };

  const stats: ProductStats = {
    productId: id,
    rating,
    reviewsCount,
    sentiment,
    sentimentPercentages: toPercentages(sentiment),
    marketplaces,
  };

  const reviews = buildReviews(id, marketplaces);
  return { product, stats, reviews };
}

export async function getMockProducts() {
  return structuredClone(productsStore);
}

export async function getMockProduct(productId: string) {
  const product = productsStore.find((item) => item.id === productId);
  if (!product) {
    throw new Error("Товар не найден");
  }
  return structuredClone(product);
}

export async function getMockProductStats(productId: string) {
  const stats = productStatsStore[productId];
  if (!stats) {
    throw new Error("Статистика не найдена");
  }
  return structuredClone(stats);
}

export async function getMockProductReviews(productId: string) {
  const reviews = reviewsStore[productId];
  if (!reviews) {
    throw new Error("Отзывы не найдены");
  }
  return structuredClone(reviews);
}

export async function analyzeMockProduct(payload: AnalyzeProductPayload) {
  const generated = createGeneratedProduct(payload);
  productsStore = [generated.product, ...productsStore];
  productStatsStore = {
    ...productStatsStore,
    [generated.product.id]: generated.stats,
  };
  reviewsStore = {
    ...reviewsStore,
    [generated.product.id]: generated.reviews,
  };
  return structuredClone(generated.product);
}

export async function refreshMockProduct(productId: string) {
  const product = productsStore.find((item) => item.id === productId);
  const stats = productStatsStore[productId];
  if (!product || !stats) {
    throw new Error("Товар не найден");
  }

  product.lastAnalyzedAt = new Date().toISOString();
  product.rating = Number((product.rating + 0.01).toFixed(2));
  stats.rating = product.rating;

  productsStore = productsStore.map((item) => (item.id === productId ? { ...product } : item));
  productStatsStore = {
    ...productStatsStore,
    [productId]: structuredClone(stats),
  };

  return structuredClone(product);
}

export async function deleteMockProduct(productId: string) {
  const product = productsStore.find((item) => item.id === productId);
  if (!product) {
    throw new Error("Товар не найден");
  }

  productsStore = productsStore.filter((item) => item.id !== productId);
  const { [productId]: _removedStats, ...nextStats } = productStatsStore;
  const { [productId]: _removedReviews, ...nextReviews } = reviewsStore;
  productStatsStore = nextStats;
  reviewsStore = nextReviews;
}
