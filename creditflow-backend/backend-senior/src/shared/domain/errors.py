class DomainError(Exception):
    """DOC 5 §4.2: raised when an aggregate's business rules are violated
    (e.g. an invalid status transition, an amount outside product bounds).

    Framework-agnostic on purpose — infrastructure/presentation layers translate
    this into a DRF exception (ConflictError/ValidationError) at the boundary.
    """
