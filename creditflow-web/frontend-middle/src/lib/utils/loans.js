export function getNextPayment(loan) {
  if (!loan?.schedule_items) return null;
  return (
    loan.schedule_items.find((item) => item.status === "OVERDUE") ||
    loan.schedule_items.find((item) => item.status === "PENDING") ||
    null
  );
}
