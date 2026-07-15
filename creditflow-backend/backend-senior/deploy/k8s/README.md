# Kubernetes — концептуальная архитектура

DOC 5 §15.2, Roadmap Этап 8 п.21: доки явно формулируют этот раздел как
"концептуально" — здесь описание архитектуры, а не исполняемые манифесты.
Соответствие сервисам `deploy/docker-compose.prod.yml`:

## Deployments (stateless, HPA)

| Deployment | Из compose-сервиса | Реплики (старт) | HPA-метрика |
|---|---|---|---|
| `web` | `web` | 3 | CPU > 70% |
| `scoring` | `scoring` | 2 | CPU > 70% |
| `scoring-consumer` | `scoring-consumer` | 1 | длина очереди `ApplicationSubmitted` (KEDA/RabbitMQ) |
| `celery-worker-scoring` | `celery-worker-scoring` | 2 | длина очереди `scoring` (KEDA/RabbitMQ или Redis) |
| `celery-worker-email` | `celery-worker-email` | 1 | длина очереди `email` |
| `celery-worker-schedule` | `celery-worker-schedule` | 1 | длина очереди `schedule` |
| `celery-worker-default` | `celery-worker-default` | 1 | CPU |
| `outbox-relay` | `outbox-relay` | 1-2 | не масштабируется агрессивно — `select_for_update(skip_locked=True)` (apps/outbox/tasks.py) допускает несколько реплик без двойной публикации, но большая очередь — сигнал к расследованию, не просто к scale-out |
| `saga-worker` | `saga-worker` | 1-2 | длина очереди Saga-команд |
| `celery-beat` | `celery-beat` | **1 обязательно** — дублирование ломает cron-расписание (двойные тики `relay-outbox`, `check-overdue-payments`) |
| `nginx` | `nginx` | 2+ | CPU / за Ingress-контроллером может не понадобиться отдельно |

## StatefulSets (хранят состояние)

| StatefulSet | Из compose-сервиса | Примечание |
|---|---|---|
| `postgres` | `db` + `db-replica` | `db-replica` — не игрушечный контейнер как в compose.prod, а настоящий standby через `pg_basebackup`/replication slot или managed Postgres (RDS/CloudSQL) вместо самостоятельного StatefulSet |
| `rabbitmq` | `rabbitmq` | кластер из 3 узлов для отказоустойчивости очередей |
| `redis` | `redis` | Redis Sentinel/Cluster вместо одного пода — §15.3 "Кэш/сессии: Redis-кластер" |
| `minio` | `minio` | или managed S3 вместо самостоятельного StatefulSet |

`pgbouncer`, `prometheus`, `grafana`, `jaeger` — обычные Deployments с одной репликой (не тянут состояние критично; Prometheus — с PVC под TSDB).

## Services + Ingress

- `ClusterIP` для каждого Deployment/StatefulSet выше (внутренний трафик).
- `Ingress` (nginx-ingress или облачный LB-контроллер) вместо самостоятельного `nginx`-контейнера — TLS termination там же, где сейчас `deploy/nginx/nginx.conf`; сертификат — через cert-manager, а не `gen-cert.sh`.

## ConfigMap / Secret

- `ConfigMap creditflow-config`: несекретные переменные из `deploy/.env.prod` (ALLOWED_HOSTS, DEBUG, AWS_S3_REGION_NAME, ...).
- `Secret creditflow-secrets`: SECRET_KEY, DB_PASSWORD, AWS_SECRET_ACCESS_KEY, GRAFANA_ADMIN_PASSWORD — через внешний secret-manager (Vault/Sealed Secrets/cloud KMS), не как git-committed YAML.

## Probes

DOC 5 §13 / `apps/health/`:
- `livenessProbe`: `GET /health/live`
- `readinessProbe`: `GET /health/ready` (db, **replica_db** — Этап 8 AC-10 фикс, redis, broker)
- `startupProbe`: `GET /health/startup` (миграции применены)

## HPA

- `web`: `HorizontalPodAutoscaler` по CPU (target 70%), min 3 / max 10.
- `celery-worker-scoring` / `scoring`: по длине очереди (`ApplicationSubmitted`, RabbitMQ) через KEDA `ScaledObject`, а не голый CPU-HPA — нагрузка скоринга не CPU-bound, а throughput-bound (§15.3 "Скоринг: отдельный autoscale по длине очереди").
- `db`/`db-replica`: без HPA — вертикальное масштабирование + read replica (§15.3), не горизонтальное.

## Отличия от docker-compose.prod

- `db-replica` в compose.prod — заглушка (второй `postgres:16` без стриминга) для локальной проверки AC-10; в K8s это реальный standby.
- `outbox-relay`/Celery-очереди в compose.prod — процессы `celery worker -Q <queue>`; в K8s то же самое, просто с HPA/KEDA вместо ручного `--scale`.
- `jaeger` в compose.prod — `all-in-one` (in-memory storage, теряет трейсы при рестарте); в K8s — `jaeger-operator` с Elasticsearch/Cassandra backend для персистентности.
