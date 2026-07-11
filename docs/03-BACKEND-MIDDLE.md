# DOC 3 — Backend Middle
# CreditFlow — Обработка, роли, real-time (расширение ядра)

**Версия:** 1.0
**Уровень:** Middle
**Стек (добавлено):** Redis, Celery, Django Channels (WebSocket), django-redis, Docker, Docker Compose
**Зависит от:** DOC 0, DOC 1 (расширяет ту же схему БД)

---

## Оглавление

1. Дельта поверх Junior
2. Расширенная архитектура
3. Новые модели (RBAC, Loan, Transaction, Notification, Audit)
4. Обновлённая ER-диаграмма
5. RBAC (роли, права, матрица)
6. Асинхронный скоринг (Celery)
7. WebSocket (Channels)
8. Кэширование (Redis)
9. Кредитные договоры, графики, транзакции
10. Админ-панель API
11. Уведомления и Email
12. Cron / периодические задачи
13. Сложная фильтрация и оптимизация запросов
14. Audit Log
15. Docker + docker-compose
16. CI/CD (описание)
17. Тестирование (integration, E2E)
18. Definition of Done + Acceptance Criteria
19. Roadmap реализации

---

## 1. Дельта поверх Junior

Middle **не переписывает** Junior. Он добавляет слои поверх той же схемы. Ключевые изменения:

| Область | Junior | Middle |
|---|---|---|
| Скоринг | синхронный, в запросе | асинхронный через Celery |
| Доступ | owner-based | полноценный RBAC |
| Real-time | нет | WebSocket (статусы, уведомления) |
| Кредит после одобрения | нет | Loan + PaymentSchedule + Transaction |
| Админка | нет | API управления продуктами/юзерами |
| Кэш | нет | Redis (продукты, агрегаты) |
| Уведомления | нет | in-app + email |
| Аудит | нет | Audit Log |
| Инфраструктура | локально | Docker Compose |

Машина состояний расширяется: добавляются `MANUAL_REVIEW` и `DISBURSED` (см. DOC 0 §3.3).

---

## 2. Расширенная архитектура

Модульный монолит + асинхронные воркеры + real-time слой.

```
                         ┌─────────────────────────┐
        HTTP/REST ──────▶│   Django + DRF (ASGI)    │
        WebSocket ──────▶│   + Channels             │
                         └───────┬─────────────────┘
                                 │
              ┌──────────────────┼───────────────────┐
              ▼                  ▼                   ▼
      ┌──────────────┐   ┌──────────────┐    ┌──────────────┐
      │  PostgreSQL  │   │    Redis     │    │  Channels    │
      │  (основные   │   │ (cache +     │    │  Layer       │
      │   данные)    │   │  Celery      │    │ (Redis)      │
      │              │   │  broker +    │    │              │
      │              │   │  result)     │    │              │
      └──────────────┘   └──────┬───────┘    └──────────────┘
                                │
                         ┌──────▼───────┐
                         │ Celery Worker│
                         │ - скоринг    │
                         │ - email      │
                         │ - генерация  │
                         │   графика    │
                         └──────────────┘
                                │
                         ┌──────▼───────┐
                         │ Celery Beat  │
                         │ (cron задачи)│
                         └──────────────┘
```

**Почему модульный монолит, а не микросервисы:** на Middle команда небольшая, единая БД упрощает транзакционную целостность (критично для финансов). Разделение на сервисы — задел на Senior (там выделим скоринг в FastAPI).

---

## 3. Новые модели

### 3.1 RBAC: Role, Permission, UserRole

Django имеет встроенные группы/права, но для явной доменной RBAC-модели вводим свои таблицы (реалистично для банковских систем, где нужен аудит прав).

**Role**

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | PK | |
| `code` | CharField(20) | unique (CLIENT, SUPPORT, UNDERWRITER, ADMIN) |
| `name` | CharField(50) | |
| `description` | TextField | blank |

**Permission**

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | PK | |
| `code` | CharField(60) | unique (напр. `application.approve`) |
| `description` | TextField | blank |

**RolePermission** (M2M): `role_id`, `permission_id` (unique together).

> `User.role` (CharField из Junior) остаётся как быстрый денормализованный указатель основной роли; таблицы Role/Permission дают детальные права. Синхронизация — через сервис `assign_role`.

### 3.2 Loan (кредитный договор)

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | PK | | |
| `application_id` | OneToOne(CreditApplication) | on_delete=PROTECT | Источник |
| `user_id` | FK(User) | indexed | Заёмщик |
| `principal` | Decimal(12,2) | >0 | Тело кредита |
| `interest_rate` | Decimal(5,2) | | Ставка (копия из продукта) |
| `term_months` | PositiveSmallInt | | Срок |
| `monthly_payment` | Decimal(12,2) | | Аннуитет |
| `outstanding_balance` | Decimal(12,2) | | Остаток долга |
| `status` | CharField(20) | choices, indexed | ACTIVE / CLOSED / OVERDUE |
| `disbursed_at` | DateTimeField | | Дата выдачи |
| `closed_at` | DateTimeField | null | Дата закрытия |

### 3.3 PaymentScheduleItem (график платежей)

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | PK | |
| `loan_id` | FK(Loan) | indexed, on_delete=CASCADE |
| `sequence` | PositiveSmallInt | № платежа |
| `due_date` | DateField | indexed |
| `amount` | Decimal(12,2) | плановая сумма |
| `principal_part` | Decimal(12,2) | часть тела |
| `interest_part` | Decimal(12,2) | часть процентов |
| `status` | CharField(20) | PENDING / PAID / OVERDUE, indexed |
| `paid_at` | DateTimeField | null |

Ограничение: `unique_together (loan, sequence)`.

### 3.4 Transaction

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | PK | |
| `loan_id` | FK(Loan) | indexed |
| `type` | CharField(20) | DISBURSEMENT / REPAYMENT / INTEREST_ACCRUAL |
| `amount` | Decimal(12,2) | |
| `balance_after` | Decimal(12,2) | остаток после операции |
| `created_at` | DateTimeField | auto_now_add, indexed |
| `idempotency_key` | CharField(64) | unique, null | защита от двойного погашения |

### 3.5 Notification

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | PK | |
| `user_id` | FK(User) | indexed |
| `type` | CharField(40) | APPLICATION_APPROVED, PAYMENT_DUE, ... |
| `title` | CharField(120) | |
| `body` | TextField | |
| `is_read` | BooleanField | default=False, indexed |
| `created_at` | DateTimeField | auto_now_add, indexed |

### 3.6 Document (документы к заявке)

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | PK | |
| `application_id` | FK(CreditApplication) | indexed |
| `file` | FileField | upload_to='documents/' |
| `doc_type` | CharField(40) | INCOME_PROOF, ID_CARD, ... |
| `uploaded_at` | DateTimeField | auto_now_add |

### 3.7 AuditLog

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | PK | |
| `actor_id` | FK(User) | null, indexed |
| `action` | CharField(60) | indexed (напр. `application.approved`) |
| `object_type` | CharField(40) | |
| `object_id` | BigInt | |
| `changes` | JSONField | before/after |
| `ip_address` | GenericIPAddress | null |
| `created_at` | DateTimeField | auto_now_add, indexed |

---

## 4. Обновлённая ER-диаграмма

```
User (1)──(1) Profile
User (*)──(*) Role ──(via UserRole)
Role (*)──(*) Permission ──(via RolePermission)

User (1)──(*) CreditApplication (*)──(1) CreditProduct
CreditApplication (1)──(0..1) ScoringResult
CreditApplication (1)──(*) Document
CreditApplication (1)──(0..1) Loan

Loan (1)──(*) PaymentScheduleItem
Loan (1)──(*) Transaction

User (1)──(*) Notification
User (1)──(*) AuditLog   [as actor]
```

---

## 5. RBAC

### 5.1 Проверка прав

```python
# common/permissions.py
from rest_framework.permissions import BasePermission

class HasPermission(BasePermission):
    required_permission = None
    def has_permission(self, request, view):
        perm = getattr(view, "required_permission", None)
        if perm is None:
            return request.user.is_authenticated
        return request.user.is_authenticated and \
               user_has_permission(request.user, perm)

def user_has_permission(user, perm_code) -> bool:
    # кэшируем набор прав пользователя в Redis на 5 минут
    cache_key = f"user_perms:{user.id}"
    perms = cache.get(cache_key)
    if perms is None:
        perms = set(Permission.objects.filter(
            rolepermission__role__userrole__user=user
        ).values_list("code", flat=True))
        cache.set(cache_key, perms, 300)
    return perm_code in perms
```

### 5.2 Матрица прав (коды permission)

| Permission code | CLIENT | SUPPORT | UNDERWRITER | ADMIN |
|---|:---:|:---:|:---:|:---:|
| `product.view` | ✅ | ✅ | ✅ | ✅ |
| `product.manage` | | | | ✅ |
| `application.view_own` | ✅ | | | ✅ |
| `application.view_all` | | ✅ | ✅ | ✅ |
| `application.approve` | | | ✅ | ✅ |
| `application.reject` | | | ✅ | ✅ |
| `loan.view_own` | ✅ | | | ✅ |
| `user.manage` | | | | ✅ |
| `audit.view` | | | | ✅ |

Инвалидация кэша прав: при `assign_role`/`revoke_role` → `cache.delete(f"user_perms:{user_id}")`.

---

## 6. Асинхронный скоринг (Celery)

### 6.1 Задача

```python
# apps/applications/tasks.py
from celery import shared_task
from django.db import transaction

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def score_application(self, application_id):
    from .services import perform_scoring
    try:
        with transaction.atomic():
            perform_scoring(application_id)
    except Exception as exc:
        raise self.retry(exc=exc)
```

### 6.2 Обновлённый submit (async)

```python
def submit_application(application):
    if application.status != "DRAFT":
        raise ConflictError("INVALID_STATE", "Only DRAFT can be submitted")
    validate_amount_and_term(application)
    application.monthly_payment = calc_annuity(...)
    application.status = "SUBMITTED"
    application.submitted_at = timezone.now()
    application.save()
    # ставим в очередь, отвечаем клиенту сразу
    score_application.delay(application.id)
    return application  # статус SUBMITTED, клиент увидит SCORING через WS
```

### 6.3 perform_scoring с MANUAL_REVIEW

```python
def perform_scoring(application_id):
    app = CreditApplication.objects.select_related("user__profile").get(id=application_id)
    app.status = "SCORING"; app.save(update_fields=["status"])
    push_status(app)  # WebSocket

    score = compute_score(app)
    if score >= 700:
        decision = "APPROVED"
    elif score >= 500:
        decision = "MANUAL_REVIEW"   # в очередь андеррайтеру
    else:
        decision = "REJECTED"

    ScoringResult.objects.create(application=app, score=score, decision=decision)
    app.status = decision
    app.save(update_fields=["status"])
    push_status(app)  # WebSocket

    if decision == "APPROVED":
        from apps.lending.services import disburse_loan
        disburse_loan(app)
    notify_user(app.user, f"application.{decision.lower()}", app)
```

---

## 7. WebSocket (Django Channels)

### 7.1 Consumer

```python
# apps/realtime/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close(code=4001)
            return
        self.group = f"user_{user.id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    # событие из бэкенда
    async def notify(self, event):
        await self.send_json(event["payload"])
```

### 7.2 Аутентификация WS через JWT

```python
# apps/realtime/middleware.py — JWTAuthMiddleware
# токен передаётся как query-параметр ?token=<access> при подключении
```

### 7.3 Push из бизнес-логики

```python
# apps/realtime/push.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def push_status(application):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        f"user_{application.user_id}",
        {"type": "notify", "payload": {
            "event": "application_status",
            "application_id": application.id,
            "status": application.status,
        }}
    )
```

**WS-эндпоинт:** `ws://host/ws/notifications/?token=<access>`.

События, приходящие клиенту:
- `application_status` — смена статуса заявки.
- `notification` — новое in-app уведомление.
- `payment_due` — приближается срок платежа.

---

## 8. Кэширование (Redis)

```python
# config/settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
    }
}
```

**Стратегия кэша:**

| Данные | Ключ | TTL | Инвалидация |
|---|---|---|---|
| Список активных продуктов | `products:active` | 10 мин | при create/update/delete продукта |
| Детали продукта | `product:{id}` | 10 мин | при update продукта |
| Права пользователя | `user_perms:{id}` | 5 мин | при смене роли |
| Счётчик непрочитанных уведомлений | `unread:{user_id}` | до изменения | при read/новом уведомлении |

```python
def get_active_products():
    key = "products:active"
    data = cache.get(key)
    if data is None:
        data = list(CreditProduct.objects.filter(is_active=True).values())
        cache.set(key, data, 600)
    return data
```

---

## 9. Кредитные договоры, графики, транзакции

### 9.1 Выдача кредита

```python
# apps/lending/services.py
from dateutil.relativedelta import relativedelta

@transaction.atomic
def disburse_loan(application):
    p = application.product
    loan = Loan.objects.create(
        application=application, user=application.user,
        principal=application.amount, interest_rate=p.interest_rate,
        term_months=application.term_months,
        monthly_payment=application.monthly_payment,
        outstanding_balance=application.amount,
        status="ACTIVE", disbursed_at=timezone.now(),
    )
    build_payment_schedule(loan)
    Transaction.objects.create(
        loan=loan, type="DISBURSEMENT",
        amount=loan.principal, balance_after=loan.principal,
    )
    application.status = "DISBURSED"
    application.save(update_fields=["status"])
    audit_log(application.user, "loan.disbursed", loan)
    return loan

def build_payment_schedule(loan):
    balance = loan.principal
    r = loan.interest_rate / 100 / 12
    items = []
    for i in range(1, loan.term_months + 1):
        interest = (balance * r).quantize(Decimal("0.01"))
        principal_part = (loan.monthly_payment - interest).quantize(Decimal("0.01"))
        balance -= principal_part
        items.append(PaymentScheduleItem(
            loan=loan, sequence=i,
            due_date=loan.disbursed_at.date() + relativedelta(months=i),
            amount=loan.monthly_payment,
            principal_part=principal_part, interest_part=interest,
            status="PENDING",
        ))
    PaymentScheduleItem.objects.bulk_create(items)
```

### 9.2 Погашение (идемпотентное)

```python
@transaction.atomic
def repay(loan, amount, idempotency_key):
    if Transaction.objects.filter(idempotency_key=idempotency_key).exists():
        raise ConflictError("DUPLICATE", "Repayment already processed")
    loan = Loan.objects.select_for_update().get(id=loan.id)
    loan.outstanding_balance -= amount
    # закрыть ближайший PENDING платёж
    item = loan.paymentscheduleitem_set.filter(status="PENDING").order_by("sequence").first()
    if item:
        item.status = "PAID"; item.paid_at = timezone.now(); item.save()
    if loan.outstanding_balance <= 0:
        loan.status = "CLOSED"; loan.closed_at = timezone.now()
    loan.save()
    Transaction.objects.create(
        loan=loan, type="REPAYMENT", amount=amount,
        balance_after=loan.outstanding_balance, idempotency_key=idempotency_key,
    )
```

---

## 10. Админ-панель API

Все требуют соответствующего permission (см. §5.2).

**Продукты (ADMIN):**
- `GET /admin/credit-products` — список (включая неактивные).
- `POST /admin/credit-products` — создать.
- `PUT /admin/credit-products/{id}` — обновить (инвалидирует кэш).
- `DELETE /admin/credit-products/{id}` — деактивировать (soft delete → `is_active=false`).

**Заявки (SUPPORT/UNDERWRITER/ADMIN):**
- `GET /admin/applications` — все заявки, фильтры по статусу/пользователю/дате.
- `GET /admin/applications/{id}` — детали + документы + скоринг.
- `POST /admin/applications/{id}/approve` — одобрить (UNDERWRITER+). Тело: `{ "comment": "..." }`. Триггерит disburse_loan.
- `POST /admin/applications/{id}/reject` — отказать. Тело: `{ "reason": "..." }`.
- `POST /admin/applications/{id}/request-documents` — запросить документы.

**Пользователи (ADMIN):**
- `GET /admin/users` — список с фильтрами/поиском.
- `PATCH /admin/users/{id}/role` — сменить роль. Тело: `{ "role": "UNDERWRITER" }`. Инвалидирует кэш прав.

**Аудит (ADMIN):**
- `GET /admin/audit-log` — фильтры: actor, action, object_type, date range.

---

## 11. Уведомления и Email

```python
# apps/notifications/services.py
def notify_user(user, notif_type, obj):
    n = Notification.objects.create(
        user=user, type=notif_type,
        title=TITLES[notif_type], body=render_body(notif_type, obj),
    )
    push_notification(user.id, n)      # WebSocket
    send_email_async.delay(user.email, notif_type, obj.id)  # Celery
    cache.delete(f"unread:{user.id}")
```

**Уведомления клиенту:**
- `GET /notifications` — список (пагинация, фильтр `is_read`).
- `POST /notifications/{id}/read` — отметить прочитанным.
- `POST /notifications/read-all` — прочитать все.
- `GET /notifications/unread-count` — счётчик (из кэша).

**Email через Celery:**
```python
@shared_task(max_retries=3)
def send_email_async(email, notif_type, obj_id):
    subject, body = build_email(notif_type, obj_id)
    send_mail(subject, body, DEFAULT_FROM, [email])
```

---

## 12. Cron / периодические задачи (Celery Beat)

```python
CELERY_BEAT_SCHEDULE = {
    "check-overdue-payments": {
        "task": "apps.lending.tasks.mark_overdue_payments",
        "schedule": crontab(hour=1, minute=0),   # каждый день в 01:00
    },
    "payment-due-reminders": {
        "task": "apps.notifications.tasks.send_due_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
}
```

- `mark_overdue_payments` — платежи с истёкшим due_date и PENDING → OVERDUE, loan → OVERDUE.
- `send_due_reminders` — за 3 дня до due_date → уведомление + email.

---

## 13. Сложная фильтрация и оптимизация запросов

### 13.1 Оптимизация N+1

```python
# admin/applications
queryset = CreditApplication.objects.select_related(
    "user", "user__profile", "product", "scoringresult"
).prefetch_related("document_set")
```

### 13.2 Аннотации и агрегаты

```python
# дашборд андеррайтера: заявки в очереди с давностью
CreditApplication.objects.filter(status="MANUAL_REVIEW").annotate(
    waiting_hours=ExtractHour(Now() - F("submitted_at"))
).order_by("submitted_at")
```

### 13.3 Составные фильтры

```python
class AdminApplicationFilter(df.FilterSet):
    status = df.MultipleChoiceFilter(choices=STATUS_CHOICES)
    created_from = df.DateFilter(field_name="created_at", lookup_expr="gte")
    created_to = df.DateFilter(field_name="created_at", lookup_expr="lte")
    user_email = df.CharFilter(field_name="user__email", lookup_expr="icontains")
    min_amount = df.NumberFilter(field_name="amount", lookup_expr="gte")
```

### 13.4 Индексы (миграция Middle)

```python
indexes = [
    models.Index(fields=["status", "submitted_at"]),   # очередь андеррайтера
    models.Index(fields=["user", "status"]),            # заявки клиента по статусу
    models.Index(fields=["created_at"]),
]
```

---

## 14. Audit Log

```python
# common/audit.py
def audit_log(actor, action, obj, changes=None, request=None):
    AuditLog.objects.create(
        actor=actor, action=action,
        object_type=obj.__class__.__name__, object_id=obj.id,
        changes=changes or {},
        ip_address=get_client_ip(request) if request else None,
    )
```

Фиксируются: смена статуса заявки, одобрение/отказ, выдача кредита, смена роли, изменение продукта, погашение.

---

## 15. Docker + docker-compose

```yaml
# docker-compose.yml
version: "3.9"
services:
  web:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    env_file: .env
    depends_on: [db, redis]
    ports: ["8000:8000"]
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: creditflow
      POSTGRES_USER: creditflow
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [pgdata:/var/lib/postgresql/data]
  redis:
    image: redis:7-alpine
  celery:
    build: .
    command: celery -A config worker -l info
    depends_on: [db, redis]
    env_file: .env
  celery-beat:
    build: .
    command: celery -A config beat -l info
    depends_on: [redis]
    env_file: .env
volumes:
  pgdata:
```

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
```

---

## 16. CI/CD (описание пайплайна)

```
GitHub Actions / GitLab CI

stage: lint
  - ruff check .
  - black --check .

stage: test
  - поднять postgres + redis (services)
  - pytest --cov (порог покрытия 70%)

stage: build
  - docker build -t creditflow:${SHA}
  - docker push в registry

stage: deploy (manual approval)
  - docker compose pull && up -d
  - применить миграции: python manage.py migrate
  - collectstatic
```

---

## 17. Тестирование

**Integration:**
```python
@pytest.mark.django_db
def test_full_approval_flow(client_authed, product, celery_eager):
    r = client_authed.post("/api/v1/credit-applications",
        {"product": product.id, "amount": "100000", "term_months": 12})
    app_id = r.data["id"]
    client_authed.post(f"/api/v1/credit-applications/{app_id}/submit")
    app = CreditApplication.objects.get(id=app_id)
    assert app.status in ("APPROVED", "MANUAL_REVIEW", "REJECTED")
    if app.status == "APPROVED":
        assert Loan.objects.filter(application_id=app_id).exists()
        assert PaymentScheduleItem.objects.filter(loan__application_id=app_id).count() == 12
```

**WebSocket-тест** (channels.testing.WebsocketCommunicator): подключение с валидным токеном → приём события смены статуса.

**E2E:** сценарий «регистрация → заявка → скоринг → (одобрение андеррайтером) → выдача → погашение».

---

## 18. Definition of Done + Acceptance Criteria

**DoD:**
- RBAC работает, права кэшируются и инвалидируются.
- Скоринг выполняется в Celery, клиент получает статус по WebSocket.
- Одобрение создаёт Loan + график + транзакцию DISBURSEMENT.
- Погашение идемпотентно, закрывает платежи, закрывает договор при нуле.
- Админ-API: продукты, заявки (approve/reject), пользователи, аудит.
- Уведомления in-app + email; счётчик непрочитанных из кэша.
- Cron помечает просрочку и шлёт напоминания.
- Всё поднимается через docker-compose одной командой.
- CI зелёный, покрытие ≥70%.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|---|---|---|
| AC-1 | CLIENT | GET /admin/applications | 403 PERMISSION_DENIED |
| AC-2 | UNDERWRITER, заявка MANUAL_REVIEW | approve | статус DISBURSED, создан Loan+график |
| AC-3 | Заявка отправлена | submit | ответ SUBMITTED сразу, скоринг в фоне |
| AC-4 | Подключён WS | статус меняется | клиент получает событие application_status |
| AC-5 | Повторный repay с тем же ключом | repay | 409 DUPLICATE, баланс не изменился |
| AC-6 | Продукт обновлён | GET /credit-products | кэш инвалидирован, новые данные |
| AC-7 | Платёж просрочен | ночной cron | статус OVERDUE, уведомление |
| AC-8 | Смена роли | PATCH role | кэш прав инвалидирован, новые права сразу |

**Что считается ошибкой:** скоринг в синхронном запросе; отсутствие идемпотентности погашения; N+1 в админ-списках; отсутствие инвалидации кэша прав/продуктов; WS без проверки токена; изменение статуса без записи в Audit Log.

---

## 19. Roadmap реализации

```
Этап 1 — Инфраструктура
  1. docker-compose (web, db, redis, celery, beat)
  2. Настройка Celery + Redis + Channels в settings/asgi

Этап 2 — RBAC (зависит от User)
  3. Модели Role/Permission/UserRole/RolePermission + seed
  4. HasPermission + кэш прав
  5. Сервисы assign_role/revoke_role

Этап 3 — Async скоринг (зависит от Celery)
  6. Вынести скоринг в задачу, submit → delay
  7. Ввести MANUAL_REVIEW/DISBURSED

Этап 4 — Lending (зависит от скоринга)
  8. Loan, PaymentScheduleItem, Transaction
  9. disburse_loan + build_payment_schedule
  10. repay (идемпотентный) + API /loans

Этап 5 — Real-time (зависит от Channels)
  11. NotificationConsumer + JWT middleware
  12. push_status/push_notification

Этап 6 — Notifications (зависит от Celery + WS)
  13. Notification модель + API + email-задача
  14. Cron: overdue + reminders (Beat)

Этап 7 — Admin (зависит от RBAC)
  15. Продукты, заявки (approve/reject), пользователи
  16. Documents (загрузка к заявке)

Этап 8 — Аудит и оптимизация
  17. AuditLog + интеграция в ключевые действия
  18. Индексы, select_related/prefetch, сложные фильтры
  19. Кэш продуктов

Этап 9 — Финал
  20. CI/CD, интеграционные + WS + E2E тесты, AC
```
