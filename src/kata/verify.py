"""Lógica de verificação — ruff, pytest, coverage, twin search.

Modularizada para que possa ser testada independentemente e reutilizada
tanto pelo CLI quanto por outros ferramentais.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
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
    cmd = [sys.executable, "-m", "ruff", "check", *paths]
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
    cmd = [sys.executable, "-m", "pytest", *testpaths, "--tb=short", "-q"]
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
    """Executa pytest com coverage e verifica o gate via --cov-fail-under.

    Args:
        source: Pacote fonte para medir coverage (--cov=<source>).
        testpaths: Diretórios de teste. Default: ["tests/"].
        ignore: Caminhos para ignorar.
        gate: Percentual mínimo de coverage (default: 70.0).
        cwd: Diretório de execução.

    Returns:
        VerifyResult com ok=True se testes passam e coverage >= gate
        (--cov-fail-under garante o gate). details inclui `coverage_pct` e `gate`.
    """
    if testpaths is None:
        testpaths = ["tests/"]
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *testpaths,
        f"--cov={source}",
        "--cov-report=term-missing",
        f"--cov-fail-under={gate}",
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

    passed = result.returncode == 0
    return VerifyResult(
        ok=passed,
        output=result.stdout + result.stderr,
        details={
            "coverage_pct": cov_pct,
            "gate": gate,
            "command": " ".join(cmd),
        },
    )


@dataclass
class SearchMatch:
    """A single match found by pattern search."""

    file: str
    line: int
    content: str


@dataclass
class SearchResult:
    """Result of a twin pattern search across the project."""

    pattern: str
    matches: list[SearchMatch] = field(default_factory=list)
    total_files: int = 0


def search_pattern(
    pattern: str,
    paths: list[str] | None = None,
    cwd: Path | None = None,
) -> SearchResult:
    """Search for a regex pattern across project files (twin check).

    Uses `rg` (ripgrep) if available, falls back to `grep -rnI`.
    Skips binary files, .git, and common cache/virtualenv dirs.

    Args:
        pattern: Regex pattern to search for.
        paths: Directories to search in. Default: ["."].
        cwd: Working directory.

    Returns:
        SearchResult with all matches found.
    """
    if paths is None:
        paths = ["."]
    if shutil.which("rg"):
        cmd = [
            "rg", "-n", "--no-heading", "--color", "never",
            "--glob", "!.git", "--glob", "!__pycache__",
            pattern, *paths,
        ]
    else:
        cmd = [
            "grep", "-rnI", "--color=never",
            "--exclude-dir=.git", "--exclude-dir=__pycache__",
            "--exclude-dir=.pytest_cache", "--exclude-dir=.ruff_cache",
            "--exclude-dir=.venv", "--exclude-dir=venv",
            "--exclude-dir=node_modules",
            pattern, *paths,
        ]
    result = _run(cmd, cwd=cwd)
    matches: list[SearchMatch] = []
    seen_files: set[str] = set()
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(":", 2)
        if len(parts) >= 2 and parts[0]:
            fpath = parts[0]
            seen_files.add(fpath)
            try:
                lineno = int(parts[1])
            except ValueError:
                lineno = 0
            content = parts[2] if len(parts) > 2 else ""
            matches.append(SearchMatch(file=fpath, line=lineno, content=content.strip()))

    return SearchResult(pattern=pattern, matches=matches, total_files=len(seen_files))


def run_all(
    ruff_paths: list[str] | None = None,
    test_paths: list[str] | None = None,
    ignore: list[str] | None = None,
    cov_source: str = "src",
    gate: float = 70.0,
    cwd: Path | None = None,
) -> dict[str, VerifyResult]:
    """Executa todas as verificações: ruff → pytest → coverage.

    Otimização: coverage só roda se pytest passar (short-circuit).

    `cov_source` default é "src" — este módulo é genérico e não deve supor
    o nome do pacote de nenhum projeto, inclusive o próprio kata. Quem
    conhece o projeto é o CLI, via cli._detect_cov_source().

    Returns:
        Dicionário com chaves "ruff", "pytest", "coverage" e seus resultados.
    """
    results: dict[str, VerifyResult] = {}

    results["ruff"] = run_ruff(paths=ruff_paths, cwd=cwd)

    results["pytest"] = run_pytest(testpaths=test_paths, ignore=ignore, cwd=cwd)

    if results["pytest"].ok:
        results["coverage"] = run_coverage(
            source=cov_source,
            testpaths=test_paths,
            ignore=ignore,
            gate=gate,
            cwd=cwd,
        )
    else:
        results["coverage"] = VerifyResult(
            ok=False,
            output="(skipped — tests failed)",
            details={"coverage_pct": 0.0, "gate": gate},
        )

    return results
