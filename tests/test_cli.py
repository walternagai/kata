"""Testes para kata.cli — helpers, steps interativos e main."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

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
        ]
        mock_confirm.return_value = True
        data: dict = {}
        result = cli._step_surgical("task", data)
        assert result["surgical"]["files"] == []
        assert result["surgical"]["removed_imports_clean"] is True


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
