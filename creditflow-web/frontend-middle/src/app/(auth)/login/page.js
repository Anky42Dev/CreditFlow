import LoginForm from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-center text-2xl font-bold text-gray-900 dark:text-gray-100">
        Вход
      </h1>
      <LoginForm />
    </div>
  );
}
