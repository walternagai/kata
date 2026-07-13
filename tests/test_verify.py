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
            returncode=0,
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
            returncode=0,
            stdout="no coverage data",
            stderr="",
        )
        result = run_coverage()
        assert result.ok is False
        assert result.details["coverage_pct"] == 0.0

    @patch("kata.verify._run")
    def test_coverage_custom_gate(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="TOTAL                 100      20     80%",
            stderr="",
        )
        result = run_coverage(gate=85.0)
        assert result.ok is False
        assert result.details["gate"] == 85.0


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
