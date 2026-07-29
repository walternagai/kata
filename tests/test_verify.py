"""Testes para kata.verify — lógica de verificação (ruff, pytest, coverage)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from kata.verify import (
    VerifyResult,
    run_all,
    run_coverage,
    run_pytest,
    run_ruff,
    search_pattern,
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
            ["echo", "hello"], capture_output=True, text=True, cwd=None
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
            ["ls"], capture_output=True, text=True, cwd=cwd
        )


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

    @patch("kata.verify._run")
    def test_coverage_pct_with_branch_columns(self, mock_run: MagicMock) -> None:
        """Branch coverage acrescenta duas colunas antes do percentual. Com o
        número de colunas fixo no regex, o parse falhava calado e gravava 0.0
        junto de coverage_pass=True."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="TOTAL                    954      6    120     8    97%\n", stderr="",
        )
        assert run_coverage().details["coverage_pct"] == 97.0

    @patch("kata.verify._run")
    def test_coverage_pct_with_decimal_precision(self, mock_run: MagicMock) -> None:
        """`[tool.coverage.report] precision` acrescenta casas decimais."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="TOTAL                    954      6    99.37%\n", stderr="",
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
        assert mock_run.call_args[1].get("cwd") == cwd or mock_run.call_args[0][0] is not None

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
    def test_search_with_rg_finds_matches(
        self, mock_which: MagicMock, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
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
        self, mock_which: MagicMock, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="src/main.py:42:def add(a, b):\n",
            stderr="",
        )
        result = search_pattern("def add")
        assert len(result.matches) == 1
        called = mock_run.call_args[0][0]
        assert called[0] == "grep"

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_no_matches(
        self, mock_which: MagicMock, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        result = search_pattern("nonexistent_pattern_xyz")
        assert len(result.matches) == 0
        assert result.total_files == 0

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_with_custom_paths(
        self, mock_which: MagicMock, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
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
        self, mock_which: MagicMock, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="src/main.py:42:def foo():\n\n\nsrc/utils.py:10:def bar():\n",
            stderr="",
        )
        result = search_pattern("def")
        assert len(result.matches) == 2

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_non_numeric_line_sets_zero(
        self, mock_which: MagicMock, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="src/main.py:abc:content here\n",
            stderr="",
        )
        result = search_pattern("content")
        assert len(result.matches) == 1
        assert result.matches[0].line == 0

    @patch("kata.verify._run")
    @patch("kata.verify.shutil.which", return_value="/usr/bin/rg")
    def test_search_malformed_line_handled(
        self, mock_which: MagicMock, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
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
