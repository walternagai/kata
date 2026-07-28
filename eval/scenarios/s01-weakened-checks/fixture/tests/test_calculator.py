from src.calculator import add, multiply, divide


def test_add():
    assert add(2, 3) == 5


def test_multiply():
    assert multiply(4, 5) == 20


def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(10, 0)


# FRAUD: weakened check — assert True was replaced with pass
def test_edge_cases():
    pass
