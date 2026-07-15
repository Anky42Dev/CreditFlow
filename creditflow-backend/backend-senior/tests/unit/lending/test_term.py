import pytest

from lending.domain.value_objects.term import Term


def test_valid_term():
    assert Term(12).months == 12


def test_zero_term_rejected():
    with pytest.raises(ValueError):
        Term(0)


def test_negative_term_rejected():
    with pytest.raises(ValueError):
        Term(-3)
