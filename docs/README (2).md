# CreditFlow — Комплект технической документации

Учебный, но приближенный к реальному рынку комплект ТЗ для одного сквозного проекта — платформы онлайн-кредитования **CreditFlow**. Проект не разбит на три разных задания: это **один продукт**, который последовательно усложняется от Junior к Senior. Каждый следующий уровень расширяет предыдущий, не переписывая его.

## Стек

- **Backend:** Django + DRF (Junior/Middle) → + FastAPI-сервисы, Clean Architecture, брокер (Senior)
- **Frontend:** Next.js (App Router) + JavaScript → Feature-Sliced Design (Senior)
- **Данные:** PostgreSQL, Redis
- **Инфраструктура (растёт по уровням):** Celery, Django Channels (WebSocket), Docker, RabbitMQ/Kafka, S3, Prometheus/OpenTelemetry

## Порядок чтения

| # | Документ | Что внутри |
|---|---|---|
| 0 | `00-MASTER-SPECIFICATION.md` | **Источник истины.** Домен, единая ER-модель, роли, машина состояний заявки, стандарты API, RBAC, матрица Backend↔Frontend |
| 1 | `01-BACKEND-JUNIOR.md` | Ядро: auth (JWT), профиль, продукты, заявки, синхронный скоринг, пагинация/фильтры, Swagger, тесты |
| 2 | `02-FRONTEND-JUNIOR.md` | Клиент: protected routes, axios + refresh flow, формы (RHF+Zod), постраничная API-карта |
| 3 | `03-BACKEND-MIDDLE.md` | RBAC, async-скоринг (Celery), WebSocket, кредиты/график/транзакции, админ-API, кэш, Docker |
| 4 | `04-FRONTEND-MIDDLE.md` | Гейтинг UI по правам, админка, WebSocket, кредиты, real-time уведомления, инвалидация кэша |
| 5 | `05-BACKEND-SENIOR.md` | Clean Architecture + DDD, FastAPI-скоринг, брокер + Saga, S3, безопасность, наблюдаемость, масштабирование |
| 6 | `06-FRONTEND-SENIOR.md` | Feature-Sliced Design, httpOnly-токены + silent refresh, оптимизация, Error Boundaries, Playwright E2E |

**Правило реализации:** backend уровня делается раньше фронта (фронт зависит от готового API-контракта).

## Сквозные принципы

- Единая схема БД: между уровнями она только **расширяется** (новые FK/таблицы), а не переписывается.
- Единый формат ответов и ошибок (`code` / `message` / `details` / `trace_id`), base URL `/api/v1/`.
- Каждый последующий документ — «дельта» поверх предыдущих и ссылается на DOC 0.
- К финальному уровню **каждый** backend-эндпоинт используется фронтендом (проверяется матрицей покрытия).

## Как использовать

Документы можно давать разработчику как реальное ТЗ: в каждом есть скоуп, модели/структура, бизнес-логика с кодом, полный API-справочник, Definition of Done, Acceptance Criteria (Given/When/Then) и пошаговый Roadmap реализации.
