export function formatMoney(value) {
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatRate(value) {
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return `${num.toFixed(2)}%`;
}
