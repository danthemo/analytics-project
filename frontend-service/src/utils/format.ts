export function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatShortDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
  }).format(new Date(value));
}

export function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

export function formatRating(value: number) {
  return value.toFixed(2);
}
