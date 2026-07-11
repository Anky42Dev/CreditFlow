# DOC 1 — Backend Junior
# CreditFlow — Ядро системы (Auth + Products + Applications)

**Версия:** 1.0
**Уровень:** Junior
**Стек:** Django 5, Django REST Framework, PostgreSQL 16, SimpleJWT, drf-spectacular, pytest
**Зависит от:** DOC 0 (Master Specification)

---

## Оглавление

1. Скоуп уровня
2. Технологический стек
3. Архитектура
4. Структура директорий
5. Модели данных
6. ER-диаграмма (Junior subset)
7. Бизнес-логика
8. API-справочник (полный)
9. Аутентификация JWT
10. Pagination / Filter / Sort / Search
11. Загрузка изображений
12. Swagger / OpenAPI
13. Тестирование
14. Definition of Done + Acceptance Criteria
15. Roadmap реализации

---

## 1. Скоуп уровня

**Что делаем:**
- Регистрация и аутентификация (JWT access + refresh).
- Профиль пользователя + загрузка аватара.
- Каталог кредитных продуктов (read-only для клиента).
- Кредитные заявки: полный CRUD + submit + синхронный псевдо-скоринг.
- Пагинация, фильтрация, сортировка, поиск.
- OpenAPI-документация.
- Unit + integration тесты.

**Что НЕ делаем на этом уровне (появится в Middle/Senior):**
- Роли и RBAC (только owner-based доступ).
- Кредитные договоры, графики платежей, транзакции.
- Асинхронный скоринг, очереди, WebSocket.
- Админ-панель, уведомления, аудит.
- Docker, кэш, Celery.

---

## 2. Технологический стек

| Компонент | Выбор | Обоснование |
|---|---|---|
| Framework | Django 5 + DRF | Богатый ORM, миграции, быстрая разработка CRUD |
| БД | PostgreSQL 16 | Реляционная модель, транзакции (важно для финансов) |
| Auth | djangorestframework-simplejwt | Access + refresh из коробки |
| Валидация | DRF Serializers | Декларативная валидация |
| Документация | drf-spectacular | Генерация OpenAPI 3.0 / Swagger UI |
| Изображения | Pillow | Обработка аватаров |
| Фильтрация | django-filter | Декларативные фильтры |
| Тесты | pytest + pytest-django + factory_boy | Стандарт индустрии |
| Env | python-decouple | Конфигурация через .env |

---

## 3. Архитектура

Простая слоистая архитектура (без излишеств — это Junior):

```
┌─────────────────────────────────────────────┐
│              HTTP (DRF Router)               │
├─────────────────────────────────────────────┤
│   View / ViewSet   (обработка запроса)       │
│      ↓                                       │
│   Serializer       (валидация + сериализация)│
│      ↓                                       │
│   Service          (бизнес-логика)           │
│      ↓                                       │
│   Model / ORM      (доступ к данным)         │
├─────────────────────────────────────────────┤
│              PostgreSQL                      │
└─────────────────────────────────────────────┘
```

**Почему так:** для Junior не нужен Repository/DDD. Но мы уже выносим бизнес-логику в отдельный слой `services.py` (а не пихаем во views) — это подготавливает переход к Service Layer на Senior без переписывания.

---

## 4. Структура директорий

```
creditflow/
├── manage.py
├── requirements.txt
├── .env.example
├── pytest.ini
├── config/                     # настройки проекта
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py                 # корневой роутинг
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/               # Identity context
│   │   ├── __init__.py
│   │   ├── models.py           # User, Profile
│   │   ├── serializers.py
│   │   ├── services.py         # регистрация, обновление профиля
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py      # IsOwner
│   │   └── tests/
│   │       ├── test_auth.py
│   │       └── test_profile.py
│   ├── products/               # каталог кредитных продуктов
│   │   ├── models.py           # CreditProduct
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── filters.py
│   │   └── tests/
│   └── applications/           # кредитные заявки
│       ├── models.py           # CreditApplication, ScoringResult
│       ├── serializers.py
│       ├── services.py         # submit, scoring
│       ├── views.py
│       ├── urls.py
│       ├── filters.py
│       ├── permissions.py
│       └── tests/
├── common/                     # сквозной код
│   ├── pagination.py           # StandardPagination
│   ├── exceptions.py           # единый формат ошибок
│   ├── responses.py
│   └── validators.py
└── media/                      # загруженные файлы (аватары)
    └── avatars/
```

---

## 5. Модели данных

### 5.1 User (кастомная модель)

Django по умолчанию использует username. Мы переопределяем на email как логин.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | BigAutoField | PK | Идентификатор |
| `email` | EmailField | unique, not null, indexed | Логин |
| `password` | CharField(128) | not null | Хэш пароля (PBKDF2) |
| `role` | CharField(20) | default='CLIENT', choices | Роль (задел на Middle) |
| `is_active` | BooleanField | default=True | Активен ли аккаунт |
| `is_staff` | BooleanField | default=False | Доступ в django-admin |
| `date_joined` | DateTimeField | auto_now_add | Дата регистрации |
| `last_login` | DateTimeField | null=True | Последний вход |

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", "ADMIN")
        return self.create_user(email, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("GUEST", "Guest"), ("CLIENT", "Client"),
        ("SUPPORT", "Support"), ("UNDERWRITER", "Underwriter"), ("ADMIN", "Admin"),
    ]
    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CLIENT")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        indexes = [models.Index(fields=["email"])]
```

### 5.2 Profile

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | BigAutoField | PK | |
| `user_id` | OneToOne(User) | unique, not null, on_delete=CASCADE | Владелец |
| `first_name` | CharField(50) | blank | Имя |
| `last_name` | CharField(50) | blank | Фамилия |
| `birth_date` | DateField | null | Дата рождения (валидация 18+) |
| `phone` | CharField(20) | blank, валидация формата | Телефон |
| `monthly_income` | DecimalField(12,2) | null, ≥0 | Ежемесячный доход (для скоринга) |
| `avatar` | ImageField | null, upload_to='avatars/' | Аватар |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

### 5.3 CreditProduct

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | BigAutoField | PK | |
| `name` | CharField(120) | not null | Название продукта |
| `slug` | SlugField | unique, indexed | URL-идентификатор |
| `description` | TextField | blank | Описание |
| `min_amount` | DecimalField(12,2) | ≥0 | Мин. сумма |
| `max_amount` | DecimalField(12,2) | ≥min_amount | Макс. сумма |
| `interest_rate` | DecimalField(5,2) | 0–100 | Годовая ставка, % |
| `min_term_months` | PositiveSmallInteger | ≥1 | Мин. срок |
| `max_term_months` | PositiveSmallInteger | ≥min_term | Макс. срок |
| `is_active` | BooleanField | default=True, indexed | Опубликован ли |
| `created_at` | DateTimeField | auto_now_add | |

**Ограничения БД:**
```python
class Meta:
    db_table = "credit_products"
    constraints = [
        models.CheckConstraint(check=Q(max_amount__gte=F("min_amount")), name="max_gte_min_amount"),
        models.CheckConstraint(check=Q(max_term_months__gte=F("min_term_months")), name="max_gte_min_term"),
        models.CheckConstraint(check=Q(interest_rate__gte=0) & Q(interest_rate__lte=100), name="rate_0_100"),
    ]
    indexes = [models.Index(fields=["is_active", "slug"])]
```

### 5.4 CreditApplication

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | BigAutoField | PK | |
| `user_id` | FK(User) | not null, on_delete=CASCADE, indexed | Заявитель |
| `product_id` | FK(CreditProduct) | not null, on_delete=PROTECT, indexed | Продукт |
| `amount` | DecimalField(12,2) | >0 | Запрошенная сумма |
| `term_months` | PositiveSmallInteger | ≥1 | Срок |
| `purpose` | CharField(255) | blank | Цель кредита |
| `status` | CharField(20) | default='DRAFT', choices, indexed | Статус |
| `monthly_payment` | DecimalField(12,2) | null | Рассчитанный аннуитет |
| `created_at` | DateTimeField | auto_now_add, indexed | |
| `updated_at` | DateTimeField | auto_now | |
| `submitted_at` | DateTimeField | null | Момент отправки |

**Статусы (Junior subset):** `DRAFT`, `SUBMITTED`, `SCORING`, `APPROVED`, `REJECTED`.

### 5.5 ScoringResult

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | BigAutoField | PK | |
| `application_id` | OneToOne(CreditApplication) | unique, on_delete=CASCADE | Заявка |
| `score` | PositiveSmallInteger | 0–1000 | Скоринговый балл |
| `decision` | CharField(20) | choices | APPROVED / REJECTED |
| `reason` | CharField(255) | blank | Причина решения |
| `created_at` | DateTimeField | auto_now_add | |

---

## 6. ER-диаграмма (Junior subset)

```
┌──────────────┐        ┌──────────────┐
│    User      │1──────1│   Profile    │
│──────────────│        │──────────────│
│ PK id        │        │ PK id        │
│ email (uniq) │        │ FK user_id   │
│ password     │        │ first_name   │
│ role         │        │ last_name    │
│ is_active    │        │ birth_date   │
│ date_joined  │        │ monthly_income│
└──────┬───────┘        │ avatar       │
       │1               └──────────────┘
       │
       │*
┌──────▼─────────────┐         ┌──────────────────┐
│ CreditApplication  │*───────1│  CreditProduct   │
│────────────────────│         │──────────────────│
│ PK id              │         │ PK id            │
│ FK user_id         │         │ name             │
│ FK product_id      │         │ slug (uniq)      │
│ amount             │         │ min_amount       │
│ term_months        │         │ max_amount       │
│ status             │         │ interest_rate    │
│ monthly_payment    │         │ min_term_months  │
│ submitted_at       │         │ max_term_months  │
└──────┬─────────────┘         │ is_active        │
       │1                      └──────────────────┘
       │
       │0..1
┌──────▼─────────┐
│ ScoringResult  │
│────────────────│
│ PK id          │
│ FK application │
│ score          │
│ decision       │
│ reason         │
└────────────────┘
```

---

## 7. Бизнес-логика

### 7.1 Регистрация

```python
# apps/accounts/services.py
def register_user(email: str, password: str) -> User:
    if User.objects.filter(email=email).exists():
        raise ConflictError("EMAIL_TAKEN", "Email already registered")
    user = User.objects.create_user(email=email, password=password, role="CLIENT")
    Profile.objects.create(user=user)   # пустой профиль сразу
    return user
```

### 7.2 Расчёт аннуитетного платежа

Формула аннуитета:
```
              P * r * (1 + r)^n
monthly = ─────────────────────────
               (1 + r)^n − 1

где:
  P = сумма кредита (amount)
  r = месячная ставка = interest_rate / 100 / 12
  n = срок в месяцах (term_months)
```

```python
# apps/applications/services.py
from decimal import Decimal

def calc_annuity(amount: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    r = annual_rate / Decimal(100) / Decimal(12)
    if r == 0:
        return (amount / months).quantize(Decimal("0.01"))
    factor = (1 + r) ** months
    payment = amount * r * factor / (factor - 1)
    return payment.quantize(Decimal("0.01"))
```

### 7.3 Отправка заявки + синхронный скоринг

```python
def submit_application(application: CreditApplication) -> CreditApplication:
    # 1. Проверка статуса
    if application.status != "DRAFT":
        raise ConflictError("INVALID_STATE", "Only DRAFT can be submitted")
    # 2. Валидация суммы против продукта
    p = application.product
    if not (p.min_amount <= application.amount <= p.max_amount):
        raise ValidationError({"amount": "Amount out of product range"})
    if not (p.min_term_months <= application.term_months <= p.max_term_months):
        raise ValidationError({"term_months": "Term out of product range"})
    # 3. Расчёт платежа
    application.monthly_payment = calc_annuity(
        application.amount, p.interest_rate, application.term_months
    )
    application.status = "SUBMITTED"
    application.submitted_at = timezone.now()
    application.save()
    # 4. Синхронный скоринг (на Middle станет асинхронным)
    run_scoring(application)
    return application

def run_scoring(application: CreditApplication) -> ScoringResult:
    application.status = "SCORING"; application.save(update_fields=["status"])
    profile = application.user.profile
    score = 500
    if profile.monthly_income:
        # платёж не должен превышать 40% дохода
        ratio = application.monthly_payment / profile.monthly_income
        if ratio < Decimal("0.2"): score += 300
        elif ratio < Decimal("0.4"): score += 100
        else: score -= 200
    if profile.birth_date is None:
        score -= 100
    score = max(0, min(1000, score))
    decision = "APPROVED" if score >= 600 else "REJECTED"
    reason = "Sufficient income" if decision == "APPROVED" else "High debt-to-income or missing data"
    application.status = decision
    application.save(update_fields=["status"])
    return ScoringResult.objects.create(
        application=application, score=score, decision=decision, reason=reason
    )
```

---

## 8. API-справочник (полный)

Base URL: `/api/v1/`. Формат ответов и ошибок — по DOC 0 §5.

### 8.1 Auth

---
**POST `/auth/register`** — регистрация

- Auth: не требуется
- Request Body:
```json
{ "email": "user@example.com", "password": "StrongPass123" }
```
- Валидация: email — формат + уникальность; password — мин. 8 символов, не только цифры.
- Response `201`:
```json
{ "id": 42, "email": "user@example.com", "role": "CLIENT" }
```
- Ошибки: `400` VALIDATION_ERROR; `409` EMAIL_TAKEN.

---
**POST `/auth/login`** — вход

- Request Body: `{ "email": "...", "password": "..." }`
- Response `200`:
```json
{ "access": "<jwt>", "refresh": "<jwt>" }
```
- Ошибки: `401` AUTHENTICATION_FAILED (неверные креды).

---
**POST `/auth/refresh`** — обновление access-токена

- Request Body: `{ "refresh": "<jwt>" }`
- Response `200`: `{ "access": "<jwt>" }`
- Ошибки: `401` TOKEN_EXPIRED / TOKEN_INVALID.

---
**GET `/auth/me`** — текущий пользователь

- Auth: Bearer
- Response `200`: `{ "id": 42, "email": "...", "role": "CLIENT" }`
- Ошибки: `401`.

### 8.2 Profile

---
**GET `/profile`** — получить свой профиль

- Auth: Bearer
- Response `200`:
```json
{
  "id": 7, "first_name": "Иван", "last_name": "Петров",
  "birth_date": "1995-04-12", "phone": "+996700123456",
  "monthly_income": "80000.00",
  "avatar": "/media/avatars/7.jpg"
}
```
- Ошибки: `401`.

---
**PUT `/profile`** — обновить профиль

- Auth: Bearer
- Request Body:
```json
{
  "first_name": "Иван", "last_name": "Петров",
  "birth_date": "1995-04-12", "phone": "+996700123456",
  "monthly_income": "80000.00"
}
```
- Валидация: `birth_date` → возраст ≥18; `monthly_income` ≥0; `phone` по regex.
- Response `200`: обновлённый профиль.
- Ошибки: `400`, `401`.

---
**POST `/profile/avatar`** — загрузка аватара

- Auth: Bearer
- Content-Type: `multipart/form-data`, поле `avatar` (файл)
- Валидация: типы `image/jpeg|png`, размер ≤ 2 МБ, ресайз до 400×400.
- Response `200`: `{ "avatar": "/media/avatars/7.jpg" }`
- Ошибки: `400` (неверный тип/размер), `401`.

### 8.3 Credit Products

---
**GET `/credit-products`** — список продуктов

- Auth: не требуется (публичный каталог)
- Query: `page`, `page_size`, `ordering` (`interest_rate`, `-max_amount`), `search` (по name/description), фильтры: `min_amount`, `max_amount`, `is_active` (только для staff).
- Response `200` (пагинация): см. DOC 0 §5.2
```json
{
  "count": 4, "next": null, "previous": null,
  "results": [
    { "id": 1, "name": "Потребительский", "slug": "consumer",
      "min_amount": "10000.00", "max_amount": "500000.00",
      "interest_rate": "18.50", "min_term_months": 3, "max_term_months": 36,
      "is_active": true }
  ]
}
```

---
**GET `/credit-products/{id}`** — детали продукта

- Path: `id`
- Response `200`: полный объект продукта.
- Ошибки: `404` NOT_FOUND.

### 8.4 Credit Applications

Все эндпоинты требуют Bearer. Доступ — только к своим заявкам (owner-based, permission `IsOwner`).

---
**GET `/credit-applications`** — список своих заявок

- Query: `page`, `page_size`, `ordering` (`-created_at`, `amount`), `search` (по purpose), фильтры: `status`, `product`, `min_amount`, `max_amount`.
- Response `200` (пагинация):
```json
{
  "count": 2, "next": null, "previous": null,
  "results": [
    { "id": 42, "product": 1, "amount": "200000.00", "term_months": 12,
      "status": "APPROVED", "monthly_payment": "18350.00",
      "created_at": "2026-07-09T10:22:00Z" }
  ]
}
```

---
**POST `/credit-applications`** — создать заявку (DRAFT)

- Request Body:
```json
{ "product": 1, "amount": "200000.00", "term_months": 12, "purpose": "Ремонт" }
```
- Валидация: продукт существует и активен; сумма/срок в диапазоне продукта.
- Response `201`: созданная заявка со `status: "DRAFT"`.
- Ошибки: `400`, `401`, `404` (продукт не найден).

---
**GET `/credit-applications/{id}`** — детали заявки

- Response `200`: заявка + вложенный `scoring_result` (если есть).
- Ошибки: `401`, `403`/`404` (чужая заявка → возвращаем `404`, чтобы не раскрывать существование).

---
**PUT `/credit-applications/{id}`** — редактировать (только DRAFT)

- Request Body: `{ "amount": "...", "term_months": ..., "purpose": "..." }`
- Правило: редактирование доступно только если `status == DRAFT`.
- Response `200`.
- Ошибки: `400`, `401`, `404`, `409` CONFLICT (не DRAFT).

---
**DELETE `/credit-applications/{id}`** — удалить (только DRAFT)

- Response `204`.
- Ошибки: `401`, `404`, `409` (не DRAFT).

---
**POST `/credit-applications/{id}/submit`** — отправить на скоринг

- Request Body: пустой.
- Логика: DRAFT → SUBMITTED → SCORING → APPROVED/REJECTED (синхронно).
- Response `200`: заявка с финальным статусом и `monthly_payment`.
- Ошибки: `401`, `404`, `409` (не DRAFT), `400` (сумма/срок вне диапазона).

---

## 9. Аутентификация JWT

### 9.1 Конфигурация SimpleJWT

```python
# config/settings.py
from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,     # на Junior — без ротации
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
}
```

### 9.2 Permission IsOwner

```python
# apps/applications/permissions.py
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
```

> В ViewSet используется `get_queryset` с фильтром `filter(user=request.user)` — чужие объекты не попадают в выборку вовсе, поэтому детальный запрос к чужой заявке отдаёт `404`.

---

## 10. Pagination / Filter / Sort / Search

```python
# common/pagination.py
from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
```

```python
# apps/applications/filters.py
import django_filters as df
from .models import CreditApplication

class ApplicationFilter(df.FilterSet):
    min_amount = df.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = df.NumberFilter(field_name="amount", lookup_expr="lte")
    class Meta:
        model = CreditApplication
        fields = ["status", "product"]
```

```python
# ViewSet
class ApplicationViewSet(ModelViewSet):
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ApplicationFilter
    ordering_fields = ["created_at", "amount", "status"]
    ordering = ["-created_at"]
    search_fields = ["purpose"]

    def get_queryset(self):
        return CreditApplication.objects.filter(user=self.request.user)\
            .select_related("product", "scoringresult")
```

---

## 11. Загрузка изображений

```python
# apps/accounts/services.py
from PIL import Image

MAX_AVATAR_SIZE = 2 * 1024 * 1024   # 2 MB
ALLOWED_TYPES = {"image/jpeg", "image/png"}

def upload_avatar(profile, file):
    if file.content_type not in ALLOWED_TYPES:
        raise ValidationError({"avatar": "Only JPEG/PNG allowed"})
    if file.size > MAX_AVATAR_SIZE:
        raise ValidationError({"avatar": "File too large (max 2MB)"})
    img = Image.open(file)
    img.thumbnail((400, 400))
    # сохранение через ImageField storage
    profile.avatar.save(f"{profile.id}.jpg", file, save=True)
    return profile
```

---

## 12. Swagger / OpenAPI

```python
# config/settings.py
INSTALLED_APPS += ["drf_spectacular"]
REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"
SPECTACULAR_SETTINGS = {
    "TITLE": "CreditFlow API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
```

```python
# config/urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
```

Доступ: `/api/docs/` — Swagger UI; `/api/schema/` — OpenAPI JSON.

---

## 13. Тестирование

### 13.1 Unit (services)

```python
def test_calc_annuity():
    from apps.applications.services import calc_annuity
    from decimal import Decimal
    p = calc_annuity(Decimal("100000"), Decimal("12"), 12)
    assert Decimal("8800") < p < Decimal("8900")
```

### 13.2 Integration (API)

```python
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_register_and_login():
    client = APIClient()
    r = client.post("/api/v1/auth/register",
                    {"email": "a@b.com", "password": "StrongPass123"})
    assert r.status_code == 201
    r = client.post("/api/v1/auth/login",
                    {"email": "a@b.com", "password": "StrongPass123"})
    assert r.status_code == 200
    assert "access" in r.data

@pytest.mark.django_db
def test_submit_flow(client_authed, credit_product):
    r = client_authed.post("/api/v1/credit-applications",
        {"product": credit_product.id, "amount": "200000.00", "term_months": 12})
    app_id = r.data["id"]
    r = client_authed.post(f"/api/v1/credit-applications/{app_id}/submit")
    assert r.data["status"] in ("APPROVED", "REJECTED")
```

**Целевое покрытие:** ≥ 70% для services, ≥ 60% общее.

---

## 14. Definition of Done + Acceptance Criteria

**Definition of Done:**
- Все модели созданы, миграции применяются с нуля без ошибок.
- Все эндпоинты из §8 реализованы и возвращают корректные статусы.
- JWT (access+refresh) работает, refresh обновляет access.
- Пагинация/фильтры/сортировка/поиск работают на заявках и продуктах.
- Аватар загружается, валидируется, ресайзится.
- Swagger UI доступен и отражает все эндпоинты.
- Тесты зелёные, покрытие ≥60%.
- Owner-based доступ: пользователь не видит чужие заявки.

**Acceptance Criteria (примеры):**

| # | Given | When | Then |
|---|---|---|---|
| AC-1 | Новый email | POST /register | 201, создан User+Profile, роль CLIENT |
| AC-2 | Существующий email | POST /register | 409 EMAIL_TAKEN |
| AC-3 | Валидные креды | POST /login | 200, access+refresh |
| AC-4 | Истёкший access | GET /profile | 401 TOKEN_EXPIRED |
| AC-5 | Валидный refresh | POST /refresh | 200, новый access |
| AC-6 | DRAFT-заявка, сумма в диапазоне | POST /{id}/submit | 200, статус APPROVED/REJECTED |
| AC-7 | Не-DRAFT заявка | POST /{id}/submit | 409 CONFLICT |
| AC-8 | Чужая заявка | GET /{id} | 404 |
| AC-9 | Файл 5 МБ | POST /avatar | 400 (too large) |

**Что считается ошибкой:** бизнес-логика во views вместо services; отсутствие валидации диапазона суммы; чужие заявки видны в списке; пароль в открытом виде; отсутствие индексов на FK.

---

## 15. Roadmap реализации

```
Этап 1 — Фундамент (зависимостей нет)
  1. Настройка проекта, settings, PostgreSQL, .env
  2. Кастомная модель User + UserManager
  3. Миграции, common/ (pagination, exceptions, responses)

Этап 2 — Auth (зависит от User)
  4. Регистрация (service + serializer + view)
  5. Login/Refresh (SimpleJWT)
  6. /auth/me
  7. Тесты auth

Этап 3 — Profile (зависит от User)
  8. Модель Profile + сигнал/сервис создания
  9. GET/PUT /profile
  10. Загрузка аватара (Pillow)

Этап 4 — Products (независим)
  11. Модель CreditProduct + constraints
  12. GET list/detail + фильтры/поиск/сортировка
  13. Наполнение тестовыми данными (fixtures/seed)

Этап 5 — Applications (зависит от User + Product + Profile)
  14. Модели CreditApplication + ScoringResult
  15. CRUD (owner-based)
  16. services: calc_annuity, submit, run_scoring
  17. POST /submit
  18. Фильтры/поиск/сортировка

Этап 6 — Финализация
  19. drf-spectacular / Swagger
  20. Интеграционные тесты полного флоу
  21. Проверка Acceptance Criteria
```
