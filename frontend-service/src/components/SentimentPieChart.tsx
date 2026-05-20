import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { SentimentTotals } from "../types/domain";


type SentimentPieChartProps = {
  sentiment: SentimentTotals;
};


const chartDataConfig = [
  { key: "positive", name: "Положительные", color: "#4f7d4f" },
  { key: "neutral", name: "Нейтральные", color: "#d39c45" },
  { key: "negative", name: "Отрицательные", color: "#bf5a52" },
] as const;


export function SentimentPieChart({ sentiment }: SentimentPieChartProps) {
  const data = chartDataConfig.map((item) => ({
    name: item.name,
    value: sentiment[item.key],
    color: item.color,
  }));

  return (
    <section className="card chart-card">
      <div className="chart-card__header">
        <h3 className="card__title">Распределение тональности</h3>
      </div>
      <div className="chart-card__body">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={70} outerRadius={102}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
