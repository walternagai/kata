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
from functools import lru_cache
from pathlib import Path
from typing import Any

from kata.config import DEFAULT_COVERAGE_PATTERN, VerifyConfig

# Rótulo de exibição de cada papel. As chaves persistidas no YAML mantêm o
# nome histórico da ferramenta (`ruff_clean`, `tests_pass`) — renomear é
# migração de schema, e não é isso que o relatório precisa. O que o humano lê
# é o papel: num projeto que roda eslint e vitest, "ruff check limpo" é ruído
# que confunde (A7 da revisão estrutural de 2026-10).
ROLE_LABELS: dict[str, str] = {
    "ruff": "lint",
    "typecheck": "typecheck",
    "pytest": "teste",
    "coverage": "coverage",
}

# O mesmo papel tem duas grafias: a que o YAML persiste em `verify.commands`
# (`test`, em inglês, porque renomear a chave é migração de schema) e a que o
# humano lê (`teste`). A divergência é só essa, e mora aqui junto da tabela em
# vez de solta no `cli`: era a quarta cópia do vocabulário, e discordava da
# primeira (A20 da revisão estrutural de 2026-10).
COMMAND_LABELS: dict[str, str] = {**ROLE_LABELS, "pytest": "test"}

# Códigos de saída que significam "o shell não achou o comando", e não "o check
# reprovou": 127 no POSIX, 9009 no Windows. Só aparecem quando o comando
# declarado é executado por um shell (`sh -c`, `cmd /c`); com argv direto o
# executável ausente levanta OSError antes de existir returncode.
_NAO_ENCONTRADO: frozenset[int] = frozenset({127, 9009})


@dataclass
class VerifyResult:
    """Resultado de uma verificação individual (ruff, pytest, ou coverage).

    `executed` separa duas falhas que `ok=False` confundia: o check rodou e
    reprovou (`executed=True`), ou o comando nunca chegou a rodar porque o
    executável não existe nesta máquina (`executed=False`). Sem a distinção o
    JUDGE acusa fraude de alta severidade contra quem não mentiu — basta o
    projeto declarar `npm test` e o juiz rodar onde não há node.
    """

    ok: bool
    output: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    executed: bool = True


def consistency_failures(task_data: dict[str, Any]) -> list[str]:
    """Motivos pelos quais uma tarefa ``approved`` não se sustenta.

    O status é um campo persistido; o report/judge/audit não podem confiar
    nele quando o próprio verify diz que o critério não foi satisfeito (ou
    nem foi declarado). Devolve lista vazia para qualquer status diferente de
    ``approved`` e para uma tarefa consistente.
    """
    if not isinstance(task_data, dict):
        return []
    if task_data.get("status") != "approved":
        return []

    verify = task_data.get("verify")
    if not isinstance(verify, dict):
        verify = {}

    falhas: list[str] = []
    done = task_data.get("done", "")
    if not isinstance(done, str) or not done.strip():
        falhas.append("critério de sucesso não declarado (done vazio)")

    success = verify.get("success_criteria_met")
    if success is False:
        falhas.append("critério de sucesso não satisfeito")
    elif success is not True:
        falhas.append("critério de sucesso não registrado")

    for chave, rotulo in (
        ("ruff_clean", "lint"),
        ("typecheck_clean", "typecheck"),
        ("tests_pass", "testes"),
        ("coverage_pass", "coverage"),
    ):
        if verify.get(chave) is False:
            falhas.append(f"{rotulo} falhou")
    return falhas


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


# Nomes de arquivo que são dados de ferramenta, nunca trabalho da tarefa.
_TOOL_ARTIFACT_NAMES = frozenset({".coverage", "coverage.xml"})

# Diretórios cujo conteúdo inteiro é gerado por ferramenta. `__pycache__` NÃO
# entra: lá o filtro é pela extensão, para um `.py` de verdade guardado ali
# não ficar invisível — a mesma doutrina do `is_kata_bookkeeping` (filtra o
# dado da ferramenta, não o diretório).
_TOOL_ARTIFACT_DIRS = frozenset({".mypy_cache", ".pytest_cache", ".ruff_cache", "htmlcov"})
_TOOL_ARTIFACT_SUFFIXES = frozenset({".pyc", ".pyo"})


def is_kata_bookkeeping(filepath: str) -> bool:
    """O arquivo é escrituração da própria ferramenta, não trabalho da tarefa.

    `.kata/<task>.yaml` é criado pelo kata, não pelo autor da tarefa. Ele é
    untracked em qualquer projeto que não tenha ignorado `.kata/` — e nada no
    kata pede isso: `--init` não mexe no .gitignore e nenhum doc instrui a
    ignorá-lo. Sem este filtro, o judge conta o arquivo da própria tarefa como
    "arquivo alterado não declarado" e acusa trabalho honesto de scope creep;
    acima de 2 arquivos a severidade vira alta e o veredito, REFUTED (R11-3).

    Duas coisas esconderam isso por dez rodadas, e as duas são ambiente: este
    repositório tem `/.kata/` no .gitignore, então o kata sobre si mesmo nunca
    via; e o harness de traps escreve `.kata/` no .git/info/exclude de todo
    fixture, o que torna a classe inalcançável até pelo s07-honest-work.

    Filtra a escrituração, não o diretório: `.kata/config.yaml` também é
    ferramenta, mas um arquivo de código que alguém guarde sob `.kata/` não
    tem por que ficar invisível ao juiz.
    """
    partes = Path(filepath).parts
    if ".kata" not in partes:
        return False
    return Path(filepath).suffix.lower() in {".yaml", ".yml", ".json"}


def _sem_escrituracao(files: list[str]) -> list[str]:
    """Remove a escrituração do kata de uma lista de arquivos."""
    return [f for f in files if not is_kata_bookkeeping(f)]


def _is_tool_artifact(filepath: str) -> bool:
    """O arquivo é dado que uma ferramenta de verificação deixou na árvore?

    O `run_all` que o próprio judge dispara — e o `--check-only` do CI —
    deixam `.coverage`, `*.pyc` e caches na árvore. Num repositório sem
    `.gitignore` para eles, a execução SEGUINTE os vê como untracked e
    `hunt_scope_creep` acusava trabalho honesto: run1 VERIFIED → run2 REFUTED
    com scope_creep [high], e uma árvore sujada por `--check-only` já caía em
    WITH CAVEATS na run 1.

    O filtro é por nome de artefato, nunca por sufixo genérico:
    `.coveragerc` é configuração do projeto e NÃO é filtrado, e um
    `src/__pycache__/helper.py` — código que alguém guardou ali — também não
    (só `.pyc`/`.pyo` saem de `__pycache__`).
    """
    path = Path(filepath)
    nome = path.name
    if nome in _TOOL_ARTIFACT_NAMES:
        return True
    # `.coverage.<host>` é dado do coverage; `.coveragerc` é config do projeto
    # e o `startswith` com ponto final não o alcança.
    if nome.startswith(".coverage."):
        return True
    if path.suffix.lower() in _TOOL_ARTIFACT_SUFFIXES:
        return True
    return bool(_TOOL_ARTIFACT_DIRS.intersection(path.parts))


def _remove_tool_artifacts(files: list[str]) -> list[str]:
    """Remove artefatos de ferramenta (coverage, caches, bytecode) da lista."""
    return [f for f in files if not _is_tool_artifact(f)]


def _commit_exists(base_commit: str, cwd: Path | None = None) -> bool:
    """O piso do diff ainda resolve para um commit?

    Só existência: ancestralidade e âncora são a checagem de baseline do judge
    (`judge._base_commit_resolves`), que precisa continuar olhando pelo
    `judge._run` para o teste de OSError continuar valendo.
    """
    try:
        result = _run(
            ["git", "rev-parse", "--verify", "--quiet", f"{base_commit}^{{commit}}"], cwd=cwd
        )
    except OSError:
        return False
    # Só o código de saída: `--quiet` já suprime o erro, e exigir stdout
    # não-vazio quebraria o caso (legítimo) de teste que mocka o comando.
    return result.returncode == 0


def changed_files(
    cwd: Path | None = None,
    base_commit: str | None = None,
    diff_end: str | None = None,
) -> list[str]:
    """Arquivos que a tarefa alterou, com a mesma janela em todo o ciclo.

    Uma implementação só, e não duas: o SURGICAL declara arquivos a partir
    desta lista e o JUDGE confere escopo a partir dela. Enquanto eram duas
    (uma olhando a árvore de trabalho, outra `base..approved_commit`), uma
    tarefa retomada depois do commit era declarada numa janela e auditada em
    outra (revisão completa 2026-10, B5).

    Janela: `base_commit..diff_end` quando ambos resolvem; `base_commit..HEAD`
    quando só o piso; e, sem piso, `HEAD` → unstaged → staged, o suficiente
    para repositório sem commits. Untracked entram sempre: `git diff` é cego a
    eles. Saem a escrituração do kata (`.kata/*.yaml`) e os dados que a
    verificação deixa na árvore (`.coverage`, caches, bytecode).
    """
    result = None
    if base_commit and _commit_exists(base_commit, cwd=cwd):
        if diff_end:
            result = _run(["git", "diff", "--name-only", base_commit, diff_end], cwd=cwd)
        else:
            result = _run(["git", "diff", "--name-only", base_commit], cwd=cwd)
    else:
        try:
            result = _run(["git", "diff", "HEAD", "--name-only"], cwd=cwd)
        except OSError:
            result = None
        if result is None or result.returncode != 0:
            try:
                result = _run(["git", "diff", "--name-only"], cwd=cwd)
            except OSError:
                return []
            if not result.stdout.strip():
                try:
                    result = _run(["git", "diff", "--cached", "--name-only"], cwd=cwd)
                except OSError:
                    return []

    tracked = _sem_escrituracao(
        _remove_tool_artifacts([f for f in result.stdout.strip().split("\n") if f.strip()])
    )
    seen = set(tracked)
    novos = _sem_escrituracao(_remove_tool_artifacts(untracked_files(cwd=cwd)))
    return tracked + [f for f in novos if f not in seen]


def _comando_portatil(cmd: list[str]) -> str:
    """argv legível para o YAML, sem o caminho absoluto do interpretador.

    `sys.executable` é caminho de máquina (`/usr/bin/python3`, o do venv, o do
    runner do CI): não é portável e não diz nada sobre o papel executado
    (A9 da revisão estrutural). A comparação do juiz normaliza o interpretador
    de qualquer forma (`judge.normaliza_comando`).
    """
    if cmd and _eh_interpretador(cmd[0]):
        return " ".join(["python", *cmd[1:]])
    return " ".join(cmd)


def _eh_interpretador(token: str) -> bool:
    """O token é um executável de Python, absoluto e fora do PATH?"""
    caminho = Path(token)
    if not caminho.is_absolute():
        return False
    return caminho.name.lower().startswith("python")


# Interpretador de ambiente virtual do projeto, na ordem em que se procura.
# A convenção `.venv/` é a do ecossistema onde o kata roda; `venv/` aparece
# nos projetos mais velhos. No Windows o binário mora em Scripts/.
_VENV_PYTHONS: tuple[Path, ...] = (
    Path(".venv") / "bin" / "python",
    Path(".venv") / "Scripts" / "python.exe",
    Path("venv") / "bin" / "python",
    Path("venv") / "Scripts" / "python.exe",
)


@lru_cache(maxsize=64)
def _interpretador_do_projeto(cwd: str, modulos: tuple[str, ...]) -> str:
    """Interpretador para rodar o gate: o do projeto se ele serve, senão o do kata.

    `sys.executable` é o Python do kata — num `pipx install kata-dev` ele não
    tem as dependências do projeto alvo, e o pytest re-executado falharia por
    `ModuleNotFoundError` num repositório limpo (falso negativo de VERIFY e
    `false_completion` no JUDGE). A raiz `AGENTS.md` do ecossistema registra o
    mesmo sintoma: "pytest puro usa o interpretador errado; use .venv/bin/python".

    O interpretador do projeto só é adotado quando ele importa os módulos do
    papel (`ruff`, `pytest`, `pytest_cov`) — um `.venv` sem as ferramentas
    continua caindo em `sys.executable`, e a falha real aparece no output em
    vez de virar troca silenciosa de ambiente. A sonda roda uma vez por
    processo e por diretório (`lru_cache`).
    """
    raiz = Path(cwd)
    for relativo in _VENV_PYTHONS:
        candidato = raiz / relativo
        if not candidato.is_file():
            continue
        sonda = _run([str(candidato), "-c", f"import {', '.join(modulos)}"], cwd=raiz)
        if sonda.returncode == 0:
            return str(candidato)
    return sys.executable


def _interpretador(cwd: Path | None, *modulos: str) -> str:
    """Atalho tipado para `_interpretador_do_projeto`."""
    return _interpretador_do_projeto(str(cwd or Path.cwd()), modulos)


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
    cmd = [_interpretador(cwd, "ruff"), "-m", "ruff", "check", *paths]
    result = _run(cmd, cwd=cwd)
    return VerifyResult(
        ok=result.returncode == 0,
        output=result.stdout + result.stderr,
        details={"command": _comando_portatil(cmd)},
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
    cmd = [_interpretador(cwd, "pytest"), "-m", "pytest", *testpaths, "--tb=short", "-q"]
    if ignore:
        for path in ignore:
            cmd.extend(["--ignore", path])
    if extra_args:
        cmd.extend(extra_args)
    result = _run(cmd, cwd=cwd)
    return VerifyResult(
        ok=result.returncode == 0,
        output=result.stdout + result.stderr,
        details={"command": _comando_portatil(cmd)},
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
        _interpretador(cwd, "pytest", "pytest_cov"),
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
            details={"coverage_pct": 0.0, "gate": gate, "command": _comando_portatil(cmd)},
        )
    cov_pct = float(match.group(1))

    passed = result.returncode == 0
    return VerifyResult(
        ok=passed,
        output=result.stdout + result.stderr,
        details={
            "coverage_pct": cov_pct,
            "gate": gate,
            "command": _comando_portatil(cmd),
        },
    )


def run_command(cmd: list[str], cwd: Path | None = None) -> VerifyResult:
    """Executa um comando de verificação declarado pelo projeto alvo.

    Aprova pelo returncode, que é o único contrato que toda ferramenta de
    lint e de teste respeita — de `ruff` a `go vet`, de `pytest` a `cargo
    test`. Comando inexistente vira falha com a mensagem do SO, e não
    exceção: no VERIFY isso tem de aparecer como verificação reprovada,
    para o ciclo poder reportá-lo; estourar aqui derrubaria a fase inteira.

    Mas "não consegui executar" não é "executei e reprovou": esses casos saem
    com `executed=False`, e é o que impede o JUDGE de tratá-los como prova de
    que o relatório mentiu.
    """
    try:
        result = _run(cmd, cwd=cwd)
    except OSError as exc:
        return VerifyResult(
            ok=False,
            output=f"não foi possível executar {' '.join(cmd)}: {exc}",
            details={"command": " ".join(cmd)},
            executed=False,
        )
    return VerifyResult(
        ok=result.returncode == 0,
        output=result.stdout + result.stderr,
        details={"command": " ".join(cmd)},
        executed=result.returncode not in _NAO_ENCONTRADO,
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
    if not result.executed:
        # O comando não rodou: não há percentual a procurar, e "não medi" não
        # pode virar "mediu 0,0%" nem "reprovou o gate".
        return VerifyResult(
            ok=False,
            output=result.output,
            details={"coverage_pct": 0.0, "gate": gate, "command": _comando_portatil(cmd)},
            executed=False,
        )
    try:
        match = re.search(pattern, result.output, re.MULTILINE)
    except re.error as exc:
        return VerifyResult(
            ok=False,
            output=result.output + f"\n(kata: padrão de coverage inválido: {exc})",
            details={"coverage_pct": 0.0, "gate": gate, "command": _comando_portatil(cmd)},
        )
    if match is None:
        return VerifyResult(
            ok=False,
            output=result.output + f"\n(kata: nenhum percentual casou com o padrão {pattern!r})",
            details={"coverage_pct": 0.0, "gate": gate, "command": _comando_portatil(cmd)},
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
            details={"coverage_pct": 0.0, "gate": gate, "command": _comando_portatil(cmd)},
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
            details={"coverage_pct": 0.0, "gate": gate, "command": _comando_portatil(cmd)},
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
            # `--` antes do padrão: sem ele, procurar por um flag (ex.:
            # `--force`, `-1`) faz o rg tratar o padrão como opção e falhar
            # com "unrecognized flag". O TWIN CHECK busca exatamente esse tipo
            # de padrão (revisão completa 2026-10, M3).
            "--",
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
            "--",
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
    """Executa todas as verificações: lint → typecheck → test → coverage.

    Otimização: coverage só roda se o teste passar (short-circuit).

    `typecheck` só existe quando o projeto declara o comando: não há default
    Python para ele, e entrar no dicionário com `ok=True` sem ter rodado nada
    seria registrar como verificada uma checagem que ninguém pediu. A chave
    ausente é o que o CLI e o JUDGE leem como "este projeto não tem esse gate".

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

    if cfg.typecheck is not None:
        results["typecheck"] = run_command(cfg.typecheck, cwd=cwd)

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
