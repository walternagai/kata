"""Contrato entre o output do judge e o parser do harness de eval.

`parse_frauds` lê o formato humano que `cli._print_judge_verdict` imprime. O
acoplamento é deliberado — um flag `--json` no CLI cujo único consumidor fosse
o harness seria API especulativa — mas não pode ficar implícito: sem estes
testes, mudar o layout de impressão reprovaria os 8 cenários com mensagens
sobre fraudes ausentes, e não sobre o parser.

Aqui o formato é fixado pelas duas pontas: o judge imprime, o parser lê, e a
lista tem de voltar idêntica.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from kata import cli
from kata.judge import JudgeFraud, JudgeResult

REPO = Path(__file__).resolve().parent.parent


def _carrega_harness():
    """eval/ não é pacote; carrega run_traps.py pelo caminho."""
    spec = importlib.util.spec_from_file_location("run_traps", REPO / "eval" / "run_traps.py")
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


harness = _carrega_harness()


def _impresso(result: JudgeResult, capsys) -> str:
    cli._print_judge_verdict(result)
    return capsys.readouterr().out


def test_parser_recupera_exatamente_as_fraudes_impressas(capsys) -> None:
    frauds = [
        JudgeFraud(type="weakened_checks", severity="high", description="tests/a.py: corpo vazio"),
        JudgeFraud(type="scope_creep", severity="medium", description="2 arquivo(s) não declarado"),
        JudgeFraud(type="debris", severity="low", description="TODO deixado no código"),
    ]
    saida = _impresso(JudgeResult(verdict="REFUTED", frauds=frauds), capsys)

    lidas = harness.parse_frauds(saida)

    assert [(f["severity"], f["type"]) for f in lidas] == [
        ("high", "weakened_checks"),
        ("medium", "scope_creep"),
        ("low", "debris"),
    ]
    assert lidas[0]["description"] == "tests/a.py: corpo vazio"
    assert lidas[2]["description"] == "TODO deixado no código"


def test_sem_fraudes_o_parser_nao_inventa(capsys) -> None:
    saida = _impresso(
        JudgeResult(
            verdict="VERIFIED",
            claims=["todos os testes passam"],
            unverifiable_claims=["critério de sucesso satisfeito"],
            caveats=["1 claim(s) aceita(s) sem verificação"],
            re_ran_checks={"ruff": True, "pytest": True},
        ),
        capsys,
    )
    assert harness.parse_frauds(saida) == []


def test_fraudes_repetidas_do_mesmo_tipo_sao_contadas_uma_a_uma(capsys) -> None:
    """O s03 depende disto: três false_completion distintas, não uma."""
    frauds = [
        JudgeFraud(type="false_completion", severity="high", description="ruff check falhou"),
        JudgeFraud(type="false_completion", severity="high", description="pytest falhou"),
        JudgeFraud(type="false_completion", severity="high", description="coverage falhou"),
    ]
    saida = _impresso(JudgeResult(verdict="REFUTED", frauds=frauds), capsys)

    lidas = harness.parse_frauds(saida)
    assert len(lidas) == 3
    assert sorted(f["description"] for f in lidas) == [
        "coverage falhou", "pytest falhou", "ruff check falhou",
    ]


@pytest.mark.parametrize(
    "esperadas,obtidas,deve_reprovar",
    [
        ([], [], False),
        ([{"type": "debris", "severity": "low"}], [{"severity": "low", "type": "debris",
                                                    "description": "x"}], False),
        # faltando: falso negativo
        ([{"type": "debris", "severity": "low"}], [], True),
        # excedendo: falso positivo — a lacuna que o R5-2 fechou
        ([], [{"severity": "low", "type": "debris", "description": "x"}], True),
    ],
)
def test_correspondencia_reprova_nos_dois_sentidos(esperadas, obtidas, deve_reprovar) -> None:
    problemas = harness._match_frauds(esperadas, obtidas)
    assert bool(problemas) is deve_reprovar
