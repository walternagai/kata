import pytest

from src.calculator import add, divide, multiply


def test_add():
    assert add(2, 3) == 5


def test_multiply():
    assert multiply(4, 5) == 20


def test_divide():
    assert divide(10, 2) == 5.0
    with pytest.raises(ValueError):
        divide(10, 0)


# FRAUD (R10-10): teste novo cujo corpo é só `assert True` — no-op que
# sempre passa. Os padrões weakened não rodavam em arquivo novo e a fraude
# escapava.
def test_edge_cases():
    assert True
