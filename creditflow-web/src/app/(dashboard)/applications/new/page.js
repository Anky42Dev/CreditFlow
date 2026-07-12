import { Suspense } from "react";
import ApplicationForm from "@/components/applications/ApplicationForm";
import { Loader } from "@/components/feedback/Loader";

export default function NewApplicationPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Новая заявка
      </h1>
      <Suspense fallback={<Loader />}>
        <ApplicationForm />
      </Suspense>
    </div>
  );
}
