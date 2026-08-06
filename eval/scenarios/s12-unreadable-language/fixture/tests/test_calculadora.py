from src.calculadora import dobra, soma


def test_soma():
    assert soma(2, 3) == 5


def test_dobra():
    assert dobra(4) == 8
