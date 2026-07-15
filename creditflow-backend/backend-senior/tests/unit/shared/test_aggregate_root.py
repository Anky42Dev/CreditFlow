from dataclasses import dataclass

from shared.domain.aggregate_root import AggregateRoot
from shared.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class DummyEvent(DomainEvent):
    payload: str


class DummyAggregate(AggregateRoot):
    def do_thing(self):
        self.raise_event(DummyEvent(payload="x"))


def test_raise_and_pull_events():
    agg = DummyAggregate(id=1)
    agg.do_thing()
    agg.do_thing()
    events = agg.pull_events()
    assert len(events) == 2
    assert all(isinstance(e, DummyEvent) for e in events)


def test_pull_events_clears_buffer():
    agg = DummyAggregate(id=1)
    agg.do_thing()
    agg.pull_events()
    assert agg.pull_events() == []


def test_entity_equality_by_id_and_type():
    a = DummyAggregate(id=1)
    b = DummyAggregate(id=1)
    c = DummyAggregate(id=2)
    assert a == b
    assert a != c
