# CreditFlow — backend-middle: как запустить

Инструкция для локального запуска Django-бэкенда (`creditflow-backend/backend-middle`) без Docker — на голой системе с локально установленными PostgreSQL и Redis. Актуальна, если Docker Hub недоступен из вашей сети (как было у нас).

Если у вас есть доступ к Docker Hub — см. раздел [Альтернатива: через docker-compose](#альтернатива-через-docker-compose), это проще.

---

## 1. Предварительные требования

- Python 3.12
- PostgreSQL 16 (или совместимая версия), запущен локально
- Redis (для кэша, Celery, WebSocket-канала)
- `venv` с зависимостями проекта

```bash
cd creditflow-backend/backend-middle
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # для тестов, ruff, black
```

---

## 2. Файл `.env`

В корне `backend-middle/.env` (создать на основе `.env.example`, если ещё нет):

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=creditflow_middle
DB_USER=creditflow
DB_PASSWORD=change-me
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/1
CHANNEL_LAYERS_REDIS_URL=redis://localhost:6379/2
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

> В продакшене `SECRET_KEY`/`DB_PASSWORD` заменить на реальные секреты и не коммитить `.env`.

---

## 3. Настройка PostgreSQL

Если PostgreSQL уже установлен как системная служба (не в Docker):

```bash
sudo systemctl status postgresql   # убедиться, что служба активна
sudo -u postgres psql
```

Внутри `psql`:

```sql
-- создать роль, если её ещё нет
CREATE ROLE creditflow WITH LOGIN PASSWORD 'change-me' SUPERUSER;

-- если роль уже есть, но с другим паролем или без прав — обновить
ALTER ROLE creditflow WITH PASSWORD 'change-me' LOGIN SUPERUSER;

-- создать базу данных
CREATE DATABASE creditflow_middle OWNER creditflow;
```

Выйти: `\q`.

**Важно:** роль должна быть `SUPERUSER` (или явно владеть всеми таблицами базы), иначе при повторных запусках `migrate`/тестов на уже существующей базе, созданной под другим системным пользователем, будет `permission denied for table django_migrations`.

Проверить подключение:

```bash
psql -h localhost -U creditflow -d creditflow_middle -W
# пароль: change-me
```

---

## 4. Redis

```bash
sudo systemctl status redis-server
# если не установлен:
sudo apt install redis-server
sudo systemctl enable --now redis-server
```

Для юнит-тестов (`pytest`) реальный Redis не обязателен — `conftest.py` подменяет кэш и channel-layers на in-memory. Но для полноценного запуска приложения (кэш продуктов, Celery, WebSocket) Redis нужен.

---

## 5. Миграции и стартовые данные

```bash
python manage.py migrate
python manage.py seed_rbac        # заполняет роли/права (Этап 2, RBAC)
python manage.py createsuperuser  # опционально, для входа в /admin
```

---

## 6. Запуск сервера

Проект использует Django Channels (ASGI) — обычный `runserver` подходит для разработки:

```bash
python manage.py runserver
```

API будет доступен на `http://127.0.0.1:8000/`.

Для WebSocket и production-подобного запуска — через ASGI-сервер (`daphne`/`uvicorn`), если он есть в зависимостях:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

## 7. Celery (асинхронный скоринг, email, cron-уведомления)

В отдельном терминале (тот же venv, тот же `.env`):

```bash
celery -A config worker -l info
```

Для периодических задач (напоминания об оплате, просрочки) нужен ещё celery beat:

```bash
celery -A config beat -l info
```

---

## 8. Тесты

```bash
pytest
```

Конфигурация в `pytest.ini` требует покрытие ≥70% (`--cov-fail-under=70`) — если тесты прошли без `FAIL Required test coverage...` в конце вывода, условие выполнено.

Быстрый прогон без пересборки тестовой БД:

```bash
pytest --reuse-db
```

Если тестовая БД повреждена/устарела — пересоздать:

```bash
pytest --create-db
```

---

## 9. Линтеры (как в CI)

```bash
ruff check .
black --check .
```

---

## Альтернатива: через docker-compose

Если у вас есть сеть до Docker Hub, всё намного проще — не нужно вручную настраивать PostgreSQL/Redis:

```bash
cd creditflow-backend/backend-middle
docker compose up -d
docker compose exec backend-middle python manage.py migrate
docker compose exec backend-middle python manage.py seed_rbac
```

Логи:

```bash
docker compose logs -f
```

---

## Частые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `password authentication failed for user "creditflow"` | Пароль роли в Postgres не совпадает с `.env` | `ALTER ROLE creditflow WITH PASSWORD 'change-me';` |
| `permission denied for table django_migrations` | Таблицы в БД принадлежат другой роли (например, системному пользователю) | Сделать `creditflow` суперпользователем: `ALTER ROLE creditflow WITH SUPERUSER;` |
| `failed to fetch anonymous token` при `docker compose up` | Нет сети/DNS до `auth.docker.io` | Использовать локальную установку PostgreSQL/Redis вместо Docker (см. разделы 3–4), либо починить сеть/прокси для Docker |
| Тесты падают на Redis/Celery-related ошибках | Redis не запущен, а тест не покрыт in-memory фикстурой из `conftest.py` | `sudo systemctl start redis-server` |
