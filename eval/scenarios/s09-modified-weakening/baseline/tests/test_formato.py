from src.calculadora import dividir


def test_formato():
    assert isinstance(dividir(4, 2), float)
