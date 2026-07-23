# DOC 6 — Frontend Senior
# CreditFlow — Production-ready клиент

**Версия:** 1.0
**Уровень:** Senior
**Стек (добавлено):** Feature-Sliced Design, httpOnly-cookie + silent refresh, Sentry-подход, Playwright, Web Vitals, Feature Flags
**Зависит от:** DOC 0, DOC 2, DOC 4 (рефакторит их в FSD), DOC 5 (Backend Senior API)

---

## Оглавление

1. Задача уровня
2. Feature-Sliced Design
3. Безопасность токенов (httpOnly + silent refresh)
4. Оптимизация производительности
5. Продвинутый state management и кэш
6. Feature Flags на фронте
7. Error Boundaries и мониторинг ошибок
8. Наблюдаемость фронта (Web Vitals)
9. Тестирование (unit, integration, E2E)
10. CI/CD фронтенда
11. Финальная API-карта (полное покрытие)
12. Definition of Done + Acceptance Criteria
13. Roadmap реализации

---

## 1. Задача уровня

Превратить приложение Middle в production-ready фронтенд: масштабируемая архитектура (FSD), безопасное хранение токенов, оптимизация производительности, мониторинг ошибок и метрик, полноценные E2E-тесты, feature flags. **Функциональность и API-контракты сохраняются** — меняется организация и качество.

---

## 2. Feature-Sliced Design

### 2.1 Слои FSD

```
app/         → инициализация, провайдеры, роутинг, глобальные стили
processes/   → сложные межстраничные сценарии (напр. оформление кредита)
pages/       → страницы (композиция виджетов)
widgets/     → самостоятельные блоки UI (Sidebar, ApplicationTable, LoanSummary)
features/    → пользовательские действия (submit-application, repay-loan, approve-application)
entities/    → бизнес-сущности (application, loan, product, user, notification)
shared/      → переиспользуемое (ui-kit, api, lib, config)

Правило импортов: слой может импортировать только слои НИЖЕ себя.
```

### 2.2 Структура

```
src/
├── app/
│   ├── providers/           # Query, Auth, WS, Theme, FeatureFlags, ErrorBoundary
│   ├── router/
│   └── styles/
├── pages/
│   ├── loans/
│   ├── applications/
│   ├── admin/
│   └── ...
├── widgets/
│   ├── application-table/
│   ├── loan-summary/
│   ├── notification-bell/
│   └── admin-sidebar/
├── features/
│   ├── submit-application/
│   │   ├── model/           # хуки, логика
│   │   ├── ui/              # компоненты действия
│   │   └── api/
│   ├── repay-loan/
│   ├── approve-application/
│   └── auth-by-credentials/
├── entities/
│   ├── application/
│   │   ├── model/           # типы, селекторы, query-хуки
│   │   ├── ui/              # ApplicationCard, StatusBadge
│   │   └── api/
│   ├── loan/
│   ├── product/
│   ├── user/
│   └── notification/
└── shared/
    ├── ui/                  # Button, Input, Modal, Table (design system)
    ├── api/                 # base client, интерцепторы
    ├── lib/                 # хуки, утилиты
    ├── config/              # env, feature flags config
    └── types/
```

**Почему FSD:** к Senior-уровню кодовая база велика (клиент + админка + кредиты + real-time). FSD даёт явные границы, предотвращает спагетти-импорты, упрощает командную разработку и переиспользование.

---

## 3. Безопасность токенов (httpOnly + silent refresh)

### 3.1 Проблема Junior/Middle

localStorage уязвим к XSS. На Senior переходим на **httpOnly-cookie для refresh** + access в памяти.

### 3.2 Модель

```
Access token   → в памяти (переменная модуля), НЕ в localStorage
Refresh token  → httpOnly + Secure + SameSite=Strict cookie (недоступен JS)

Логин:  POST /auth/login → бэк ставит refresh в httpOnly cookie, возвращает access
Refresh: POST /auth/refresh (cookie отправляется автоматически) → новый access
Silent refresh: по таймеру за ~1 мин до истечения access — фоновое обновление
```

### 3.3 Реализация

```javascript
// shared/api/auth-store.js — access только в памяти
let accessToken = null;
export const setAccess = (t) => { accessToken = t; };
export const getAccess = () => accessToken;
export const clearAccess = () => { accessToken = null; };
```

```javascript
// shared/api/client.js
const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  withCredentials: true,          // отправлять httpOnly cookie
});

api.interceptors.request.use((cfg) => {
  const t = getAccess();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// 401 → refresh (cookie) → retry; очередь параллельных запросов (как в DOC 2, но без localStorage)
```

```javascript
// app/providers/AuthProvider — silent refresh по таймеру
useEffect(() => {
  if (!accessExp) return;
  const ms = accessExp * 1000 - Date.now() - 60_000; // за минуту до истечения
  const id = setTimeout(() => refreshSilently(), Math.max(ms, 0));
  return () => clearTimeout(id);
}, [accessExp]);
```

### 3.4 Защита от XSS/CSRF

- refresh недоступен JS (httpOnly) → XSS не украдёт его.
- `SameSite=Strict` + CSRF-токен для мутаций → защита от CSRF.
- Строгий CSP, экранирование пользовательского ввода, отказ от `dangerouslySetInnerHTML`.

---

## 4. Оптимизация производительности

| Техника | Применение |
|---|---|
| **Мемоизация** | `React.memo` для строк таблиц, `useMemo`/`useCallback` для тяжёлых вычислений и стабильных пропсов |
| **Виртуализация** | `@tanstack/react-virtual` для графиков платежей и больших админ-таблиц |
| **Code splitting** | `dynamic import` по маршрутам + тяжёлые модалки/чарты |
| **Prefetch** | React Query `prefetchQuery` при наведении на строку заявки |
| **Оптимистичные обновления** | отметка прочитанным, лайки статусов |
| **Debounce/throttle** | поисковые поля, фильтры |
| **Изображения** | `next/image` (lazy, оптимизация, WebP) |
| **Bundle analysis** | `@next/bundle-analyzer` в CI, бюджет на размер чанков |
| **Streaming SSR / RSC** | серверные компоненты для статичных частей (каталог продуктов) |

**Целевые Web Vitals:** LCP < 2.5s, CLS < 0.1, INP < 200ms.

---

## 5. Продвинутый state management и кэш

### 5.1 Разделение состояния

```
Server state  → TanStack Query (заявки, кредиты, продукты, уведомления)
Client state  → Zustand (UI: модалки, тема, фильтры-драфты)
URL state     → searchParams (фильтры, пагинация — shareable)
Form state    → React Hook Form
```

### 5.2 Стратегии кэша Query (Senior)

- `staleTime`/`gcTime` подобраны по типу данных (продукты — долго, заявки — коротко).
- **Query key factory** для консистентности ключей:
```javascript
// entities/application/model/keys.js
export const applicationKeys = {
  all: ["applications"],
  lists: () => [...applicationKeys.all, "list"],
  list: (filters) => [...applicationKeys.lists(), filters],
  details: () => [...applicationKeys.all, "detail"],
  detail: (id) => [...applicationKeys.details(), id],
};
```
- **Точечная инвалидация** через фабрику ключей.
- **WS-driven обновления:** событие → `setQueryData` (патч конкретного объекта) вместо полной инвалидации, где возможно.
- **Persisted cache** (опционально) для мгновенного показа при возврате.

---

## 6. Feature Flags на фронте

```javascript
// app/providers/FeatureFlagsProvider.js
// флаги приходят из бэка (GET /feature-flags для текущего юзера) или конфига
const FeatureFlagsContext = createContext({});

export function useFlag(name) {
  return useContext(FeatureFlagsContext)[name] ?? false;
}
```

Использование — постепенный rollout UI:
```javascript
const instantDisbursement = useFlag("instant_disbursement");
{instantDisbursement && <InstantDisburseBanner />}
```

Флаги синхронизированы с бэковыми (DOC 5 §11): один источник истины, фронт лишь читает.

---

## 7. Error Boundaries и мониторинг ошибок

### 7.1 Иерархия Error Boundary

```
RootErrorBoundary        → фатальные ошибки → fallback-страница
  RouteErrorBoundary     → ошибка страницы → локальный fallback + «назад»
    WidgetErrorBoundary  → изолирует падение виджета (остальная страница жива)
```

```javascript
// shared/lib/ErrorBoundary.js
class ErrorBoundary extends React.Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, info) {
    reportError(error, info);   // отправка в Sentry-подобный сервис
  }
  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}
```

### 7.2 Мониторинг (Sentry-подход)

```javascript
// shared/lib/monitoring.js
export function reportError(error, context) {
  Sentry.captureException(error, { extra: context });
}
// перехват необработанных промисов и глобальных ошибок
window.addEventListener("unhandledrejection", (e) => reportError(e.reason));
```

- Source maps загружаются в мониторинг для читаемых стектрейсов.
- Хлебные крошки (навигация, запросы) прикрепляются к ошибке.
- PII не отправляется (скрабинг).

---

## 8. Наблюдаемость фронта (Web Vitals)

```javascript
// app/reportWebVitals.js
import { onCLS, onINP, onLCP } from "web-vitals";
function send(metric) { navigator.sendBeacon("/analytics", JSON.stringify(metric)); }
onCLS(send); onINP(send); onLCP(send);
```

Дашборд производительности (p75 по LCP/INP/CLS), корреляция с релизами. Алерты при регрессии.

---

## 9. Тестирование

| Уровень | Что тестируем | Инструмент |
|---|---|---|
| Unit | утилиты, хуки, селекторы entities | Vitest + Testing Library |
| Component | ui-kit, features (submit, repay) с моками API | Testing Library + MSW |
| Integration | страница + реальный React Query + мок-сервер | MSW |
| E2E | критические пути в браузере | Playwright |
| Visual regression | ключевые экраны | Playwright screenshots |
| A11y | доступность | axe-core |

### 9.1 E2E-сценарии (Playwright)

```
1. Регистрация → логин → оформление заявки → (WS) статус APPROVED → просмотр кредита
2. Погашение: двойной клик → ровно одна транзакция (idempotency)
3. Silent refresh: истечение access не разлогинивает пользователя
4. RBAC: CLIENT не видит /admin, UNDERWRITER одобряет заявку
5. Оффлайн/разрыв WS → реконнект, данные консистентны
```

```javascript
// e2e/application-flow.spec.js
test("client submits and gets approved", async ({ page }) => {
  await login(page, "client@test.com");
  await page.goto("/applications/new");
  await page.fill('[name=amount]', "100000");
  await page.fill('[name=term_months]', "12");
  await page.click("text=Отправить");
  await expect(page.locator(".status-badge")).toHaveText(/APPROVED|SCORING/);
});
```

MSW используется для детерминированных unit/integration; реальный бэк (в compose) — для E2E.

---

## 10. CI/CD фронтенда

```
stage: quality
  - eslint, prettier --check
  - typecheck (jsconfig + JSDoc или миграция на TS — опционально)

stage: test
  - vitest --coverage (порог 70%)
  - playwright test (E2E против compose-стенда)
  - axe a11y checks

stage: build
  - next build
  - bundle-analyzer, проверка бюджета размера

stage: deploy
  - build Docker image / деплой на Vercel/статик + CDN
  - upload source maps в Sentry
  - smoke-тест после деплоя
```

---

## 11. Финальная API-карта (полное покрытие)

Требование DOC 0 §7: **каждый** backend-эндпоинт используется. Итоговое сопоставление:

| Backend endpoint | Frontend-место использования |
|---|---|
| `POST /auth/register` | feature auth, `/register` |
| `POST /auth/login` | feature auth, `/login` |
| `POST /auth/refresh` | shared/api silent refresh + интерцептор |
| `GET /auth/me` | AuthProvider (профиль + permissions + flags) |
| `GET/PUT /profile` | `/profile` |
| `POST /profile/avatar` | feature avatar-upload |
| `GET /credit-products` | `/products`, `/applications/new` |
| `GET /credit-products/{id}` | `/products/[id]` |
| `GET/POST /credit-applications` | `/applications`, feature submit |
| `GET/PUT/DELETE /credit-applications/{id}` | `/applications/[id]` |
| `POST /credit-applications/{id}/submit` | feature submit-application |
| `GET /loans`, `/loans/{id}` | `/loans`, `/loans/[id]` (график платежей и транзакции приходят вложенными в тело `Loan` — `schedule_items`/`transactions` — отдельного `/schedule`-эндпоинта на Senior нет, в отличие от матрицы DOC 0 §7) |
| `POST /loans/{id}/repay` | feature repay-loan |
| `GET /notifications`, `/unread-count` | notification-bell, `/notifications` |
| `POST /notifications/{id}/read`, `/read-all` | feature mark-read |
| `GET/POST/PUT/DELETE /admin/credit-products` | `/admin/products` |
| `GET /admin/applications`, `/{id}` | `/admin/applications` |
| `POST /admin/applications/{id}/approve|reject|request-documents` | feature approve-application |
| `GET /admin/users`, `PATCH /{id}/role` | `/admin/users` |
| `GET /admin/audit-log` | `/admin/audit` |
| `GET /feature-flags` | FeatureFlagsProvider |
| `ws /ws/notifications/` | WebSocketProvider |
| `GET /health/*` | (инфраструктурный, не UI) |

**Обработка ошибок — финальные правила (сквозные):**
- 401 → silent refresh; при неудаче → чистый logout, редирект `/login`.
- 403 → route guard + toast (не показываем недоступные действия заранее).
- 404 → страница/EmptyState «Не найдено».
- 429 → toast с `Retry-After`, блокировка кнопки на время.
- 500/сеть → ErrorBoundary/ErrorState + retry, событие в мониторинг.
- WS-разрыв → экспоненциальный реконнект, индикатор «переподключение». Channel layer (`group_send`) ничего не буферизует и не реплеит: события, отправленные, пока клиент отключён (в т.ч. на время реконнекта), теряются безвозвратно — после каждого успешного (пере)подключения фронт обязан дёргать `GET /notifications` (и при необходимости обновлять статус текущей заявки через `GET /credit-applications/{id}`), а не полагаться на то, что WS дошлёт пропущенное.

---

## 12. Definition of Done + Acceptance Criteria

**DoD:**
- Кодовая база организована по FSD, правило импортов соблюдается (линтер `boundaries`).
- Access в памяти, refresh в httpOnly-cookie, silent refresh работает.
- Web Vitals в целевых порогах; bundle-бюджет соблюдён.
- Error Boundaries на 3 уровнях, ошибки уходят в мониторинг с source maps.
- Feature flags читаются из единого источника с бэком.
- Все эндпоинты из §11 задействованы (покрытие 100%).
- E2E (Playwright) на критических путях зелёные в CI; a11y-проверки проходят.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|---|---|---|
| AC-1 | Импорт из слоя выше | сборка | линтер падает (нарушение FSD) |
| AC-2 | Access истёк | пользователь активен | silent refresh, без разлогина и без мигания |
| AC-3 | XSS-инъекция в поле | — | refresh недоступен (httpOnly), скрипт не исполняется (CSP) |
| AC-4 | Падение виджета | — | остальная страница работает (WidgetErrorBoundary) |
| AC-5 | Ошибка на проде | — | улетает в мониторинг с читаемым стектрейсом |
| AC-6 | Флаг instant_disbursement off | — | соответствующий UI скрыт |
| AC-7 | E2E: полный путь заявки | прогон | проходит стабильно (не флак) |
| AC-8 | Список 60 платежей | рендер | виртуализирован, INP < 200ms |
| AC-9 | 429 от бэка | repay | toast Retry-After, кнопка заблокирована |
| AC-10 | Аудит покрытия API | — | 100% эндпоинтов используются (§11) |

**Что считается ошибкой:** access/refresh в localStorage; нарушение границ FSD; полная инвалидация кэша вместо точечных патчей; отсутствие Error Boundary (белый экран); неиспользуемые бэковые эндпоинты; флаки E2E; отправка PII в мониторинг.

---

## 13. Roadmap реализации

```
Этап 1 — Миграция на FSD
  1. Переразбить код Middle по слоям (shared → entities → features → widgets → pages → app)
  2. Линтер границ (eslint-plugin-boundaries)
  3. Query key factory на entities

Этап 2 — Безопасность токенов
  4. Access в памяти, refresh httpOnly (совместно с Backend Senior)
  5. Silent refresh по таймеру
  6. CSP, CSRF, скрабинг

Этап 3 — Надёжность
  7. Иерархия Error Boundaries
  8. Интеграция мониторинга ошибок + source maps
  9. Web Vitals reporting

Этап 4 — Производительность
  10. Виртуализация, мемоизация, prefetch
  11. Code splitting + bundle budget в CI
  12. next/image, RSC для статики

Этап 5 — Feature flags и кэш
  13. FeatureFlagsProvider (единый источник с бэком)
  14. WS-driven setQueryData, оптимистичные обновления

Этап 6 — Тестирование и CI
  15. Unit/Component (Vitest + MSW)
  16. E2E (Playwright) критические пути
  17. a11y (axe), visual regression
  18. CI-пайплайн, деплой, smoke-тесты
  19. Аудит 100% покрытия API, финальная проверка AC
```
