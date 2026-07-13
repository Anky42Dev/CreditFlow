import ProfileForm from "@/widgets/profile-form/ui/ProfileForm";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

export function ProfilePage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Профиль
      </h1>
      <WidgetErrorBoundary name="profile-form">
        <ProfileForm />
      </WidgetErrorBoundary>
    </div>
  );
}
