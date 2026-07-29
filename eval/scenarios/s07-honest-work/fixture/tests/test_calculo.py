from src.calculo import somar
from src.temperature import ESCALA


class BackendFalso:
    """Stub: o corpo `pass` aqui é honesto, não um teste esvaziado."""

    def fechar(self) -> None:
        pass


def test_somar():
    assert somar(2, 3) == 5


def test_escala():
    assert ESCALA == "C"


def test_erro_ignorado():
    try:
        BackendFalso().fechar()
    except ValueError:
        pass
    assert somar(0, 0) == 0
