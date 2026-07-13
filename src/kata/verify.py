"""Lógica de verificação — ruff, pytest, coverage.

Modularizada para que possa ser testada independentemente e reutilizada
tanto pelo CLI quanto por outros ferramentais.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VerifyResult:
    """Resultado de uma verificação individual (ruff, pytest, ou coverage)."""

    ok: bool
    output: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Executa um comando e captura saída."""
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def run_ruff(
    paths: list[str] | None = None,
    cwd: Path | None = None,
) -> VerifyResult:
    """Executa `ruff check` nos caminhos especificados.

    Args:
        paths: Lista de diretórios/arquivos para checar. Default: ["src/", "tests/"].
        cwd: Diretório de execução. Default: CWD atual.

    Returns:
        VerifyResult com ok=True se ruff não encontrar erros.
    """
    if paths is None:
        paths = ["src/", "tests/"]
    cmd = ["python3", "-m", "ruff", "check", *paths]
    result = _run(cmd, cwd=cwd)
    return VerifyResult(
        ok=result.returncode == 0,
        output=result.stdout + result.stderr,
        details={"command": " ".join(cmd)},
    )


def run_pytest(
    testpaths: list[str] | None = None,
    ignore: list[str] | None = None,
    cwd: Path | None = None,
    extra_args: list[str] | None = None,
) -> VerifyResult:
    """Executa pytest nos caminhos especificados.

    Args:
        testpaths: Diretórios de teste. Default: ["tests/"].
        ignore: Caminhos para ignorar (--ignore).
        cwd: Diretório de execução.
        extra_args: Argumentos extras para o pytest.

    Returns:
        VerifyResult com ok=True se todos os testes passam.
    """
    if testpaths is None:
        testpaths = ["tests/"]
    cmd = ["python3", "-m", "pytest", *testpaths, "--tb=short", "-q"]
    if ignore:
        for path in ignore:
            cmd.extend(["--ignore", path])
    if extra_args:
        cmd.extend(extra_args)
    result = _run(cmd, cwd=cwd)
    return VerifyResult(
        ok=result.returncode == 0,
        output=result.stdout + result.stderr,
        details={"command": " ".join(cmd)},
    )


def run_coverage(
    source: str = "src",
    testpaths: list[str] | None = None,
    ignore: list[str] | None = None,
    gate: float = 70.0,
    cwd: Path | None = None,
) -> VerifyResult:
    """Executa pytest com coverage e verifica o gate.

    Args:
        source: Pacote fonte para medir coverage (--cov=<source>).
        testpaths: Diretórios de teste. Default: ["tests/"].
        ignore: Caminhos para ignorar.
        gate: Percentual mínimo de coverage (default: 70.0).
        cwd: Diretório de execução.

    Returns:
        VerifyResult com ok=True se coverage >= gate e testes passam.
        details inclui `coverage_pct` e `gate`.
    """
    if testpaths is None:
        testpaths = ["tests/"]
    cmd = [
        "python3",
        "-m",
        "pytest",
        *testpaths,
        f"--cov={source}",
        "--cov-report=term-missing",
        "-q",
    ]
    if ignore:
        for path in ignore:
            cmd.extend(["--ignore", path])
    result = _run(cmd, cwd=cwd)

    # Extrai percentual de coverage do output
    cov_pct = 0.0
    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", result.stdout)
    if match:
        cov_pct = float(match.group(1))

    passed = result.returncode == 0 and cov_pct >= gate
    return VerifyResult(
        ok=passed,
        output=result.stdout + result.stderr,
        details={
            "coverage_pct": cov_pct,
            "gate": gate,
            "command": " ".join(cmd),
        },
    )


def run_all(
    ruff_paths: list[str] | None = None,
    test_paths: list[str] | None = None,
    ignore: list[str] | None = None,
    cov_source: str = "src",
    gate: float = 70.0,
    cwd: Path | None = None,
) -> dict[str, VerifyResult]:
    """Executa todas as verificações: ruff → pytest → coverage.

    Returns:
        Dicionário com chaves "ruff", "pytest", "coverage" e seus resultados.
    """
    return {
        "ruff": run_ruff(paths=ruff_paths, cwd=cwd),
        "pytest": run_pytest(testpaths=test_paths, ignore=ignore, cwd=cwd),
        "coverage": run_coverage(
            source=cov_source,
            testpaths=test_paths,
            ignore=ignore,
            gate=gate,
            cwd=cwd,
        ),
    }
