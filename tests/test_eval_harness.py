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
        "coverage falhou",
        "pytest falhou",
        "ruff check falhou",
    ]


@pytest.mark.parametrize(
    "esperadas,obtidas,deve_reprovar",
    [
        ([], [], False),
        (
            [{"type": "debris", "severity": "low"}],
            [{"severity": "low", "type": "debris", "description": "x"}],
            False,
        ),
        # faltando: falso negativo
        ([{"type": "debris", "severity": "low"}], [], True),
        # excedendo: falso positivo — a lacuna que o R5-2 fechou
        ([], [{"severity": "low", "type": "debris", "description": "x"}], True),
    ],
)
def test_correspondencia_reprova_nos_dois_sentidos(esperadas, obtidas, deve_reprovar) -> None:
    problemas = harness._match_frauds(esperadas, obtidas)
    assert bool(problemas) is deve_reprovar


def test_eval_exige_codigo_de_saida_coerente_com_veredito() -> None:
    ground_truth = {"expected_verdict": "VERIFIED", "expected_frauds": []}
    output = {
        "returncode": 1,
        "stdout": "✅  KATA JUDGE — VERIFIED\n",
        "stderr": "",
    }

    passed, messages = harness.evaluate(Path("."), ground_truth, output)

    assert passed is False
    assert any("Código de saída" in message for message in messages)


def test_ground_truth_exige_veredito(tmp_path) -> None:
    (tmp_path / "ground_truth.yaml").write_text("expected_frauds: []\n", encoding="utf-8")

    with pytest.raises(harness.ScenarioError, match="expected_verdict"):
        harness.load_ground_truth(tmp_path)


def test_ground_truth_rejeita_leave_untracked_nao_lista(tmp_path) -> None:
    """P2-5: string viraria iteração por caractere no git rm --cached —
    erro nomeado no load, não diagnóstico enganoso."""
    (tmp_path / "ground_truth.yaml").write_text(
        "expected_verdict: REFUTED\nleave_untracked: tests/test_x.py\n",
        encoding="utf-8",
    )

    with pytest.raises(harness.ScenarioError, match="leave_untracked"):
        harness.load_ground_truth(tmp_path)


def test_ground_truth_rejeita_expected_absent_nao_lista(tmp_path) -> None:
    (tmp_path / "ground_truth.yaml").write_text(
        "expected_verdict: VERIFIED\nexpected_absent: scratch\n",
        encoding="utf-8",
    )

    with pytest.raises(harness.ScenarioError, match="expected_absent"):
        harness.load_ground_truth(tmp_path)


@pytest.mark.parametrize("chave", ["tamper_base_commit", "kata_visivel"])
def test_ground_truth_rejeita_chave_booleana_nao_booleana(tmp_path, chave: str) -> None:
    """R11-3: as chaves booleanas governam o SETUP do fixture. Um valor que
    não é booleano ("sim", "false") seria lido como truthy e montaria um
    ambiente diferente do que o cenário declara — cenário passando ou
    reprovando por motivo que ninguém escreveu."""
    (tmp_path / "ground_truth.yaml").write_text(
        f"expected_verdict: VERIFIED\n{chave}: sim\n",
        encoding="utf-8",
    )

    with pytest.raises(harness.ScenarioError, match=chave):
        harness.load_ground_truth(tmp_path)


def test_init_git_repo_respeita_kata_visivel(tmp_path) -> None:
    """R11-3: com `.kata/` no exclude, o arquivo da própria tarefa some do
    diff e o judge nunca tem chance de contá-lo como scope creep — foi assim
    que a classe atravessou dez rodadas e o s07-honest-work."""
    (tmp_path / ".kata").mkdir()
    (tmp_path / ".kata" / "t.yaml").write_text("task: t\n", encoding="utf-8")

    harness.init_git_repo(tmp_path, kata_visivel=True)
    exclude = (tmp_path / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".kata/" not in exclude

    harness.init_git_repo(tmp_path, kata_visivel=False)
    exclude = (tmp_path / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".kata/" in exclude


def test_fraude_ausente_com_baseline_sugere_a_convencao(tmp_path) -> None:
    """P2-6: fraude esperada não vista com baseline presente merece o
    diagnóstico da convenção, não só 'não encontrada'."""
    (tmp_path / "baseline").mkdir()
    ground_truth = {
        "expected_verdict": "REFUTED",
        "expected_frauds": [{"type": "weakened_checks", "severity": "high"}],
    }
    output = {"returncode": 1, "stdout": "✅  KATA JUDGE — REFUTED\n", "stderr": ""}

    passed, messages = harness.evaluate(tmp_path, ground_truth, output)

    assert passed is False
    assert any("baseline/" in message for message in messages)
