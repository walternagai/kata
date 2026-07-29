from src.parser import parse


def test_parse():
    assert parse(' x ') == 'OUTRO'
