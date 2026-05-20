import type { SentimentPercentages, SentimentTotals } from "../types/domain";
import { formatPercent } from "../utils/format";


type SentimentSummaryProps = {
  sentiment: SentimentTotals;
  percentages?: SentimentPercentages;
  compact?: boolean;
};


const items = [
  { key: "positive", label: "Положительные" },
  { key: "neutral", label: "Нейтральные" },
  { key: "negative", label: "Отрицательные" },
] as const;


export function SentimentSummary({ sentiment, percentages, compact = false }: SentimentSummaryProps) {
  return (
    <div className={`sentiment-summary${compact ? " sentiment-summary--compact" : ""}`}>
      {items.map((item) => (
        <div key={item.key} className="stat-card">
          <span className="stat-card__label">{item.label}</span>
          <strong className="stat-card__value">{sentiment[item.key]}</strong>
          {percentages ? (
            <span className="stat-card__meta">{formatPercent(percentages[item.key])}</span>
          ) : null}
        </div>
      ))}
    </div>
  );
}
