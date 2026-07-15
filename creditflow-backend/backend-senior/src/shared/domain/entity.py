class Entity:
    """DOC 5 §3, §4: base for domain entities — identity-based equality, no ORM/Django import."""

    def __init__(self, id):
        self.id = id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))
