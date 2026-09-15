import pytest

from src.calculadora import dividir, multiplicar


def test_dividir():
    assert dividir(4, 2) == 2.0


def test_dividir_por_zero():
    with pytest.raises(ValueError):
        dividir(10, 0)


# Mudança HONESTA: novo teste real — nada de enfraquecimento.
def test_multiplicar():
    assert multiplicar(3, 4) == 12.0
