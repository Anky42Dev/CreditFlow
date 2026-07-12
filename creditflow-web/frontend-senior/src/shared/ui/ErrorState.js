import { AlertTriangle } from "lucide-react";
import { Button } from "@/shared/ui/Button";

export function ErrorState({
  title = "Что-то пошло не так",
  description,
  onRetry,
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <AlertTriangle size={32} className="text-red-500" />
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{title}</p>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
      )}
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} className="mt-2">
          Повторить
        </Button>
      )}
    </div>
  );
}
