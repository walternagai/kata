"""Lógica de verificação — ruff, pytest, coverage, twin search.

Modularizada para que possa ser testada independentemente e reutilizada
tanto pelo CLI quanto por outros ferramentais.

Abriga também as consultas ao git que fit, judge e cli compartilham
(`untracked_files`, `is_inspectable`), porque é onde já vive o wrapper de
subprocess que os três importam. Cada uma dessas chegou aqui depois de existir
em duas ou três cópias.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kata.config import DEFAULT_COVERAGE_PATTERN, VerifyConfig


@dataclass
class VerifyResult:
    """Resultado de uma verificação individual (ruff, pytest, ou coverage)."""

    ok: bool
    output: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Executa um comando e captura saída."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return subprocess.CompletedProcess(
            cmd,
            124,
            stdout=stdout,
            stderr=f"{stderr}\n(kata: comando excedeu {COMMAND_TIMEOUT_SECONDS}s)",
        )


# Teto único para leitura de arquivo untracked. Acima disto, `kata.judge` não
# consegue inspecionar o conteúdo e `kata.fit` não consegue contar as linhas
# baratinho. Ordens de grandeza acima de qualquer arquivo de código, ordens de
# grandeza abaixo de um dataset ou log.
MAX_UNTRACKED_FILE_BYTES = 256 * 1024
COMMAND_TIMEOUT_SECONDS = 300


def is_inspectable(path: Path) -> bool:
    """Arquivo pequeno o bastante para ser lido inteiro.

    Compartilhado por fit e judge para que o limite seja um número só. A
    consequência de estourá-lo é que cada um decide: o judge pula o arquivo e
    declara em caveat; o fit o trata como grande demais para ser trivial —
    pular ali reintroduziria a cegueira que o triviality gate acabou de
    fechar, porque "0 linha contada" viraria "mudança trivial".
    """
    try:
        return path.is_file() and path.stat().st_size <= MAX_UNTRACKED_FILE_BYTES
    except OSError:
        return False


def untracked_files(cwd: Path | None = None) -> list[str]:
    """Arquivos que o git ainda não rastreia.

    Fonte única: `kata.fit` (triviality gate), `kata.judge` (caça a fraude) e
    `kata.cli` (SIMPLIFY, SURGICAL, detrito) todos precisam desta lista, e
    cada um tinha sua própria cópia do comando. Mora aqui porque este módulo
    já é onde vive o wrapper de subprocess que fit e judge importam.

    `git diff` — unstaged, staged, contra commit, qualquer forma — é cego a
    arquivos que nunca entraram no índice, então esta consulta é a única
    maneira de enxergá-los.
    """
    result = _run(["git", "ls-files", "--others", "--exclude-standard"], cwd=cwd)
    return [f for f in result.stdout.strip().split("\n") if f.strip()]


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
    source: str | list[str] = "src",
    testpaths: list[str] | None = None,
    ignore: list[str] | None = None,
    gate: float = 70.0,
    cwd: Path | None = None,
) -> VerifyResult:
    """Executa pytest com coverage e verifica o gate via --cov-fail-under.

    Args:
        source: Pacote fonte para medir coverage (--cov=<source>). Uma lista
            vira um --cov por entrada — o pytest-cov soma todas as fontes na
            linha TOTAL, então o gate mede o projeto inteiro que o
            pyproject.toml declarou, não só a primeira (R12-02).
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
    sources = [source] if isinstance(source, str) else source
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *testpaths,
    ]
    for src in sources:
        cmd.extend([f"--cov={src}"])
    cmd.extend(["--cov-report=term-missing", f"--cov-fail-under={gate}", "-q"])
    if ignore:
        for path in ignore:
            cmd.extend(["--ignore", path])
    result = _run(cmd, cwd=cwd)

    # Extrai percentual de coverage da linha TOTAL. O percentual é sempre a
    # última coluna, mas quantas colunas o antecedem varia: branch coverage
    # acrescenta duas, e `precision` acrescenta casas decimais. Fixar o
    # número de colunas fazia o regex falhar calado e gravar 0.0 junto de
    # coverage_pass=True — um YAML internamente contraditório que o JUDGE
    # depois lê como verdade.
    match = re.search(r"^TOTAL\s+.*?(\d+(?:\.\d+)?)%", result.stdout, re.MULTILINE)
    if match is None:
        return VerifyResult(
            ok=False,
            output=result.stdout + result.stderr + "\n(kata: linha TOTAL de coverage ausente)",
            details={"coverage_pct": 0.0, "gate": gate, "command": " ".join(cmd)},
        )
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


def run_command(cmd: list[str], cwd: Path | None = None) -> VerifyResult:
    """Executa um comando de verificação declarado pelo projeto alvo.

    Aprova pelo returncode, que é o único contrato que toda ferramenta de
    lint e de teste respeita — de `ruff` a `go vet`, de `pytest` a `cargo
    test`. Comando inexistente vira falha com a mensagem do SO, e não
    exceção: no VERIFY isso tem de aparecer como verificação reprovada,
    para o ciclo poder reportá-lo; estourar aqui derrubaria a fase inteira.
    """
    try:
        result = _run(cmd, cwd=cwd)
    except OSError as exc:
        return VerifyResult(
            ok=False,
            output=f"não foi possível executar {' '.join(cmd)}: {exc}",
            details={"command": " ".join(cmd)},
        )
    return VerifyResult(
        ok=result.returncode == 0,
        output=result.stdout + result.stderr,
        details={"command": " ".join(cmd)},
    )


def run_command_coverage(
    cmd: list[str],
    pattern: str = DEFAULT_COVERAGE_PATTERN,
    gate: float = 70.0,
    cwd: Path | None = None,
) -> VerifyResult:
    """Coverage por comando declarado, com o gate conferido aqui.

    Difere de `run_coverage` num ponto que importa: lá o gate é delegado ao
    `--cov-fail-under` do pytest-cov, que não existe fora do Python. Aqui o
    percentual é extraído por `pattern` e comparado explicitamente — se o
    padrão não casar, o resultado é reprovado em vez de virar 0.0% aprovado,
    porque "não consegui medir" não é "mediu e passou".
    """
    result = run_command(cmd, cwd=cwd)
    try:
        match = re.search(pattern, result.output, re.MULTILINE)
    except re.error as exc:
        return VerifyResult(
            ok=False,
            output=result.output + f"\n(kata: padrão de coverage inválido: {exc})",
            details={"coverage_pct": 0.0, "gate": gate, "command": " ".join(cmd)},
        )
    if match is None:
        return VerifyResult(
            ok=False,
            output=result.output + f"\n(kata: nenhum percentual casou com o padrão {pattern!r})",
            details={"coverage_pct": 0.0, "gate": gate, "command": " ".join(cmd)},
        )

    try:
        cov_pct = float(match.group(1))
    except IndexError:
        # O padrão CASOU mas não tem grupo de captura (ex.: "coverage:\s+\d+%"):
        # não há percentual a extrair, e não é possível medir. Reprovar nomeado
        # em vez de estourar VERIFY e JUDGE com traceback (R10-1).
        return VerifyResult(
            ok=False,
            output=result.output
            + f"\n(kata: o padrão {pattern!r} não tem grupo de captura para o percentual)",
            details={"coverage_pct": 0.0, "gate": gate, "command": " ".join(cmd)},
        )
    except ValueError:
        # O padrão CASOU mas o grupo não é número (ex.: "N/A"). Não conseguiu
        # medir não é reprovação silenciosa nem 0.0 aprovado: é o mesmo
        # contrato do padrão que não casa, e estourar aqui derrubaria VERIFY
        # e JUDGE com traceback em vez de reprovar a checagem.
        return VerifyResult(
            ok=False,
            output=result.output
            + f"\n(kata: o percentual casado {match.group(1)!r} não é um número)",
            details={"coverage_pct": 0.0, "gate": gate, "command": " ".join(cmd)},
        )

    return VerifyResult(
        ok=result.ok and cov_pct >= gate,
        output=result.output,
        details={"coverage_pct": cov_pct, "gate": gate, "command": " ".join(cmd)},
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
    error: str = ""


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
    # As exclusões têm de ser as MESMAS com rg e com grep (R10-4): o twin
    # check compara recorrências, e a árvore varrida muda conforme o binário
    # disponível. Antes, rg só excluía .git/__pycache__ e varria node_modules
    # e .venv que o grep pulava — falso positivo de recorrência e, com o
    # timeout de _run, busca interrompida em repo grande.
    if shutil.which("rg"):
        cmd = [
            "rg",
            "-n",
            "--no-heading",
            "--color",
            "never",
            "--glob",
            "!.git",
            "--glob",
            "!__pycache__",
            "--glob",
            "!.pytest_cache",
            "--glob",
            "!.ruff_cache",
            "--glob",
            "!.venv",
            "--glob",
            "!venv",
            "--glob",
            "!node_modules",
            pattern,
            *paths,
        ]
    else:
        cmd = [
            "grep",
            "-rnI",
            "--color=never",
            "--exclude-dir=.git",
            "--exclude-dir=__pycache__",
            "--exclude-dir=.pytest_cache",
            "--exclude-dir=.ruff_cache",
            "--exclude-dir=.venv",
            "--exclude-dir=venv",
            "--exclude-dir=node_modules",
            pattern,
            *paths,
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

    error = ""
    if result.returncode not in (0, 1):
        error = result.stderr.strip() or f"busca terminou com código {result.returncode}"
    return SearchResult(
        pattern=pattern,
        matches=matches,
        total_files=len(seen_files),
        error=error,
    )


def run_all(
    ruff_paths: list[str] | None = None,
    test_paths: list[str] | None = None,
    ignore: list[str] | None = None,
    cov_source: str | list[str] = "src",
    gate: float = 70.0,
    cwd: Path | None = None,
    config: VerifyConfig | None = None,
) -> dict[str, VerifyResult]:
    """Executa todas as verificações: lint → test → coverage.

    Otimização: coverage só roda se o teste passar (short-circuit).

    `config` traz os comandos que o projeto alvo declarou em
    `.kata/config.yaml`. Cada papel declarado é executado verbatim; cada
    papel omitido cai no default Python (ruff/pytest/pytest-cov) e continua
    obedecendo aos parâmetros de caminho. Sem config, o comportamento é
    idêntico ao de antes.

    `cov_source` default é "src" — este módulo é genérico e não deve supor
    o nome do pacote de nenhum projeto, inclusive o próprio kata. Quem
    conhece o projeto é o CLI, via cli._detect_cov_source(), que pode
    entregar uma lista quando o pyproject declara várias fontes (R12-02).

    Returns:
        Dicionário com chaves "ruff", "pytest", "coverage" e seus resultados.
        As chaves são os papéis (lint, teste, coverage) e permanecem com o
        nome histórico porque são o mesmo vocabulário que o schema da tarefa
        persiste (`ruff_clean`, `tests_pass`, `coverage_pass`) e que o JUDGE
        confronta.
    """
    cfg = config or VerifyConfig()
    results: dict[str, VerifyResult] = {}

    if cfg.lint is not None:
        results["ruff"] = run_command(cfg.lint, cwd=cwd)
    else:
        results["ruff"] = run_ruff(paths=ruff_paths, cwd=cwd)

    if cfg.test is not None:
        results["pytest"] = run_command(cfg.test, cwd=cwd)
    else:
        results["pytest"] = run_pytest(testpaths=test_paths, ignore=ignore, cwd=cwd)

    if results["pytest"].ok:
        if cfg.coverage is not None:
            results["coverage"] = run_command_coverage(
                cfg.coverage,
                pattern=cfg.coverage_pattern,
                gate=gate,
                cwd=cwd,
            )
        else:
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
