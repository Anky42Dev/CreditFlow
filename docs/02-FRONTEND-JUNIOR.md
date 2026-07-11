# DOC 2 — Frontend Junior
# CreditFlow — Клиентский веб-интерфейс (ядро)

**Версия:** 1.0
**Уровень:** Junior
**Стек:** Next.js 14+ (App Router), JavaScript, Axios, TanStack Query, React Hook Form + Zod, Tailwind CSS
**Зависит от:** DOC 0 (Master Spec), DOC 1 (Backend Junior API)

---

## Оглавление

1. Скоуп уровня
2. Технологический стек
3. Структура папок
4. Роутинг и Protected Routes
5. API-слой (клиент, интерцепторы, refresh flow)
6. Управление состоянием (Auth Context + React Query)
7. Формы и валидация
8. Постраничная карта (страница → API)
9. Обработка ошибок и Toast
10. Loader / Skeleton, тёмная тема, адаптивность
11. Загрузка изображений
12. Definition of Done + Acceptance Criteria
13. Roadmap реализации

---

## 1. Скоуп уровня

**Что делаем:**
- Регистрация, логин, хранение и обновление JWT.
- Protected routes (личный кабинет только для авторизованных).
- Профиль: просмотр, редактирование, загрузка аватара.
- Каталог продуктов: список + детали.
- Заявки: список, создание, редактирование (DRAFT), отправка, просмотр.
- Обработка 401/403/404/500, Toast-уведомления.
- Loader, Skeleton, тёмная тема, адаптивность.

**Что НЕ делаем (Middle/Senior):**
- Админ-панель, WebSocket, real-time уведомления.
- Infinite scroll, code splitting стратегии, FSD.
- Feature flags, Sentry.

---

## 2. Технологический стек

| Компонент | Выбор | Обоснование |
|---|---|---|
| Framework | Next.js 14 App Router | SSR/CSR гибрид, файловый роутинг, market-standard |
| Язык | JavaScript (ES2022) | По требованию заказчика |
| HTTP | Axios + интерцепторы | Централизованная обработка токенов/ошибок |
| Server state | TanStack Query v5 | Кэш, ре-фетч, инвалидация из коробки |
| Формы | React Hook Form + Zod | Производительные формы + схемная валидация |
| Стили | Tailwind CSS | Быстрая адаптивная вёрстка, тёмная тема |
| Уведомления | react-hot-toast | Toast |
| Иконки | lucide-react | |

> **Важно про App Router + JWT:** аутентификация делается на клиенте (CSR), защищённые страницы рендерятся как client components. Токены хранятся в памяти + refresh в httpOnly-подходе эмулируется через localStorage на Junior (осознанное упрощение; на Senior — httpOnly cookie + silent refresh).

---

## 3. Структура папок

```
creditflow-web/
├── package.json
├── next.config.js
├── tailwind.config.js
├── .env.local                      # NEXT_PUBLIC_API_URL
├── src/
│   ├── app/                        # App Router
│   │   ├── layout.js               # корневой layout (providers)
│   │   ├── page.js                 # лендинг / редирект
│   │   ├── (auth)/                 # группа без сайдбара
│   │   │   ├── login/page.js
│   │   │   └── register/page.js
│   │   ├── (dashboard)/            # группа с сайдбаром (protected)
│   │   │   ├── layout.js           # проверка авторизации
│   │   │   ├── profile/page.js
│   │   │   ├── products/
│   │   │   │   ├── page.js
│   │   │   │   └── [id]/page.js
│   │   │   └── applications/
│   │   │       ├── page.js
│   │   │       ├── new/page.js
│   │   │       └── [id]/page.js
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                     # Button, Input, Card, Badge, Modal
│   │   ├── layout/                 # Sidebar, Header, ThemeToggle
│   │   ├── feedback/               # Loader, Skeleton, EmptyState, ErrorState
│   │   ├── auth/                   # LoginForm, RegisterForm
│   │   ├── profile/                # ProfileForm, AvatarUpload
│   │   ├── products/               # ProductCard, ProductList, ProductFilters
│   │   └── applications/           # ApplicationForm, ApplicationCard, StatusBadge
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.js           # axios instance + интерцепторы
│   │   │   ├── auth.js             # authApi
│   │   │   ├── profile.js
│   │   │   ├── products.js
│   │   │   └── applications.js
│   │   ├── auth/
│   │   │   ├── AuthContext.js
│   │   │   └── tokenStorage.js
│   │   ├── validation/             # zod-схемы
│   │   └── utils/                  # formatMoney, formatDate
│   ├── hooks/
│   │   ├── useAuth.js
│   │   ├── useProducts.js
│   │   ├── useApplications.js
│   │   └── useProfile.js
│   └── providers/
│       ├── QueryProvider.js
│       └── ThemeProvider.js
└── public/
```

---

## 4. Роутинг и Protected Routes

### 4.1 Карта маршрутов

| Путь | Доступ | Описание |
|---|---|---|
| `/` | public | Лендинг / редирект в dashboard если авторизован |
| `/login` | guest-only | Форма входа |
| `/register` | guest-only | Форма регистрации |
| `/profile` | protected | Профиль |
| `/products` | protected | Каталог |
| `/products/[id]` | protected | Детали продукта |
| `/applications` | protected | Список заявок |
| `/applications/new` | protected | Создание заявки |
| `/applications/[id]` | protected | Детали/редактирование |

### 4.2 Защита маршрутов

```javascript
// src/app/(dashboard)/layout.js
"use client";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Sidebar from "@/components/layout/Sidebar";
import { Loader } from "@/components/feedback/Loader";

export default function DashboardLayout({ children }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [user, isLoading, router]);

  if (isLoading) return <Loader fullscreen />;
  if (!user) return null;

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
```

---

## 5. API-слой

### 5.1 Axios instance + интерцепторы (ключевой файл)

```javascript
// src/lib/api/client.js
import axios from "axios";
import { getTokens, setTokens, clearTokens } from "@/lib/auth/tokenStorage";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL + "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// Request: подставляем access token
api.interceptors.request.use((config) => {
  const { access } = getTokens();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

// Response: обрабатываем 401 → refresh → retry
let isRefreshing = false;
let queue = [];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    if (status === 401 && !original._retry) {
      original._retry = true;
      const { refresh } = getTokens();
      if (!refresh) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }
      if (isRefreshing) {
        // ждём завершения текущего refresh
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject, original });
        });
      }
      isRefreshing = true;
      try {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
          { refresh }
        );
        setTokens({ access: data.access, refresh });
        original.headers.Authorization = `Bearer ${data.access}`;
        queue.forEach((p) => {
          p.original.headers.Authorization = `Bearer ${data.access}`;
          p.resolve(api(p.original));
        });
        queue = [];
        return api(original);
      } catch (e) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 5.2 API-модули

```javascript
// src/lib/api/auth.js
import api from "./client";
export const authApi = {
  register: (data) => api.post("/auth/register", data),
  login: (data) => api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
};

// src/lib/api/applications.js
export const applicationsApi = {
  list: (params) => api.get("/credit-applications", { params }),
  get: (id) => api.get(`/credit-applications/${id}`),
  create: (data) => api.post("/credit-applications", data),
  update: (id, data) => api.put(`/credit-applications/${id}`, data),
  remove: (id) => api.delete(`/credit-applications/${id}`),
  submit: (id) => api.post(`/credit-applications/${id}/submit`),
};

// src/lib/api/products.js
export const productsApi = {
  list: (params) => api.get("/credit-products", { params }),
  get: (id) => api.get(`/credit-products/${id}`),
};

// src/lib/api/profile.js
export const profileApi = {
  get: () => api.get("/profile"),
  update: (data) => api.put("/profile", data),
  uploadAvatar: (file) => {
    const fd = new FormData();
    fd.append("avatar", file);
    return api.post("/profile/avatar", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
```

### 5.3 tokenStorage

```javascript
// src/lib/auth/tokenStorage.js
const ACCESS = "cf_access", REFRESH = "cf_refresh";
export const getTokens = () => ({
  access: typeof window !== "undefined" ? localStorage.getItem(ACCESS) : null,
  refresh: typeof window !== "undefined" ? localStorage.getItem(REFRESH) : null,
});
export const setTokens = ({ access, refresh }) => {
  localStorage.setItem(ACCESS, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
};
export const clearTokens = () => {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
};
```

---

## 6. Управление состоянием

### 6.1 AuthContext

```javascript
// src/lib/auth/AuthContext.js
"use client";
import { createContext, useState, useEffect } from "react";
import { authApi } from "@/lib/api/auth";
import { getTokens, setTokens, clearTokens } from "./tokenStorage";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setLoading] = useState(true);

  useEffect(() => {
    const { access } = getTokens();
    if (!access) { setLoading(false); return; }
    authApi.me()
      .then((r) => setUser(r.data))
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await authApi.login({ email, password });
    setTokens({ access: data.access, refresh: data.refresh });
    const me = await authApi.me();
    setUser(me.data);
  };

  const logout = () => { clearTokens(); setUser(null); window.location.href = "/login"; };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

### 6.2 React Query для серверных данных

```javascript
// src/hooks/useApplications.js
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationsApi } from "@/lib/api/applications";

export function useApplications(params) {
  return useQuery({
    queryKey: ["applications", params],
    queryFn: () => applicationsApi.list(params).then((r) => r.data),
  });
}

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => applicationsApi.submit(id).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}
```

**Стратегия кэша (Junior):**
- `staleTime`: 30 сек для списков, 5 мин для продуктов.
- Инвалидация: после create/update/delete/submit заявки → invalidate `["applications"]`.
- После обновления профиля → invalidate `["profile"]`.

---

## 7. Формы и валидация

```javascript
// src/lib/validation/schemas.js
import { z } from "zod";

export const registerSchema = z.object({
  email: z.string().email("Некорректный email"),
  password: z.string().min(8, "Минимум 8 символов")
    .regex(/[a-zA-Z]/, "Должна быть буква"),
});

export const applicationSchema = z.object({
  product: z.number().int().positive(),
  amount: z.coerce.number().positive("Сумма должна быть > 0"),
  term_months: z.coerce.number().int().min(1),
  purpose: z.string().max(255).optional(),
});
```

```javascript
// src/components/auth/RegisterForm.js
"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema } from "@/lib/validation/schemas";
import { authApi } from "@/lib/api/auth";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";

export default function RegisterForm() {
  const router = useRouter();
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } =
    useForm({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (values) => {
    try {
      await authApi.register(values);
      toast.success("Регистрация успешна! Войдите.");
      router.push("/login");
    } catch (e) {
      const code = e.response?.data?.error?.code;
      if (code === "EMAIL_TAKEN") setError("email", { message: "Email уже занят" });
      else toast.error("Ошибка регистрации");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <input {...register("email")} placeholder="Email" />
      {errors.email && <span className="text-red-500">{errors.email.message}</span>}
      <input type="password" {...register("password")} placeholder="Пароль" />
      {errors.password && <span className="text-red-500">{errors.password.message}</span>}
      <button disabled={isSubmitting}>Зарегистрироваться</button>
    </form>
  );
}
```

---

## 8. Постраничная карта (страница → API)

### `/register`
- **API:** `POST /auth/register` — при сабмите.
- **Отправляем:** `{ email, password }`.
- **Приходит:** `{ id, email, role }`.
- **Ошибки:** 400 → показать под полями; 409 EMAIL_TAKEN → ошибка на поле email.
- **Успех:** toast + редирект на `/login`.

### `/login`
- **API:** `POST /auth/login` при сабмите; затем `GET /auth/me`.
- **Отправляем:** `{ email, password }`.
- **Приходит:** `{ access, refresh }`, затем профиль пользователя.
- **Ошибки:** 401 → toast «Неверный email или пароль».
- **Успех:** сохранить токены, редирект на `/products`.

### `/profile`
- **API при загрузке:** `GET /profile`.
- **API при сохранении:** `PUT /profile`.
- **API при загрузке аватара:** `POST /profile/avatar`.
- **Приходит:** объект профиля.
- **Отправляем:** поля профиля / файл.
- **Ошибки:** 400 → под полями; 401 → refresh flow (авто); файл >2МБ → toast.
- **Инвалидация:** после PUT/avatar → invalidate `["profile"]`.

### `/products`
- **API при загрузке:** `GET /credit-products?page=&search=&ordering=`.
- **Приходит:** пагинированный список.
- **Отправляем:** query-параметры фильтров.
- **UI:** ProductCard grid, ProductFilters (поиск, сортировка по ставке), Pagination.
- **Ошибки:** 500 → ErrorState с кнопкой «Повторить».

### `/products/[id]`
- **API:** `GET /credit-products/{id}`.
- **Приходит:** полный продукт.
- **Ошибки:** 404 → «Продукт не найден».
- **CTA:** кнопка «Оформить» → `/applications/new?product={id}`.

### `/applications`
- **API:** `GET /credit-applications?page=&status=&ordering=-created_at`.
- **Приходит:** пагинированный список заявок.
- **UI:** ApplicationCard + StatusBadge + фильтр по статусу.
- **Ошибки:** 401 (авто-refresh), 500 → ErrorState.

### `/applications/new`
- **API при загрузке:** `GET /credit-products` (для выбора продукта, если не передан).
- **API при сабмите:** `POST /credit-applications` → затем опционально `POST /{id}/submit`.
- **Отправляем:** `{ product, amount, term_months, purpose }`.
- **Приходит:** созданная заявка.
- **UI:** live-расчёт примерного платежа (по формуле аннуитета на клиенте).
- **Ошибки:** 400 (сумма вне диапазона) → под полем amount; 404 (продукт).
- **Инвалидация:** invalidate `["applications"]`, редирект на `/applications/{id}`.

### `/applications/[id]`
- **API при загрузке:** `GET /credit-applications/{id}`.
- **API редактирования (DRAFT):** `PUT /credit-applications/{id}`.
- **API отправки:** `POST /credit-applications/{id}/submit`.
- **API удаления (DRAFT):** `DELETE /credit-applications/{id}`.
- **Приходит:** заявка + scoring_result.
- **UI:** если DRAFT — форма редактирования + кнопки «Отправить»/«Удалить»; иначе — read-only + StatusBadge + результат скоринга.
- **Ошибки:** 404 → «Заявка не найдена»; 409 → toast «Действие недоступно в этом статусе».
- **Инвалидация:** после submit/update/delete → invalidate `["applications"]` и `["application", id]`.

---

## 9. Обработка ошибок и Toast

### 9.1 Глобальная стратегия HTTP-статусов

| Статус | Действие на фронте |
|---|---|
| 400 | Показать ошибки валидации под полями формы (из `error.details`) |
| 401 | Автоматический refresh (интерцептор); при неудаче → logout + redirect `/login` |
| 403 | Toast «Недостаточно прав» (на Junior почти не встречается) |
| 404 | Показать EmptyState/ErrorState «Не найдено» на странице |
| 409 | Toast с сообщением из `error.message` |
| 500 | ErrorState «Что-то пошло не так» + кнопка «Повторить» |
| Network | Toast «Нет соединения с сервером» |

### 9.2 Хелпер извлечения ошибки

```javascript
// src/lib/utils/errors.js
export function getApiError(error) {
  const e = error.response?.data?.error;
  return {
    code: e?.code || "UNKNOWN",
    message: e?.message || "Произошла ошибка",
    details: e?.details || {},
    status: error.response?.status,
  };
}
```

---

## 10. Loader / Skeleton, тёмная тема, адаптивность

### 10.1 Skeleton при загрузке списков

```javascript
// src/components/feedback/Skeleton.js
export function CardSkeleton() {
  return <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg h-32" />;
}
export function ListSkeleton({ count = 6 }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => <CardSkeleton key={i} />)}
    </div>
  );
}
```

Использование: пока `isLoading` из React Query → `<ListSkeleton />`, при ошибке → `<ErrorState />`, при пустом → `<EmptyState />`.

### 10.2 Тёмная тема

```javascript
// tailwind.config.js → darkMode: "class"
// ThemeProvider переключает класс на <html>, состояние в React state (не localStorage на Junior)
```
Toggle в Header, иконка солнце/луна.

### 10.3 Адаптивность

- Mobile-first через Tailwind breakpoints (`sm/md/lg`).
- Sidebar → бургер-меню на мобильных.
- Grid продуктов: 1 колонка (mobile) → 2 (tablet) → 3 (desktop).

---

## 11. Загрузка изображений

```javascript
// src/components/profile/AvatarUpload.js
"use client";
import { useState } from "react";
import { profileApi } from "@/lib/api/profile";
import toast from "react-hot-toast";
import { useQueryClient } from "@tanstack/react-query";

export default function AvatarUpload({ current }) {
  const [preview, setPreview] = useState(current);
  const qc = useQueryClient();

  const onChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) return toast.error("Файл больше 2 МБ");
    if (!["image/jpeg", "image/png"].includes(file.type))
      return toast.error("Только JPEG/PNG");
    setPreview(URL.createObjectURL(file));
    try {
      const { data } = await profileApi.uploadAvatar(file);
      qc.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Аватар обновлён");
    } catch {
      toast.error("Ошибка загрузки");
    }
  };

  return (
    <div>
      <img src={preview || "/placeholder.png"} className="w-24 h-24 rounded-full object-cover" />
      <input type="file" accept="image/jpeg,image/png" onChange={onChange} />
    </div>
  );
}
```

---

## 12. Definition of Done + Acceptance Criteria

**Definition of Done:**
- Все страницы из §4.1 реализованы и защищены корректно.
- Axios-интерцептор автоматически обновляет access по refresh.
- Все API из DOC 1 используются (см. §8).
- Формы валидируются через Zod, ошибки бэка мапятся на поля.
- Loader/Skeleton при загрузке, EmptyState/ErrorState для пустых/ошибок.
- Тёмная тема и адаптивность работают.
- Аватар загружается с клиентской валидацией.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|---|---|---|
| AC-1 | Гость | заходит на `/profile` | редирект на `/login` |
| AC-2 | Валидные креды | логин | токены сохранены, редирект в кабинет |
| AC-3 | Истёк access | любой запрос | авто-refresh, запрос повторяется прозрачно |
| AC-4 | Истёк refresh | любой запрос | logout + редирект `/login` |
| AC-5 | Занятый email | регистрация | ошибка на поле email |
| AC-6 | DRAFT-заявка | нажать «Отправить» | статус меняется, список инвалидируется |
| AC-7 | Загрузка списка | ожидание | показывается Skeleton, не пустой экран |
| AC-8 | Файл 3 МБ | загрузка аватара | toast-ошибка, запрос не уходит |

**Что считается ошибкой:** прямые вызовы Axios без интерцептора; хранение user в localStorage вместо контекста; отсутствие обработки 401; «прыгающий» layout без Skeleton; несоответствие полей запроса контракту DOC 1.

---

## 13. Roadmap реализации

```
Этап 1 — Каркас
  1. Next.js проект, Tailwind, providers (Query, Theme, Auth)
  2. UI-kit: Button, Input, Card, Badge, Modal
  3. Layout: (auth) и (dashboard) группы, Sidebar/Header

Этап 2 — API-инфраструктура (зависит от каркаса)
  4. axios client + интерцепторы (request/response, refresh)
  5. tokenStorage, api-модули (auth/profile/products/applications)

Этап 3 — Auth (зависит от API)
  6. AuthContext + useAuth
  7. RegisterForm, LoginForm
  8. Protected layout, guest-only редиректы

Этап 4 — Profile (зависит от Auth)
  9. ProfileForm (GET/PUT)
  10. AvatarUpload

Этап 5 — Products (зависит от Auth)
  11. useProducts, ProductList/Card/Filters
  12. Детальная страница продукта

Этап 6 — Applications (зависит от Products)
  13. useApplications, список + StatusBadge + фильтры
  14. ApplicationForm (create) + live-расчёт платежа
  15. Детальная страница: edit/submit/delete

Этап 7 — Полировка
  16. Skeleton/EmptyState/ErrorState везде
  17. Тёмная тема, адаптивность, проверка AC
```
