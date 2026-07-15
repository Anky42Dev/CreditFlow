"""DOC 5 §14, Roadmap Этап 5 п.14: Transaction/AuditLog are partitioned by
month on `created_at` (migrations apps/lending/migrations/0003_partition_by_month.py,
apps/audit/migrations/0002_partition_by_month.py). These run against the real
Postgres test DB (required by this project's test setup, see RUNNING.md) —
no mocking needed to verify native partitioning actually took effect.
"""
from decimal import Decimal

import pytest
from django.db import connection

from apps.accounts.models import User
from apps.applications.models import CreditApplication
from apps.audit.models import AuditLog
from apps.lending.models import Loan, Transaction
from apps.products.models import CreditProduct


def _relkind(table_name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT relkind FROM pg_class WHERE relname = %s", [table_name])
        row = cursor.fetchone()
        return row[0] if row else None


def _partition_of_row(table_name, pk_id):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT tableoid::regclass FROM {table_name} WHERE id = %s", [pk_id])
        row = cursor.fetchone()
        return str(row[0]) if row else None


@pytest.mark.django_db
def test_transactions_table_is_natively_partitioned_by_range():
    assert _relkind("transactions") == "p"  # 'p' = partitioned table


@pytest.mark.django_db
def test_audit_logs_table_is_natively_partitioned_by_range():
    assert _relkind("audit_logs") == "p"


@pytest.mark.django_db
def test_new_transaction_row_lands_in_this_months_partition():
    user = User.objects.create_user(email="partition-tx@example.com", password="pw12345")
    product = CreditProduct.objects.create(
        name="Test", slug="test-partition", min_amount=Decimal("1000"), max_amount=Decimal("100000"),
        interest_rate=Decimal("10.00"), min_term_months=1, max_term_months=12, is_active=True,
    )
    application = CreditApplication.objects.create(
        user=user, product=product, amount=Decimal("10000.00"), term_months=6,
    )
    loan = Loan.objects.create(
        application=application, user=user, principal=Decimal("10000.00"),
        interest_rate=Decimal("10.00"), term_months=6, monthly_payment=Decimal("1750.00"),
        outstanding_balance=Decimal("10000.00"), disbursed_at="2026-07-01T00:00:00Z",
    )
    tx = Transaction.objects.create(
        loan=loan, type="DISBURSEMENT", amount=Decimal("10000.00"), balance_after=Decimal("10000.00"),
    )

    partition = _partition_of_row("transactions", tx.id)
    expected = tx.created_at.strftime("transactions_%Y_%m")
    assert partition == expected


@pytest.mark.django_db
def test_new_audit_log_row_lands_in_this_months_partition():
    entry = AuditLog.objects.create(
        actor=None, action="test.action", object_type="Test", object_id=1, changes={},
    )

    partition = _partition_of_row("audit_logs", entry.id)
    expected = entry.created_at.strftime("audit_logs_%Y_%m")
    assert partition == expected


def _make_loan(email, slug):
    user = User.objects.create_user(email=email, password="pw12345")
    product = CreditProduct.objects.create(
        name=slug, slug=slug, min_amount=Decimal("1000"), max_amount=Decimal("100000"),
        interest_rate=Decimal("10.00"), min_term_months=1, max_term_months=12, is_active=True,
    )
    application = CreditApplication.objects.create(
        user=user, product=product, amount=Decimal("10000.00"), term_months=6,
    )
    return Loan.objects.create(
        application=application, user=user, principal=Decimal("10000.00"),
        interest_rate=Decimal("10.00"), term_months=6, monthly_payment=Decimal("1750.00"),
        outstanding_balance=Decimal("10000.00"), disbursed_at="2026-07-01T00:00:00Z",
    )


def _raw_insert_transaction(loan_id, idempotency_key, created_at):
    """`created_at` has auto_now_add=True, so the ORM always overrides any
    explicit value passed to .create() — these two tests need precise
    control over it to exercise the (idempotency_key, created_at) constraint
    directly, so they insert via raw SQL instead."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO transactions (loan_id, type, amount, balance_after, created_at, idempotency_key)
            VALUES (%s, 'REPAYMENT', 100.00, 9900.00, %s, %s)
            """,
            [loan_id, created_at, idempotency_key],
        )


@pytest.mark.django_db
def test_transaction_idempotency_key_unique_constraint_still_blocks_true_duplicates():
    """The (idempotency_key, created_at) constraint still does its job for a
    real duplicate insert (same key, same instant — e.g. a retried request
    that resolves to an identical timestamp)."""
    loan = _make_loan("partition-idem-1@example.com", "test-partition-1")

    from django.db import IntegrityError
    from django.db import transaction as db_transaction

    _raw_insert_transaction(loan.id, "dup-key", "2026-07-14T10:00:00Z")
    with pytest.raises(IntegrityError):
        with db_transaction.atomic():
            _raw_insert_transaction(loan.id, "dup-key", "2026-07-14T10:00:00Z")


@pytest.mark.django_db
def test_transaction_idempotency_key_trade_off_allows_same_key_at_different_instants():
    """Documents the trade-off (see Transaction's docstring): uniqueness is
    now (idempotency_key, created_at), not idempotency_key alone — required
    because Postgres partitioned tables must include the partition key in
    every unique constraint. In practice `apps.lending.services` always
    checks-then-creates inside one transaction, so this gap isn't reachable
    from the real request flow — this test just makes the DB-level relaxation
    explicit and regression-checked."""
    loan = _make_loan("partition-idem-2@example.com", "test-partition-2")

    _raw_insert_transaction(loan.id, "same-key", "2026-07-14T10:00:00Z")
    # Different created_at -> the composite constraint does not fire, unlike
    # the old lone-column unique=True which would have rejected this.
    _raw_insert_transaction(loan.id, "same-key", "2026-07-14T11:00:00Z")

    assert Transaction.objects.filter(idempotency_key="same-key").count() == 2
