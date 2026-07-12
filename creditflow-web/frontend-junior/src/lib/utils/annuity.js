export function calcAnnuity(amount, annualRate, months) {
  const a = Number(amount);
  const rate = Number(annualRate);
  const n = Number(months);
  if (!a || !n || a <= 0 || n <= 0) return null;

  const r = rate / 100 / 12;
  if (r === 0) return a / n;

  const factor = Math.pow(1 + r, n);
  return (a * r * factor) / (factor - 1);
}
