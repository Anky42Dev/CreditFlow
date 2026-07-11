# DOC 5 — Backend Senior
# CreditFlow — Production-ready система

**Версия:** 1.0
**Уровень:** Senior
**Стек (добавлено):** Clean Architecture + DDD, FastAPI (скоринг-сервис), RabbitMQ/Kafka, S3 (MinIO), Prometheus, OpenTelemetry, Feature Flags
**Зависит от:** DOC 0, DOC 1, DOC 3 (рефакторит их код в чистую архитектуру)

---

## Оглавление

1. Задача уровня
2. Clean Architecture + DDD
3. Слоистая структура директорий
4. Доменный слой (Entities, VO, Aggregates, Domain Events)
5. Repository Pattern + Unit of Work
6. Service / Use Case слой + DI
7. Выделение скоринг-сервиса (FastAPI)
8. Брокер сообщений (RabbitMQ/Kafka) + Saga
9. S3 и работа с файлами
10. Безопасность (OWASP, Rate Limit, JWT rotation, Audit)
11. Feature Flags
12. Наблюдаемость (метрики, логи, трассировка)
13. Health Checks
14. Оптимизация БД
15. Масштабирование, Docker Compose (prod), Kubernetes (концепт.)
16. Тестирование
17. Definition of Done + Acceptance Criteria
18. Roadmap реализации

---

## 1. Задача уровня

Превратить модульный монолит Middle в production-ready систему: чистая архитектура, доменная модель, выделенный async-скоринг, событийная интеграция через брокер, S3, полная наблюдаемость и безопасность. **Схема БД и API-контракты сохраняются** (обратная совместимость) — меняется организация кода и инфраструктура.

---

## 2. Clean Architecture + DDD

### 2.1 Принцип зависимостей

```
        ┌─────────────────────────────────────────┐
        │            Frameworks & Drivers          │  ← Django, FastAPI, PostgreSQL,
        │   (web, db, broker, s3, cache)           │    RabbitMQ, Redis, S3
        ├─────────────────────────────────────────┤
        │          Interface Adapters              │  ← DRF views, serializers,
        │   (controllers, presenters, repos impl)  │    repository implementations
        ├─────────────────────────────────────────┤
        │          Application (Use Cases)         │  ← сценарии: SubmitApplication,
        │                                          │    ApproveApplication, RepayLoan
        ├─────────────────────────────────────────┤
        │              Domain (Core)               │  ← Entities, Value Objects,
        │   (бизнес-правила, не знает о Django)     │    Aggregates, Domain Events
        └─────────────────────────────────────────┘

     Зависимости направлены ВНУТРЬ. Domain ничего не импортирует извне.
```

### 2.2 Bounded Contexts как модули

```
Identity   → пользователи, аутентификация, роли
Lending    → продукты, заявки, скоринг, договоры (ядро домена)
Payments   → графики, транзакции, погашения
Notification → уведомления, email
Platform   → audit, feature flags, health
```

Контексты общаются через доменные события и явные интерфейсы, а не через прямой доступ к чужим моделям.

---

## 3. Слоистая структура директорий

```
creditflow/
├── src/
│   ├── shared/                       # kernel: базовые VO, Result, ошибки, events bus
│   │   ├── domain/
│   │   │   ├── entity.py
│   │   │   ├── value_object.py
│   │   │   ├── domain_event.py
│   │   │   └── aggregate_root.py
│   │   ├── application/
│   │   │   ├── use_case.py
│   │   │   └── unit_of_work.py
│   │   └── infrastructure/
│   │       ├── event_bus.py          # публикация в брокер
│   │       └── di.py                 # контейнер зависимостей
│   │
│   ├── lending/                      # Bounded Context
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   ├── application.py     # CreditApplication (Aggregate Root)
│   │   │   │   └── product.py
│   │   │   ├── value_objects/
│   │   │   │   ├── money.py
│   │   │   │   ├── term.py
│   │   │   │   └── application_status.py
│   │   │   ├── events/
│   │   │   │   ├── application_submitted.py
│   │   │   │   ├── application_approved.py
│   │   │   │   └── application_rejected.py
│   │   │   ├── services/              # доменные сервисы
│   │   │   │   └── scoring_policy.py
│   │   │   └── repositories/          # ИНТЕРФЕЙСЫ (ABC)
│   │   │       └── application_repository.py
│   │   ├── application/               # Use Cases
│   │   │   ├── submit_application.py
│   │   │   ├── approve_application.py
│   │   │   └── dto.py
│   │   ├── infrastructure/
│   │   │   ├── models.py              # Django ORM модели
│   │   │   ├── repositories.py        # реализация репозиториев
│   │   │   ├── mappers.py             # ORM ↔ domain entity
│   │   │   └── consumers.py           # обработчики событий из брокера
│   │   └── presentation/
│   │       ├── views.py               # DRF
│   │       ├── serializers.py
│   │       └── urls.py
│   │
│   ├── payments/                     # аналогичная структура
│   ├── identity/
│   ├── notification/
│   └── platform/                     # audit, feature_flags, health, metrics
│
├── scoring_service/                  # ОТДЕЛЬНЫЙ FastAPI-сервис
│   ├── main.py
│   ├── domain/scoring.py
│   ├── api/routes.py
│   └── consumers/                    # слушает ApplicationSubmitted
│
├── deploy/
│   ├── docker-compose.prod.yml
│   ├── k8s/                          # манифесты (концептуально)
│   └── monitoring/                   # prometheus.yml, grafana dashboards
└── tests/
    ├── unit/                         # доменные тесты (без БД)
    ├── integration/
    └── e2e/
```

---

## 4. Доменный слой

### 4.1 Value Objects

```python
# src/lending/domain/value_objects/money.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "KGS"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money cannot be negative")

    def __add__(self, other): return Money(self.amount + other.amount, self.currency)
    def __sub__(self, other): return Money(self.amount - other.amount, self.currency)
```

```python
# application_status.py — статус как VO с правилами переходов
from enum import Enum

class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"; SUBMITTED = "SUBMITTED"; SCORING = "SCORING"
    APPROVED = "APPROVED"; REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"; DISBURSED = "DISBURSED"

    ALLOWED = {
        "DRAFT": {"SUBMITTED"},
        "SUBMITTED": {"SCORING"},
        "SCORING": {"APPROVED", "REJECTED", "MANUAL_REVIEW"},
        "MANUAL_REVIEW": {"APPROVED", "REJECTED"},
        "APPROVED": {"DISBURSED"},
    }

    def can_transition_to(self, target) -> bool:
        return target.value in self.ALLOWED.get(self.value, set())
```

### 4.2 Aggregate Root

```python
# src/lending/domain/entities/application.py
class CreditApplicationAggregate(AggregateRoot):
    def __init__(self, id, user_id, product, amount: Money, term: Term, status):
        super().__init__(id)
        self.user_id = user_id
        self.product = product
        self.amount = amount
        self.term = term
        self.status = status
        self.monthly_payment = None

    def submit(self):
        if self.status != ApplicationStatus.DRAFT:
            raise DomainError("Only DRAFT can be submitted")
        self.product.validate_amount(self.amount)   # бизнес-правило внутри домена
        self.monthly_payment = self.product.calc_annuity(self.amount, self.term)
        self._transition(ApplicationStatus.SUBMITTED)
        self.raise_event(ApplicationSubmitted(self.id, self.user_id))

    def apply_scoring(self, decision: str, score: int):
        self._transition(ApplicationStatus.SCORING)
        if decision == "APPROVED":
            self._transition(ApplicationStatus.APPROVED)
            self.raise_event(ApplicationApproved(self.id, self.user_id, self.amount))
        elif decision == "MANUAL_REVIEW":
            self._transition(ApplicationStatus.MANUAL_REVIEW)
        else:
            self._transition(ApplicationStatus.REJECTED)
            self.raise_event(ApplicationRejected(self.id, self.user_id))

    def _transition(self, target):
        if not self.status.can_transition_to(target):
            raise DomainError(f"Invalid transition {self.status} → {target}")
        self.status = target
```

### 4.3 Domain Events

```python
# src/lending/domain/events/application_approved.py
@dataclass(frozen=True)
class ApplicationApproved(DomainEvent):
    application_id: int
    user_id: int
    amount: Money
    occurred_at: datetime = field(default_factory=datetime.utcnow)
```

События собираются в агрегате и публикуются в брокер после успешного коммита (см. §8, transactional outbox).

---

## 5. Repository Pattern + Unit of Work

### 5.1 Интерфейс (в domain)

```python
# src/lending/domain/repositories/application_repository.py
from abc import ABC, abstractmethod

class ApplicationRepository(ABC):
    @abstractmethod
    def get(self, application_id) -> CreditApplicationAggregate: ...
    @abstractmethod
    def save(self, aggregate: CreditApplicationAggregate) -> None: ...
    @abstractmethod
    def list_for_review(self): ...
```

### 5.2 Реализация (в infrastructure)

```python
# src/lending/infrastructure/repositories.py
class DjangoApplicationRepository(ApplicationRepository):
    def get(self, application_id):
        model = CreditApplicationModel.objects.select_related("product").get(id=application_id)
        return ApplicationMapper.to_domain(model)

    def save(self, aggregate):
        model = ApplicationMapper.to_model(aggregate)
        model.save()
        # доменные события → в outbox
        for event in aggregate.pull_events():
            OutboxModel.objects.create(
                event_type=event.__class__.__name__,
                payload=serialize(event),
            )
```

### 5.3 Unit of Work

```python
# src/shared/application/unit_of_work.py
class DjangoUnitOfWork:
    def __enter__(self):
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self
    def __exit__(self, exc_type, *a):
        self._atomic.__exit__(exc_type, *a)
```

---

## 6. Service / Use Case слой + DI

### 6.1 Use Case

```python
# src/lending/application/submit_application.py
class SubmitApplicationUseCase:
    def __init__(self, repo: ApplicationRepository, uow, event_bus):
        self.repo = repo
        self.uow = uow
        self.event_bus = event_bus

    def execute(self, application_id: int) -> ApplicationDTO:
        with self.uow:
            app = self.repo.get(application_id)
            app.submit()                 # доменная логика
            self.repo.save(app)          # + запись событий в outbox
        # events публикуются outbox-релеем асинхронно
        return ApplicationDTO.from_aggregate(app)
```

### 6.2 DI-контейнер

```python
# src/shared/infrastructure/di.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    application_repo = providers.Factory(DjangoApplicationRepository)
    uow = providers.Factory(DjangoUnitOfWork)
    event_bus = providers.Singleton(RabbitMQEventBus, url=config.BROKER_URL)

    submit_application = providers.Factory(
        SubmitApplicationUseCase,
        repo=application_repo, uow=uow, event_bus=event_bus,
    )
```

DRF view вызывает use case из контейнера — не знает о репозиториях/ORM:

```python
class ApplicationSubmitView(APIView):
    def post(self, request, pk):
        uc = container.submit_application()
        dto = uc.execute(pk)
        return Response(ApplicationSerializer(dto).data)
```

---

## 7. Выделение скоринг-сервиса (FastAPI)

### 7.1 Зачем отдельный сервис

Скоринг — CPU/IO-интенсивный, async, потенциально ML-модель, свой цикл релизов. Выносим в независимый FastAPI-сервис, слушающий события из брокера.

```
Django (Lending) ──ApplicationSubmitted──▶ [Broker] ──▶ Scoring Service (FastAPI)
                                                              │
                     ScoringCompleted ◀───[Broker]◀──────────┘
        ▼
Django применяет решение к агрегату (apply_scoring)
```

### 7.2 FastAPI-сервис

```python
# scoring_service/main.py
from fastapi import FastAPI
app = FastAPI(title="CreditFlow Scoring Service")

@app.post("/score")
async def score(payload: ScoreRequest) -> ScoreResponse:
    result = await scoring_engine.evaluate(payload)
    return ScoreResponse(score=result.score, decision=result.decision)

@app.get("/health")
async def health(): return {"status": "ok"}
```

Consumer в сервисе слушает `ApplicationSubmitted`, считает скор, публикует `ScoringCompleted`. Django-consumer применяет результат к агрегату.

---

## 8. Брокер сообщений + Saga

### 8.1 Transactional Outbox

Гарантия «сохранили агрегат ⇒ событие точно опубликуется»:

```
1. save(aggregate) + INSERT в outbox  — в одной транзакции
2. Outbox Relay (Celery/поллер) читает необработанные записи
3. Публикует в RabbitMQ/Kafka
4. Помечает published=true
```

### 8.2 Saga выдачи кредита

```
ApplicationApproved
   → [Payments] CreateLoan
       → LoanCreated
           → [Payments] BuildSchedule
               → ScheduleBuilt
                   → [Lending] MarkDisbursed → ApplicationDisbursed
                       → [Notification] NotifyClient

Компенсации при сбое:
  - CreateLoan fail → ApplicationApprovalFailed → вернуть в MANUAL_REVIEW
```

### 8.3 Выбор брокера

| Критерий | RabbitMQ | Kafka |
|---|---|---|
| Модель | очереди, роутинг | лог событий, replay |
| Наш кейс | команды/Saga | event sourcing/аудит |
| Решение | **RabbitMQ для команд Saga** + **Kafka для потока доменных событий/аналитики** (можно ограничиться RabbitMQ на старте) | |

---

## 9. S3 и работа с файлами

```python
# document upload → S3 (MinIO локально, AWS S3 в prod)
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT")
AWS_STORAGE_BUCKET_NAME = "creditflow-documents"
```

- Аватары/документы → S3.
- Приватные документы → presigned URL с TTL (не публичный доступ).
- Обработка изображений (ресайз аватара) → фоновая Celery-задача, результат в S3.
- Антивирус-скан документов (концептуально) — событие `DocumentUploaded` → сканер.

---

## 10. Безопасность

### 10.1 OWASP Top 10 — меры

| Риск | Мера |
|---|---|
| Broken Access Control | RBAC + object-level permission, тесты на IDOR |
| Injection | ORM (параметризация), валидация DTO |
| Sensitive Data Exposure | шифрование PII в покое, TLS в транзите, маскирование в логах |
| Security Misconfiguration | secrets в vault/env, DEBUG=False, security headers |
| Vulnerable Components | Dependabot, регулярный `pip-audit` |
| SSRF/Broken Auth | JWT rotation + blacklist, короткий TTL |

### 10.2 JWT rotation + blacklist

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```
При refresh старый refresh инвалидируется. Logout → refresh в blacklist.

### 10.3 Rate Limiting

```python
# через django-ratelimit / DRF throttling + Redis
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "login": "5/min",         # защита от брутфорса
    "register": "10/hour",
    "user": "1000/hour",
    "anon": "100/hour",
}
```
Ответ `429` с заголовком `Retry-After`.

### 10.4 Security headers

`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Content-Security-Policy` — через middleware.

### 10.5 Audit Log (immutable)

Append-only таблица, запрет UPDATE/DELETE на уровне БД-прав; каждое финансовое/статусное действие логируется с actor, IP, before/after.

---

## 11. Feature Flags

```python
# src/platform/feature_flags/service.py
def is_enabled(flag: str, user=None) -> bool:
    # флаги в Redis, поддержка percentage rollout и per-user
    cfg = flag_store.get(flag)
    if not cfg: return False
    if cfg.get("global"): return True
    if user and user.id % 100 < cfg.get("percentage", 0): return True
    return False
```

Примеры: `new_scoring_model` (постепенный rollout нового скоринга), `instant_disbursement`, `kafka_events`. Управление — через admin API + аудит смены флага.

---

## 12. Наблюдаемость

### 12.1 Метрики (Prometheus)

```python
# счётчики/гистограммы
applications_submitted_total = Counter("cf_applications_submitted_total", ...)
scoring_duration_seconds = Histogram("cf_scoring_duration_seconds", ...)
loans_disbursed_amount = Counter("cf_loans_disbursed_amount_total", ...)
http_request_duration = Histogram("cf_http_request_duration_seconds", ["endpoint", "method", "status"])
```
Экспорт на `/metrics`. Grafana-дашборды: воронка заявок, latency, error rate, длина очереди MANUAL_REVIEW.

### 12.2 Структурное логирование

JSON-логи с `trace_id`, `user_id`, `request_id`. Централизация — ELK/Loki (концептуально). PII маскируется.

### 12.3 Трассировка (OpenTelemetry)

Сквозной `trace_id` через HTTP → брокер → скоринг-сервис → обратно. Экспорт в Jaeger/Tempo. Позволяет видеть весь путь заявки между сервисами.

---

## 13. Health Checks

| Эндпоинт | Проверяет | Использование |
|---|---|---|
| `GET /health/live` | процесс жив | K8s liveness probe |
| `GET /health/ready` | БД, Redis, брокер доступны | K8s readiness probe |
| `GET /health/startup` | миграции применены | startup probe |

```python
def readiness():
    checks = {"db": check_db(), "redis": check_redis(), "broker": check_broker()}
    status = 200 if all(checks.values()) else 503
    return JsonResponse(checks, status=status)
```

---

## 14. Оптимизация БД

- **Индексы:** составные под реальные запросы (`(status, submitted_at)`, `(user, status)`, `(loan, sequence)`), частичные индексы (`WHERE status='MANUAL_REVIEW'`).
- **Партиционирование:** `Transaction` и `AuditLog` по месяцам (растут быстрее всего).
- **Read replica:** тяжёлые отчёты/админ-аналитика → на реплику (роутер БД).
- **Connection pooling:** PgBouncer.
- **N+1:** обязательный `select_related/prefetch_related`, `django-debug-toolbar`/`nplusone` в CI.
- **Пагинация больших таблиц:** keyset (cursor) pagination вместо offset для аудита/транзакций.

---

## 15. Масштабирование и деплой

### 15.1 docker-compose.prod.yml (сервисы)

```
services:
  web         (Django ASGI, N реплик за LB)
  scoring     (FastAPI, независимо масштабируется)
  celery      (воркеры, отдельно скоринг/email/schedule очереди)
  celery-beat
  outbox-relay
  db          (PostgreSQL + реплика)
  pgbouncer
  redis
  rabbitmq
  minio       (S3)
  prometheus
  grafana
  nginx       (reverse proxy, TLS, rate limit на кромке)
```

### 15.2 Kubernetes (концептуально)

```
Deployments: web, scoring, celery-worker, outbox-relay (HPA по CPU/queue length)
StatefulSets: postgres, rabbitmq, redis
Services + Ingress (TLS termination)
ConfigMap/Secret: конфиг и креды
Probes: liveness/readiness/startup (§13)
HPA: scoring по длине очереди; web по CPU
```

### 15.3 Стратегии масштабирования

- **Горизонтальное:** web и воркеры stateless → добавляем реплики.
- **Скоринг:** отдельный autoscale по длине очереди `ApplicationSubmitted`.
- **БД:** вертикально + read replica + партиционирование.
- **Кэш/сессии:** Redis-кластер.

---

## 16. Тестирование

| Уровень | Что | Инструмент |
|---|---|---|
| Unit (domain) | агрегаты, VO, переходы статусов, скоринг-политика — **без БД** | pytest |
| Integration | репозитории, use cases с реальной БД, outbox | pytest + testcontainers |
| Contract | контракт событий между Django и scoring-service | pact/схемы |
| E2E | полный путь заявка→скоринг→saga→выдача→погашение | pytest + compose |
| Нагрузочное | throughput скоринга, latency API | Locust |
| Security | IDOR, authz, rate limit | автоматизированные тесты + pip-audit |

Пример доменного unit-теста (быстрый, без инфраструктуры):
```python
def test_cannot_submit_non_draft():
    app = make_aggregate(status=ApplicationStatus.SUBMITTED)
    with pytest.raises(DomainError):
        app.submit()

def test_invalid_transition_rejected():
    app = make_aggregate(status=ApplicationStatus.DRAFT)
    with pytest.raises(DomainError):
        app._transition(ApplicationStatus.DISBURSED)
```

---

## 17. Definition of Done + Acceptance Criteria

**DoD:**
- Домен изолирован: `domain/` не импортирует Django/DRF; unit-тесты домена бегут без БД.
- Use cases вызываются через DI; views не содержат бизнес-логики.
- Скоринг вынесен в FastAPI, интеграция через брокер.
- Transactional Outbox гарантирует доставку событий; Saga выдачи работает с компенсациями.
- JWT rotation + blacklist; rate limiting; security headers; immutable audit.
- Feature flags управляемы и аудируются.
- Prometheus-метрики, структурные логи с trace_id, OTel-трассировка сквозная.
- Health-пробы работают; система поднимается в compose.prod; K8s-манифесты описаны.
- Индексы/партиционирование применены; N+1 отсутствует (проверка в CI).

**Acceptance Criteria:**

| # | Given | When | Then |
|---|---|---|---|
| AC-1 | Домен-тесты | запуск без БД | проходят (изоляция домена) |
| AC-2 | Заявка отправлена | submit | ApplicationSubmitted попадает в outbox, публикуется |
| AC-3 | Скоринг-сервис недоступен | submit | заявка остаётся SUBMITTED, ретрай без потери события |
| AC-4 | Одобрение | approve | Saga создаёт Loan+график, статус DISBURSED, уведомление |
| AC-5 | Сбой на шаге BuildSchedule | — | компенсация: заявка → MANUAL_REVIEW, аудит |
| AC-6 | 6 логинов за минуту | login | 6-й → 429 Retry-After |
| AC-7 | Refresh использован дважды | 2-й refresh | 401 (ротация + blacklist) |
| AC-8 | Флаг new_scoring_model 10% | скоринг | ~10% пользователей на новой модели |
| AC-9 | Запрос | любой | trace_id сквозной через все сервисы в Jaeger |
| AC-10 | БД-реплика недоступна | /health/ready | 503 |

**Что считается ошибкой:** бизнес-логика в ORM-моделях или views; прямая публикация событий без outbox (риск потери); refresh без ротации; отсутствие компенсаций в Saga; логирование PII в открытом виде; отсутствие индексов под ключевые запросы; домен, зависящий от Django.

---

## 18. Roadmap реализации

```
Этап 1 — Каркас чистой архитектуры
  1. shared/kernel (Entity, VO, AggregateRoot, DomainEvent, UoW)
  2. DI-контейнер
  3. Рефакторинг lending: domain → application → infrastructure → presentation
     (поведение и API не меняются — покрыто тестами Middle)

Этап 2 — Repository + Use Cases
  4. Интерфейсы репозиториев + Django-реализации + мапперы
  5. Use cases: Submit/Approve/Reject/Repay
  6. Views → тонкие адаптеры к use cases

Этап 3 — События и брокер
  7. Transactional Outbox + Outbox Relay
  8. RabbitMQ, публикация/потребление доменных событий
  9. Saga выдачи кредита + компенсации

Этап 4 — Скоринг-сервис
  10. FastAPI-сервис, /score + /health
  11. Consumer ApplicationSubmitted → ScoringCompleted
  12. Contract-тесты

Этап 5 — Инфраструктура данных/файлов
  13. S3 (MinIO), presigned URLs, async обработка изображений
  14. Индексы, партиционирование, read replica, PgBouncer

Этап 6 — Безопасность
  15. JWT rotation+blacklist, throttling, security headers
  16. Immutable audit, OWASP-тесты

Этап 7 — Наблюдаемость и надёжность
  17. Prometheus-метрики + Grafana
  18. Структурные логи + OpenTelemetry (Jaeger)
  19. Health checks, feature flags

Этап 8 — Деплой и масштабирование
  20. docker-compose.prod, nginx/TLS
  21. K8s-манифесты (концептуально), HPA
  22. Нагрузочные тесты, финальная проверка AC
```
