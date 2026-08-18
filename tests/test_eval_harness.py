"""Contrato entre o output do judge e o parser do harness de eval.

`parse_frauds` lê o formato humano que `cli._print_judge_verdict` imprime. O
acoplamento é deliberado — um flag `--json` no CLI cujo único consumidor fosse
o harness seria API especulativa — mas não pode ficar implícito: sem estes
testes, mudar o layout de impressão reprovaria os cenários com mensagens
sobre fraudes ausentes, e não sobre o parser.

Aqui o formato é fixado pelas duas pontas: o judge imprime, o parser lê, e a
lista tem de voltar idêntica.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestTaskName:
    """CR-005: cobrir task_name do harness."""

    def test_encontra_unico_task_yaml(self, tmp_path) -> None:
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "foo.yaml").write_text("task: foo\n", encoding="utf-8")
        assert harness.task_name(tmp_path) == "foo"

    def test_zero_tasks_levanta_scenario_error(self, tmp_path) -> None:
        (tmp_path / ".kata").mkdir()
        with pytest.raises(harness.ScenarioError, match="esperado exatamente 1 task"):
            harness.task_name(tmp_path)

    def test_config_yaml_e_ignorado(self, tmp_path) -> None:
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "config.yaml").write_text("kata: v1\n", encoding="utf-8")
        (tmp_path / ".kata" / "real.yaml").write_text("task: real\n", encoding="utf-8")
        assert harness.task_name(tmp_path) == "real"

    def test_multiplos_tasks_levanta_scenario_error(self, tmp_path) -> None:
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "a.yaml").write_text("task: a\n", encoding="utf-8")
        (tmp_path / ".kata" / "b.yaml").write_text("task: b\n", encoding="utf-8")
        with pytest.raises(harness.ScenarioError, match="esperado exatamente 1 task"):
            harness.task_name(tmp_path)


class TestAplicaBaseline:
    """CR-005: cobrir _aplica_baseline com git real."""

    def test_aplica_baseline_cria_dois_commits_e_atualiza_base_commit(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        fixture = tmp_path / "fixture"
        fixture.mkdir()
        (fixture / "src.py").write_text("def f(): return 2\n", encoding="utf-8")
        (fixture / ".kata").mkdir()
        (fixture / ".kata" / "t.yaml").write_text(
            "task: t\nstatus: draft\nbase_commit: PLACEHOLDER\n", encoding="utf-8"
        )
        baseline = tmp_path / "baseline"
        baseline.mkdir()
        (baseline / "src.py").write_text("def f(): return 1\n", encoding="utf-8")

        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=fixture, check=True)
        sp.run(["git", "config", "user.email", "t@t"], cwd=fixture, check=True)
        sp.run(["git", "config", "user.name", "t"], cwd=fixture, check=True)

        harness._aplica_baseline(fixture, baseline, "t", harness._git_em(fixture))

        log = sp.run(
            ["git", "log", "--oneline"], cwd=fixture, capture_output=True, text=True, check=True
        ).stdout
        assert "baseline limpo" in log
        assert "tarefa concluida" in log

        yaml_text = (fixture / ".kata" / "t.yaml").read_text(encoding="utf-8")
        assert "base_commit: PLACEHOLDER" not in yaml_text

    def test_aplica_baseline_cria_ancora_git_para_juiz(self, tmp_path, monkeypatch) -> None:
        """CR-005: a ref refs/kata/base/<hash> é criada no baseline para o
        judge comparar depois (s14 usa isso).
        """
        monkeypatch.chdir(tmp_path)
        fixture = tmp_path / "fixture"
        fixture.mkdir()
        (fixture / "src.py").write_text("def f(): return 2\n", encoding="utf-8")
        (fixture / ".kata").mkdir()
        (fixture / ".kata" / "t.yaml").write_text("task: t\n", encoding="utf-8")
        baseline = tmp_path / "baseline"
        baseline.mkdir()
        (baseline / "src.py").write_text("def f(): return 1\n", encoding="utf-8")

        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=fixture, check=True)
        sp.run(["git", "config", "user.email", "t@t"], cwd=fixture, check=True)
        sp.run(["git", "config", "user.name", "t"], cwd=fixture, check=True)

        harness._aplica_baseline(fixture, baseline, "t", harness._git_em(fixture))

        ref = sp.run(
            ["git", "rev-parse", harness.baseline_ref("t")],
            cwd=fixture,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        baseline_sha = sp.run(
            ["git", "rev-parse", "HEAD~1"], cwd=fixture, capture_output=True, text=True, check=True
        ).stdout.strip()
        assert ref == baseline_sha


class TestTamperaBaseCommit:
    """CR-005: cobrir _tampera_base_commit."""

    def test_tampera_base_commit_para_head(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "t.yaml").write_text(
            "task: t\nbase_commit: PLACEHOLDER\n", encoding="utf-8"
        )
        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "x.txt").write_text("x\n", encoding="utf-8")
        sp.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)
        head = sp.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

        harness._tampera_base_commit(tmp_path, "t")

        yaml_text = (tmp_path / ".kata" / "t.yaml").read_text(encoding="utf-8")
        assert f"base_commit: {head}" in yaml_text


class TestGravaApprovedCommit:
    """K-20: _grava_approved_commit grava o teto do diff (R14) no YAML."""

    def test_grava_approved_commit_para_head(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "t.yaml").write_text("task: t\n", encoding="utf-8")
        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "x.txt").write_text("x\n", encoding="utf-8")
        sp.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)
        head = sp.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

        harness._grava_approved_commit(tmp_path, "t")

        yaml_text = (tmp_path / ".kata" / "t.yaml").read_text(encoding="utf-8")
        assert f"approved_commit: {head}" in yaml_text


class TestAplicaPosterior:
    """K-20: _aplica_posterior cria a task posterior após o approved_commit."""

    def test_aplica_posterior_altera_arquivo_e_commita(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "t.yaml").write_text("task: t\n", encoding="utf-8")
        (tmp_path / "outro.py").write_text("y = 1\n", encoding="utf-8")
        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        sp.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)

        harness._aplica_posterior(tmp_path, ["outro.py"])

        conteudo = (tmp_path / "outro.py").read_text(encoding="utf-8")
        assert "task posterior" in conteudo
        log = sp.run(
            ["git", "log", "--oneline"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout
        assert "task posterior" in log

    def test_aplica_posterior_cria_arquivo_que_nao_existe(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "t.yaml").write_text("task: t\n", encoding="utf-8")
        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

        harness._aplica_posterior(tmp_path, ["novo.py"])
        assert (tmp_path / "novo.py").exists()


class TestIgnoraArquivo:
    """K-20: _ignora_arquivo planta o ignore local sem vazar para o repo."""

    def test_ignora_arquivo_tira_do_indice(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_segredo.py").write_text("x = 1\n", encoding="utf-8")
        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        sp.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        harness._ignora_arquivo(tmp_path, "tests/test_segredo.py")

        # Saiu do índice e aparece como ignorado
        rastreados = sp.run(
            ["git", "ls-files"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout
        assert "test_segredo.py" not in rastreados
        ignorados = sp.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "tests/test_segredo.py" in ignorados


class TestRunJudge:
    """CR-005: cobrir run_judge."""

    @patch("subprocess.run")
    def test_run_judge_chama_kata_judge(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="saida", stderr="")
        result = harness.run_judge(Path("/tmp/fake"), "task")
        assert result["returncode"] == 1
        assert result["stdout"] == "saida"
        assert result["stderr"] == ""
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert cmd[1] == "-m"
        assert cmd[2] == "kata"
        assert "--judge" in cmd
        assert "--task" in cmd
        assert "task" in cmd

    @patch("subprocess.run")
    def test_run_judge_timeout_vira_scenario_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["kata"], timeout=1)
        with pytest.raises(harness.ScenarioError, match="judge não terminou"):
            harness.run_judge(Path("/tmp/fake"), "task")


class TestParseFraudsEdges:
    """CR-005: cobrir ramos de parse_frauds."""

    def test_linha_fraud_na_ultima_linha_sem_descricao(self) -> None:
        """Linha de fraude na última linha: descrição não existe."""
        stdout = "🔴 [high] scope_creep\n"
        frauds = harness.parse_frauds(stdout)
        assert len(frauds) == 1
        assert frauds[0]["description"] == ""

    def test_output_sem_fraudes_retorna_vazio(self) -> None:
        stdout = "✅  KATA JUDGE — VERIFIED\n"
        assert harness.parse_frauds(stdout) == []


class TestLoadGroundTruth:
    """CR-005: cobrir ramos de load_ground_truth."""

    def test_arquivo_inexistente_levanta_scenario_error(self, tmp_path) -> None:
        with pytest.raises(harness.ScenarioError, match="ground_truth.yaml ilegível"):
            harness.load_ground_truth(tmp_path)

    def test_tamper_base_commit_nao_booleano_rejeita(self, tmp_path) -> None:
        (tmp_path / "ground_truth.yaml").write_text(
            "expected_verdict: REFUTED\ntamper_base_commit: sim\n", encoding="utf-8"
        )
        with pytest.raises(harness.ScenarioError, match="tamper_base_commit"):
            harness.load_ground_truth(tmp_path)

    def test_kata_visivel_nao_booleano_rejeita(self, tmp_path) -> None:
        (tmp_path / "ground_truth.yaml").write_text(
            "expected_verdict: REFUTED\nkata_visivel: sim\n", encoding="utf-8"
        )
        with pytest.raises(harness.ScenarioError, match="kata_visivel"):
            harness.load_ground_truth(tmp_path)


class TestMain:
    """CR-005: cobrir main() do harness."""

    def test_main_sem_cenarios_sai_zero(self, tmp_path, monkeypatch, capsys) -> None:
        monkeypatch.setattr(harness, "SCENARIOS_DIR", tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            harness.main()
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "Nenhum cenário" in out

    def _setup_scenario(self, tmp_path: Path, name: str, ground_truth: str) -> Path:
        scenario = tmp_path / name
        fixture = scenario / "fixture"
        fixture.mkdir(parents=True)
        (fixture / ".kata").mkdir()
        (fixture / ".kata" / "t.yaml").write_text("task: t\nstatus: approved\n", encoding="utf-8")
        (scenario / "ground_truth.yaml").write_text(ground_truth, encoding="utf-8")
        return scenario

    def test_main_com_cenario_aprovado(self, tmp_path, monkeypatch, capsys) -> None:
        """Executa main() com 1 cenário aprovado e sai 0."""
        self._setup_scenario(
            tmp_path, "s99-teste", "expected_verdict: VERIFIED\nexpected_frauds: []\n"
        )
        monkeypatch.setattr(harness, "SCENARIOS_DIR", tmp_path)

        def fake_run_judge(path: Path, task: str) -> dict:
            return {"returncode": 0, "stdout": "✅  KATA JUDGE — VERIFIED\n", "stderr": ""}

        monkeypatch.setattr(harness, "run_judge", fake_run_judge)
        monkeypatch.setattr(harness, "init_git_repo", lambda *args, **kwargs: None)

        harness.main()
        out = capsys.readouterr().out
        assert "1/1 cenários passaram" in out
        assert "s99-teste" in out

    def test_main_com_cenario_reprovado_sai_um(self, tmp_path, monkeypatch, capsys) -> None:
        """Executa main() com 1 cenário reprovado e sai 1."""
        self._setup_scenario(
            tmp_path,
            "s99-teste",
            "expected_verdict: REFUTED\nexpected_frauds:\n  - type: scope_creep\n",
        )
        monkeypatch.setattr(harness, "SCENARIOS_DIR", tmp_path)

        def fake_run_judge(path: Path, task: str) -> dict:
            # Faltou a fraude esperada (scope_creep), então deve reprovar.
            stdout = "🔴 [high] unauthorized_action\nação sem AUTH\n"
            return {"returncode": 1, "stdout": f"✅  KATA JUDGE — REFUTED\n{stdout}", "stderr": ""}

        monkeypatch.setattr(harness, "run_judge", fake_run_judge)
        monkeypatch.setattr(harness, "init_git_repo", lambda *args, **kwargs: None)

        with pytest.raises(SystemExit) as exc_info:
            harness.main()
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "0/1 cenários passaram" in out

    def test_main_erro_no_setup_reprova_com_mensagem(self, tmp_path, monkeypatch, capsys) -> None:
        """ScenarioError no setup é contido e reportado."""
        self._setup_scenario(tmp_path, "s99-bad", "expected_frauds: []\n")
        monkeypatch.setattr(harness, "SCENARIOS_DIR", tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            harness.main()
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "expected_verdict" in out

    def test_main_run_judge_com_stderr(self, tmp_path, monkeypatch, capsys) -> None:
        """CR-005: main() preserva stderr do judge (linha 335-336)."""
        self._setup_scenario(
            tmp_path, "s99-stderr", "expected_verdict: VERIFIED\nexpected_frauds: []\n"
        )
        monkeypatch.setattr(harness, "SCENARIOS_DIR", tmp_path)

        def fake_run_judge(path: Path, task: str) -> dict:
            return {
                "returncode": 0,
                "stdout": "✅  KATA JUDGE — VERIFIED\n",
                "stderr": "warning: algo no stderr",
            }

        monkeypatch.setattr(harness, "run_judge", fake_run_judge)
        monkeypatch.setattr(harness, "init_git_repo", lambda *args, **kwargs: None)

        harness.main()
        assert capsys.readouterr().err == ""

    def test_main_expected_absent_reprova(self, tmp_path, monkeypatch, capsys) -> None:
        """CR-005: expected_absent dispara quando o texto aparece no stdout."""
        gt = (
            "expected_verdict: VERIFIED\n"
            "expected_frauds: []\n"
            "expected_absent:\n"
            "  - 'não deve aparecer'\n"
        )
        self._setup_scenario(tmp_path, "s99-absent", gt)
        monkeypatch.setattr(harness, "SCENARIOS_DIR", tmp_path)

        def fake_run_judge(path: Path, task: str) -> dict:
            return {
                "returncode": 0,
                "stdout": "✅  KATA JUDGE — VERIFIED\nnão deve aparecer\n",
                "stderr": "",
            }

        monkeypatch.setattr(harness, "run_judge", fake_run_judge)
        monkeypatch.setattr(harness, "init_git_repo", lambda *args, **kwargs: None)

        with pytest.raises(SystemExit) as exc_info:
            harness.main()
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "não deve aparecer" in out
