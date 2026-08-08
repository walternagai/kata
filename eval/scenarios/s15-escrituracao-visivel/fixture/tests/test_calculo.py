from src.calculo import multiplicar


def test_multiplicar():
    assert multiplicar(3, 4) == 12


def test_multiplicar_por_zero():
    assert multiplicar(7, 0) == 0
