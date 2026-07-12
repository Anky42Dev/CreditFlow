import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
        CreditFlow
      </h1>
      <p className="max-w-md text-gray-600 dark:text-gray-400">
        Платформа онлайн-кредитования: подайте заявку и получите решение за
        секунды.
      </p>
      <div className="flex gap-3">
        <Link href="/login">
          <Button variant="primary">Войти</Button>
        </Link>
        <Link href="/register">
          <Button variant="secondary">Регистрация</Button>
        </Link>
      </div>
    </main>
  );
}
