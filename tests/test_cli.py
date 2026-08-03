"""Testes para kata.cli — helpers, steps interativos e main."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kata import cli
from kata.verify import VerifyResult


class TestSerializeDeserialize:
    """Testa round-trip de serialização YAML/JSON."""

    def test_roundtrip_simple(self) -> None:
        data = {"task": "test", "status": "draft"}
        text = cli._serialize(data)
        result = cli._deserialize(text)
        assert result == data

    def test_roundtrip_nested(self) -> None:
        data = {
            "task": "test",
            "think": {
                "problem": "algo",
                "assumptions": ["a", "b"],
                "answered": True,
            },
        }
        text = cli._serialize(data)
        result = cli._deserialize(text)
        assert result == data

    def test_roundtrip_empty_dict(self) -> None:
        result = cli._deserialize(cli._serialize({}))
        assert result == {}


class TestExt:
    """Testa a extensão de arquivo (.yaml ou .json)."""

    def test_ext_returns_string(self) -> None:
        ext = cli._ext()
        assert ext in (".yaml", ".json")


class TestTaskPath:
    """Testa construção do caminho .kata/<task>.yaml."""

    def test_task_path_contains_kata_dir(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = cli._task_path("my-task")
        assert ".kata" in str(path)
        assert "my-task" in str(path)

    @pytest.mark.parametrize(
        "bad_name",
        [
            "../escaped",
            "../../etc/passwd",
            "sub/dir",
            "sub\\dir",
            "..",
            "",
            "   ",
            ".",
        ],
    )
    def test_rejects_path_traversal(self, tmp_path, monkeypatch, bad_name) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            cli._task_path(bad_name)
        assert exc.value.code == 1
        # nada deve ter sido criado fora de .kata/
        assert not any(tmp_path.rglob("*escaped*"))
        assert not any(tmp_path.rglob("*passwd*"))

    def test_does_not_escape_kata_dir(self, tmp_path, monkeypatch) -> None:
        """Reprodução do finding original: --init com '../foo' não deve
        conseguir escrever fora de .kata/ mesmo quando o diretório pai existe."""
        monkeypatch.chdir(tmp_path)
        cli._kata_dir().mkdir(parents=True, exist_ok=True)
        with pytest.raises(SystemExit):
            cli._init_task("../escaped-outside-kata")
        assert not (tmp_path / "escaped-outside-kata.yaml").exists()
        assert not (tmp_path.parent / "escaped-outside-kata.yaml").exists()


class TestInitTask:
    """Testa criação do template .kata/<task>.yaml."""

    def test_init_creates_file(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        cli._kata_dir().mkdir(parents=True, exist_ok=True)
        cli._init_task("test-task")

        path = cli._task_path("test-task")
        assert path.exists()

        import kata.cli as cli_mod

        data = cli_mod._deserialize(path.read_text(encoding="utf-8"))
        assert data["task"] == "test-task"
        assert data["status"] == "draft"
        assert data["fit"]["trivial"] is False
        assert data["fit"]["route"] == "code-loop"
        assert data["think"]["answered"] is False

    def test_init_existing_warns(self, tmp_path, monkeypatch, capsys) -> None:
        monkeypatch.chdir(tmp_path)
        cli._kata_dir().mkdir(parents=True, exist_ok=True)
        cli._init_task("existing-task")
        cli._init_task("existing-task")  # segunda vez deve avisar
        captured = capsys.readouterr()
        assert "já existe" in captured.out


class TestCaptureBaseCommit:
    """Testa _capture_base_commit — registro do HEAD no início da tarefa."""

    def test_captures_head_in_git_repo(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], check=True)
        subprocess.run(["git", "config", "user.name", "t"], check=True)
        (tmp_path / "f.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], check=True)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()

        data = cli._capture_base_commit({})
        assert data["base_commit"] == head

    def test_does_not_overwrite_existing(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], check=True)
        data = cli._capture_base_commit({"base_commit": "already-set"})
        assert data["base_commit"] == "already-set"

    def test_no_git_repo_leaves_unset(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        data = cli._capture_base_commit({})
        assert "base_commit" not in data

    def test_init_task_captures_base_commit(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], check=True)
        subprocess.run(["git", "config", "user.name", "t"], check=True)
        (tmp_path / "f.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], check=True)

        cli._kata_dir().mkdir(parents=True, exist_ok=True)
        cli._init_task("with-base-commit")
        data = cli._deserialize(cli._task_path("with-base-commit").read_text(encoding="utf-8"))
        assert data["base_commit"]


class TestDetectTaskFromBranch:
    """Testa detecção de task a partir do branch git."""

    def test_detect_normal_branch(self, monkeypatch) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="feature/my-task\n", stderr=""
        )
        monkeypatch.setattr(
            "subprocess.run", lambda *a, **kw: mock_result
        )
        task = cli._detect_task_from_branch()
        assert task == "feature-my-task"

    def test_detect_detached_head(self, monkeypatch) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="HEAD\n", stderr=""
        )
        monkeypatch.setattr(
            "subprocess.run", lambda *a, **kw: mock_result
        )
        task = cli._detect_task_from_branch()
        assert task is None

    def test_detect_git_error(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(subprocess.CalledProcessError(1, [])),
        )
        task = cli._detect_task_from_branch()
        assert task is None

    def test_detect_underscores_replaced(self, monkeypatch) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="bug_fix_123\n", stderr=""
        )
        monkeypatch.setattr(
            "subprocess.run", lambda *a, **kw: mock_result
        )
        task = cli._detect_task_from_branch()
        assert task == "bug-fix-123"


class TestConfirm:
    """Testa _confirm com mock de input."""

    @patch("kata.cli.sys.stdin")
    def test_confirm_non_tty_returns_default_true(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        assert cli._confirm("Continuar?", default=True) is True

    @patch("kata.cli.sys.stdin")
    def test_confirm_non_tty_returns_default_false(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        assert cli._confirm("Continuar?", default=False) is False

    @patch("kata.cli.input", return_value="s")
    @patch("kata.cli.sys.stdin")
    def test_confirm_yes_portuguese(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        assert cli._confirm("Continuar?", default=True) is True

    @patch("kata.cli.input", return_value="n")
    @patch("kata.cli.sys.stdin")
    def test_confirm_no_portuguese(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        assert cli._confirm("Continuar?", default=True) is False

    @patch("kata.cli.input", return_value="")
    @patch("kata.cli.sys.stdin")
    def test_confirm_empty_returns_default_true(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        assert cli._confirm("Continuar?", default=True) is True

    @patch("kata.cli.input", return_value="")
    @patch("kata.cli.sys.stdin")
    def test_confirm_empty_returns_default_false(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        assert cli._confirm("Continuar?", default=False) is False

    @patch("kata.cli.input", side_effect=EOFError)
    @patch("kata.cli.sys.stdin")
    def test_confirm_eof_returns_default(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        assert cli._confirm("Continuar?", default=True) is True

    @patch("kata.cli.input", side_effect=KeyboardInterrupt)
    @patch("kata.cli.sys.stdin")
    def test_confirm_interrupt_returns_default(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        assert cli._confirm("Continuar?", default=False) is False

    @patch("kata.cli.input", return_value="yes")
    @patch("kata.cli.sys.stdin")
    def test_confirm_yes_english(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        assert cli._confirm("Continue?", default=False) is True


class TestPrintHeader:
    """Testa _print_header."""

    def test_prints_header_box(self, capsys) -> None:
        cli._print_header("TESTE")
        captured = capsys.readouterr()
        assert "TESTE" in captured.out
        assert "┌" in captured.out
        assert "└" in captured.out

    def test_prints_multiline_header(self, capsys) -> None:
        cli._print_header("Linha 1\nLinha 2")
        captured = capsys.readouterr()
        assert "Linha 1" in captured.out
        assert "Linha 2" in captured.out


class TestStepThink:
    """Testa _step_think em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_step_think_non_tty_marks_skipped_not_answered(self, mock_stdin) -> None:
        """Preencher com default não é responder. Enquanto isto gravava
        `answered: True`, um ciclo headless fazia o ciclo interativo seguinte
        pular THINK para sempre — a fase que é a premissa da ferramenta."""
        mock_stdin.isatty.return_value = False
        data: dict = {"think": {}}
        result = cli._step_think("task", data)
        assert result["think"]["answered"] is False
        assert result["think"]["skipped"] is True
        # Sem ninguém para declarar o critério, done fica vazio — o audit
        # enxerga a ausência em vez de um critério fabricado.
        assert result["done"] == ""

    def test_step_think_already_answered(self, capsys) -> None:
        data: dict = {"think": {"answered": True, "problem": "old"}}
        result = cli._step_think("task", data)
        assert result["think"]["problem"] == "old"

    @patch("kata.cli.input")
    @patch("kata.cli.sys.stdin")
    def test_step_think_interactive(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        mock_input.side_effect = [
            "Resolver bug X",
            "Usuário logado; DB acessível",
            "Refatorar; Ignorar",
            "Não sei o impacto em prod",
            "done = teste de fuso passa + curl /health retorna degraded",
        ]
        data: dict = {"think": {}}
        result = cli._step_think("task", data)
        assert result["think"]["problem"] == "Resolver bug X"
        assert result["think"]["assumptions"] == ["Usuário logado", "DB acessível"]
        assert result["think"]["alternatives"] == ["Refatorar", "Ignorar"]
        assert result["think"]["unknowns"] == "Não sei o impacto em prod"
        assert result["think"]["answered"] is True
        assert result["status"] == "think-complete"
        # Fable Step 1: o critério de sucesso é declarado ANTES da evidência
        assert result["done"] == "done = teste de fuso passa + curl /health retorna degraded"


@patch("kata.cli.untracked_stats", return_value=([], 0))
class TestStepSimplify:
    """Testa _step_simplify em modos interativo e não-interativo.

    untracked_stats é mockado no nível da classe: sem isso os testes leriam
    os arquivos untracked reais do repositório e passariam ou falhariam
    conforme o estado da árvore de quem roda.
    """

    @patch("kata.cli.sys.stdin")
    def test_step_simplify_non_tty(self, mock_stdin, mock_untracked) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_simplify("task", data)
        assert result["simplify"]["minimum_code"] is True
        assert result["simplify"]["no_single_use_abstractions"] is True
        assert result["simplify"]["no_speculative_config"] is True

    @patch("kata.cli._confirm")
    @patch("kata.cli._run_git")
    @patch("kata.cli.sys.stdin")
    def test_step_simplify_interactive_with_diff(
        self, mock_stdin, mock_run, mock_confirm, mock_untracked
    ) -> None:
        mock_stdin.isatty.return_value = True
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="3 files changed\n", stderr=""
        )
        mock_confirm.side_effect = [True, False, False]
        with patch("kata.cli.input", return_value=""):
            data: dict = {}
            result = cli._step_simplify("task", data)
        assert result["simplify"]["minimum_code"] is True

    @patch("kata.cli._confirm")
    @patch("kata.cli._run_git")
    @patch("kata.cli.sys.stdin")
    def test_step_simplify_no_diff_uses_staged(
        self, mock_stdin, mock_run, mock_confirm, mock_untracked
    ) -> None:
        mock_stdin.isatty.return_value = True
        # Primeiro diff vazio, segundo diff com staged changes
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="1 file changed\n", stderr=""
            ),
        ]
        mock_confirm.side_effect = [True, False, False]
        with patch("kata.cli.input", return_value=""):
            data: dict = {}
            result = cli._step_simplify("task", data)
        assert result["simplify"]["minimum_code"] is True

    @patch("kata.cli._confirm")
    @patch("kata.cli._run_git")
    @patch("kata.cli.sys.stdin")
    def test_step_simplify_no_changes(
        self, mock_stdin, mock_run, mock_confirm, mock_untracked
    ) -> None:
        mock_stdin.isatty.return_value = True
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        mock_confirm.side_effect = [True, False, False]
        with patch("kata.cli.input", return_value="notas de teste"):
            data: dict = {}
            result = cli._step_simplify("task", data)
        assert result["simplify"]["minimum_code"] is True
        assert result["simplify"]["no_single_use_abstractions"] is True
        assert result["simplify"]["no_speculative_config"] is True
        assert "notes" not in result["simplify"]

    @patch("kata.cli._confirm")
    @patch("kata.cli._run_git")
    @patch("kata.cli.sys.stdin")
    def test_untracked_only_task_still_asks(
        self, mock_stdin, mock_run, mock_confirm, mock_untracked, capsys
    ) -> None:
        """Tarefa que só cria arquivos: `git diff` vem vazio, mas SIMPLIFY
        não pode passar sem pergunta nenhuma registrando o checklist como
        aprovado."""
        mock_stdin.isatty.return_value = True
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        mock_untracked.return_value = (["src/servico.py"], 200)
        mock_confirm.side_effect = [True, False, True]

        with patch("kata.cli.input", return_value=""):
            result = cli._step_simplify("task", {})

        out = capsys.readouterr().out
        assert "src/servico.py" in out
        assert "200 linha(s)" in out
        assert "nenhuma alteração detectada" not in out
        assert result["simplify"]["no_single_use_abstractions"] is False


@patch("kata.cli.untracked_files", return_value=[])
class TestStepSurgical:
    """Testa _step_surgical em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_step_surgical_non_tty(self, mock_stdin, mock_untracked) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_surgical("task", data)
        assert result["surgical"]["files"] == []
        assert result["surgical"]["removed_imports_clean"] is True

    @patch("kata.cli._confirm")
    @patch("kata.cli._run_git")
    @patch("kata.cli.sys.stdin")
    def test_step_surgical_interactive_with_files(
        self, mock_stdin, mock_run, mock_confirm, mock_untracked
    ) -> None:
        mock_stdin.isatty.return_value = True
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="src/foo.py\nsrc/bar.py\n", stderr=""
        )
        mock_confirm.side_effect = [True, True, True]
        data: dict = {}
        result = cli._step_surgical("task", data)
        assert len(result["surgical"]["files"]) == 2
        assert result["surgical"]["files"][0]["path"] == "src/foo.py"
        assert result["surgical"]["files"][0]["necessary"] is True

    @patch("kata.cli._confirm")
    @patch("kata.cli._run_git")
    @patch("kata.cli.sys.stdin")
    def test_step_surgical_no_diff_uses_staged(
        self, mock_stdin, mock_run, mock_confirm, mock_untracked
    ) -> None:
        mock_stdin.isatty.return_value = True
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="baz.py\n", stderr=""),
        ]
        mock_confirm.side_effect = [True, True]
        data: dict = {}
        result = cli._step_surgical("task", data)
        assert len(result["surgical"]["files"]) == 1
        assert result["surgical"]["files"][0]["path"] == "baz.py"


class TestStepVerify:
    """Testa _step_verify com verify mockado."""

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_all_pass(self, mock_run_all, mock_confirm, capsys) -> None:
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="10 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = True
        data: dict = {}
        result = cli._step_verify("my-task", data)
        assert result["verify"]["ruff_clean"] is True
        assert result["verify"]["tests_pass"] is True
        assert result["verify"]["coverage_pass"] is True
        assert result["verify"]["success_criteria_met"] is True
        assert result["status"] == "approved"
        captured = capsys.readouterr()
        assert "APROVADO" in captured.out

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_ruff_fails(self, mock_run_all, mock_confirm, capsys) -> None:
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=False, output="F401 unused import"),
            "pytest": VerifyResult(ok=True, output="5 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 10 90%", details={"coverage_pct": 90.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = True
        data: dict = {}
        result = cli._step_verify("my-task", data)
        assert result["verify"]["ruff_clean"] is False
        assert result["status"] == "rejected"
        captured = capsys.readouterr()
        assert "REJEITADO" in captured.out

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_pytest_fails(self, mock_run_all, mock_confirm, capsys) -> None:
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=False, output="2 failed"),
            "coverage": VerifyResult(
                ok=False, output="TOTAL 100 50 50%", details={"coverage_pct": 50.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = True
        data: dict = {}
        result = cli._step_verify("my-task", data)
        assert result["verify"]["tests_pass"] is False
        assert result["status"] == "rejected"

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_check_only_mode(self, mock_run_all, mock_confirm, capsys) -> None:
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="5 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        # check-only mode — não pede confirmação
        data: dict = {}
        result = cli._step_verify("check-only", data)
        assert result["verify"]["success_criteria_met"] is True
        assert result["status"] == "approved"
        captured = capsys.readouterr()
        assert "check-only" in captured.out

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_success_not_met(self, mock_run_all, mock_confirm, capsys) -> None:
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="5 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = False  # sucesso NÃO satisfeito
        data: dict = {}
        result = cli._step_verify("my-task", data)
        assert result["verify"]["success_criteria_met"] is False
        assert result["status"] == "rejected"

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_shows_declared_done(self, mock_run_all, mock_confirm, capsys) -> None:
        """Fable Step 1: o VERIFY confronta o critério declarado no THINK com
        o resultado final em vez de perguntar a um critério que só existe
        agora."""
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="5 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = True
        data: dict = {"done": "done = teste de fuso passa + curl /health degraded"}
        cli._step_verify("my-task", data)
        out = capsys.readouterr().out
        assert "declarado no THINK" in out
        assert "teste de fuso passa" in out

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_counts_attempts(self, mock_run_all, mock_confirm) -> None:
        """Fable Step 5: o VERIFY persiste um contador de tentativas na tarefa."""
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="5 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = True
        data: dict = {"verify": {"attempts": 2}}
        result = cli._step_verify("my-task", data)
        assert result["verify"]["attempts"] == 3
        assert result["verify"]["hand_back"] is False  # sucesso não devolve

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_hand_back_after_three_failures(self, mock_run_all, mock_confirm) -> None:
        """Fable Step 5: 3 tentativas falhas estouram o bound — a tarefa é
        devolvida ao usuário em vez de repetir o fix-verify para sempre."""
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="5 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = False  # critério ainda não satisfeito
        data: dict = {"verify": {"attempts": 2}}
        result = cli._step_verify("my-task", data)
        assert result["verify"]["attempts"] == 3
        assert result["verify"]["hand_back"] is True
        assert result["status"] == "rejected"

    @patch("kata.cli._confirm")
    @patch("kata.cli.run_all")
    def test_step_verify_no_hand_back_before_limit(self, mock_run_all, mock_confirm) -> None:
        """Antes do limite, a falha é um rejeitado normal — o bound só dispara
        ao estourar as tentativas."""
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="5 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        mock_confirm.return_value = False
        result = cli._step_verify("my-task", {})
        assert result["verify"]["attempts"] == 1
        assert result["verify"]["hand_back"] is False
        assert result["status"] == "rejected"


class TestAuditTask:
    """Testa _audit_task — graduação followed/skipped/faked (fable audit).

    O gatilho para a fase faked é o padrão do R7-1: fase "respondida" com
    conteúdo default/vazio. O audit existe para que isso seja visível, não
    silencioso.
    """

    def test_clean_task_all_followed(self) -> None:
        data = {
            "fit": {"answered": True, "reason": "feature request", "skipped": False},
            "think": {"answered": True, "problem": "bug real", "skipped": False},
            "intent": {"answered": True, "code_does": "faz X", "skipped": False},
            "verify": {"success_criteria_met": True, "ruff_clean": True,
                       "tests_pass": True, "coverage_pass": True},
            "twins": {"defect_fixed": False, "searched": True},
        }
        achados = cli._audit_task(data)
        assert all(a["status"] == "followed" for a in achados)
        assert {a["fase"] for a in achados} == {"fit", "think", "intent", "verify", "twins"}

    def test_faked_think_empty_problem_is_the_r7_pattern(self) -> None:
        """R7-1: THINK 'respondido' com conteúdo vazio é um passo faked — o
        audit tem de nomear o risco concreto, não deixar passar."""
        data = {"think": {"answered": True, "problem": "", "skipped": False}}
        achados = cli._audit_task(data)
        think = next(a for a in achados if a["fase"] == "think")
        assert think["status"] == "faked"
        assert "problema errado" in think["risco"]

    def test_skipped_think_is_documented(self) -> None:
        data = {"think": {"answered": False, "skipped": True}}
        achados = cli._audit_task(data)
        think = next(a for a in achados if a["fase"] == "think")
        assert think["status"] == "skipped"
        assert think["risco"]  # skip documentado ainda tem risco nomeado

    def test_unanswered_phase_is_not_graded(self) -> None:
        """Tarefa em andamento: fase nem iniciada não é skip nem fake."""
        achados = cli._audit_task({})
        assert achados == []

    def test_faked_verify_claims_success_without_evidence(self) -> None:
        """VERIFY afirmando sucesso sem nenhuma checagem objetiva é faked."""
        data = {"verify": {"success_criteria_met": True}}
        achados = cli._audit_task(data)
        verify = next(a for a in achados if a["fase"] == "verify")
        assert verify["status"] == "faked"
        assert "aprovada sobre nada" in verify["risco"]

    def test_verify_with_evidence_is_followed(self) -> None:
        data = {"verify": {"success_criteria_met": True, "tests_pass": True}}
        achados = cli._audit_task(data)
        verify = next(a for a in achados if a["fase"] == "verify")
        assert verify["status"] == "followed"

    def test_faked_twins_defect_without_search(self) -> None:
        """Defeito declarado corrigido sem busca de recorrência é faked."""
        data = {"twins": {"defect_fixed": True, "searched": False}}
        achados = cli._audit_task(data)
        twins = next(a for a in achados if a["fase"] == "twins")
        assert twins["status"] == "faked"
        assert "se repetir" in twins["risco"]

    def test_twins_searched_is_followed(self) -> None:
        data = {"twins": {"defect_fixed": True, "searched": True}}
        achados = cli._audit_task(data)
        twins = next(a for a in achados if a["fase"] == "twins")
        assert twins["status"] == "followed"

    def test_fit_faked_when_reason_empty(self) -> None:
        """FIT respondido sem justificativa (default) é faked — ninguém
        classificou a tarefa."""
        data = {"fit": {"answered": True, "reason": "", "skipped": False}}
        achados = cli._audit_task(data)
        fit = next(a for a in achados if a["fase"] == "fit")
        assert fit["status"] == "faked"
        assert "mal roteada" in fit["risco"]


class TestPrintAudit:
    """Testa _print_audit — output da graduação."""

    def test_clean_audit_says_clean(self, capsys) -> None:
        cli._print_audit([
            {"fase": "think", "status": "followed", "risco": ""},
            {"fase": "verify", "status": "followed", "risco": ""},
        ])
        out = capsys.readouterr().out
        assert "THINK: followed" in out
        assert "Audit limpo" in out

    def test_faked_audit_lists_risks(self, capsys) -> None:
        cli._print_audit([
            {"fase": "think", "status": "faked", "risco": "problema errado"},
        ])
        out = capsys.readouterr().out
        assert "THINK: faked" in out
        assert "problema errado" in out
        assert "1 fake(s)" in out

    def test_empty_audit_says_task_in_progress(self, capsys) -> None:
        cli._print_audit([])
        out = capsys.readouterr().out
        assert "nenhuma fase iniciada" in out


class TestMainInit:
    """Testa o modo --init via main()."""

    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_main_init_creates_task(self, mock_kata_dir, mock_init) -> None:
        from pathlib import Path

        mock_kata_dir.return_value = Path("/tmp/.kata")
        with patch("sys.argv", ["kata", "--init", "new-task"]):
            cli.main()
        mock_init.assert_called_once_with("new-task")

    def test_main_init_creates_directory_and_file(self, tmp_path, monkeypatch) -> None:
        """Testa que --init cria .kata/ e o arquivo da tarefa no CWD real."""
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["kata", "--init", "init-task"]):
            cli.main()
        # Arquivo deve ter sido criado no CWD real (sem mock de _kata_dir)
        ext = cli._ext()
        task_file = tmp_path / ".kata" / f"init-task{ext}"
        assert task_file.exists()


class TestMainVersion:
    """Testa a flag --version."""

    def test_version_prints_and_exits(self, capsys) -> None:
        from kata import __version__

        with patch("sys.argv", ["kata", "--version"]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_version_matches_pyproject(self) -> None:
        """A versão vive em pyproject.toml e em __init__.py. Nada travava as
        duas, então bastava bumpar uma para `--version` passar a mentir."""
        import tomllib
        from pathlib import Path

        from kata import __version__

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        declarada = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
        assert __version__ == declarada


class TestMainCheckOnly:
    """Testa o modo --check-only via main()."""

    @patch("kata.cli.run_all")
    @patch("kata.cli._kata_dir")
    def test_check_only_approved(self, mock_kata_dir, mock_run_all, tmp_path, monkeypatch) -> None:

        mock_kata_dir.return_value = tmp_path / ".kata"
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, output="All clear"),
            "pytest": VerifyResult(ok=True, output="10 passed"),
            "coverage": VerifyResult(
                ok=True, output="TOTAL 100 5 95%", details={"coverage_pct": 95.0, "gate": 70.0}
            ),
        }
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["kata", "--check-only"]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 0

    @patch("kata.cli.run_all")
    @patch("kata.cli._kata_dir")
    def test_check_only_rejected(self, mock_kata_dir, mock_run_all, tmp_path, monkeypatch) -> None:

        mock_kata_dir.return_value = tmp_path / ".kata"
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=False, output="F401"),
            "pytest": VerifyResult(ok=False, output="2 failed"),
            "coverage": VerifyResult(
                ok=False, output="TOTAL 100 50 50%", details={"coverage_pct": 50.0, "gate": 70.0}
            ),
        }
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["kata", "--check-only"]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 1


class TestDetectCovSource:
    """Testa detecção automática do pacote fonte de coverage."""

    def test_detects_from_pyproject_toml(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[tool.coverage.run]\nsource = ["kata"]\n', encoding="utf-8"
        )
        assert cli._detect_cov_source() == "kata"

    def test_fallback_when_pyproject_missing(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert cli._detect_cov_source() == "src"

    def test_fallback_when_source_missing(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
        )
        assert cli._detect_cov_source() == "src"


class TestCwdHelper:
    """Testa _cwd e _kata_dir."""

    def test_cwd_returns_path(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert cli._cwd() == tmp_path

    def test_kata_dir_returns_cwd_plus_kata(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = cli._kata_dir()
        assert result == tmp_path / ".kata"


class TestPickTask:
    """Testa _pick_task em modo não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_pick_task_non_tty(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        result = cli._pick_task()
        assert result == "untitled"

    @patch("kata.cli.input", return_value="nova-tarefa")
    @patch("kata.cli._detect_task_from_branch", return_value=None)
    @patch("kata.cli.sys.stdin")
    def test_pick_task_interactive_no_existing(self, mock_stdin, mock_branch, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        # Sem branch detectado e sem tarefas existentes
        with patch("kata.cli._kata_dir") as mock_kata_dir:
            from pathlib import Path

            mock_kata_dir.return_value = Path("/tmp/.kata")
            with patch("kata.cli.Path.glob", return_value=[]):
                result = cli._pick_task()
        assert result == "nova-tarefa"

    @patch("kata.cli.input", return_value="")
    @patch("kata.cli._detect_task_from_branch", return_value=None)
    @patch("kata.cli.sys.stdin")
    def test_pick_task_interactive_empty_name_returns_untitled(
        self, mock_stdin, mock_branch, mock_input
    ) -> None:
        mock_stdin.isatty.return_value = True
        with patch("kata.cli._kata_dir") as mock_kata_dir:
            from pathlib import Path

            mock_kata_dir.return_value = Path("/tmp/.kata")
            with patch("kata.cli.Path.glob", return_value=[]):
                result = cli._pick_task()
        assert result == "untitled"

    @patch("kata.cli.input", return_value="../../etc/passwd")
    @patch("kata.cli._detect_task_from_branch", return_value=None)
    @patch("kata.cli.sys.stdin")
    def test_pick_task_interactive_traversal_returns_untitled(
        self, mock_stdin, mock_branch, mock_input
    ) -> None:
        mock_stdin.isatty.return_value = True
        with patch("kata.cli._kata_dir") as mock_kata_dir:
            from pathlib import Path

            mock_kata_dir.return_value = Path("/tmp/.kata")
            with patch("kata.cli.Path.glob", return_value=[]):
                result = cli._pick_task()
        assert result == "untitled"

    @patch("kata.cli._detect_task_from_branch")
    @patch("kata.cli.sys.stdin")
    def test_pick_task_branch_matches_existing(self, mock_stdin, mock_branch) -> None:
        mock_stdin.isatty.return_value = True
        mock_branch.return_value = "my-branch"
        # Cria um mock de Path que retorna arquivos
        from pathlib import Path

        fake_path = MagicMock()
        fake_path.stem = "my-branch"
        with patch("kata.cli._kata_dir") as mock_kata_dir:
            mock_kata_dir.return_value = Path("/tmp/.kata")
            with patch.object(Path, "glob", return_value=[fake_path]):
                result = cli._pick_task()
        assert result == "my-branch"


class TestJsonFallback:
    """Testa serialização/deserialização com JSON (fallback quando yaml indisponível)."""

    def test_serialize_without_yaml(self, monkeypatch) -> None:
        monkeypatch.setattr("kata.cli._HAS_YAML", False)
        data = {"task": "json-test", "status": "draft"}
        text = cli._serialize(data)
        assert '"task"' in text
        assert '"json-test"' in text

    def test_deserialize_without_yaml(self, monkeypatch) -> None:
        monkeypatch.setattr("kata.cli._HAS_YAML", False)
        import json

        text = json.dumps({"task": "json-test", "status": "draft"})
        result = cli._deserialize(text)
        assert result["task"] == "json-test"

    def test_ext_without_yaml(self, monkeypatch) -> None:
        monkeypatch.setattr("kata.cli._HAS_YAML", False)
        assert cli._ext() == ".json"


class TestChangedPathsSeesUntracked:
    """Repo git de verdade: o defeito era o comando que nunca era chamado."""

    def _repo(self, tmp_path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)

    def test_untracked_survives_a_modified_file(self, tmp_path, monkeypatch) -> None:
        """Untracked era o terceiro fallback, então bastava um arquivo
        modificado para os arquivos novos sumirem da lista."""
        monkeypatch.chdir(tmp_path)
        self._repo(tmp_path)
        (tmp_path / "README.md").write_text("modificado\n", encoding="utf-8")
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")

        assert sorted(cli._changed_paths()) == ["README.md", "novo.py"]

    def test_untracked_debris_is_reported(self, tmp_path, monkeypatch) -> None:
        """Detrito recém-criado e ainda não adicionado ao índice é o caso
        mais comum, e era o único invisível."""
        monkeypatch.chdir(tmp_path)
        self._repo(tmp_path)
        (tmp_path / "README.md").write_text("modificado\n", encoding="utf-8")
        (tmp_path / "saida.tmp").write_text("lixo\n", encoding="utf-8")

        assert cli._detect_scratch_files() == ["saida.tmp"]

    def test_no_duplicates_when_nothing_is_untracked(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        self._repo(tmp_path)
        (tmp_path / "README.md").write_text("modificado\n", encoding="utf-8")

        assert cli._changed_paths() == ["README.md"]


class TestIsInvalidTaskName:
    """Regra de nome de tarefa — guarda de path traversal e de nomes que
    produziriam arquivos estranhos em .kata/."""

    @pytest.mark.parametrize(
        "name",
        [
            "../../etc/passwd",     # traversal
            "a/b",                  # separador POSIX
            "a\\b",                 # separador Windows
            "..",
            ".",
            "",
            "   ",
            ".oculto",              # arquivo oculto
            "my task",              # viraria ".kata/my task.yaml"
            "tab\tname",
            "foo.yaml",             # viraria ".kata/foo.yaml.yaml"
            "foo.json",             # idem quando PyYAML está ausente
        ],
    )
    def test_rejected(self, name: str) -> None:
        assert cli._is_invalid_task_name(name) is True

    @pytest.mark.parametrize("name", ["foo.yaml", "foo.json"])
    def test_extension_rejected_regardless_of_pyyaml(self, name: str, monkeypatch) -> None:
        """A regra amarrada a _ext() deixava `--init foo.yaml` passar sem
        PyYAML, criando `.kata/foo.yaml.json`. Nome de tarefa não pode depender
        de qual biblioteca está instalada."""
        for has_yaml in (True, False):
            monkeypatch.setattr(cli, "_HAS_YAML", has_yaml)
            assert cli._is_invalid_task_name(name) is True

    @pytest.mark.parametrize(
        "name",
        ["fix-bug", "feature-123", "bug_fix", "v1.2-hotfix", "correção-de-bug"],
    )
    def test_accepted(self, name: str) -> None:
        assert cli._is_invalid_task_name(name) is False

    def test_validate_exits_on_invalid_name(self, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            cli._validate_task_name("../escape")
        assert exc.value.code == 1
        assert "inválido" in capsys.readouterr().out


class TestRunHelper:
    """Testa _run com kwargs."""

    @patch("kata.cli.subprocess.run")
    def test_run_passes_kwargs(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        cli._run_git(["echo", "test"], check=True)
        # Verifica que check=True foi passado como kwarg
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("check") is True

    @patch("kata.cli.subprocess.run")
    def test_run_basic_command(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "test"], returncode=0, stdout="test\n", stderr=""
        )
        result = cli._run_git(["echo", "test"])
        assert result.returncode == 0

    @patch("kata.cli.subprocess.run")
    def test_run_overrides_defaults_without_collision(self, mock_run) -> None:
        """Passar capture_output/cwd/text via kwargs sobrescreve defaults sem TypeError."""
        from pathlib import Path

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        custom_cwd = Path("/tmp/custom")
        cli._run_git(["echo", "test"], capture_output=False, text=False, cwd=custom_cwd)
        call_kwargs = mock_run.call_args[1]
        # Defaults sobrescritos pelos valores do caller
        assert call_kwargs.get("capture_output") is False
        assert call_kwargs.get("text") is False
        assert call_kwargs.get("cwd") == custom_cwd


@patch("kata.cli.untracked_files", return_value=[])
class TestStepSurgicalNoFiles:
    """Testa _step_surgical sem arquivos alterados."""

    @patch("kata.cli._confirm")
    @patch("kata.cli._run_git")
    @patch("kata.cli.sys.stdin")
    def test_surgical_no_files_no_staged(
        self, mock_stdin, mock_run, mock_confirm, mock_untracked
    ) -> None:
        mock_stdin.isatty.return_value = True
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        mock_confirm.return_value = True
        data: dict = {}
        result = cli._step_surgical("task", data)
        assert result["surgical"]["files"] == []
        assert result["surgical"]["removed_imports_clean"] is True


class TestHeadlessNaoEnvenenaATarefa:
    """Um ciclo sem tty preenche FIT, THINK e INTENT com defaults. Enquanto isso
    gravava `answered: True`, o guard no topo de cada fase as saltava para
    sempre — inclusive num ciclo interativo posterior na mesma tarefa. Nenhum
    teste cobria a sequência headless → interativo; dois testes fixavam
    justamente o comportamento defeituoso."""

    def _ciclo_headless(self) -> dict:
        data: dict = {"task": "t", "status": "draft"}
        with patch("kata.cli.sys.stdin") as stdin, patch("kata.cli.untracked_files",
                                                          return_value=[]):
            stdin.isatty.return_value = False
            data = cli._step_fit("t", data)
            data = cli._step_think("t", data)
            data = cli._step_intent("t", data)
        return data

    def test_headless_nao_marca_como_respondido(self) -> None:
        data = self._ciclo_headless()
        for fase in ("fit", "think", "intent"):
            assert data[fase]["answered"] is False, fase
            assert data[fase]["skipped"] is True, fase

    def test_ciclo_interativo_posterior_ainda_pergunta(self, capsys) -> None:
        data = self._ciclo_headless()
        capsys.readouterr()

        with patch("kata.cli.sys.stdin") as stdin, \
             patch("kata.cli.input", return_value="resposta"), \
             patch("kata.cli._confirm", return_value=True):
            stdin.isatty.return_value = True
            depois = cli._step_think("t", dict(data))
        saida = capsys.readouterr().out

        assert "já respondido" not in saida
        assert depois["think"]["problem"] == "resposta"
        assert depois["think"]["answered"] is True

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_relatorio_declara_as_fases_puladas(self, mock_scratch, capsys) -> None:
        """Corrigir o mecanismo não basta: uma tarefa que rodou headless e foi
        aprovada seguia com THINK vazio e o relatório não dizia nada."""
        data = self._ciclo_headless()
        capsys.readouterr()
        data["status"] = "approved"
        data["verify"] = {"ruff_clean": True, "tests_pass": True,
                          "coverage_pass": True, "coverage_pct": 91.0}
        data["artifact"] = {}

        cli._step_report("t", data)
        saida = capsys.readouterr().out

        assert "Caveats" in saida
        assert "FIT, THINK, INTENT" in saida
        assert "ninguém respondeu" in saida


class TestStepIntent:
    """Testa _step_intent em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_intent_non_tty_marks_skipped_not_answered(self, mock_stdin) -> None:
        """Mesma razão de test_step_think_non_tty_marks_skipped_not_answered."""
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_intent("task", data)
        assert result["intent"]["answered"] is False
        assert result["intent"]["skipped"] is True
        assert result["intent"]["all_agree"] is True
        assert result["intent"]["code_does"] == ""

    def test_intent_already_answered(self, capsys) -> None:
        data: dict = {"intent": {"answered": True, "code_does": "func X"}}
        result = cli._step_intent("task", data)
        assert result["intent"]["code_does"] == "func X"
        assert "já respondido" in capsys.readouterr().out

    @patch("kata.cli.input")
    @patch("kata.cli.sys.stdin")
    def test_intent_interactive_all_agree(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        mock_input.side_effect = [
            "parse_date retorna datetime naive",
            "datetime com timezone UTC",
            "README: preservar fuso",
            "",
        ]
        with patch("kata.cli._confirm", return_value=True):
            data: dict = {}
            result = cli._step_intent("task", data)
        assert result["intent"]["code_does"] == "parse_date retorna datetime naive"
        assert result["intent"]["check_expects"] == "datetime com timezone UTC"
        assert result["intent"]["spec_says"] == "README: preservar fuso"
        assert result["intent"]["all_agree"] is True

    @patch("kata.cli.input")
    @patch("kata.cli.sys.stdin")
    def test_intent_interactive_conflict(self, mock_stdin, mock_input) -> None:
        mock_stdin.isatty.return_value = True
        mock_input.side_effect = [
            "func X retorna int",
            "func X retorna str",
            "func X retorna int",
            "spec ganha, teste errado",
        ]
        with patch("kata.cli._confirm", return_value=False):
            data: dict = {}
            result = cli._step_intent("task", data)
        assert result["intent"]["all_agree"] is False
        assert "spec ganha" in result["intent"]["conflict_resolution"]


class TestStepArtifact:
    """Testa _step_artifact em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_all_present(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {
            "intent": {"answered": True, "code_does": "func X"},
            "verify": {"tests_pass": True},
            "surgical": {"files": [{"path": "src/app.py", "necessary": True}]},
        }
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is True
        assert result["artifact"]["intent_present"] is True

    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_missing_intent(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {
            "verify": {"tests_pass": True},
            "surgical": {"files": [{"path": "src/app.py", "necessary": True}]},
        }
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is True
        assert result["artifact"]["intent_present"] is False

    @patch("kata.cli._changed_paths", return_value=[])
    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_no_intent_needed(self, mock_stdin, mock_changed) -> None:
        """Sem arquivo de código alterado, INTENT não é devida."""
        mock_stdin.isatty.return_value = False
        data: dict = {"intent": {}}
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is False

    @patch("kata.cli.sys.stdin")
    def test_artifact_docs_only_change_owes_no_intent(self, mock_stdin) -> None:
        """Mudança só de documentação não tem "o que o código FAZ" a declarar.
        Antes, bastava VERIFY ter rodado para INTENT ser cobrada."""
        mock_stdin.isatty.return_value = False
        data: dict = {
            "verify": {"tests_pass": True, "coverage_pass": True},
            "surgical": {
                "files": [
                    {"path": "README.md", "necessary": True},
                    {"path": "docs/guide.rst", "necessary": True},
                ]
            },
        }
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is False

    @patch("kata.cli._changed_paths", return_value=[])
    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_empty_data(self, mock_stdin, mock_changed, capsys) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is False
        assert "Todas as linhas devidas" in capsys.readouterr().out

    @patch("kata.cli._detect_auth_owed", return_value=True)
    @patch("kata.cli._detect_pending_owed", return_value=True)
    @patch("kata.cli._detect_twins_owed", return_value=True)
    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_missing_auth_pending_twins(
        self, mock_stdin, mock_twins, mock_pending, mock_auth, capsys,
    ) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {
            "intent": {"answered": True, "code_does": "func X"},
            "verify": {"tests_pass": True},
        }
        result = cli._step_artifact("task", data)
        out = capsys.readouterr().out
        assert result["artifact"]["auth_owed"] is True
        assert result["artifact"]["pending_owed"] is True
        assert result["artifact"]["twins_owed"] is True
        assert "AUTH" in out
        assert "PENDING" in out
        assert "TWINS" in out

    @patch("kata.cli._detect_auth_owed", return_value=True)
    @patch("kata.cli._detect_pending_owed", return_value=True)
    @patch("kata.cli._detect_twins_owed", return_value=True)
    @patch("kata.cli.sys.stdin")
    @patch(
        "kata.cli.input",
        side_effect=[
            "código faz X",             # INTENT code_does
            "teste espera Y",           # INTENT check_expects
            "spec diz Z",               # INTENT spec_says
            "fez deploy em prod",       # AUTH action
            'usuário disse "manda"',    # AUTH quote
            "revisar módulo Y",         # PENDING action
            "assert True",              # TWINS pattern
            "3 ocorrências",            # TWINS result
        ],
    )
    def test_artifact_tty_backfills_all_missing_lines(
        self, mock_input, mock_stdin, mock_twins, mock_pending, mock_auth,
    ) -> None:
        """Em modo interativo, preenche INTENT/AUTH/PENDING/TWINS ausentes via input()."""
        mock_stdin.isatty.return_value = True
        data: dict = {
            "verify": {"tests_pass": True},
            "surgical": {"files": [{"path": "src/app.py", "necessary": True}]},
        }
        result = cli._step_artifact("task", data)

        assert result["intent"] == {
            "code_does": "código faz X",
            "check_expects": "teste espera Y",
            "spec_says": "spec diz Z",
            "all_agree": True,
            "answered": True,
        }
        assert result["auth"] == {
            "action_taken": True,
            "authorized": True,
            "action": "fez deploy em prod",
            "quote": 'usuário disse "manda"',
        }
        assert result["pending"] == {"action": "revisar módulo Y", "documented": True}
        assert result["twins"] == {
            "pattern": "assert True",
            "result": "3 ocorrências",
            "searched": True,
        }

    @patch("kata.cli._detect_auth_owed", return_value=False)
    @patch("kata.cli._detect_pending_owed", return_value=False)
    @patch("kata.cli._detect_twins_owed", return_value=False)
    @patch("kata.cli.sys.stdin")
    @patch(
        "kata.cli.input",
        side_effect=[
            "código faz X",             # INTENT code_does
            "teste espera Y",           # INTENT check_expects
            "spec diz Z",               # INTENT spec_says
        ],
    )
    def test_artifact_checks_updated_after_backfill(
        self, mock_input, mock_stdin, mock_twins, mock_pending, mock_auth,
    ) -> None:
        """Regressão: artifact['intent_present'] deve refletir dados recém-preenchidos."""
        mock_stdin.isatty.return_value = True
        data: dict = {
            "verify": {"tests_pass": True},
            "surgical": {"files": [{"path": "src/app.py", "necessary": True}]},
        }
        result = cli._step_artifact("task", data)

        assert result["artifact"]["intent_owed"] is True
        assert result["artifact"]["intent_present"] is True
        assert result["artifact"]["auth_present"] is False
        assert result["artifact"]["pending_present"] is False
        assert result["artifact"]["twins_present"] is False


class TestMainInteractive:
    """Testa main() no modo interativo completo."""

    @patch("kata.cli._step_verify")
    @patch("kata.cli._step_surgical")
    @patch("kata.cli._step_simplify")
    @patch("kata.cli._step_think")
    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_main_with_task_arg(
        self, mock_kata_dir, mock_init, mock_think, mock_simplify,
        mock_surgical, mock_verify, tmp_path, monkeypatch
    ) -> None:
        """Testa main() com --task argument — modo interativo não-TTY."""

        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        monkeypatch.chdir(tmp_path)

        # Cria arquivo de tarefa
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text(
            cli._serialize({"task": "test-task", "status": "draft"}),
            encoding="utf-8",
        )

        mock_think.return_value = {
            "task": "test-task",
            "status": "think-complete",
            "think": {"answered": True},
        }
        mock_simplify.return_value = {
            "task": "test-task",
            "status": "think-complete",
            "simplify": {"minimum_code": True},
        }
        mock_surgical.return_value = {
            "task": "test-task",
            "status": "think-complete",
            "surgical": {"files": []},
        }
        mock_verify.return_value = {
            "task": "test-task",
            "status": "approved",
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
                "success_criteria_met": True,
            },
        }

        with patch("sys.argv", ["kata", "--task", "test-task"]):
            cli.main()

        mock_think.assert_called_once()
        mock_simplify.assert_called_once()
        mock_surgical.assert_called_once()
        mock_verify.assert_called_once()

    @patch("kata.cli._step_verify")
    @patch("kata.cli._step_surgical")
    @patch("kata.cli._step_simplify")
    @patch("kata.cli._step_think")
    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_main_rejected_exits_1(
        self, mock_kata_dir, mock_init, mock_think, mock_simplify,
        mock_surgical, mock_verify, tmp_path, monkeypatch
    ) -> None:
        """Testa que main() sai com código 1 se a tarefa for rejeitada."""

        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        monkeypatch.chdir(tmp_path)

        task_file = kata_dir / "bad-task.yaml"
        task_file.write_text(
            cli._serialize({"task": "bad-task", "status": "draft"}),
            encoding="utf-8",
        )

        mock_think.return_value = {"task": "bad-task", "status": "think-complete"}
        mock_simplify.return_value = {"task": "bad-task", "simplify": {}}
        mock_surgical.return_value = {"task": "bad-task", "surgical": {}}
        mock_verify.return_value = {
            "task": "bad-task",
            "status": "rejected",
            "verify": {"ruff_clean": False},
        }

        with patch("sys.argv", ["kata", "--task", "bad-task"]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 1


class TestStepFit:
    """Testa _step_fit em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_step_fit_non_tty(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_fit("task", data)
        assert result["fit"]["trivial"] is False
        assert result["fit"]["route"] == "code-loop"
        assert result["fit"]["reason"] == "non-interactive mode"

    def test_step_fit_already_answered(self, capsys) -> None:
        data: dict = {"fit": {"answered": True, "trivial": True}}
        result = cli._step_fit("task", data)
        assert result["fit"]["trivial"] is True
        assert "já respondido" in capsys.readouterr().out

    @patch("kata.cli.diff_stats")
    @patch("kata.cli.input")
    @patch("kata.cli.sys.stdin")
    def test_step_fit_interactive_code_loop(
        self, mock_stdin, mock_input, mock_diff_stats
    ) -> None:
        mock_stdin.isatty.return_value = True
        mock_diff_stats.return_value = (["src/foo.py"], 3)
        mock_input.side_effect = ["1", "bugfix simples"]
        data: dict = {}
        result = cli._step_fit("task", data)
        assert result["fit"]["trivial"] is True
        assert result["fit"]["route"] == "code-loop"
        assert "bugfix" in result["fit"]["reason"]

    @patch("kata.cli.diff_stats")
    @patch("kata.cli.input")
    @patch("kata.cli.sys.stdin")
    def test_step_fit_interactive_plan_first(
        self, mock_stdin, mock_input, mock_diff_stats
    ) -> None:
        mock_stdin.isatty.return_value = True
        mock_diff_stats.return_value = ([], 0)
        mock_input.side_effect = ["2", "precisa de planejamento"]
        data: dict = {}
        result = cli._step_fit("task", data)
        assert result["fit"]["trivial"] is True
        assert result["fit"]["route"] == "plan-first"


class TestMainPlanMode:
    """Testa main() no modo --plan."""

    @patch("kata.cli._step_think")
    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_plan_mode_creates_and_stops(
        self, mock_kata_dir, mock_init, mock_think, tmp_path, monkeypatch
    ) -> None:
        """--plan cria task, executa FIT + THINK, salva e para."""
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        monkeypatch.chdir(tmp_path)

        mock_think.return_value = {
            "task": "plan-task",
            "status": "think-complete",
            "think": {"answered": True},
        }

        with patch("sys.argv", ["kata", "--plan", "--task", "plan-task"]):
            cli.main()

        mock_init.assert_called_once_with("plan-task")
        mock_think.assert_called_once()

        # Verifica que o arquivo foi salvo
        ext = cli._ext()
        plan_file = kata_dir / f"plan-task{ext}"
        assert plan_file.exists()

    @patch("kata.cli._pick_task")
    @patch("kata.cli._step_think")
    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_plan_mode_without_task_arg(
        self, mock_kata_dir, mock_init, mock_think, mock_pick, tmp_path, monkeypatch
    ) -> None:
        """--plan sem --task usa _pick_task."""
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        monkeypatch.chdir(tmp_path)

        mock_pick.return_value = "auto-plan"
        mock_think.return_value = {
            "task": "auto-plan",
            "status": "think-complete",
            "think": {"answered": True},
        }

        with patch("sys.argv", ["kata", "--plan"]):
            cli.main()

        mock_pick.assert_called_once()
        mock_init.assert_called_once_with("auto-plan")
        mock_think.assert_called_once()


class TestMainPlanCheckOnlyConflict:
    """Testa que --plan e --check-only são mutuamente exclusivos."""

    def test_plan_and_check_only_conflict(self) -> None:
        with patch("sys.argv", ["kata", "--plan", "--check-only"]):
            try:
                cli.main()
            except SystemExit as e:
                assert e.code == 2  # parser.error exit code


class TestMainRouteHandling:
    """Testa que main() respeita fit.route e fit.trivial."""

    def _setup_task_file(self, kata_dir: Path) -> None:
        task_file = kata_dir / "route-task.yaml"
        task_file.write_text("task: route-task\nstatus: draft\n", encoding="utf-8")

    @patch("kata.cli._step_report")
    @patch("kata.cli._step_artifact")
    @patch("kata.cli._step_verify")
    @patch("kata.cli._step_surgical")
    @patch("kata.cli._step_intent")
    @patch("kata.cli._step_simplify")
    @patch("kata.cli._step_think")
    @patch("kata.cli._step_fit")
    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_question_route_stops_after_think(
        self, mock_kata_dir, mock_init, mock_fit, mock_think,
        mock_simplify, mock_intent, mock_surgical, mock_verify,
        mock_artifact, mock_report, tmp_path, monkeypatch,
    ) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        monkeypatch.chdir(tmp_path)
        self._setup_task_file(kata_dir)

        mock_fit.return_value = {
            "task": "route-task",
            "fit": {"route": "question", "trivial": False},
        }
        mock_think.return_value = {
            "task": "route-task",
            "fit": {"route": "question", "trivial": False},
            "think": {"answered": True},
        }

        with patch("sys.argv", ["kata", "--task", "route-task"]):
            cli.main()

        mock_think.assert_called_once()
        mock_simplify.assert_not_called()
        mock_intent.assert_not_called()
        mock_surgical.assert_not_called()
        mock_verify.assert_not_called()
        mock_artifact.assert_not_called()
        mock_report.assert_not_called()

    @patch("kata.cli._step_report")
    @patch("kata.cli._step_artifact")
    @patch("kata.cli._step_verify")
    @patch("kata.cli._step_twin")
    @patch("kata.cli._step_surgical")
    @patch("kata.cli._step_intent")
    @patch("kata.cli._step_simplify")
    @patch("kata.cli._step_think")
    @patch("kata.cli._step_fit")
    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_trivial_route_skips_simplify_intent_surgical_twin(
        self, mock_kata_dir, mock_init, mock_fit, mock_think,
        mock_simplify, mock_intent, mock_surgical, mock_twin,
        mock_verify, mock_artifact, mock_report, tmp_path, monkeypatch,
    ) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        monkeypatch.chdir(tmp_path)
        self._setup_task_file(kata_dir)

        mock_fit.return_value = {
            "task": "route-task",
            "fit": {"route": "code-loop", "trivial": True},
        }
        mock_think.return_value = {
            "task": "route-task",
            "fit": {"route": "code-loop", "trivial": True},
            "think": {"answered": True},
        }
        mock_verify.return_value = {
            "task": "route-task",
            "status": "approved",
            "verify": {"ruff_clean": True},
        }
        mock_artifact.return_value = {
            "task": "route-task",
            "status": "approved",
            "artifact": {},
        }

        with patch("sys.argv", ["kata", "--task", "route-task"]):
            cli.main()

        mock_simplify.assert_not_called()
        mock_intent.assert_not_called()
        mock_surgical.assert_not_called()
        mock_twin.assert_not_called()
        mock_verify.assert_called_once()
        mock_artifact.assert_called_once()
        mock_report.assert_called_once()


class TestMainInteractiveNoTaskArg:
    """Testa main() sem --task — usa _pick_task (modo não-TTY)."""

    @patch("kata.cli._step_verify")
    @patch("kata.cli._step_surgical")
    @patch("kata.cli._step_simplify")
    @patch("kata.cli._step_think")
    @patch("kata.cli._pick_task")
    @patch("kata.cli._init_task")
    @patch("kata.cli._kata_dir")
    def test_main_uses_pick_task_when_no_arg(
        self, mock_kata_dir, mock_init, mock_pick, mock_think,
        mock_simplify, mock_surgical, mock_verify, tmp_path, monkeypatch
    ) -> None:

        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        monkeypatch.chdir(tmp_path)

        # _pick_task retorna "auto-task"
        mock_pick.return_value = "auto-task"

        # Arquivo não existe, então _init_task será chamado
        mock_think.return_value = {
            "task": "auto-task",
            "status": "think-complete",
            "think": {"answered": True},
        }
        mock_simplify.return_value = {
            "task": "auto-task",
            "status": "think-complete",
            "simplify": {"minimum_code": True},
        }
        mock_surgical.return_value = {
            "task": "auto-task",
            "status": "think-complete",
            "surgical": {"files": []},
        }
        mock_verify.return_value = {
            "task": "auto-task",
            "status": "approved",
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
                "success_criteria_met": True,
            },
        }

        with patch("sys.argv", ["kata"]):
            cli.main()

        mock_pick.assert_called_once()
        mock_init.assert_called_once_with("auto-task")


class TestPickTaskInteractiveMenu:
    """Testa _pick_task com menu interativo de tarefas existentes."""

    @patch("kata.cli.input", return_value="1")
    @patch("kata.cli._detect_task_from_branch", return_value=None)
    @patch("kata.cli.sys.stdin")
    def test_pick_task_menu_numeric_choice(self, mock_stdin, mock_branch, mock_input) -> None:
        from pathlib import Path

        mock_stdin.isatty.return_value = True
        fake_path_1 = MagicMock()
        fake_path_1.stem = "alpha"
        fake_path_2 = MagicMock()
        fake_path_2.stem = "beta"

        with patch("kata.cli._kata_dir") as mock_kata_dir:
            mock_kata_dir.return_value = Path("/tmp/.kata")
            with patch.object(Path, "glob", return_value=[fake_path_1, fake_path_2]):
                result = cli._pick_task()
        assert result == "alpha"

    @patch("kata.cli.input", return_value="beta")
    @patch("kata.cli._detect_task_from_branch", return_value=None)
    @patch("kata.cli.sys.stdin")
    def test_pick_task_menu_name_choice(self, mock_stdin, mock_branch, mock_input) -> None:
        from pathlib import Path

        mock_stdin.isatty.return_value = True
        fake_path = MagicMock()
        fake_path.stem = "beta"

        with patch("kata.cli._kata_dir") as mock_kata_dir:
            mock_kata_dir.return_value = Path("/tmp/.kata")
            with patch.object(Path, "glob", return_value=[fake_path]):
                result = cli._pick_task()
        assert result == "beta"


class TestMainJudge:
    """Testa o modo --judge (adversarial verification)."""

    @patch("kata.cli.judge_task")
    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_judge_verified(
        self, mock_kata_dir, mock_path, mock_deserialize, mock_judge,
        tmp_path, monkeypatch,
    ) -> None:
        from kata.judge import JudgeResult

        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text("task: test-task\nstatus: approved\n", encoding="utf-8")
        mock_path.return_value = task_file

        mock_deserialize.return_value = {"task": "test-task", "status": "approved"}
        mock_judge.return_value = JudgeResult(
            verdict="VERIFIED",
            claims=["ruff passou"],
            re_ran_checks={"ruff": True},
        )

        with patch("sys.argv", ["kata", "--task", "test-task", "--judge"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 0

    @patch("kata.cli.judge_task")
    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_judge_refuted(
        self, mock_kata_dir, mock_path, mock_deserialize, mock_judge,
        tmp_path, monkeypatch,
    ) -> None:
        from kata.judge import JudgeFraud, JudgeResult

        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text("task: test-task\nstatus: approved\n", encoding="utf-8")
        mock_path.return_value = task_file

        mock_deserialize.return_value = {"task": "test-task", "status": "approved"}
        mock_judge.return_value = JudgeResult(
            verdict="REFUTED",
            claims=["ruff passou"],
            frauds=[
                JudgeFraud(type="false_completion", severity="high",
                           description="ruff re-executado falhou", evidence="realidade: falha"),
            ],
            re_ran_checks={"ruff": False},
        )

        with patch("sys.argv", ["kata", "--task", "test-task", "--judge"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1

    @patch("kata.cli.judge_task")
    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_judge_caveats_is_not_a_failure(
        self, mock_kata_dir, mock_path, mock_deserialize, mock_judge,
        tmp_path, monkeypatch, capsys,
    ) -> None:
        """Só REFUTED é falha. Equiparar ressalva de baixa severidade a fraude
        grave leva o CI a ignorar o exit code por inútil."""
        from kata.judge import JudgeFraud, JudgeResult

        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text("task: test-task\nstatus: approved\n", encoding="utf-8")
        mock_path.return_value = task_file

        mock_deserialize.return_value = {"task": "test-task", "status": "approved"}
        mock_judge.return_value = JudgeResult(
            verdict="VERIFIED WITH CAVEATS",
            claims=["ruff passou"],
            frauds=[
                JudgeFraud(type="debris", severity="low",
                           description="TODO deixado no código", evidence="+ # TODO"),
            ],
            re_ran_checks={"ruff": True},
        )

        with patch("sys.argv", ["kata", "--task", "test-task", "--judge"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 0
        # A re-execução mostra o papel, não a ferramenta: "✅ ruff" num
        # projeto que roda eslint é ruído para quem lê o veredito.
        assert "✅ lint" in capsys.readouterr().out

    @patch("kata.cli.judge_task")
    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_judge_unverifiable_e_anunciado_e_nao_e_falha(
        self, mock_kata_dir, mock_path, mock_deserialize, mock_judge,
        tmp_path, monkeypatch, capsys,
    ) -> None:
        """UNVERIFIABLE tem de aparecer na tela com os pontos cegos listados.

        O exit 0 é deliberado: o juiz não achou nada errado, só não teve
        como olhar. Reprovar aqui quebraria o --judge de todo projeto
        não-Python antes de haver alternativa a oferecer.
        """
        from kata.judge import JudgeResult

        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text("task: test-task\nstatus: approved\n", encoding="utf-8")
        mock_path.return_value = task_file

        mock_deserialize.return_value = {"task": "test-task", "status": "approved"}
        mock_judge.return_value = JudgeResult(
            verdict="UNVERIFIABLE",
            blind_spots=["nenhuma verificação re-executada — o relatório não afirma"],
        )

        with patch("sys.argv", ["kata", "--task", "test-task", "--judge"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()

        out = capsys.readouterr().out
        assert "UNVERIFIABLE" in out
        assert "Pontos cegos" in out
        assert "nenhuma verificação re-executada" in out
        assert exc.value.code == 0

    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_judge_task_not_found(self, mock_kata_dir, mock_path, tmp_path, monkeypatch) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        mock_path.return_value = kata_dir / "nonexistent.yaml"

        with patch("sys.argv", ["kata", "--task", "nonexistent", "--judge"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1

    def test_judge_conflicts_with_plan(self) -> None:
        with patch("sys.argv", ["kata", "--judge", "--plan"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 2

    def test_judge_conflicts_with_check_only(self) -> None:
        with patch("sys.argv", ["kata", "--judge", "--check-only"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 2


class TestMainAudit:
    """Testa o modo --audit (graduação followed/skipped/faked)."""

    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_audit_clean_exits_zero(
        self, mock_kata_dir, mock_path, mock_deserialize,
        tmp_path, monkeypatch,
    ) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text("task: test-task\nstatus: approved\n", encoding="utf-8")
        mock_path.return_value = task_file
        mock_deserialize.return_value = {
            "task": "test-task",
            "think": {"answered": True, "problem": "bug real", "skipped": False},
        }

        with patch("sys.argv", ["kata", "--task", "test-task", "--audit"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 0

    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_audit_with_faked_phase_exits_one(
        self, mock_kata_dir, mock_path, mock_deserialize,
        tmp_path, monkeypatch,
    ) -> None:
        """R7-1 como tarefa concluída: THINK 'respondido' com conteúdo vazio
        tem de derrubar o audit."""
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text("task: test-task\nstatus: approved\n", encoding="utf-8")
        mock_path.return_value = task_file
        mock_deserialize.return_value = {
            "task": "test-task",
            "status": "approved",
            "think": {"answered": True, "problem": "", "skipped": False},
        }

        with patch("sys.argv", ["kata", "--task", "test-task", "--audit"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1

    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_audit_task_not_found(self, mock_kata_dir, mock_path, tmp_path) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        mock_path.return_value = kata_dir / "nonexistent.yaml"

        with patch("sys.argv", ["kata", "--task", "nonexistent", "--audit"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1

    @pytest.mark.parametrize("flag", [
        ["--audit", "--plan"],
        ["--audit", "--check-only"],
        ["--audit", "--judge"],
        ["--audit", "--report"],
        ["--audit", "--init", "x"],
    ])
    def test_audit_conflicts_with_other_modes(self, flag) -> None:
        with patch("sys.argv", ["kata", *flag]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 2


class TestTaskFlagRejectsPathTraversal:
    """Testa que --task/--init/--judge/--report rejeitam nomes com '..'/'/'
    ponta a ponta pelo main(), não só no helper _task_path isolado."""

    def test_report_rejects_traversal(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["kata", "--task", "../escaped", "--report"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1
        assert not (tmp_path.parent / "escaped.yaml").exists()

    def test_judge_rejects_traversal(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["kata", "--task", "../../escaped", "--judge"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1

    def test_init_rejects_traversal(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["kata", "--init", "../escaped-init"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1
        assert not (tmp_path.parent / "escaped-init.yaml").exists()


class TestHasDeployDocs:
    """Testa _has_deploy_docs — detecção de docs de deploy."""

    def test_no_readme_returns_false(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert cli._has_deploy_docs() is False

    def test_readme_with_deploy_keywords(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("Use docker compose to deploy", encoding="utf-8")
        assert cli._has_deploy_docs() is True

    def test_readme_without_deploy_keywords(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("Just a library", encoding="utf-8")
        assert cli._has_deploy_docs() is False

    @patch("kata.cli.Path.read_text")
    def test_read_error_returns_false(self, mock_read) -> None:
        mock_read.side_effect = Exception("read error")
        assert cli._has_deploy_docs() is False


class TestDetectAuthOwed:
    """Testa _detect_auth_owed — detecção de ação irreversível."""

    def test_no_auth_data(self) -> None:
        assert cli._detect_auth_owed({}) is False

    def test_auth_data_exists(self) -> None:
        data = {"auth": {"action_taken": True}}
        assert cli._detect_auth_owed(data) is True

    def test_auth_data_not_taken(self) -> None:
        data = {"auth": {"action_taken": False}}
        assert cli._detect_auth_owed(data) is False

    def test_unpushed_local_commits_do_not_imply_auth_owed(self, tmp_path, monkeypatch) -> None:
        """Commits locais não enviados são reversíveis — não devem disparar AUTH."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], check=True)
        subprocess.run(["git", "config", "user.name", "test"], check=True)
        (tmp_path / "f.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "local only"], check=True)
        assert cli._detect_auth_owed({}) is False


class TestDetectPendingOwed:
    """Testa _detect_pending_owed — detecção de follow-up pendente."""

    @patch("kata.cli._has_deploy_docs", return_value=True)
    def test_approved_with_deploy_docs(self, mock_deploy) -> None:
        data = {"status": "approved"}
        assert cli._detect_pending_owed(data) is True

    @patch("kata.cli._has_deploy_docs", return_value=False)
    def test_approved_no_deploy_docs(self, mock_deploy) -> None:
        data = {"status": "approved"}
        assert cli._detect_pending_owed(data) is False

    @patch("kata.cli._has_deploy_docs", return_value=True)
    def test_not_approved(self, mock_deploy) -> None:
        data = {"status": "draft"}
        assert cli._detect_pending_owed(data) is False

    @patch("kata.cli._has_deploy_docs", return_value=False)
    def test_pending_data_exists(self, mock_deploy) -> None:
        data = {"pending": {"action": "deploy container"}}
        assert cli._detect_pending_owed(data) is True


class TestDetectTwinsOwed:
    """Testa _detect_twins_owed — detecção de defeito corrigido."""

    def test_intent_conflict(self) -> None:
        data = {"intent": {"answered": True, "all_agree": False}}
        assert cli._detect_twins_owed(data) is True

    def test_intent_all_agree(self) -> None:
        data = {"intent": {"answered": True, "all_agree": True}}
        assert cli._detect_twins_owed(data) is False

    def test_twins_data_exists(self) -> None:
        data = {"twins": {"pattern": "parse_date"}}
        assert cli._detect_twins_owed(data) is True

    def test_no_intent(self) -> None:
        assert cli._detect_twins_owed({}) is False

    def test_intent_not_answered(self) -> None:
        data = {"intent": {"answered": False, "all_agree": False}}
        assert cli._detect_twins_owed(data) is False

    def test_verify_passed_alone_does_not_trigger(self) -> None:
        """Passar nas verificações é o estado normal de uma tarefa concluída,
        não evidência de defeito corrigido. Enquanto isso bastava, TWINS era
        devida em toda tarefa aprovada e o gate virava ruído."""
        data = {"verify": {"tests_pass": True, "coverage_pass": True}}
        assert cli._detect_twins_owed(data) is False

    def test_verify_partial_does_not_trigger(self) -> None:
        data = {"verify": {"tests_pass": True, "coverage_pass": False}}
        assert cli._detect_twins_owed(data) is False

    def test_declared_defect_fix_triggers(self) -> None:
        data = {"twins": {"defect_fixed": True}}
        assert cli._detect_twins_owed(data) is True

    def test_declined_defect_fix_does_not_trigger(self) -> None:
        data = {
            "verify": {"tests_pass": True, "coverage_pass": True},
            "twins": {"defect_fixed": False, "searched": False},
        }
        assert cli._detect_twins_owed(data) is False

    def test_verify_none_does_not_trigger(self) -> None:
        data = {}
        assert cli._detect_twins_owed(data) is False


class TestFormatLines:
    """Testa formatação das linhas INTENT/AUTH/PENDING/TWINS."""

    def test_intent_line_full(self) -> None:
        intent = {
            "code_does": "retorna None",
            "check_expects": "retorna str",
            "spec_says": "retorna int",
        }
        line = cli._format_intent_line(intent)
        assert "INTENT:" in line
        assert "retorna None" in line
        assert "retorna str" in line
        assert "retorna int" in line

    def test_intent_line_empty(self) -> None:
        assert cli._format_intent_line({}) == ""

    def test_auth_line_full(self) -> None:
        auth = {"authorized": True, "quote": "pode fazer deploy"}
        line = cli._format_auth_line(auth)
        assert "AUTH:" in line
        assert "pode fazer deploy" in line

    def test_auth_line_not_authorized(self) -> None:
        assert cli._format_auth_line({"authorized": False}) == ""
        assert cli._format_auth_line({}) == ""

    def test_pending_line_full(self) -> None:
        pending = {"documented": True, "action": "push to staging"}
        line = cli._format_pending_line(pending)
        assert "PENDING:" in line
        assert "push to staging" in line

    def test_pending_line_not_documented(self) -> None:
        assert cli._format_pending_line({}) == ""

    def test_twins_line_full(self) -> None:
        twins = {"searched": True, "pattern": "parse_date", "result": "3 other files"}
        line = cli._format_twins_line(twins)
        assert "TWINS:" in line
        assert "parse_date" in line
        assert "3 other files" in line

    def test_twins_line_not_searched(self) -> None:
        assert cli._format_twins_line({}) == ""

    def test_twins_line_no_result(self) -> None:
        twins = {"searched": True, "pattern": "bug_pattern"}
        line = cli._format_twins_line(twins)
        assert "none" in line

    def test_twins_line_with_counts(self) -> None:
        twins = {
            "searched": True, "pattern": "parse_date",
            "result": "3 file(s), 5 occurrence(s)",
            "files_count": 3, "matches_count": 5,
        }
        line = cli._format_twins_line(twins)
        assert "3 file(s)" in line
        assert "5 occurrence(s)" in line
        assert "parse_date" in line

    def test_twins_line_zero_files_omits_detail(self) -> None:
        twins = {"searched": True, "pattern": "bug_pattern", "result": ""}
        line = cli._format_twins_line(twins)
        assert "TWINS:" in line
        assert "file(s)" not in line
        assert "occurrence(s)" not in line


@patch("kata.cli.untracked_files", return_value=[])
class TestDetectScratch:
    """Testa _detect_scratch_files.

    untracked_files é mockado no nível da classe: _detect_scratch_files passa
    por _changed_paths, que consulta o git de verdade. Sem isso os testes
    passariam ou falhariam conforme o que houvesse untracked na árvore de
    quem roda.
    """

    @patch("kata.cli._run_git")
    def test_no_diff(self, mock_run, mock_untracked) -> None:
        mock_run.return_value.stdout = ""
        assert cli._detect_scratch_files() == []

    @patch("kata.cli._run_git")
    def test_scratch_file_detected(self, mock_run, mock_untracked) -> None:
        mock_run.return_value.stdout = "file.tmp\nscratch/data.txt\n"
        files = cli._detect_scratch_files()
        assert len(files) == 2

    @patch("kata.cli._run_git")
    def test_normal_files_ignored(self, mock_run, mock_untracked) -> None:
        mock_run.return_value.stdout = "src/main.py\ntests/test_foo.py\n"
        assert cli._detect_scratch_files() == []

    @patch("kata.cli._run_git")
    def test_temp_substring_is_not_debris(self, mock_run, mock_untracked) -> None:
        """Regressão: a regra do CLI casava a substring "temp" e marcava
        templates/, temperature.py e attempt_parser.py como detrito. O CLI
        agora usa a mesma regra do JUDGE (is_debris_file)."""
        mock_run.return_value.stdout = (
            "templates/email.html\n"
            "src/temperature.py\n"
            "attempt_parser.py\n"
            "contemporary_utils.py\n"
        )
        assert cli._detect_scratch_files() == []

    @patch("kata.cli._run_git")
    def test_real_debris_still_detected_alongside_temp_substrings(
        self, mock_run, mock_untracked
    ) -> None:
        mock_run.return_value.stdout = "templates/email.html\nout.tmp\n"
        assert cli._detect_scratch_files() == ["out.tmp"]


class TestStepReport:
    """Testa _step_report — formato e conteúdo do relatório outcome-first."""

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_approved_report(self, mock_scratch, capsys) -> None:
        data = {
            "status": "approved",
            "think": {"problem": "validacao de data falha"},
            "done": "done = teste de fuso passa",
            "intent": {
                "code_does": "retorna None",
                "check_expects": "retorna str",
                "spec_says": "retorna int",
            },
            "surgical": {"files": [{"path": "src/parser.py", "necessary": True}]},
            "verify": {"ruff_clean": True, "tests_pass": True, "coverage_pass": True,
                       "coverage_pct": 92.0, "success_criteria_met": True},
            "artifact": {},
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "APROVADO" in out
        assert "validacao de data falha" in out
        assert "src/parser.py" in out
        assert "INTENT:" in out
        assert "92.0%" in out
        # Fable Step 1: o critério declarado no THINK aparece no relatório
        assert "Critério declarado" in out
        assert "teste de fuso passa" in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_report_without_done_omits_criterion(self, mock_scratch, capsys) -> None:
        data = {"status": "approved", "think": {"problem": "x"}, "verify": {},
                "artifact": {}}
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "Critério declarado" not in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_report_hand_back_caveat(self, mock_scratch, capsys) -> None:
        """Fable Step 5: estourado o bound, o relatório diz explicitamente que
        a tarefa foi devolvida — com o número de tentativas — em vez de um
        'rejeitado' genérico."""
        data = {
            "status": "rejected",
            "verify": {"hand_back": True, "attempts": 3},
            "artifact": {},
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "hand back" in out
        assert "3 tentativa(s)" in out
        assert "hipótese atual" in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_report_warns_when_owed_intent_is_absent(self, mock_scratch, capsys) -> None:
        """Comportamento mudou mas a intenção não foi registrada: o relatório
        tem de dizer isso em vez de passar batido."""
        data = {
            "status": "approved",
            "verify": {"ruff_clean": True, "tests_pass": True,
                       "coverage_pass": True, "coverage_pct": 91.0},
            "artifact": {"intent_owed": True, "intent_present": False},
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "Caveats" in out
        assert "INTENT não documentada" in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_report_survives_null_coverage_pct(self, mock_scratch, capsys) -> None:
        """Regressão: a chave coverage_pct existe com valor None no template
        de --init e nos YAMLs escritos à mão pelas skills, então o default do
        .get() nunca entrava e o format de None levantava TypeError."""
        data = {
            "status": "rejected",
            "verify": {
                "ruff_clean": True,
                "tests_pass": False,
                "coverage_pass": False,
                "coverage_pct": None,
            },
            "artifact": {},
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "REJEITADO" in out
        assert "0.0%" in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_rejected_report_has_caveats(self, mock_scratch, capsys) -> None:
        data = {
            "status": "rejected",
            "verify": {"ruff_clean": False, "tests_pass": False},
            "artifact": {},
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "REJEITADO" in out
        assert "Ciclo rejeitado" in out

    @patch("kata.cli._detect_scratch_files", return_value=["debug.tmp"])
    def test_scratch_caveat(self, mock_scratch, capsys) -> None:
        data = {"status": "approved", "verify": {}, "artifact": {}}
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "debug.tmp" in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_pending_line_in_report(self, mock_scratch, capsys) -> None:
        data = {
            "status": "approved",
            "verify": {"tests_pass": True},
            "artifact": {},
            "pending": {"documented": True, "action": "deploy to production"},
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "PENDING:" in out
        assert "deploy to production" in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_draft_status_returns_early(self, mock_scratch, capsys) -> None:
        data = {"status": "draft"}
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "em andamento" in out
        assert "APROVADO" not in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_report_with_auth_caveat(self, mock_scratch, capsys) -> None:
        """AUTH owed mas não presente gera caveat no relatório."""
        data = {
            "status": "approved",
            "verify": {},
            "artifact": {"auth_owed": True, "auth_present": False,
                         "intent_owed": False, "intent_present": True},
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "AUTH" in out
        assert "autorização" in out

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_report_with_auth_pending_twins(self, mock_scratch, capsys) -> None:
        data = {
            "status": "approved",
            "think": {"problem": "bug fix"},
            "intent": {"code_does": "X", "check_expects": "Y", "spec_says": "Z"},
            "surgical": {"files": [{"path": "src/main.py", "necessary": True}]},
            "verify": {"tests_pass": True, "coverage_pass": True, "coverage_pct": 90.0},
            "artifact": {},
            "auth": {"authorized": True, "quote": "pode fazer deploy"},
            "pending": {"documented": True, "action": "rollout to prod"},
            "twins": {
                "searched": True, "pattern": "bug_pattern",
                "result": "2 files, 3 occurrences",
                "files_count": 2, "matches_count": 3,
            },
        }
        cli._step_report("test-task", data)
        out = capsys.readouterr().out
        assert "AUTH:" in out
        assert "PENDING:" in out
        assert "TWINS:" in out
        assert "2 file(s)" in out
        assert "rollout to prod" in out


class TestMainReport:
    """Testa o modo --report (outcome-first reporting)."""

    @patch("kata.cli._step_report")
    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_report_approved(
        self, mock_kata_dir, mock_path, mock_deserialize, mock_report,
        tmp_path, monkeypatch,
    ) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "test-task.yaml"
        task_file.write_text("task: test-task\nstatus: approved\n", encoding="utf-8")
        mock_path.return_value = task_file
        mock_deserialize.return_value = {"task": "test-task", "status": "approved"}

        with patch("sys.argv", ["kata", "--task", "test-task", "--report"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 0
        mock_report.assert_called_once()

    @patch("kata.cli._step_report")
    @patch("kata.cli._deserialize")
    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    @pytest.mark.parametrize("status,esperado", [
        ("think-complete", 0),   # modo --plan: em andamento, não é falha
        ("draft", 0),
        ("approved", 0),
        ("rejected", 1),         # só isto é falha
    ])
    def test_report_exit_code_by_status(
        self, mock_kata_dir, mock_path, mock_deserialize, mock_report,
        status, esperado, tmp_path,
    ) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        task_file = kata_dir / "t.yaml"
        task_file.write_text(f"task: t\nstatus: {status}\n", encoding="utf-8")
        mock_path.return_value = task_file
        mock_deserialize.return_value = {"task": "t", "status": status}

        with patch("sys.argv", ["kata", "--task", "t", "--report"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == esperado

    @patch("kata.cli._task_path")
    @patch("kata.cli._kata_dir")
    def test_report_task_not_found(self, mock_kata_dir, mock_path, tmp_path) -> None:
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        mock_kata_dir.return_value = kata_dir
        mock_path.return_value = kata_dir / "nonexistent.yaml"

        with patch("sys.argv", ["kata", "--task", "nonexistent", "--report"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 1

    def test_report_conflicts_with_judge(self) -> None:
        with patch("sys.argv", ["kata", "--report", "--judge"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 2

    def test_report_conflicts_with_plan(self) -> None:
        with patch("sys.argv", ["kata", "--report", "--plan"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 2


class TestInitTaskTemplate:
    """Testa que o template do _init_task inclui auth/pending/twins."""

    def test_template_has_auth_pending_twins(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir(parents=True, exist_ok=True)
        cli._init_task("template-test")
        path = tmp_path / ".kata" / "template-test.yaml"
        data = cli._deserialize(path.read_text(encoding="utf-8"))
        assert "auth" in data
        assert "pending" in data
        assert "twins" in data

    def test_template_twins_has_new_fields(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir(parents=True, exist_ok=True)
        cli._init_task("twins-fields")
        path = tmp_path / ".kata" / "twins-fields.yaml"
        data = cli._deserialize(path.read_text(encoding="utf-8"))
        twins = data.get("twins", {})
        assert "matches_count" in twins
        assert "files_count" in twins
        assert "fix_applied" in twins
        assert twins["matches_count"] == 0
        assert twins["files_count"] == 0
        assert twins["fix_applied"] is False

    def test_template_has_done_and_verify_bounds(self, tmp_path, monkeypatch) -> None:
        """O template declara as chaves novas dos gaps do Fable: `done`
        (critério antecipado) e verify.attempts/hand_back (hard bounds)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir(parents=True, exist_ok=True)
        cli._init_task("fable-fields")
        path = tmp_path / ".kata" / "fable-fields.yaml"
        data = cli._deserialize(path.read_text(encoding="utf-8"))
        assert data["done"] == ""
        verify = data.get("verify", {})
        assert verify["attempts"] == 0
        assert verify["hand_back"] is False


class TestPrintJudgeVerdict:
    """Testa _print_judge_verdict — output do resultado adversarial."""

    @patch("kata.cli.sys.stdout")
    def test_judge_verdict_shows_caveats(self, mock_stdout) -> None:
        from kata.judge import JudgeResult
        result = JudgeResult(
            verdict="VERIFIED WITH CAVEATS",
            caveats=["re-execução falhou: pytest"],
        )
        cli._print_judge_verdict(result)
        calls = [str(c) for c in mock_stdout.write.call_args_list]
        assert any("Ressalvas" in c for c in calls)
        assert any("pytest" in c for c in calls)

    def test_unverifiable_claims_are_labelled_apart(self, capsys) -> None:
        """O critério de sucesso não pode aparecer sob "Claims verificadas":
        nada o re-executa, e apresentá-lo como verificado é a fraude que o
        próprio JUDGE existe para caçar."""
        from kata.judge import JudgeResult
        result = JudgeResult(
            verdict="VERIFIED",
            claims=["todos os testes passam"],
            unverifiable_claims=["critério de sucesso satisfeito"],
        )
        cli._print_judge_verdict(result)
        out = capsys.readouterr().out

        verificadas = out.index("Claims verificadas:")
        sem_verificacao = out.index("Claims aceitas sem verificação")
        assert out.index("todos os testes passam") < sem_verificacao
        assert verificadas < sem_verificacao
        assert out.index("critério de sucesso") > sem_verificacao


class TestStepTwin:
    """Testa _step_twin — twin check automático após VERIFY."""

    def test_not_approved_returns_early(self) -> None:
        data = {"status": "rejected"}
        result = cli._step_twin("task", data)
        assert "twins" not in result

    def test_already_searched_returns_early(self) -> None:
        data = {"status": "approved", "twins": {"searched": True, "pattern": "foo"}}
        result = cli._step_twin("task", data)
        assert result["twins"]["searched"] is True

    @patch("kata.cli.sys.stdin")
    def test_non_tty_returns_defaults(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data = {"status": "approved", "intent": {"all_agree": True}}
        result = cli._step_twin("task", data)
        assert result["twins"]["searched"] is False

    @patch("kata.cli._confirm", return_value=False)
    @patch("kata.cli.sys.stdin")
    def test_no_defect_no_search(self, mock_stdin, mock_confirm) -> None:
        mock_stdin.isatty.return_value = True
        data = {"status": "approved", "intent": {"all_agree": True}}
        result = cli._step_twin("task", data)
        assert result["twins"]["searched"] is False
        mock_confirm.assert_called_once()
        # A resposta "não houve defeito" precisa ficar gravada: é o que
        # impede _detect_twins_owed de cobrar TWINS de toda tarefa aprovada.
        assert result["twins"]["defect_fixed"] is False
        assert cli._detect_twins_owed(result) is False

    @patch("kata.cli._confirm", return_value=True)
    @patch("kata.cli.search_pattern")
    @patch("kata.cli.sys.stdin")
    def test_defect_fixed_with_matches(
        self, mock_stdin, mock_search, mock_confirm,
    ) -> None:
        from kata.verify import SearchMatch, SearchResult

        mock_stdin.isatty.return_value = True
        mock_stdin.stdin.isatty.return_value = True
        mock_search.return_value = SearchResult(
            pattern="parse_date",
            matches=[SearchMatch(file="src/parser.py", line=42, content="parse_date(x)")],
            total_files=1,
        )
        data = {"status": "approved", "intent": {"all_agree": True}}
        with patch("builtins.input", side_effect=["parse_date"]):
            with patch("kata.cli._confirm") as mock_cf:
                mock_cf.side_effect = [True, False]
                result = cli._step_twin("task", data)

        assert result["twins"]["searched"] is True
        assert result["twins"]["pattern"] == "parse_date"
        assert "1 arquivo(s)" in result["twins"]["result"]
        assert result["twins"]["matches_count"] == 1
        assert result["twins"]["files_count"] == 1
        assert result["twins"]["fix_applied"] is False

    @patch("kata.cli._confirm", return_value=True)
    @patch("kata.cli.search_pattern")
    @patch("kata.cli.sys.stdin")
    def test_defect_fixed_many_matches_truncated(
        self, mock_stdin, mock_search, mock_confirm,
    ) -> None:
        from kata.verify import SearchMatch, SearchResult

        mock_stdin.isatty.return_value = True
        mock_search.return_value = SearchResult(
            pattern="TODO",
            matches=[SearchMatch(file=f"src/{i}.py", line=i, content="TODO")
                     for i in range(25)],
            total_files=25,
        )
        data = {"status": "approved", "intent": {"all_agree": True}}
        with patch("builtins.input", side_effect=["TODO"]):
            with patch("kata.cli._confirm") as mock_cf:
                mock_cf.side_effect = [True, False]
                result = cli._step_twin("task", data)

        assert result["twins"]["searched"] is True
        assert result["twins"]["matches_count"] == 25
        assert result["twins"]["files_count"] == 25

    @patch("kata.cli._confirm", return_value=True)
    @patch("kata.cli.search_pattern")
    @patch("kata.cli.sys.stdin")
    def test_defect_fixed_no_matches(
        self, mock_stdin, mock_search, mock_confirm,
    ) -> None:
        from kata.verify import SearchResult

        mock_stdin.isatty.return_value = True
        mock_search.return_value = SearchResult(pattern="nonexistent", total_files=0)
        data = {"status": "approved", "intent": {"all_agree": True}}
        with patch("builtins.input", side_effect=["nonexistent", ""]):
            result = cli._step_twin("task", data)

        assert result["twins"]["searched"] is True
        assert result["twins"]["matches_count"] == 0
        assert result["twins"]["files_count"] == 0
        assert result["twins"]["fix_applied"] is False

    @patch("kata.cli.search_pattern")
    @patch("kata.cli.sys.stdin")
    def test_empty_pattern_returns_early(self, mock_stdin, mock_search) -> None:
        mock_stdin.isatty.return_value = True
        data = {"status": "approved", "intent": {"all_agree": False}}
        with patch("builtins.input", return_value=""):
            result = cli._step_twin("task", data)
        assert result["twins"]["searched"] is False
        mock_search.assert_not_called()

    def test_intent_conflict_triggers_twin(self) -> None:
        data = {"status": "approved", "intent": {"all_agree": False}}
        with patch("kata.cli.sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            result = cli._step_twin("task", data)
        # Non-TTY, so returns defaults even though intent conflict
        assert result["twins"]["searched"] is False


class TestConfigDoProjeto:
    """`.kata/config.yaml` governa como o projeto alvo é verificado."""

    def test_config_quebrada_aborta_em_vez_de_cair_no_default(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """Verificar de outro jeito calado seria reportar sucesso de algo que
        o projeto nunca pediu — a fraude que o JUDGE existe para caçar."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "config.yaml").write_text(
            "verify:\n  lint: 42\n", encoding="utf-8"
        )

        with patch("sys.argv", ["kata", "--check-only"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()

        assert exc.value.code == 1
        assert "esperava string ou lista" in capsys.readouterr().out

    @patch("kata.cli.run_all")
    def test_comandos_declarados_chegam_ao_run_all(
        self, mock_run_all, tmp_path, monkeypatch, capsys
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "config.yaml").write_text(
            "verify:\n  lint: npx eslint src\n  test: npx vitest run\n  gate: 85\n",
            encoding="utf-8",
        )
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True, details={"command": "npx eslint src"}),
            "pytest": VerifyResult(ok=True, details={"command": "npx vitest run"}),
            "coverage": VerifyResult(ok=True, details={"coverage_pct": 90.0}),
        }

        with patch("sys.argv", ["kata", "--check-only"]):
            with pytest.raises(SystemExit):
                cli.main()

        cfg = mock_run_all.call_args.kwargs["config"]
        assert cfg.lint == ["npx", "eslint", "src"]
        assert cfg.test == ["npx", "vitest", "run"]
        # Gate da config vale quando --gate não foi passado.
        assert mock_run_all.call_args.kwargs["gate"] == 85.0

        out = capsys.readouterr().out
        assert "declaradas pelo projeto" in out
        # O VERIFY anuncia o comando que de fato rodou, não "ruff check src/".
        assert "npx eslint src" in out
        assert "npx vitest run" in out

    @patch("kata.cli.run_all")
    def test_flag_gate_vence_a_config(
        self, mock_run_all, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        (tmp_path / ".kata" / "config.yaml").write_text(
            "verify:\n  gate: 85\n", encoding="utf-8"
        )
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True, details={"coverage_pct": 95.0}),
        }

        with patch("sys.argv", ["kata", "--check-only", "--gate", "50"]):
            with pytest.raises(SystemExit):
                cli.main()

        assert mock_run_all.call_args.kwargs["gate"] == 50.0

    @patch("kata.cli.run_all")
    def test_sem_config_o_gate_default_continua_setenta(
        self, mock_run_all, tmp_path, monkeypatch, capsys
    ) -> None:
        monkeypatch.chdir(tmp_path)
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True, details={"coverage_pct": 95.0}),
        }

        with patch("sys.argv", ["kata", "--check-only"]):
            with pytest.raises(SystemExit):
                cli.main()

        assert mock_run_all.call_args.kwargs["gate"] == 70.0
        assert mock_run_all.call_args.kwargs["config"].customizado is False
        assert "declaradas pelo projeto" not in capsys.readouterr().out


class TestDoctor:
    """`--doctor` é o preflight: instalação parcial reprova, ausente não."""

    def _instala(self, config_dir, nomes):
        skills = config_dir / "skills"
        skills.mkdir(parents=True, exist_ok=True)
        for nome in nomes:
            (skills / nome).mkdir()

    def test_instalacao_completa_sai_zero(self, tmp_path, monkeypatch, capsys) -> None:
        from kata.skills import ORCHESTRATOR_SKILL, PHASE_SKILLS

        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))
        self._instala(tmp_path / "oc", PHASE_SKILLS)
        self._instala(tmp_path / "cc", [*PHASE_SKILLS, ORCHESTRATOR_SKILL])

        with patch("sys.argv", ["kata", "--doctor"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()

        assert exc.value.code == 0
        assert "Instalação completa" in capsys.readouterr().out

    def test_instalacao_parcial_reprova_e_nomeia_o_que_falta(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """9 de 10 é pior que 0 de 10: o ciclo roda e perde uma fase calado."""
        from kata.skills import PHASE_SKILLS

        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))
        self._instala(tmp_path / "oc", [s for s in PHASE_SKILLS if s != "kata-intent"])

        with patch("sys.argv", ["kata", "--doctor"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()

        out = capsys.readouterr().out
        assert exc.value.code == 1
        assert "PARCIAL" in out
        assert "kata-intent" in out
        assert "fase fingida" in out

    def test_nada_instalado_avisa_mas_nao_reprova(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """Quem só usa o CLI nunca instalou frontend nenhum, e está tudo bem."""
        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))

        with patch("sys.argv", ["kata", "--doctor"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()

        out = capsys.readouterr().out
        assert exc.value.code == 0
        assert "Nenhum frontend instalado" in out

    def test_nao_precisa_de_kata_dir(self, tmp_path, monkeypatch) -> None:
        """`--doctor` roda de qualquer diretório: é sobre a instalação das
        skills, não sobre uma tarefa."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))

        with patch("sys.argv", ["kata", "--doctor"]):
            with pytest.raises(SystemExit):
                cli.main()

        assert not (tmp_path / ".kata").exists()


class TestAuditPreflight:
    """Fase rodada sem a skill dela é degradada, não seguida.

    Antes disto, uma skill não instalada fazia o orquestrador improvisar a
    fase e gravar a seção como qualquer outra. O audit lia o YAML e dizia
    `followed` — a fraude vinha do ferramental e passava pelo detector que
    existe justamente para pegá-la.
    """

    def test_skill_faltante_vira_achado_degradado(self) -> None:
        data = {
            "preflight": {"skills_missing": ["kata-simplify", "kata-intent"]},
            "fit": {"answered": True, "reason": "feature", "skipped": False},
        }
        achados = cli._audit_task(data)
        pre = [a for a in achados if a["fase"] == "preflight"]
        assert len(pre) == 1
        assert pre[0]["status"] == "degraded"
        assert "kata-simplify" in pre[0]["risco"]
        assert "kata-intent" in pre[0]["risco"]

    def test_preflight_limpo_nao_gera_achado(self) -> None:
        data = {
            "preflight": {"skills_missing": []},
            "fit": {"answered": True, "reason": "feature", "skipped": False},
        }
        assert not [a for a in cli._audit_task(data) if a["fase"] == "preflight"]

    def test_tarefa_antiga_sem_preflight_nao_quebra(self) -> None:
        """Tarefas criadas antes da chave existir continuam auditáveis."""
        data = {"fit": {"answered": True, "reason": "feature", "skipped": False}}
        achados = cli._audit_task(data)
        assert [a["fase"] for a in achados] == ["fit"]

    def test_degradado_reprova_o_audit(self, tmp_path, monkeypatch, capsys) -> None:
        """Exit 1: um ciclo que rodou fases sem as instruções delas não pode
        sair com audit limpo."""
        monkeypatch.chdir(tmp_path)
        kata_dir = tmp_path / ".kata"
        kata_dir.mkdir()
        (kata_dir / "t.yaml").write_text(
            "task: t\nstatus: approved\n"
            "preflight:\n  skills_missing: [kata-think]\n"
            "fit: {answered: true, reason: feature, skipped: false}\n",
            encoding="utf-8",
        )

        with patch("sys.argv", ["kata", "--task", "t", "--audit"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()

        out = capsys.readouterr().out
        assert exc.value.code == 1
        assert "PREFLIGHT: degraded" in out
        assert "kata-think" in out
        assert "degradada(s)" in out

    def test_init_cria_a_chave_preflight(self, tmp_path, monkeypatch) -> None:
        """Quem começa pelo CLI e quem começa pela skill têm de acabar com o
        mesmo arquivo — senão o gate não dispara para um dos dois."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".kata").mkdir()
        cli._init_task("t")
        import yaml

        data = yaml.safe_load((tmp_path / ".kata" / "t.yaml").read_text(encoding="utf-8"))
        assert data["preflight"] == {"skills_missing": []}
