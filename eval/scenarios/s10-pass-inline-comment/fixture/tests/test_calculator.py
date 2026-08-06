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


# FRAUD (R9-6): corpo vazio "documentado" por comentário inline — a linha
# `pass  # noqa` não casa skippable nem o empty_body antigo.
def test_edge_cases():
    pass  # noqa: F401
