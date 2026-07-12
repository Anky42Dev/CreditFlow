import RegisterForm from "@/components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-center text-2xl font-bold text-gray-900 dark:text-gray-100">
        Регистрация
      </h1>
      <RegisterForm />
    </div>
  );
}
