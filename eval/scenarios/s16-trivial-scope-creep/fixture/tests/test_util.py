from src.util import saudacao
from src.helper import dobrar


def test_saudacao():
    assert saudacao("Kata") == "Olá, Kata!"


def test_dobrar():
    assert dobrar(5) == 10
