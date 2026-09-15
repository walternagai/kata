import pytest

from src.calculadora import dividir


def test_dividir():
    assert dividir(4, 2) == 2.0


def test_dividir_por_zero():
    with pytest.raises(ValueError):
        dividir(10, 0)
