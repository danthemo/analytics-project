import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MarketplaceStats } from "../types/domain";
import { formatRating } from "../utils/format";


type MarketplaceComparisonChartProps = {
  title: string;
  stats: MarketplaceStats[];
  variant: "reviews" | "rating";
};


const barColors = ["#5f7cfa", "#55a3a6", "#f59f53"];

function formatTooltipRating(value: number | string | readonly (number | string)[] | undefined) {
  const rawValue = Array.isArray(value) ? value[0] : value;
  const normalizedValue = typeof rawValue === "number" ? rawValue : Number(rawValue ?? 0);
  return formatRating(normalizedValue);
}


export function MarketplaceComparisonChart({
  title,
  stats,
  variant,
}: MarketplaceComparisonChartProps) {
  const data = stats.map((item) => ({
    marketplace: item.marketplace,
    reviewsCount: item.reviewsCount,
    rating: Number(item.rating.toFixed(2)),
  }));

  return (
    <section className="card chart-card">
      <div className="chart-card__header">
        <h3 className="card__title">{title}</h3>
      </div>
      <div className="chart-card__body">
        <ResponsiveContainer width="100%" height={280}>
          {variant === "reviews" ? (
            <BarChart data={data}>
              <CartesianGrid stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="marketplace" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} />
              <Tooltip />
              <Bar dataKey="reviewsCount" radius={[8, 8, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell key={entry.marketplace} fill={barColors[index % barColors.length]} />
                ))}
              </Bar>
            </BarChart>
          ) : (
            <LineChart data={data}>
              <CartesianGrid stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="marketplace" tickLine={false} axisLine={false} />
              <YAxis domain={[0, 5]} tickLine={false} axisLine={false} />
              <Tooltip formatter={formatTooltipRating} />
              <Line
                type="monotone"
                dataKey="rating"
                stroke="#374151"
                strokeWidth={2}
                dot={{ r: 5, fill: "#374151" }}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </section>
  );
}
