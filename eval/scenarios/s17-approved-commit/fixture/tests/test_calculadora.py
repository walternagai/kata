import pytest

from src.calculadora import dividir, formatar_resultado


def test_dividir():
    assert dividir(10, 2) == 5.0


def test_formatar_resultado():
    assert formatar_resultado(3.14159) == "3.14"


def test_dividir_por_zero():
    with pytest.raises(ValueError):
        dividir(10, 0)
