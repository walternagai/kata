"""Testes para kata.cli — helpers, steps interativos e main."""

from __future__ import annotations

import subprocess
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
    def test_step_think_non_tty_skips(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {"think": {}}
        result = cli._step_think("task", data)
        assert result["think"]["answered"] is True

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
        ]
        data: dict = {"think": {}}
        result = cli._step_think("task", data)
        assert result["think"]["problem"] == "Resolver bug X"
        assert result["think"]["assumptions"] == ["Usuário logado", "DB acessível"]
        assert result["think"]["alternatives"] == ["Refatorar", "Ignorar"]
        assert result["think"]["unknowns"] == "Não sei o impacto em prod"
        assert result["think"]["answered"] is True
        assert result["status"] == "think-complete"


class TestStepSimplify:
    """Testa _step_simplify em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_step_simplify_non_tty(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_simplify("task", data)
        assert result["simplify"]["minimum_code"] is True
        assert result["simplify"]["no_single_use_abstractions"] is True
        assert result["simplify"]["no_speculative_config"] is True

    @patch("kata.cli._confirm")
    @patch("kata.cli._run")
    @patch("kata.cli.sys.stdin")
    def test_step_simplify_interactive_with_diff(self, mock_stdin, mock_run, mock_confirm) -> None:
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
    @patch("kata.cli._run")
    @patch("kata.cli.sys.stdin")
    def test_step_simplify_no_diff_uses_staged(self, mock_stdin, mock_run, mock_confirm) -> None:
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
    @patch("kata.cli._run")
    @patch("kata.cli.sys.stdin")
    def test_step_simplify_no_changes(self, mock_stdin, mock_run, mock_confirm) -> None:
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
        assert result["simplify"]["notes"] == "notas de teste"


class TestStepSurgical:
    """Testa _step_surgical em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_step_surgical_non_tty(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_surgical("task", data)
        assert result["surgical"]["files"] == []
        assert result["surgical"]["removed_imports_clean"] is True

    @patch("kata.cli._confirm")
    @patch("kata.cli._run")
    @patch("kata.cli.sys.stdin")
    def test_step_surgical_interactive_with_files(self, mock_stdin, mock_run, mock_confirm) -> None:
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
    @patch("kata.cli._run")
    @patch("kata.cli.sys.stdin")
    def test_step_surgical_no_diff_uses_staged(self, mock_stdin, mock_run, mock_confirm) -> None:
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


class TestRunHelper:
    """Testa _run com kwargs."""

    @patch("kata.cli.subprocess.run")
    def test_run_passes_kwargs(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        cli._run(["echo", "test"], check=True)
        # Verifica que check=True foi passado como kwarg
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("check") is True

    @patch("kata.cli.subprocess.run")
    def test_run_basic_command(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "test"], returncode=0, stdout="test\n", stderr=""
        )
        result = cli._run(["echo", "test"])
        assert result.returncode == 0

    @patch("kata.cli.subprocess.run")
    def test_run_overrides_defaults_without_collision(self, mock_run) -> None:
        """Passar capture_output/cwd/text via kwargs sobrescreve defaults sem TypeError."""
        from pathlib import Path

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        custom_cwd = Path("/tmp/custom")
        cli._run(["echo", "test"], capture_output=False, text=False, cwd=custom_cwd)
        call_kwargs = mock_run.call_args[1]
        # Defaults sobrescritos pelos valores do caller
        assert call_kwargs.get("capture_output") is False
        assert call_kwargs.get("text") is False
        assert call_kwargs.get("cwd") == custom_cwd


class TestStepSurgicalNoFiles:
    """Testa _step_surgical sem arquivos alterados."""

    @patch("kata.cli._confirm")
    @patch("kata.cli._run")
    @patch("kata.cli.sys.stdin")
    def test_surgical_no_files_no_staged(self, mock_stdin, mock_run, mock_confirm) -> None:
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


class TestStepIntent:
    """Testa _step_intent em modos interativo e não-interativo."""

    @patch("kata.cli.sys.stdin")
    def test_intent_non_tty(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {}
        result = cli._step_intent("task", data)
        assert result["intent"]["answered"] is True
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
        }
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is True
        assert result["artifact"]["intent_present"] is True

    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_missing_intent(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = False
        data: dict = {"verify": {"tests_pass": True}}
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is True
        assert result["artifact"]["intent_present"] is False

    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_no_intent_needed(self, mock_stdin) -> None:
        """Se verify não tem tests_pass, INTENT não é devida."""
        mock_stdin.isatty.return_value = False
        data: dict = {"intent": {}}
        result = cli._step_artifact("task", data)
        assert result["artifact"]["intent_owed"] is False

    @patch("kata.cli.sys.stdin")
    def test_artifact_non_tty_empty_data(self, mock_stdin, capsys) -> None:
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


class TestHasUnpushed:
    """Testa _has_unpushed_commits — detecção de commits não enviados."""

    @patch("kata.cli._run")
    def test_has_unpushed_commits_exception(self, mock_run) -> None:
        mock_run.side_effect = Exception("git error")
        assert cli._has_unpushed_commits() is False


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

    @patch("kata.cli._has_unpushed_commits", return_value=True)
    def test_unpushed_commits(self, mock_unpushed) -> None:
        assert cli._detect_auth_owed({}) is True

    @patch("kata.cli._has_unpushed_commits", return_value=False)
    def test_no_unpushed_no_auth_data(self, mock_unpushed) -> None:
        assert cli._detect_auth_owed({}) is False

    @patch("kata.cli._has_unpushed_commits", return_value=False)
    def test_auth_data_exists(self, mock_unpushed) -> None:
        data = {"auth": {"action_taken": True}}
        assert cli._detect_auth_owed(data) is True

    @patch("kata.cli._has_unpushed_commits", return_value=False)
    def test_auth_data_not_taken(self, mock_unpushed) -> None:
        data = {"auth": {"action_taken": False}}
        assert cli._detect_auth_owed(data) is False


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

    def test_verify_passed_triggers_twins(self) -> None:
        data = {"verify": {"tests_pass": True, "coverage_pass": True}}
        assert cli._detect_twins_owed(data) is True

    def test_verify_partial_does_not_trigger(self) -> None:
        data = {"verify": {"tests_pass": True, "coverage_pass": False}}
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


class TestDetectScratch:
    """Testa _detect_scratch_files."""

    @patch("kata.cli._run")
    def test_no_diff(self, mock_run) -> None:
        mock_run.return_value.stdout = ""
        assert cli._detect_scratch_files() == []

    @patch("kata.cli._run")
    def test_scratch_file_detected(self, mock_run) -> None:
        mock_run.return_value.stdout = "file.tmp\nscratch/data.txt\n"
        files = cli._detect_scratch_files()
        assert len(files) == 2

    @patch("kata.cli._run")
    def test_normal_files_ignored(self, mock_run) -> None:
        mock_run.return_value.stdout = "src/main.py\ntests/test_foo.py\n"
        assert cli._detect_scratch_files() == []


class TestStepReport:
    """Testa _step_report — formato e conteúdo do relatório outcome-first."""

    @patch("kata.cli._detect_scratch_files", return_value=[])
    def test_approved_report(self, mock_scratch, capsys) -> None:
        data = {
            "status": "approved",
            "think": {"problem": "validacao de data falha"},
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
