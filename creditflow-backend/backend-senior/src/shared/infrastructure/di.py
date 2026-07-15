"""DOC 5 §6.2: dependency-injection primitives.

Hand-rolled rather than the `dependency_injector` package the doc's example uses —
this project doesn't otherwise depend on it, and `Factory`/`Singleton` cover the
DoD requirement ("use cases вызываются через DI") without adding a new third-party
dependency. Swap for `dependency_injector` later if provider composition outgrows
this (e.g. overrides for testing, wiring modules) — see ASSUMPTIONS in Этап 1 report.

No bounded-context bindings are registered here yet: each context wires its own
`Container` subclass once its infrastructure layer (repositories, use cases)
exists, starting Этап 2.
"""

from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class Provider(Generic[T]):
    def __call__(self) -> T:
        raise NotImplementedError


class Factory(Provider[T]):
    """Resolves a new instance on every call. Dependencies passed as kwargs may
    themselves be Providers (resolved lazily) or plain values.
    """

    def __init__(self, factory: Callable[..., T], **kwargs):
        self._factory = factory
        self._kwargs = kwargs

    def __call__(self) -> T:
        resolved = {
            key: (value() if isinstance(value, Provider) else value)
            for key, value in self._kwargs.items()
        }
        return self._factory(**resolved)


class Singleton(Factory[T]):
    """Resolves once, then returns the same instance on every subsequent call."""

    def __init__(self, factory: Callable[..., T], **kwargs):
        super().__init__(factory, **kwargs)
        self._instance: T | None = None

    def __call__(self) -> T:
        if self._instance is None:
            self._instance = super().__call__()
        return self._instance


class Container:
    """Base class for bounded-context DI containers composed of Factory/Singleton
    providers declared as class attributes, e.g.:

        class LendingContainer(Container):
            application_repo = Factory(DjangoApplicationRepository)
            submit_application = Factory(SubmitApplicationUseCase, repo=application_repo)
    """
