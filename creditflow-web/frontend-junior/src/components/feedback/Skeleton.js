export function CardSkeleton() {
  return <div className="animate-pulse rounded-lg bg-gray-200 h-32 dark:bg-gray-700" />;
}

export function ListSkeleton({ count = 6 }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export function RowSkeleton() {
  return <div className="animate-pulse rounded-lg bg-gray-200 h-20 dark:bg-gray-700" />;
}

export function RowListSkeleton({ count = 5 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <RowSkeleton key={i} />
      ))}
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-2xl animate-pulse space-y-4 rounded-lg bg-gray-200 p-6 dark:bg-gray-700">
      <div className="h-6 w-1/2 rounded bg-gray-300 dark:bg-gray-600" />
      <div className="h-4 w-full rounded bg-gray-300 dark:bg-gray-600" />
      <div className="h-4 w-3/4 rounded bg-gray-300 dark:bg-gray-600" />
      <div className="h-24 w-full rounded bg-gray-300 dark:bg-gray-600" />
    </div>
  );
}
