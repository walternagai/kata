"""Testes para kata.verify — lógica de verificação (ruff, pytest, coverage)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from kata.config import VerifyConfig
from kata.verify import (
    COMMAND_LABELS,
    COMMAND_TIMEOUT_SECONDS,
    MAX_UNTRACKED_FILE_BYTES,
    ROLE_LABELS,
    VerifyResult,
    _run,
    changed_files,
    consistency_failures,
    is_inspectable,
    run_all,
    run_command,
    run_command_coverage,
    run_coverage,
    run_pytest,
    run_ruff,
    search_pattern,
    untracked_files,
)


class TestVerifyResult:
    """Verifica o dataclass VerifyResult."""

    def test_default_values(self) -> None:
        result = VerifyResult(ok=True)
        assert result.ok is True
        assert result.output == ""
        assert result.details == {}

    def test_with_output_and_details(self) -> None:
        result = VerifyResult(
            ok=False,
            output="error",
            details={"command": "ruff check"},
        )
        assert result.ok is False
        assert result.output == "error"
        assert result.details["command"] == "ruff check"


class TestRunRuff:
    """Testa run_ruff com subprocess mockado."""

    @patch("kata.verify._run")
    def test_ruff_clean(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="All clear", stderr=""
        )
        result = run_ruff(paths=["src/", "tests/"])
        assert result.ok is True
        assert "All clear" in result.output

    @patch("kata.verify._run")
    def test_ruff_with_errors(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="F401 unused import", stderr=""
        )
        result = run_ruff()
        assert result.ok is False
        assert "F401" in result.output

    @patch("kata.verify._run")
    def test_ruff_default_paths(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        run_ruff()
        called_cmd = mock_run.call_args[0][0]
        assert "src/" in called_cmd
        assert "tests/" in called_cmd


class TestRun:
    """Testa a função _run (subprocess wrapper)."""

    @patch("kata.verify.subprocess.run")
    def test_run_passes_command(self, mock_subprocess_run: MagicMock) -> None:
        from kata.verify import _run

        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="hello\n", stderr=""
        )
        result = _run(["echo", "hello"])
        assert result.stdout == "hello\n"
        mock_subprocess_run.assert_called_once_with(
            ["echo", "hello"],
            capture_output=True,
            text=True,
            cwd=None,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

    @patch("kata.verify.subprocess.run")
    def test_run_with_cwd(self, mock_subprocess_run: MagicMock) -> None:
        from pathlib import Path

        from kata.verify import _run

        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        cwd = Path("/tmp")
        _run(["ls"], cwd=cwd)
        mock_subprocess_run.assert_called_once_with(
            ["ls"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

    @patch("kata.verify.subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 300))
    def test_run_timeout_vira_falha_observavel(self, mock_subprocess_run: MagicMock) -> None:
        result = _run(["sleep", "999"])
        assert result.returncode == 124
        assert "excedeu" in result.stderr

    @patch(
        "kata.verify.subprocess.run",
        side_effect=subprocess.TimeoutExpired("sleep", 300, output=b"parcial"),
    )
    def test_run_timeout_com_bytes_nao_crasha(self, mock_subprocess_run: MagicMock) -> None:
        """P-3: TimeoutExpired com stdout/stderr em bytes (comportamento real
        quando text=True não é respeitado) precisa decodificar com
        errors='replace', não crashar."""
        result = _run(["sleep", "999"])
        assert result.returncode == 124
        assert "parcial" in result.stdout
        assert "excedeu" in result.stderr


class TestRunPytest:
    """Testa run_pytest com subprocess mockado."""

    @patch("kata.verify._run")
    def test_pytest_pass(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="10 passed", stderr=""
        )
        result = run_pytest(testpaths=["tests/"])
        assert result.ok is True

    @patch("kata.verify._run")
    def test_pytest_fail(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="2 failed", stderr=""
        )
        result = run_pytest()
        assert result.ok is False

    @patch("kata.verify._run")
    def test_pytest_with_ignore(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        run_pytest(ignore=["tests/slow/"])
        called_cmd = mock_run.call_args[0][0]
        assert "--ignore" in called_cmd
        assert "tests/slow/" in called_cmd

    @patch("kata.verify._run")
    def test_pytest_with_extra_args(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="5 passed", stderr=""
        )
        run_pytest(extra_args=["-x", "--durations=5"])
        called_cmd = mock_run.call_args[0][0]
        assert "-x" in called_cmd
        assert "--durations=5" in called_cmd


class TestRunCoverage:
    """Testa run_coverage com subprocess mockado."""

    @patch("kata.verify._run")
    def test_coverage_above_gate(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                 100      10     90%",
            stderr="",
        )
        result = run_coverage(source="src", gate=70.0)
        assert result.ok is True
        assert result.details["coverage_pct"] == 90.0

    @patch("kata.verify._run")
    def test_coverage_below_gate(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="TOTAL                 100      50     50%",
            stderr="",
        )
        result = run_coverage(source="src", gate=70.0)
        assert result.ok is False
        assert result.details["coverage_pct"] == 50.0

    @patch("kata.verify._run")
    def test_coverage_no_total_line(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="no coverage data",
            stderr="",
        )
        result = run_coverage()
        assert result.ok is False
        assert result.details["coverage_pct"] == 0.0
        assert "TOTAL" in result.output

    @patch("kata.verify._run")
    def test_coverage_pct_with_branch_columns(self, mock_run: MagicMock) -> None:
        """Branch coverage acrescenta duas colunas antes do percentual. Com o
        número de colunas fixo no regex, o parse falhava calado e gravava 0.0
        junto de coverage_pass=True."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                    954      6    120     8    97%\n",
            stderr="",
        )
        assert run_coverage().details["coverage_pct"] == 97.0

    @patch("kata.verify._run")
    def test_coverage_pct_with_decimal_precision(self, mock_run: MagicMock) -> None:
        """`[tool.coverage.report] precision` acrescenta casas decimais."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                    954      6    99.37%\n",
            stderr="",
        )
        assert run_coverage().details["coverage_pct"] == 99.37

    @patch("kata.verify._run")
    def test_coverage_custom_gate(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="TOTAL                 100      20     80%",
            stderr="",
        )
        result = run_coverage(gate=85.0)
        assert result.ok is False
        assert result.details["gate"] == 85.0

    @patch("kata.verify._run")
    def test_coverage_with_ignore(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                 100       5     95%",
            stderr="",
        )
        result = run_coverage(ignore=["tests/slow/"])
        called_cmd = mock_run.call_args[0][0]
        assert "--ignore" in called_cmd
        assert "tests/slow/" in called_cmd
        assert result.ok is True

    @patch("kata.verify._run")
    def test_coverage_com_multiplas_sources_emite_uma_flag_por_source(
        self, mock_run: MagicMock
    ) -> None:
        """R12-02: lista de sources vira um --cov por entrada — o gate mede o
        projeto inteiro que o pyproject declarou, não só a primeira."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                2172     120    98%",
            stderr="",
        )
        result = run_coverage(source=["src/kata", "scripts/build_skills.py", "eval/run_traps.py"])
        called_cmd = mock_run.call_args[0][0]
        assert [a for a in called_cmd if a.startswith("--cov=")] == [
            "--cov=src/kata",
            "--cov=scripts/build_skills.py",
            "--cov=eval/run_traps.py",
        ]
        assert result.ok is True

    @patch("kata.verify._run")
    def test_coverage_with_cwd(self, mock_run: MagicMock) -> None:
        from pathlib import Path

        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                 100       5     95%",
            stderr="",
        )
        cwd = Path("/tmp/project")
        result = run_coverage(cwd=cwd)
        assert result.ok is True
        # Verifica que _run foi chamado com cwd
        mock_run.assert_called_once()
        # O segundo disjunto (`call_args[0][0] is not None`) era sempre True —
        # o mock de _run recebe sempre a lista de comando — e o teste passava
        # mesmo se run_coverage esquecesse de repassar cwd (R10-28).
        assert mock_run.call_args.kwargs.get("cwd") == cwd

    @patch("kata.verify._run")
    def test_coverage_pytest_fails(self, mock_run: MagicMock) -> None:
        """Cobertura falha mesmo com cobertura alta se pytest falhar."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="TOTAL                 100       5     95%\n2 failed",
            stderr="",
        )
        result = run_coverage(gate=70.0)
        assert result.ok is False


class TestRunAll:
    """Testa a função run_all que combina todas as verificações."""

    @patch("kata.verify._run")
    def test_run_all_all_pass(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                 100       5     95%",
            stderr="",
        )
        results = run_all()
        assert results["ruff"].ok is True
        assert results["pytest"].ok is True
        assert results["coverage"].ok is True
        assert results["coverage"].details["coverage_pct"] == 95.0

    @patch("kata.verify._run")
    def test_run_all_returns_three_keys(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        results = run_all()
        assert set(results.keys()) == {"ruff", "pytest", "coverage"}

    @patch("kata.verify._run")
    def test_default_cov_source_is_generic(self, mock_run: MagicMock) -> None:
        """kata.verify é genérico: o default de coverage não pode supor o
        nome do pacote de projeto nenhum — nem o do próprio kata. Quem
        conhece o projeto é cli._detect_cov_source()."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        run_all()
        cov_cmd = mock_run.call_args_list[-1][0][0]
        assert "--cov=src" in cov_cmd
        assert "--cov=kata" not in cov_cmd

    @patch("kata.verify._run")
    def test_run_all_pytest_fails_coverage_skipped(self, mock_run: MagicMock) -> None:
        """Quando pytest falha, coverage é pulado e retorna ok=False."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="ruff error", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=1, stdout="2 failed", stderr=""),
        ]
        results = run_all()
        assert results["ruff"].ok is False
        assert results["pytest"].ok is False
        assert results["coverage"].ok is False
        assert "(skipped" in results["coverage"].output
        assert results["coverage"].details["coverage_pct"] == 0.0


class TestSearchPattern:
    """Testa search_pattern — busca de padrão no projeto."""

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_padrao_com_dash_e_passado_apos_separador(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """M3: `--force`/`-1` são padrões legítimos no TWIN CHECK.

        Sem `--` antes do padrão, o rg lê o padrão como opção e falha com
        "unrecognized flag", deixando a fase inutilizável para esse caso.
        """
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        search_pattern("--force")

        chamado = mock_run.call_args[0][0]
        assert "--" in chamado
        assert chamado[chamado.index("--") + 1] == "--force"

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value=None)
    def test_grep_tambem_recebe_o_separador(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=""
        )

        search_pattern("-1")

        chamado = mock_run.call_args[0][0]
        assert chamado[0] == "grep"
        assert chamado[chamado.index("--") + 1] == "-1"

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_with_rg_finds_matches(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="src/main.py:42:def add(a, b):\nsrc/utils.py:10:def add(x, y):\n",
            stderr="",
        )
        result = search_pattern("def add")
        assert len(result.matches) == 2
        assert result.total_files == 2
        assert result.pattern == "def add"
        assert result.matches[0].file == "src/main.py"
        assert result.matches[0].line == 42
        assert result.matches[0].content == "def add(a, b):"
        assert result.matches[1].file == "src/utils.py"
        assert result.matches[1].line == 10
        called = mock_run.call_args[0][0]
        assert called[0] == "rg"

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value=None)
    def test_search_with_grep_fallback(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="src/main.py:42:def add(a, b):\n",
            stderr="",
        )
        result = search_pattern("def add")
        assert len(result.matches) == 1
        called = mock_run.call_args[0][0]
        assert called[0] == "grep"

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_rg_exclui_o_mesmo_que_o_grep(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """R10-4: as exclusões de rg e grep têm de ser as MESMAS — antes, rg
        varria node_modules/.venv que o grep pulava, e o twin check mudava de
        resultado conforme o binário disponível."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        search_pattern("def add")
        rg_cmd = mock_run.call_args[0][0]

        mock_run.reset_mock()
        with patch("kata.verify.shutil.which", return_value=None):
            search_pattern("def add")
        grep_cmd = mock_run.call_args[0][0]

        rg_excluidos = {
            rg_cmd[i + 1].removeprefix("!") for i, arg in enumerate(rg_cmd) if arg == "--glob"
        }
        grep_excluidos = {
            a.removeprefix("--exclude-dir=") for a in grep_cmd if a.startswith("--exclude-dir=")
        }
        # O conjunto de exclusões tem de ser idêntico nos dois binários
        # (R10-4) — só a sintaxe muda.
        assert rg_excluidos == grep_excluidos

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_no_matches(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        result = search_pattern("nonexistent_pattern_xyz")
        assert len(result.matches) == 0
        assert result.total_files == 0

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_with_custom_paths(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="src/app.py:5:DEBUG = True\n",
            stderr="",
        )
        result = search_pattern("DEBUG", paths=["src/"])
        assert len(result.matches) == 1
        called = mock_run.call_args[0][0]
        assert "src/" in called

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_empty_lines_skipped(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="src/main.py:42:def foo():\n\n\nsrc/utils.py:10:def bar():\n",
            stderr="",
        )
        result = search_pattern("def")
        assert len(result.matches) == 2

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_non_numeric_line_sets_zero(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="src/main.py:abc:content here\n",
            stderr="",
        )
        result = search_pattern("content")
        assert len(result.matches) == 1
        assert result.matches[0].line == 0

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_malformed_line_handled(
        self,
        mock_which: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=":no-colons-here\n",
            stderr="",
        )
        result = search_pattern("foo")
        assert len(result.matches) == 0
        assert result.total_files == 0

    def test_search_match_defaults(self) -> None:
        from kata.verify import SearchMatch

        m = SearchMatch(file="f.py", line=1, content="x")
        assert m.file == "f.py"
        assert m.line == 1
        assert m.content == "x"

    def test_search_result_defaults(self) -> None:
        from kata.verify import SearchResult

        r = SearchResult(pattern="test")
        assert r.pattern == "test"
        assert r.matches == []
        assert r.total_files == 0
        assert r.error == ""

    @patch("kata.verify._run")
    def test_busca_invalida_expoe_erro(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=2, stdout="", stderr="regex inválida"
        )
        result = search_pattern("[")
        assert result.error == "regex inválida"


class TestIsInspectable:
    """Teto único de leitura, compartilhado por fit e judge."""

    def test_small_file(self, tmp_path) -> None:
        f = tmp_path / "a.py"
        f.write_text("x = 1\n", encoding="utf-8")
        assert is_inspectable(f) is True

    def test_oversized_file(self, tmp_path) -> None:
        f = tmp_path / "grande.csv"
        f.write_text("x,y\n" * 200_000, encoding="utf-8")
        assert f.stat().st_size > MAX_UNTRACKED_FILE_BYTES
        assert is_inspectable(f) is False

    def test_missing_path(self, tmp_path) -> None:
        assert is_inspectable(tmp_path / "nao-existe.py") is False

    def test_directory(self, tmp_path) -> None:
        assert is_inspectable(tmp_path) is False

    def test_stat_error_is_not_inspectable(self, tmp_path, monkeypatch) -> None:
        """stat() falhando (permissão, race) não pode derrubar quem chama."""
        f = tmp_path / "a.py"
        f.write_text("x = 1\n", encoding="utf-8")

        def explode(self, *args, **kwargs):
            raise OSError("permissão negada")

        monkeypatch.setattr(Path, "stat", explode)
        assert is_inspectable(f) is False


class TestUntrackedFiles:
    """Fonte única de "arquivos que o git não rastreia", usada por fit, judge e
    cli. Antes cada um tinha sua própria cópia do comando."""

    def test_lists_only_untracked(self, repo_git, tmp_path) -> None:
        (repo_git / "base.txt").write_text("base modificado\n", encoding="utf-8")  # rastreado
        (repo_git / "novo.py").write_text("y = 1\n", encoding="utf-8")

        assert untracked_files(cwd=repo_git) == ["novo.py"]

    def test_empty_when_nothing_new(self, repo_git, tmp_path) -> None:
        assert untracked_files(cwd=tmp_path) == []

    def test_respects_gitignore(self, repo_git, tmp_path) -> None:
        """--exclude-standard: o que o projeto ignora não é "arquivo novo"."""
        (tmp_path / ".gitignore").write_text("ignorado/\n", encoding="utf-8")
        (tmp_path / "ignorado").mkdir()
        (tmp_path / "ignorado" / "x.py").write_text("z = 1\n", encoding="utf-8")

        assert untracked_files(cwd=tmp_path) == [".gitignore"]


class TestConsistencyFailures:
    """Uma tarefa ``approved`` precisa de critério declarado e satisfeito."""

    def test_approved_consistente(self) -> None:
        data = {
            "status": "approved",
            "done": "teste passa",
            "verify": {
                "success_criteria_met": True,
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
            },
        }
        assert consistency_failures(data) == []

    def test_sucesso_falso(self) -> None:
        data = {
            "status": "approved",
            "done": "teste passa",
            "verify": {"success_criteria_met": False},
        }
        assert "critério de sucesso não satisfeito" in consistency_failures(data)

    def test_done_vazio(self) -> None:
        data = {
            "status": "approved",
            "done": "   ",
            "verify": {"success_criteria_met": True},
        }
        assert "critério de sucesso não declarado (done vazio)" in consistency_failures(data)

    def test_check_explicito_falso(self) -> None:
        data = {
            "status": "approved",
            "done": "x",
            "verify": {"success_criteria_met": True, "ruff_clean": False},
        }
        assert "lint falhou" in consistency_failures(data)

    def test_status_diferente_de_approved_nao_e_avaliado(self) -> None:
        data = {"status": "rejected", "done": "", "verify": {"success_criteria_met": False}}
        assert consistency_failures(data) == []

    def test_typecheck_falho_torna_a_tarefa_inconsistente(self) -> None:
        """Um typecheck reprovado junto de `status: approved` é a mesma
        contradição que lint/testes/coverage reprovados: o arquivo afirma
        aprovado sobre uma verificação que falhou."""
        data = {
            "status": "approved",
            "done": "x",
            "verify": {"success_criteria_met": True, "typecheck_clean": False},
        }
        assert "typecheck falhou" in consistency_failures(data)

    def test_verify_nao_mapa_nao_crasha(self) -> None:
        data = {"status": "approved", "done": "x", "verify": True}
        assert "critério de sucesso não registrado" in consistency_failures(data)


class TestChangedFiles:
    """A janela de arquivos alterados — uma só para SURGICAL e JUDGE (B5).

    Antes havia duas implementações: o CLI olhava a árvore de trabalho e o
    judge `base..approved_commit`. Uma tarefa retomada depois do commit era
    declarada numa janela e auditada em outra.
    """

    def test_usa_base_commit_quando_resolve(self, repo_git) -> None:
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_git, capture_output=True, text=True
        ).stdout.strip()
        (repo_git / "novo.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "novo.py"], cwd=repo_git, check=True)
        subprocess.run(
            ["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "add"],
            cwd=repo_git,
            check=True,
        )

        assert changed_files(cwd=repo_git, base_commit=base) == ["novo.py"]

    def test_janela_fecha_no_diff_end(self, repo_git) -> None:
        """`base..approved_commit`: o que veio depois não é trabalho desta tarefa."""
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_git, capture_output=True, text=True
        ).stdout.strip()
        (repo_git / "um.py").write_text("a = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "um.py"], cwd=repo_git, check=True)
        subprocess.run(
            ["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "um"],
            cwd=repo_git,
            check=True,
        )
        aprovado = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_git, capture_output=True, text=True
        ).stdout.strip()
        (repo_git / "dois.py").write_text("b = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "dois.py"], cwd=repo_git, check=True)
        subprocess.run(
            ["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "dois"],
            cwd=repo_git,
            check=True,
        )

        assert changed_files(cwd=repo_git, base_commit=base, diff_end=aprovado) == ["um.py"]

    def test_escrituracao_do_kata_sai_da_lista(self, repo_git) -> None:
        (repo_git / ".kata").mkdir()
        (repo_git / ".kata" / "t.yaml").write_text("task: t\n", encoding="utf-8")
        (repo_git / "codigo.py").write_text("y = 2\n", encoding="utf-8")

        assert changed_files(cwd=repo_git) == ["codigo.py"]

    def test_artefatos_de_ferramenta_saem_da_lista(self, repo_git) -> None:
        (repo_git / ".coverage").write_text("dados\n", encoding="utf-8")
        (repo_git / "real.py").write_text("z = 3\n", encoding="utf-8")

        assert changed_files(cwd=repo_git) == ["real.py"]


class TestRunCommand:
    """Comando declarado pelo projeto: aprova pelo returncode e nada mais."""

    @patch("kata.verify._run")
    def test_returncode_zero_aprova(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        r = run_command(["go", "vet", "./..."])
        assert r.ok is True
        assert r.details["command"] == "go vet ./..."

    @patch("kata.verify._run")
    def test_returncode_nao_zero_reprova(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
        r = run_command(["npx", "eslint", "src"])
        assert r.ok is False
        assert "boom" in r.output

    @patch("kata.verify._run", side_effect=FileNotFoundError("no such file: golangci-lint"))
    def test_comando_inexistente_vira_falha_e_nao_excecao(self, mock_run: MagicMock) -> None:
        """Estourar aqui derrubaria a fase VERIFY inteira. O ciclo precisa
        poder reportar 'a verificação não rodou' como reprovação."""
        r = run_command(["golangci-lint", "run"])
        assert r.ok is False
        assert "não foi possível executar" in r.output


class TestRunCommandCoverage:
    """Coverage por comando: o gate é conferido aqui, não delegado ao pytest-cov."""

    @patch("kata.verify._run")
    def test_percentual_acima_do_gate(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="All files |   87.5 |", stderr="")
        r = run_command_coverage(
            ["npx", "vitest", "run", "--coverage"],
            pattern=r"All files\s+\|\s+([\d.]+)",
            gate=70.0,
        )
        assert r.ok is True
        assert r.details["coverage_pct"] == 87.5

    @patch("kata.verify._run")
    def test_percentual_abaixo_do_gate_reprova(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="All files |   41.0 |", stderr="")
        r = run_command_coverage(
            ["npm", "run", "cov"], pattern=r"All files\s+\|\s+([\d.]+)", gate=70.0
        )
        assert r.ok is False
        assert r.details["coverage_pct"] == 41.0

    @patch("kata.verify._run")
    def test_comando_falhou_reprova_mesmo_com_percentual_alto(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="All files |   99.0 |", stderr="")
        r = run_command_coverage(
            ["npm", "run", "cov"], pattern=r"All files\s+\|\s+([\d.]+)", gate=70.0
        )
        assert r.ok is False

    @patch("kata.verify._run")
    def test_padrao_que_nao_casa_reprova_em_vez_de_virar_zero_aprovado(
        self, mock_run: MagicMock
    ) -> None:
        """ "Não consegui medir" não é "mediu e passou" — a mesma doutrina do
        UNVERIFIABLE, aplicada ao percentual."""
        mock_run.return_value = MagicMock(returncode=0, stdout="nada aqui", stderr="")
        r = run_command_coverage(["npm", "run", "cov"], pattern=r"Cobertura: ([\d.]+)")
        assert r.ok is False
        assert r.details["coverage_pct"] == 0.0
        assert "nenhum percentual casou" in r.output

    @patch("kata.verify._run")
    def test_padrao_que_casa_nao_numerico_reprova_em_vez_de_crashar(
        self, mock_run: MagicMock
    ) -> None:
        """R9-1: o padrão CASA mas o grupo não é número — float() levantava
        ValueError e derrubava VERIFY/JUDGE com traceback. "N/A" tem de ser
        reprovação nomeada, não crash."""
        mock_run.return_value = MagicMock(returncode=0, stdout="coverage: N/A", stderr="")
        r = run_command_coverage(["npm", "run", "cov"], pattern=r"coverage:\s+([\w.]+)")
        assert r.ok is False
        assert r.details["coverage_pct"] == 0.0
        assert "não é um número" in r.output

    @patch("kata.verify._run")
    def test_padrao_invalido_reprova_em_vez_de_crashar(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="coverage: 90", stderr="")
        r = run_command_coverage(["npm", "run", "cov"], pattern="[")
        assert r.ok is False
        assert "padrão de coverage inválido" in r.output

    @patch("kata.verify._run")
    def test_padrao_sem_grupo_de_captura_reprova_em_vez_de_crashar(
        self, mock_run: MagicMock
    ) -> None:
        """R10-1: padrão VÁLIDO que casa sem grupo de captura — match.group(1)
        levantava IndexError e derrubava VERIFY/JUDGE com traceback. Sem grupo
        não há percentual a extrair: reprovação nomeada, não crash."""
        mock_run.return_value = MagicMock(returncode=0, stdout="All files | 87.5 |", stderr="")
        r = run_command_coverage(
            ["npx", "vitest", "run", "--coverage"],
            pattern=r"All files\s+\|\s+[\d.]+",
        )
        assert r.ok is False
        assert r.details["coverage_pct"] == 0.0
        assert "não tem grupo de captura" in r.output

    @patch("kata.verify._run")
    def test_padrao_default_le_a_linha_total(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="TOTAL    100    5    95%", stderr=""
        )
        r = run_command_coverage(["qualquer", "coisa"], gate=70.0)
        assert r.ok is True
        assert r.details["coverage_pct"] == 95.0


class TestRunAllComConfig:
    """Papel declarado é executado verbatim; papel omitido cai no default."""

    @patch("kata.verify._run")
    def test_config_vazia_mantem_o_comportamento_anterior(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="TOTAL 90%", stderr="")
        run_all(config=VerifyConfig())
        comandos = [" ".join(c.args[0]) for c in mock_run.call_args_list]
        assert any("ruff check" in c for c in comandos)
        assert any("pytest" in c for c in comandos)

    @patch("kata.verify._run")
    def test_papeis_declarados_substituem_os_defaults(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="All files |  90.0 |", stderr="")
        cfg = VerifyConfig(
            lint=["npx", "eslint", "src"],
            test=["npx", "vitest", "run"],
            coverage=["npx", "vitest", "run", "--coverage"],
            coverage_pattern=r"All files\s+\|\s+([\d.]+)",
        )
        results = run_all(config=cfg)

        comandos = [" ".join(c.args[0]) for c in mock_run.call_args_list]
        assert comandos == [
            "npx eslint src",
            "npx vitest run",
            "npx vitest run --coverage",
        ]
        assert all(r.ok for r in results.values())
        assert results["coverage"].details["coverage_pct"] == 90.0

    @patch("kata.verify._run")
    def test_papel_parcial_mistura_declarado_e_default(self, mock_run: MagicMock) -> None:
        """Um projeto Python que só troca o lint continua usando pytest."""
        mock_run.return_value = MagicMock(returncode=0, stdout="TOTAL 90%", stderr="")
        run_all(config=VerifyConfig(lint=["flake8", "src"]))
        comandos = [" ".join(c.args[0]) for c in mock_run.call_args_list]
        assert comandos[0] == "flake8 src"
        assert "pytest" in comandos[1]

    @patch("kata.verify._run")
    def test_typecheck_roda_entre_o_lint_e_o_teste(self, mock_run: MagicMock) -> None:
        """Ordem importa para o relatório: lint → typecheck → teste → coverage."""
        mock_run.return_value = MagicMock(returncode=0, stdout="All files |  90.0 |", stderr="")
        cfg = VerifyConfig(
            lint=["npx", "eslint", "src"],
            typecheck=["npx", "tsc", "--noEmit"],
            test=["npx", "vitest", "run"],
            coverage=["npx", "vitest", "run", "--coverage"],
            coverage_pattern=r"All files\s+\|\s+([\d.]+)",
        )
        results = run_all(config=cfg)

        comandos = [" ".join(c.args[0]) for c in mock_run.call_args_list]
        assert comandos == [
            "npx eslint src",
            "npx tsc --noEmit",
            "npx vitest run",
            "npx vitest run --coverage",
        ]
        assert results["typecheck"].ok is True

    @patch("kata.verify._run")
    def test_sem_typecheck_declarado_a_chave_nao_existe(self, mock_run: MagicMock) -> None:
        """Ausente é "não há gate de tipos" — não `True`, que seria afirmar
        uma verificação que ninguém pediu."""
        mock_run.return_value = MagicMock(returncode=0, stdout="TOTAL 90%", stderr="")
        results = run_all(config=VerifyConfig())
        assert "typecheck" not in results

    @patch("kata.verify._run")
    def test_typecheck_reprovado_nao_impede_o_resto(self, mock_run: MagicMock) -> None:
        """Só o coverage é curto-circuitado pelo teste; o typecheck reprovado
        aparece no resultado para o relatório poder reprovar o ciclo."""
        mock_run.return_value = MagicMock(returncode=0, stdout="TOTAL 90%", stderr="")
        cfg = VerifyConfig(
            typecheck=["npx", "tsc", "--noEmit"],
            lint=["true"],
            test=["true"],
            coverage=["true"],
            coverage_pattern=r"(\d+)%",
        )
        results = run_all(config=cfg)
        assert results["typecheck"].ok is True
        assert results["coverage"].ok is True

    @patch("kata.verify._run")
    def test_teste_declarado_que_falha_pula_o_coverage(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="falhou", stderr="")
        results = run_all(config=VerifyConfig(test=["npx", "vitest", "run"]))
        assert results["pytest"].ok is False
        assert results["coverage"].ok is False
        assert "skipped" in results["coverage"].output


class TestComandoDeclaradoDeVerdade:
    """A14: o caminho "comando declarado" executava zero subprocessos na suíte.

    Todos os testes de `run_command` mockam `kata.verify._run` — inclusive o
    caso de `FileNotFoundError`. Um mock no wrapper esconde exatamente a
    classe de defeito que o caminho existe para cobrir: comando que não existe,
    que sai diferente de zero, ou que devolve saída. Estes três rodam de
    verdade, com `python -c`, para não depender de ferramenta instalada.

    Todas as roles são declaradas de propósito: com uma só, o `run_all` cai no
    pytest real e roda a suíte inteira dentro da suíte.
    """

    @staticmethod
    def _cfg(**kwargs) -> VerifyConfig:
        return VerifyConfig(
            coverage_pattern=r"TOTAL\s+\d+\s+\d+\s+(\d+)%",
            gate=70.0,
            **kwargs,
        )

    def test_papeis_declarados_executam_e_aprovam(self, tmp_path) -> None:
        cfg = self._cfg(
            lint=[sys.executable, "-c", "print('lint ok')"],
            test=[sys.executable, "-c", "print('test ok')"],
            coverage=[sys.executable, "-c", "print('TOTAL 10 1 90%')"],
        )
        results = run_all(config=cfg, cwd=tmp_path)

        assert results["ruff"].ok is True
        assert "lint ok" in results["ruff"].output
        assert results["pytest"].ok is True
        assert "test ok" in results["pytest"].output
        assert results["coverage"].details["coverage_pct"] == 90.0

    def test_returncode_diferente_de_zero_reprova(self, tmp_path) -> None:
        cfg = self._cfg(
            lint=[sys.executable, "-c", "import sys; sys.exit(3)"],
            test=[sys.executable, "-c", "print('ok')"],
            coverage=[sys.executable, "-c", "print('TOTAL 10 1 90%')"],
        )
        results = run_all(config=cfg, cwd=tmp_path)

        assert results["ruff"].ok is False

    def test_comando_inexistente_reprova_sem_excecao(self, tmp_path) -> None:
        cfg = self._cfg(
            lint=["comando-que-nao-existe-kata-xyz"],
            test=[sys.executable, "-c", "print('ok')"],
            coverage=[sys.executable, "-c", "print('TOTAL 10 1 90%')"],
        )
        results = run_all(config=cfg, cwd=tmp_path)

        assert results["ruff"].ok is False
        assert "não foi possível executar" in results["ruff"].output


def test_comando_gravado_nao_tem_caminho_absoluto() -> None:
    """A9: `sys.executable` no YAML não é portável e não diz o papel.

    `verify.commands.lint` gravava `/usr/bin/python3 -m ruff check ...` — o
    mesmo comando em outra máquina (ou venv) saía diferente sem que nada
    tivesse mudado no projeto.
    """
    with patch("kata.verify._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        comando = run_ruff(paths=["src"]).details["command"]

    assert comando.startswith("python -m ruff check")
    assert sys.executable not in comando


def test_tabelas_de_rotulo_cobrem_os_mesmos_papeis() -> None:
    """A20: gravação e exibição saem da mesma tabela, com uma exceção só.

    O mapa que gravava `verify.commands` vivia inline no `cli` e discordava de
    `ROLE_LABELS` em `pytest` (`test` gravado, `teste` exibido). O teste trava
    a divergência em exatamente um papel: uma segunda exceção reprova.
    """
    assert set(COMMAND_LABELS) == set(ROLE_LABELS)
    divergentes = {
        papel for papel, rotulo in ROLE_LABELS.items() if COMMAND_LABELS[papel] != rotulo
    }
    assert divergentes == {"pytest"}
    assert COMMAND_LABELS["pytest"] == "test"
