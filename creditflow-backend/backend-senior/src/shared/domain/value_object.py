from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """DOC 5 §3, §4.1: marker base for immutable value objects, compared by value.

    Subclasses are plain `@dataclass(frozen=True)`; equality/hash come for free
    from the dataclass machinery once all fields are hashable.
    """
