# DOC 4 — Frontend Middle
# CreditFlow — Админка, real-time, кредиты (расширение клиента)

**Версия:** 1.0
**Уровень:** Middle
**Стек (добавлено):** native WebSocket, react-window (виртуализация), dynamic import (code splitting)
**Зависит от:** DOC 0, DOC 2 (Frontend Junior), DOC 3 (Backend Middle API)

---

## Оглавление

1. Дельта поверх Junior
2. Обновлённая структура папок
3. RBAC на фронте (гейтинг UI)
4. Админ-панель (страницы)
5. WebSocket-интеграция
6. Кредиты: договоры, график, погашение
7. Уведомления (in-app + real-time)
8. Сложная фильтрация/сортировка UI
9. Infinite Scroll, Lazy Loading, Code Splitting
10. Кэш-инвалидация (стратегии React Query)
11. Обновлённая постраничная API-карта
12. Definition of Done + Acceptance Criteria
13. Roadmap реализации

---

## 1. Дельта поверх Junior

| Область | Junior | Middle |
|---|---|---|
| Роли на фронте | нет (все CLIENT) | гейтинг UI по правам |
| Админка | нет | продукты, заявки, юзеры, аудит |
| Real-time | нет | WebSocket: статусы, уведомления |
| Кредиты | нет | договоры, график, погашение |
| Уведомления | нет | in-app колокольчик + toast из WS |
| Списки | pagination | + infinite scroll, виртуализация |
| Загрузка кода | всё сразу | code splitting (админка отдельно) |

---

## 2. Обновлённая структура папок

```
src/
├── app/
│   ├── (dashboard)/
│   │   ├── loans/
│   │   │   ├── page.js
│   │   │   └── [id]/page.js
│   │   ├── notifications/page.js
│   │   └── ... (из Junior)
│   └── (admin)/                    # отдельная группа, code-split
│       ├── layout.js               # проверка admin-прав
│       └── admin/
│           ├── products/page.js
│           ├── applications/
│           │   ├── page.js
│           │   └── [id]/page.js
│           ├── users/page.js
│           └── audit/page.js
├── components/
│   ├── admin/                      # AdminTable, RoleSelect, ApproveModal
│   ├── loans/                      # LoanCard, ScheduleTable, RepayModal
│   ├── notifications/              # NotificationBell, NotificationList
│   └── ... (из Junior)
├── lib/
│   ├── api/
│   │   ├── loans.js
│   │   ├── notifications.js
│   │   └── admin.js
│   ├── ws/
│   │   └── WebSocketProvider.js    # подключение, реконнект
│   └── rbac/
│       ├── permissions.js          # PERMISSIONS константы
│       └── Can.js                  # компонент-гейт
├── hooks/
│   ├── useWebSocket.js
│   ├── useLoans.js
│   ├── useNotifications.js
│   ├── useInfiniteApplications.js
│   └── usePermission.js
```

---

## 3. RBAC на фронте (гейтинг UI)

> Фронтовый RBAC — это UX, не безопасность. Реальная защита — на бэке (DOC 3 §5). Фронт лишь скрывает недоступные элементы и предотвращает бессмысленные запросы.

```javascript
// src/lib/rbac/permissions.js
export const PERMISSIONS = {
  PRODUCT_MANAGE: "product.manage",
  APP_VIEW_ALL: "application.view_all",
  APP_APPROVE: "application.approve",
  USER_MANAGE: "user.manage",
  AUDIT_VIEW: "audit.view",
};
```

Бэкенд возвращает права в `GET /auth/me`:
```json
{ "id": 42, "email": "...", "role": "UNDERWRITER",
  "permissions": ["product.view", "application.view_all", "application.approve"] }
```

```javascript
// src/hooks/usePermission.js
import { useAuth } from "./useAuth";
export function usePermission(perm) {
  const { user } = useAuth();
  return user?.permissions?.includes(perm) ?? false;
}
```

```javascript
// src/lib/rbac/Can.js
import { usePermission } from "@/hooks/usePermission";
export function Can({ perm, children, fallback = null }) {
  return usePermission(perm) ? children : fallback;
}
```

Использование:
```javascript
<Can perm={PERMISSIONS.APP_APPROVE}>
  <ApproveButton applicationId={app.id} />
</Can>
```

Пункты меню админки и `/admin/*` роуты защищены аналогично (в `(admin)/layout.js` — редирект, если нет `application.view_all`).

---

## 4. Админ-панель

### 4.1 `/admin/products`
- **API:** `GET/POST/PUT/DELETE /admin/credit-products`.
- **UI:** таблица продуктов (вкл. неактивные), кнопки создать/редактировать/деактивировать, модалка формы.
- **Инвалидация:** после мутации → invalidate `["admin-products"]` и `["products"]` (клиентский каталог).

### 4.2 `/admin/applications`
- **API:** `GET /admin/applications` (фильтры: статус, дата, email, сумма).
- **Очередь MANUAL_REVIEW:** отдельная вкладка с сортировкой по времени ожидания.
- **UI:** AdminTable с серверной пагинацией/фильтрами.

### 4.3 `/admin/applications/[id]`
- **API:** `GET /admin/applications/{id}`; `POST /{id}/approve`; `POST /{id}/reject`; `POST /{id}/request-documents`.
- **UI:** детали заявки, скоринг, документы, кнопки решения (гейт `APP_APPROVE`), модалка с комментарием/причиной.
- **После решения:** invalidate списка + деталей; toast.

### 4.4 `/admin/users`
- **API:** `GET /admin/users`; `PATCH /admin/users/{id}/role`.
- **UI:** таблица пользователей, RoleSelect для смены роли (гейт `USER_MANAGE`), поиск по email.

### 4.5 `/admin/audit`
- **API:** `GET /admin/audit-log` (фильтры: actor, action, тип, даты).
- **UI:** таблица логов, разворачивание `changes` (before/after).

---

## 5. WebSocket-интеграция

### 5.1 Provider с реконнектом

```javascript
// src/lib/ws/WebSocketProvider.js
"use client";
import { createContext, useEffect, useRef, useState } from "react";
import { getTokens } from "@/lib/auth/tokenStorage";
import { useAuth } from "@/hooks/useAuth";

export const WSContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { user } = useAuth();
  const wsRef = useRef(null);
  const [lastEvent, setLastEvent] = useState(null);
  const reconnectRef = useRef(0);

  useEffect(() => {
    if (!user) return;
    let closed = false;

    const connect = () => {
      const { access } = getTokens();
      const url = `${process.env.NEXT_PUBLIC_WS_URL}/ws/notifications/?token=${access}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => { reconnectRef.current = 0; };
      ws.onmessage = (e) => setLastEvent(JSON.parse(e.data));
      ws.onclose = () => {
        if (closed) return;
        // экспоненциальный бэкофф
        const delay = Math.min(1000 * 2 ** reconnectRef.current, 30000);
        reconnectRef.current++;
        setTimeout(connect, delay);
      };
    };

    connect();
    return () => { closed = true; wsRef.current?.close(); };
  }, [user]);

  return <WSContext.Provider value={{ lastEvent }}>{children}</WSContext.Provider>;
}
```

### 5.2 Реакция на события

```javascript
// src/hooks/useWebSocket.js — подписка + маршрутизация событий
import { useContext, useEffect } from "react";
import { WSContext } from "@/lib/ws/WebSocketProvider";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

export function useWSEvents() {
  const { lastEvent } = useContext(WSContext);
  const qc = useQueryClient();

  useEffect(() => {
    if (!lastEvent) return;
    switch (lastEvent.event) {
      case "application_status":
        qc.invalidateQueries({ queryKey: ["applications"] });
        qc.invalidateQueries({ queryKey: ["application", lastEvent.application_id] });
        toast(`Заявка #${lastEvent.application_id}: ${lastEvent.status}`);
        break;
      case "notification":
        qc.invalidateQueries({ queryKey: ["notifications"] });
        qc.invalidateQueries({ queryKey: ["unread-count"] });
        toast(lastEvent.title);
        break;
      case "payment_due":
        toast(`Приближается платёж по кредиту #${lastEvent.loan_id}`);
        break;
    }
  }, [lastEvent, qc]);
}
```

Хук вызывается один раз в `(dashboard)/layout.js`.

---

## 6. Кредиты: договоры, график, погашение

### 6.1 `/loans`
- **API:** `GET /loans` (свои договоры).
- **UI:** LoanCard: остаток, статус (ACTIVE/OVERDUE/CLOSED), ближайший платёж.

### 6.2 `/loans/[id]`
- **API:** `GET /loans/{id}`; `GET /loans/{id}/schedule`; `POST /loans/{id}/repay`.
- **UI:** карточка договора + ScheduleTable (график с подсветкой PAID/PENDING/OVERDUE) + кнопка «Внести платёж».
- **RepayModal:** сумма (по умолчанию = ближайший платёж), генерирует idempotency_key (UUID) на клиенте, отправляет `{ amount, idempotency_key }`.
- **Ошибки:** 409 DUPLICATE → toast «Платёж уже обработан»; 400 → под полем.
- **Инвалидация:** после repay → invalidate `["loan", id]`, `["loans"]`, `["schedule", id]`.

```javascript
// RepayModal — защита от двойного клика через idempotency_key
const idemKey = useRef(crypto.randomUUID());
const repay = useRepay();  // mutation
const onConfirm = () => repay.mutate({ loanId, amount, idempotency_key: idemKey.current });
```

---

## 7. Уведомления (in-app + real-time)

### 7.1 NotificationBell (в Header)
- **API:** `GET /notifications/unread-count` (при загрузке + инвалидация по WS).
- **UI:** колокольчик с бейджем-счётчиком; клик → дропдаун последних уведомлений.

### 7.2 `/notifications`
- **API:** `GET /notifications?is_read=`; `POST /{id}/read`; `POST /read-all`.
- **UI:** список с фильтром прочитано/непрочитано; клик по уведомлению → read + переход к объекту (заявке/кредиту).
- **Real-time:** новое уведомление из WS → инвалидация счётчика и списка + toast.

---

## 8. Сложная фильтрация/сортировка UI

```javascript
// src/components/admin/ApplicationFilters.js
// Синхронизация фильтров с URL query params (shareable/persistent)
"use client";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

export function useUrlFilters() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const setFilter = (key, value) => {
    const next = new URLSearchParams(params);
    value ? next.set(key, value) : next.delete(key);
    next.set("page", "1");   // сброс страницы при смене фильтра
    router.push(`${pathname}?${next.toString()}`);
  };

  return { params, setFilter };
}
```

Фильтры админ-заявок: статус (multi-select), диапазон дат, email (debounced-поиск), диапазон суммы. Все — в URL, чтобы состояние сохранялось при перезагрузке и было shareable.

---

## 9. Infinite Scroll, Lazy Loading, Code Splitting

### 9.1 Infinite Scroll (список уведомлений/заявок)

```javascript
// src/hooks/useInfiniteApplications.js
import { useInfiniteQuery } from "@tanstack/react-query";
import { applicationsApi } from "@/lib/api/applications";

export function useInfiniteApplications(filters) {
  return useInfiniteQuery({
    queryKey: ["applications-infinite", filters],
    queryFn: ({ pageParam = 1 }) =>
      applicationsApi.list({ ...filters, page: pageParam }).then((r) => r.data),
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
    initialPageParam: 1,
  });
}
```

IntersectionObserver на sentinel-элементе → `fetchNextPage()`.

### 9.2 Code Splitting

```javascript
// админ-компоненты грузятся лениво
import dynamic from "next/dynamic";
const AuditTable = dynamic(() => import("@/components/admin/AuditTable"), {
  loading: () => <ListSkeleton />,
  ssr: false,
});
```

Вся `(admin)` группа App Router автоматически code-split по маршрутам. Тяжёлые модалки (approve, repay) — тоже через `dynamic`.

### 9.3 Виртуализация длинных списков

Для графика платежей на 60 месяцев и больших админ-таблиц — `react-window` (рендер только видимых строк).

---

## 10. Кэш-инвалидация (стратегии React Query)

| Действие | Инвалидируемые ключи |
|---|---|
| Создать/обновить заявку | `["applications"]`, `["application", id]` |
| Submit заявки | `["applications"]`, `["application", id]` |
| WS: смена статуса | `["applications"]`, `["application", id]` |
| Approve/Reject (админ) | `["admin-applications"]`, `["admin-application", id]` |
| Погашение | `["loan", id]`, `["loans"]`, `["schedule", id]` |
| Смена роли юзера | `["admin-users"]` + перезапросить `["me"]` если это текущий юзер |
| CRUD продукта (админ) | `["admin-products"]`, `["products"]`, `["product", id]` |
| Read уведомления | `["notifications"]`, `["unread-count"]` |

**Оптимистичные обновления** для быстрых действий (отметка прочитанным): мгновенно меняем кэш, откат при ошибке.

```javascript
useMutation({
  mutationFn: (id) => notificationsApi.read(id),
  onMutate: async (id) => {
    await qc.cancelQueries({ queryKey: ["unread-count"] });
    const prev = qc.getQueryData(["unread-count"]);
    qc.setQueryData(["unread-count"], (n) => Math.max(0, (n ?? 1) - 1));
    return { prev };
  },
  onError: (e, id, ctx) => qc.setQueryData(["unread-count"], ctx.prev),
  onSettled: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
});
```

---

## 11. Обновлённая постраничная API-карта

| Страница | API | Когда | Что приходит | Что отправляем | Ошибки |
|---|---|---|---|---|---|
| `/loans` | `GET /loans` | mount | список договоров | — | 401(auto), 500 |
| `/loans/[id]` | `GET /loans/{id}`, `/schedule` | mount | договор + график | — | 404 |
| `/loans/[id]` repay | `POST /loans/{id}/repay` | клик | транзакция | `{amount, idempotency_key}` | 409 DUP, 400 |
| `/notifications` | `GET /notifications` | mount | список | фильтр is_read | 401 |
| bell | `GET /notifications/unread-count` | mount + WS | счётчик | — | — |
| `/admin/products` | `GET/POST/PUT/DELETE /admin/credit-products` | CRUD | продукты | тело продукта | 403, 400 |
| `/admin/applications` | `GET /admin/applications` | mount/фильтр | заявки | query-фильтры | 403 |
| `/admin/applications/[id]` | `GET`, `approve`, `reject` | mount/клик | заявка+доки | comment/reason | 403, 409 |
| `/admin/users` | `GET /admin/users`, `PATCH role` | mount/смена | юзеры | `{role}` | 403 |
| `/admin/audit` | `GET /admin/audit-log` | mount/фильтр | логи | фильтры | 403 |
| WS | `ws /ws/notifications/?token=` | после логина | события | — | reconnect |

**Обработка WS-разрыва:** экспоненциальный реконнект; при обновлении токена новое подключение использует свежий access.

---

## 12. Definition of Done + Acceptance Criteria

**DoD:**
- RBAC-гейтинг: элементы и роуты скрыты/защищены по правам из `/auth/me`.
- Админка полностью функциональна (продукты, заявки, юзеры, аудит).
- WebSocket подключается после логина, реконнектится, обновляет данные и шлёт toast.
- Кредиты: список, график с подсветкой статусов, идемпотентное погашение.
- Уведомления: колокольчик со счётчиком, real-time обновление, отметка прочитанным (оптимистично).
- Infinite scroll и code splitting работают; админка загружается отдельным чанком.
- Фильтры синхронизированы с URL.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|---|---|---|
| AC-1 | CLIENT | заходит на `/admin/products` | редирект (нет прав) |
| AC-2 | UNDERWRITER | видит заявку MANUAL_REVIEW | доступна кнопка Approve |
| AC-3 | Открыт дашборд | бэк меняет статус заявки | приходит WS-событие, список обновляется, toast |
| AC-4 | WS-соединение оборвано | сеть восстановилась | авто-реконнект с бэкоффом |
| AC-5 | Двойной клик по «Внести платёж» | — | один запрос (idempotency_key), второй не создаёт транзакцию |
| AC-6 | Клиент отметил уведомление | клик | счётчик уменьшается мгновенно (оптимистично) |
| AC-7 | Список из 200 заявок | скролл | подгрузка следующих страниц (infinite) |
| AC-8 | Переход на `/admin/*` | — | грузится отдельный JS-чанк (code split) |

**Что считается ошибкой:** доверие фронтовому RBAC как защите; отсутствие реконнекта WS; погашение без idempotency_key; инвалидация всего кэша вместо точечной; загрузка админки в основной бандл.

---

## 13. Roadmap реализации

```
Этап 1 — RBAC-инфраструктура
  1. Расширить /auth/me обработку (permissions)
  2. usePermission, Can, гейтинг меню/роутов

Этап 2 — WebSocket (зависит от Auth)
  3. WebSocketProvider + реконнект
  4. useWSEvents (маршрутизация событий + инвалидация)

Этап 3 — Кредиты (зависит от Backend Middle)
  5. useLoans, LoanCard, /loans
  6. ScheduleTable, /loans/[id]
  7. RepayModal (idempotency_key)

Этап 4 — Уведомления (зависит от WS)
  8. NotificationBell + счётчик
  9. /notifications + оптимистичная отметка

Этап 5 — Админка (зависит от RBAC, code-split)
  10. (admin) layout + защита
  11. /admin/products (CRUD)
  12. /admin/applications + очередь MANUAL_REVIEW
  13. /admin/applications/[id] (approve/reject)
  14. /admin/users (смена роли)
  15. /admin/audit

Этап 6 — Оптимизация
  16. Infinite scroll, виртуализация
  17. Dynamic import для тяжёлых компонентов
  18. URL-синхронизация фильтров
  19. Проверка AC
```
