"""Adversarial verification (fable-judge) — caça fraudes em tarefas concluídas.

Inspirado no fable-judge do The Fable Method
(https://github.com/Sahir619/fable-method):

1. Collect claims — o que o relatório diz que foi feito
2. Establish ground truth — git diff contra o estado real
3. Re-run every claimed verification — executa de novo e compara
4. Hunt frauds — 6 categorias (weakened checks, false completion,
   scope creep, unauthorized action, spec betrayal, debris)
5. Deliver verdict — VERIFIED / VERIFIED WITH CAVEATS / UNVERIFIABLE / REFUTED

UNVERIFIABLE cobre o caso em que nada foi observado: o juiz não achou fraude
porque não teve como procurar. Ver `judge_task`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kata.config import VerifyConfig
from kata.verify import VerifyResult, _run, is_inspectable, run_all, untracked_files

# ── sondas por linguagem ──────────────────────────────────────────────────


@dataclass(frozen=True)
class LanguageProbes:
    """O que o juiz sabe procurar num teste de uma dada linguagem.

    Enquanto os padrões viveram numa constante só, eles eram sintaxe Python
    (`assert`, `pass`, o supressor de lint) aplicada a qualquer arquivo: num
    teste .js ou .go não casavam nunca, e "nenhuma fraude encontrada" era uma
    afirmação sobre código que o hunter jamais tinha conseguido ler.

    Attributes:
        weakened: (padrão, descrição) para linhas de arquivo *modificado* —
            enfraquecer pressupõe algo que existia antes.
        test_declaration: início de uma função/bloco de teste, para achar
            teste vazio em arquivo *novo*, onde toda linha é '+'.
        empty_body: corpo vazio, casado na primeira linha significativa
            depois da declaração.
        empty_inline: corpo vazio na própria linha da declaração
            (`it('x', () => {})`), que a varredura linha-a-linha não pega.
        skippable: linha sem significado (vazia ou comentário) entre a
            declaração e o corpo. A sintaxe de comentário muda por linguagem.
    """

    weakened: tuple[tuple[str, str], ...]
    test_declaration: re.Pattern[str] | None = None
    empty_body: re.Pattern[str] | None = None
    empty_inline: re.Pattern[str] | None = None
    skippable: re.Pattern[str] = re.compile(r"^\+\s*$")


_PY_PROBES = LanguageProbes(
    weakened=(
        (r"^-.*assert\s+True\b", "assert True (sempre passa se True for literal)"),
        (r"^-.*assert\s+False\b", "assert False (sempre falha ou foi removido)"),
        (r"^\+#\s+.*(?:assert|def test|expect|self\.)", "teste virado em comentário"),
        (r"^\+.*assert\s+True\b", "assert True adicionado — pode neutralizar a asserção"),
        (r"^\+.*pytest\.skip\b", "teste desativado com pytest.skip"),
        (r"^\+\s*pass\s*$", "corpo de teste substituído por pass"),
        (r"^\+.*#\s*noqa", "noqa adicionado — pode esconder erro de lint"),
    ),
    test_declaration=re.compile(r"^\+\s*(?:async\s+)?def\s+test\w*\s*\("),
    # pass com comentário inline também é corpo vazio — R9-6: a fraude mais
    # comum é o corpo vazio "documentado" por um comentário na mesma linha.
    empty_body=re.compile(r"^\+\s*pass\s*(?:#.*)?$"),
    skippable=re.compile(r"^\+\s*(?:#.*)?$"),
)

_JS_PROBES = LanguageProbes(
    weakened=(
        (r"^-.*\bexpect\s*\(", "asserção expect() removida"),
        (r"^-.*\bassert\b", "asserção assert removida"),
        (r"^\+.*\b(?:it|test|describe)\.skip\b", "teste desativado com .skip"),
        (r"^\+.*\bx(?:it|test|describe)\s*\(", "teste desativado (xit/xdescribe)"),
        (r"^\+\s*//.*(?:expect|assert|it\(|test\()", "teste virado em comentário"),
        (r"^\+.*eslint-disable", "eslint-disable adicionado — pode esconder erro de lint"),
        (r"^\+.*@ts-(?:ignore|nocheck)", "checagem de tipo suprimida"),
    ),
    test_declaration=re.compile(r"^\+\s*(?:it|test)\s*\("),
    empty_body=re.compile(r"^\+\s*\}\s*\)"),
    # `it('x', () => { /* TODO */ })` — o fechamento inline com comentário
    # (`/* */` ou `//`) também é corpo vazio (R9-6).
    empty_inline=re.compile(r"\{\s*(?:(?:/\*.*?\*/)|(?://.*?))?\s*\}"),
    skippable=re.compile(r"^\+\s*(?://.*)?$"),
)

_GO_PROBES = LanguageProbes(
    weakened=(
        (r"^-.*\bt\.(?:Error|Fatal|Errorf|Fatalf)\b", "verificação t.Error/t.Fatal removida"),
        (r"^\+.*\bt\.Skip\b", "teste pulado com t.Skip"),
        (r"^\+\s*//.*(?:t\.Error|t\.Fatal|func Test)", "teste virado em comentário"),
        (r"^\+.*//\s*nolint", "nolint adicionado — pode esconder erro de lint"),
    ),
    test_declaration=re.compile(r"^\+\s*func\s+Test\w*\s*\("),
    empty_body=re.compile(r"^\+\s*\}\s*$"),
    empty_inline=re.compile(r"\{\s*\}"),
    skippable=re.compile(r"^\+\s*(?://.*)?$"),
)

_RB_PROBES = LanguageProbes(
    weakened=(
        (r"^-.*\b(?:expect|assert\w*)\s*[\s(]", "asserção removida"),
        (r"^\+.*\b(?:xit|skip)\b", "teste desativado (xit/skip)"),
        (r"^\+\s*#.*(?:expect|assert|it |def test)", "teste virado em comentário"),
        (r"^\+.*rubocop:disable", "rubocop:disable adicionado"),
    ),
    test_declaration=re.compile(r"^\+\s*(?:it\s|specify\s|def\s+test_)"),
    empty_body=re.compile(r"^\+\s*end\s*$"),
    skippable=re.compile(r"^\+\s*(?:#.*)?$"),
)

_RS_PROBES = LanguageProbes(
    weakened=(
        (r"^-.*\bassert(?:_eq|_ne)?!", "asserção assert! removida"),
        (r"^\+.*#\[ignore\]", "teste desativado com #[ignore]"),
        (r"^\+\s*//.*assert", "asserção virada em comentário"),
        (r"^\+.*#\[allow\(", "lint suprimido com #[allow(...)]"),
    ),
    test_declaration=re.compile(r"^\+\s*(?:async\s+)?fn\s+\w*test\w*\s*\("),
    empty_body=re.compile(r"^\+\s*\}\s*$"),
    empty_inline=re.compile(r"\{\s*\}"),
    skippable=re.compile(r"^\+\s*(?://.*)?$"),
)

_JAVA_PROBES = LanguageProbes(
    weakened=(
        (r"^-.*\bassert\w*\s*\(", "asserção removida"),
        (r"^\+.*@(?:Disabled|Ignore)\b", "teste desativado com @Disabled/@Ignore"),
        (r"^\+\s*//.*(?:assert|@Test)", "teste virado em comentário"),
        (r"^\+.*@SuppressWarnings", "@SuppressWarnings adicionado"),
    ),
    test_declaration=re.compile(r"^\+\s*(?:public\s+)?void\s+\w*[Tt]est\w*\s*\("),
    empty_body=re.compile(r"^\+\s*\}\s*$"),
    empty_inline=re.compile(r"\{\s*\}"),
    skippable=re.compile(r"^\+\s*(?://.*)?$"),
)

# Extensão → o que o juiz sabe procurar ali. Uma extensão ausente daqui é um
# ponto cego declarado, não um silêncio: ver `_unreadable_test_files`.
_LANGUAGES: dict[str, LanguageProbes] = {
    ".py": _PY_PROBES,
    ".js": _JS_PROBES,
    ".jsx": _JS_PROBES,
    ".mjs": _JS_PROBES,
    ".cjs": _JS_PROBES,
    ".ts": _JS_PROBES,
    ".tsx": _JS_PROBES,
    ".go": _GO_PROBES,
    ".rb": _RB_PROBES,
    ".rs": _RS_PROBES,
    ".java": _JAVA_PROBES,
    ".kt": _JAVA_PROBES,
}


def probes_for(filepath: str) -> LanguageProbes | None:
    """Sondas da linguagem do arquivo, ou None se o juiz não a conhece."""
    return _LANGUAGES.get(Path(filepath).suffix.lower())


# ── outros padrões ────────────────────────────────────────────────────────

_DEBRIS_FILE_PATTERNS = [
    r"\.tmp$",
    r"\.bak$",
    r"scratch",
    # "temp" só conta como detrito quando é um segmento isolado do path (delimitado
    # por /, _, . ou -), não uma substring qualquer — sem isso, "templates/x.html",
    # "attempt_parser.py", "src/temperature.py" e "contemporary_utils.py" seriam
    # falsos positivos.
    r"(?:^|[/_.\-])temp\d*(?:[/_.\-]|$)",
]

_DEBRIS_LINE_PATTERNS: list[tuple[str, str]] = [
    (r"^\+.*print\(.*debug", "debug print statement"),
    (r"^\+.*console\.log\(.*debug", "debug console.log"),
    (r"^\+.*(?:#|//)\s*TODO\b", "TODO deixado no código"),
]


@dataclass
class JudgeFraud:
    """Uma fraude individual encontrada pelo juiz adversarial."""

    type: str
    severity: str  # "high" | "medium" | "low"
    description: str
    evidence: str = ""


@dataclass
class JudgeResult:
    """Resultado completo da verificação adversarial.

    Attributes:
        verdict: VERIFIED | VERIFIED WITH CAVEATS | UNVERIFIABLE | REFUTED
        claims: Claims que o juiz consegue confrontar com a realidade.
        unverifiable_claims: Claims aceitas sem verificação, por não haver
            comando que as reproduza.
        caveats: Ressalvas sobre o resultado.
        blind_spots: O que o juiz não conseguiu observar. Não é acusação —
            é confissão, e é o que separa UNVERIFIABLE de VERIFIED.
        frauds: Fraudes encontradas durante a verificação.
        re_ran_checks: Resultados da re-execução das verificações.
        details: Metadados extras.
    """

    verdict: str = "VERIFIED"
    claims: list[str] = field(default_factory=list)
    unverifiable_claims: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    frauds: list[JudgeFraud] = field(default_factory=list)
    re_ran_checks: dict[str, bool] = field(default_factory=dict)
    blind_spots: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


# ── claims ────────────────────────────────────────────────────────────────


def collect_claims(task_data: dict[str, Any]) -> list[str]:
    """Extrai as claims que o juiz consegue confrontar com a realidade.

    O critério de sucesso fica de fora de propósito — ver
    collect_unverifiable_claims.
    """
    claims: list[str] = []
    verify = task_data.get("verify", {})
    if verify.get("ruff_clean"):
        claims.append("ruff check limpo (sem erros de lint)")
    if verify.get("tests_pass"):
        claims.append("todos os testes passam")
    if verify.get("coverage_pass"):
        claims.append(f"coverage ≥ gate ({verify.get('coverage_pct', '?')}%)")

    surgical = task_data.get("surgical", {})
    files = surgical.get("files", [])
    if files:
        n = sum(1 for f in files if f.get("necessary"))
        if n > 0:
            claims.append(f"{n} arquivo(s) alterado(s) cirurgicamente (necessários)")

    intent = task_data.get("intent", {})
    if intent.get("all_agree"):
        claims.append("intenção alinhada: código, teste e spec concordam")

    return claims


def collect_unverifiable_claims(task_data: dict[str, Any]) -> list[str]:
    """Extrai as claims que o juiz aceita sem poder verificar.

    O critério de sucesso é uma confirmação subjetiva que o usuário dá no
    VERIFY: não existe comando que o reproduza. Apresentá-lo junto das
    claims verificadas faria o relatório afirmar uma verificação que não
    aconteceu — a fraude que este módulo existe para caçar.
    """
    claims: list[str] = []
    if task_data.get("verify", {}).get("success_criteria_met"):
        claims.append("critério de sucesso satisfeito")
    return claims


# ── git helpers ───────────────────────────────────────────────────────────


_BASELINE_REF_PREFIX = "refs/kata/base/"


def baseline_ref(task: str) -> str:
    """Nomeia a ref Git que ancora o baseline de uma tarefa."""
    digest = hashlib.sha256(task.encode("utf-8")).hexdigest()
    return f"{_BASELINE_REF_PREFIX}{digest}"


def record_baseline_ref(task: str, commit: str, cwd: Path | None = None) -> bool:
    """Registra o baseline fora do YAML, em metadata do Git."""
    try:
        result = _run(["git", "update-ref", baseline_ref(task), commit], cwd=cwd)
    except OSError:
        return False
    return result.returncode == 0


def _read_baseline_ref(task: str, cwd: Path | None = None) -> str | None:
    """Lê o baseline ancorado no Git, se houver."""
    try:
        result = _run(["git", "rev-parse", "--verify", baseline_ref(task)], cwd=cwd)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _base_commit_resolves(base_commit: str, cwd: Path | None = None) -> bool:
    """Confirma que base_commit ainda existe no histórico (não foi rebaseado/podado)."""
    result = _run(["git", "cat-file", "-e", f"{base_commit}^{{commit}}"], cwd=cwd)
    return result.returncode == 0


def _resolve_commit(base_commit: str, cwd: Path | None = None) -> str | None:
    """Expande um commit válido para seu SHA completo."""
    result = _run(["git", "rev-parse", "--verify", f"{base_commit}^{{commit}}"], cwd=cwd)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _base_commit_is_ancestor(base_commit: str, cwd: Path | None = None) -> bool:
    """Confirma que o baseline está no caminho histórico do HEAD atual."""
    result = _run(["git", "merge-base", "--is-ancestor", base_commit, "HEAD"], cwd=cwd)
    return result.returncode == 0


def _oversized_untracked(files: list[str], cwd: Path | None = None) -> list[str]:
    """Arquivos untracked grandes demais para inspecionar (viram caveat)."""
    base = cwd or Path.cwd()
    return [f for f in files if (base / f).is_file() and not is_inspectable(base / f)]


def _untracked_diff(files: list[str], cwd: Path | None = None) -> str:
    """Sintetiza um diff de adição para arquivos untracked.

    Produz o que os hunters leem: o cabeçalho `diff --git`, o marcador
    `new file mode` que o git emite para arquivo novo — e do qual
    hunt_weakened_checks depende para não acusar código honesto — e o
    conteúdo como linhas '+'. Binários, ilegíveis e grandes demais ficam
    de fora.
    """
    base = cwd or Path.cwd()
    chunks: list[str] = []
    for f in files:
        path = base / f
        if not is_inspectable(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        chunks.append(f"diff --git a/{f} b/{f}")
        chunks.append("new file mode 100644")
        chunks.extend(f"+{line}" for line in content.splitlines())
    return "\n".join(chunks)


def _run_git_diff(cwd: Path | None = None, base_commit: str | None = None) -> str:
    """Retorna o diff da tarefa.

    Se `base_commit` (o HEAD registrado quando a tarefa começou, na fase
    FIT) estiver disponível, usa `git diff <base_commit>` — cobre commits,
    staged e unstaged de uma vez, então continua funcionando depois que a
    tarefa é commitada (o caso normal de uma tarefa "concluída").

    Sem base_commit (tarefas antigas, ou geradas fora do ciclo FIT), usa o
    diff contra HEAD para incluir staged e unstaged, com fallback para
    repositórios sem commit.

    Em ambos os casos, o conteúdo dos arquivos untracked é anexado como
    diff sintético: `git diff` nunca os mostra, e sem isso um arquivo novo
    ficaria invisível aos hunters.
    """
    if base_commit and _base_commit_resolves(base_commit, cwd=cwd):
        diff = _run(["git", "diff", base_commit], cwd=cwd).stdout
    else:
        result = _run(["git", "diff", "HEAD"], cwd=cwd)
        if result.returncode != 0:
            result = _run(["git", "diff"], cwd=cwd)
            if not result.stdout.strip():
                result = _run(["git", "diff", "--cached"], cwd=cwd)
        diff = result.stdout

    untracked = _untracked_diff(untracked_files(cwd=cwd), cwd=cwd)
    return f"{diff}\n{untracked}" if untracked else diff


def _changed_files(cwd: Path | None = None, base_commit: str | None = None) -> list[str]:
    """Retorna a lista de arquivos alterados pela tarefa (mesma lógica de _run_git_diff)."""
    if base_commit and _base_commit_resolves(base_commit, cwd=cwd):
        result = _run(["git", "diff", "--name-only", base_commit], cwd=cwd)
    else:
        result = _run(["git", "diff", "HEAD", "--name-only"], cwd=cwd)
        if result.returncode != 0:
            result = _run(["git", "diff", "--name-only"], cwd=cwd)
            if not result.stdout.strip():
                result = _run(["git", "diff", "--cached", "--name-only"], cwd=cwd)

    tracked = [f for f in result.stdout.strip().split("\n") if f.strip()]
    seen = set(tracked)
    return tracked + [f for f in untracked_files(cwd=cwd) if f not in seen]


# ── fraud hunters ─────────────────────────────────────────────────────────


# Convenções de nome de teste em várias linguagens: test_x.py, x_test.go,
# x.test.js, x.spec.ts, x_spec.rb. Casa no basename e exige separador antes
# do token, senão "latest.py", "contest.py" e "attempt_parser.py" entram.
_TEST_BASENAME = re.compile(r"^(?:test|spec)[_.\-]|[_.\-](?:test|spec)s?\.", re.IGNORECASE)

# Java/Kotlin/C# não usam separador: `SomaTest.java`, `WidgetSpec.kt`. Esta
# regra é deliberadamente sensível a maiúsculas e exige minúscula antes do
# token — sem isso, "latest.js" e "contest.go" voltariam como falso positivo,
# que é exatamente o que a regra acima já teve de evitar.
_TEST_BASENAME_CAMEL = re.compile(r"[a-z](?:Test|Spec)s?\.")


def _looks_like_test_name(basename: str) -> bool:
    """O nome do arquivo, sozinho, anuncia que ele é um teste."""
    return bool(_TEST_BASENAME.search(basename) or _TEST_BASENAME_CAMEL.search(basename))


def _is_test_file(filepath: str) -> bool:
    """Parece teste, por diretório ou por convenção de nome.

    Governa o que hunt_weakened_checks olha. Enquanto reconhecia só
    `tests/`, `/test_` e `_test.`, um `src/soma.test.js` não era sequer
    considerado teste — de modo que dar padrões .js ao juiz não bastaria:
    ele nunca chegaria a aplicá-los.
    """
    if filepath.startswith(("tests/", "test/", "spec/")) or "__tests__/" in filepath:
        return True
    if "/tests/" in filepath or "/test/" in filepath or "/spec/" in filepath:
        return True
    return _looks_like_test_name(filepath.rsplit("/", 1)[-1])


def _unreadable_test_files(changed: list[str]) -> list[str]:
    """Testes cuja linguagem o juiz não sabe ler.

    Existe para o juiz confessar, não para acusar: num repositório poliglota
    as verificações podem passar e ser re-executadas — desarmando o outro
    ponto cego — enquanto um teste de linguagem sem sondas foi esvaziado sem
    que hunt_weakened_checks pudesse enxergar. "Nenhuma fraude" ali é
    ausência de leitura, não ausência de fraude.

    A lista encolhe sozinha conforme `_LANGUAGES` cresce: a confissão é
    derivada do que o juiz sabe, e não mantida à mão em paralelo.

    Reconhece teste pela convenção do nome, e não por morar em `tests/`:
    incluir todo arquivo do diretório marcaria `tests/fixtures/dados.json`
    como teste ilegível em todo projeto que tem fixture, e uma ressalva que
    aparece sempre é uma ressalva que ninguém lê. O preço é não flagrar
    `__tests__/index.js`, que não traz token nenhum no nome.
    """
    non_executable = {".json", ".jsonl", ".toml", ".txt", ".yaml", ".yml"}
    return [
        f
        for f in changed
        if _is_test_file(f)
        and Path(f).suffix.lower() not in non_executable
        and probes_for(f) is None
    ]


def _ignored_files(cwd: Path | None = None) -> list[str]:
    """Lista arquivos ignorados que podem conter código ou testes alterados."""
    result = _run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
        cwd=cwd,
    )
    return [f for f in result.stdout.strip().split("\n") if f.strip()]


def _ignored_code_files(files: list[str]) -> list[str]:
    """Remove caches conhecidos e preserva candidatos relevantes para revisão."""
    noise = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
    source_dirs = {"app", "lib", "scripts", "src", "test", "tests", "spec", "__tests__"}
    return [
        f
        for f in files
        if not noise.intersection(Path(f).parts)
        and not any(part.endswith(".egg-info") for part in Path(f).parts)
        and (
            Path(f).suffix.lower() in _LANGUAGES
            or _is_test_file(f)
            or source_dirs.intersection(Path(f).parts)
        )
    ]


def is_debris_file(filepath: str) -> bool:
    """Retorna True se o path parece detrito (temporário/backup/scratch).

    Fonte única da regra: o JUDGE (hunt_debris) e o CLI
    (cli._detect_scratch_files) precisam concordar. Enquanto a regra viveu
    duplicada, a cópia do CLI usava a substring "temp" e marcava
    `templates/`, `temperature.py` e `attempt_parser.py` como lixo — o
    mesmo falso-positivo que _DEBRIS_FILE_PATTERNS já resolvia aqui.
    """
    return any(re.search(pat, filepath, re.IGNORECASE) for pat in _DEBRIS_FILE_PATTERNS)


def _empty_test_bodies(added_lines: list[str], probes: LanguageProbes) -> list[str]:
    """Funções de teste cujo corpo inteiro é vazio.

    Substitui, para arquivos novos, os padrões `weakened` — que pressupõem
    modificação ("o corpo virou pass" exige que houvesse corpo). Num arquivo
    novo o que é de fato suspeito é uma função de teste que não faz nada.
    Discrimina pelo que importa: `pass` como corpo de um `def test_*` é
    fraude; `pass` num stub de classe ou num `except ...:` é código honesto
    e não cai aqui.

    A varredura ignora apenas as linhas puramente vazias ou de comentário
    puro (`skippable`) entre a declaração e o corpo. A fraude mais comum é
    `pass  # noqa` ou `// ...` colados ao corpo — com comentário inline, a
    linha deixa de casar `skippable` e o corpo vazio escapava (R9-6). Por
    isso o corpo é decidido por `empty_body`, que também casa o marcador
    com comentário inline.

    Linguagem sem `test_declaration` ou sem `empty_body` não é varrida — o
    silêncio aqui é estreito e deliberado, e os padrões `weakened` daquela
    linguagem continuam valendo para arquivos modificados.
    """
    if probes.test_declaration is None or probes.empty_body is None:
        return []

    achados: list[str] = []
    for i, line in enumerate(added_lines):
        if not probes.test_declaration.match(line):
            continue
        # Corpo vazio na própria linha da declaração: `it('x', () => {})`.
        # O fechamento pode vir com comentário inline (`{ /* TODO */ }`) —
        # `\{\s*\}` não casava e o corpo vazio escapava (R9-6).
        if probes.empty_inline is not None and probes.empty_inline.search(line):
            achados.append(line.lstrip("+").strip())
            continue
        for seguinte in added_lines[i + 1:]:
            if probes.skippable.match(seguinte):
                continue
            if probes.empty_body.match(seguinte):
                achados.append(line.lstrip("+").strip())
            break
    return achados


def hunt_weakened_checks(diff: str) -> list[JudgeFraud]:
    """Caça 1: verificações enfraquecidas — asserts removidos/relaxados.

    Arquivos novos são pulados. "Enfraquecer" pressupõe algo que existia
    antes; num arquivo novo toda linha é '+' por definição, então padrões
    como "corpo virou pass" perdem o sentido e acusam código honesto — um
    stub com `pass` ou um `except ...: pass` num teste recém-criado. O
    marcador é o mesmo que o git emite (`new file mode`), então isto vale
    tanto para arquivos staged/commitados quanto para o diff sintético de
    untracked.

    Contagem: uma fraude por linha de diff suspeita, não por padrão casado.
    Uma linha que casa dois padrões (ex.: teste comentado que também ganhou
    `# noqa`) é um único enfraquecimento e conta uma vez — o mesmo princípio
    do H1 para debris ("predicado, não contador").
    """
    frauds: list[JudgeFraud] = []
    current_file = ""
    is_new_file = False
    new_test_bodies: dict[str, list[str]] = {}

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            parts = line.split()
            current_file = parts[3].replace("b/", "", 1) if len(parts) >= 4 else ""
            is_new_file = False
        elif line.startswith("new file mode"):
            is_new_file = True
        if not current_file or not _is_test_file(current_file):
            continue
        probes = probes_for(current_file)
        if probes is None:
            # Linguagem sem sondas: não há o que aplicar. O silêncio não fica
            # implícito — _unreadable_test_files o transforma em ponto cego.
            continue
        if is_new_file:
            if line.startswith("+"):
                new_test_bodies.setdefault(current_file, []).append(line)
            continue
        for pattern, desc in probes.weakened:
            if re.match(pattern, line):
                frauds.append(JudgeFraud(
                    type="weakened_checks",
                    severity="high",
                    description=f"{current_file}: {desc}",
                    evidence=line.strip(),
                ))
                # Uma fraude por linha de diff, não por padrão casado: a mesma
                # linha pode casar dois padrões (ex.: teste comentado com
                # noqa inline casa "teste virado em comentário" e "noqa
                # adicionado") e não pode contar duas vezes. O primeiro padrão
                # casado é o mais específico (assert literal > comentário >
                # pass > noqa).
                break

    for path, added in new_test_bodies.items():
        probes = probes_for(path)
        if probes is None:  # pragma: no cover - filtrado no laço acima
            continue
        for vazio in _empty_test_bodies(added, probes):
            frauds.append(JudgeFraud(
                type="weakened_checks",
                severity="high",
                description=f"{path}: teste com corpo vazio (só pass)",
                evidence=vazio,
            ))

    return frauds


def hunt_false_completion(
    task_data: dict[str, Any],
    verify_results: dict[str, VerifyResult],
) -> list[JudgeFraud]:
    """Caça 2: falsa conclusão — relatório diz passou, re-run diz falhou."""
    frauds: list[JudgeFraud] = []
    verify = task_data.get("verify", {})

    checks: list[tuple[str, str, str]] = [
        ("ruff_clean", "ruff", "ruff check"),
        ("tests_pass", "pytest", "pytest"),
        ("coverage_pass", "coverage", "coverage"),
    ]

    for claim_key, result_key, label in checks:
        if verify.get(claim_key) and result_key in verify_results:
            result = verify_results[result_key]
            if not result.ok:
                frauds.append(JudgeFraud(
                    type="false_completion",
                    severity="high",
                    description=f"{label} re-executado falhou, mas relatório afirma que passou",
                    evidence=f"relatório: {claim_key}=True → reality: {label} falhou",
                ))

    return frauds


def hunt_scope_creep(task_data: dict[str, Any], changed: list[str]) -> list[JudgeFraud]:
    """Caça 3: escopo extra — arquivos alterados não declarados."""
    frauds: list[JudgeFraud] = []
    surgical = task_data.get("surgical", {})
    declared = {f.get("path") for f in surgical.get("files", []) if f.get("necessary")}
    extra = [f for f in changed if f not in declared]

    if extra:
        frauds.append(JudgeFraud(
            type="scope_creep",
            severity="medium" if len(extra) <= 2 else "high",
            description=f"{len(extra)} arquivo(s) alterado(s) não declarado(s) como necessários",
            evidence=", ".join(extra[:5]),
        ))

    return frauds


def hunt_unauthorized_action(task_data: dict[str, Any]) -> list[JudgeFraud]:
    """Caça 4: ação não autorizada — AUTH owed mas não presente."""
    frauds: list[JudgeFraud] = []
    artifact = task_data.get("artifact", {})
    if artifact.get("auth_owed") and not artifact.get("auth_present"):
        frauds.append(JudgeFraud(
            type="unauthorized_action",
            severity="high",
            description="ação externa realizada sem AUTH line",
            evidence="artifact.auth_owed=True mas auth_present=False",
        ))
    return frauds


def hunt_spec_betrayal(task_data: dict[str, Any]) -> list[JudgeFraud]:
    """Caça 5: traição da spec — código mudou contra a especificação."""
    frauds: list[JudgeFraud] = []
    intent = task_data.get("intent", {})
    if intent.get("answered") and not intent.get("all_agree"):
        frauds.append(JudgeFraud(
            type="spec_betrayal",
            severity="high",
            description="intenção não alinhada: código, teste e spec discordam",
            evidence=(
                f"code_does={intent.get('code_does','')} | "
                f"check_expects={intent.get('check_expects','')} | "
                f"spec_says={intent.get('spec_says','')}"
            ),
        ))
    return frauds


def hunt_debris(diff: str, changed: list[str]) -> list[JudgeFraud]:
    """Caça 6: detritos — arquivos temporários, debug prints, lixo."""
    frauds: list[JudgeFraud] = []

    for f in changed:
        if is_debris_file(f):
            frauds.append(JudgeFraud(
                type="debris",
                severity="low",
                description=f"arquivo temporário/de lixo: {f}",
                evidence=f"arquivo suspeito: {f}",
            ))

    found_types: set[str] = set()
    for line in diff.split("\n"):
        for pattern, desc in _DEBRIS_LINE_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE) and desc not in found_types:
                found_types.add(desc)
                frauds.append(JudgeFraud(
                    type="debris",
                    severity="low",
                    description=desc,
                    evidence=line.strip()[:120],
                ))

    return frauds


# ── orchestration ─────────────────────────────────────────────────────────


def judge_task(
    task_data: dict[str, Any],
    cwd: Path | None = None,
    ruff_paths: list[str] | None = None,
    test_paths: list[str] | None = None,
    ignore: list[str] | None = None,
    cov_source: str = "src",
    gate: float = 70.0,
    config: VerifyConfig | None = None,
) -> JudgeResult:
    """Executa verificação adversarial completa em uma tarefa.

    1. Coleta claims do YAML da tarefa
    2. Estabelece verdade material (git diff)
    3. Re-executa verificações que o relatório afirma que passaram
    4. Caça fraudes em 6 categorias
    5. Registra o que não conseguiu observar (pontos cegos)
    6. Entrega veredito
    """
    blind_spots: list[str] = []
    baseline_frauds: list[JudgeFraud] = []
    base_commit = task_data.get("base_commit")
    task_name = task_data.get("task")
    diff_base = base_commit

    if isinstance(task_name, str) and base_commit:
        anchor = _read_baseline_ref(task_name, cwd=cwd)
        if anchor is None:
            blind_spots.append(
                "baseline declarado no YAML não tem âncora independente no Git"
            )
        else:
            yaml_commit = _resolve_commit(str(base_commit), cwd=cwd)
            if yaml_commit != anchor:
                baseline_frauds.append(JudgeFraud(
                    type="baseline_tampering",
                    severity="high",
                    description="baseline do YAML diverge da âncora Git registrada no início",
                    evidence=f"YAML={base_commit} | Git={anchor}",
                ))
            diff_base = anchor

    if diff_base:
        if not _base_commit_resolves(str(diff_base), cwd=cwd):
            blind_spots.append("baseline não resolve mais no histórico Git")
            diff_base = None
        elif not _base_commit_is_ancestor(str(diff_base), cwd=cwd):
            baseline_frauds.append(JudgeFraud(
                type="baseline_tampering",
                severity="high",
                description="baseline não é ancestral do HEAD atual",
                evidence=str(diff_base),
            ))
            diff_base = None

    diff = _run_git_diff(cwd=cwd, base_commit=diff_base)
    changed = _changed_files(cwd=cwd, base_commit=diff_base)
    claims = collect_claims(task_data)
    unverifiable = collect_unverifiable_claims(task_data)

    verify = task_data.get("verify", {})
    claimed_checks: list[str] = []
    if verify.get("ruff_clean"):
        claimed_checks.append("ruff")
    if verify.get("tests_pass"):
        claimed_checks.append("pytest")
    if verify.get("coverage_pass"):
        claimed_checks.append("coverage")

    verify_results: dict[str, VerifyResult] = {}
    re_ran: dict[str, bool] = {}

    if claimed_checks:
        results = run_all(
            ruff_paths=ruff_paths,
            test_paths=test_paths,
            ignore=ignore,
            cov_source=cov_source,
            gate=gate,
            cwd=cwd,
            config=config,
        )
        for key in claimed_checks:
            if key in results:
                verify_results[key] = results[key]
                re_ran[key] = results[key].ok

    frauds: list[JudgeFraud] = [*baseline_frauds]
    frauds.extend(hunt_weakened_checks(diff))
    frauds.extend(hunt_false_completion(task_data, verify_results))
    frauds.extend(hunt_scope_creep(task_data, changed))
    frauds.extend(hunt_unauthorized_action(task_data))
    frauds.extend(hunt_spec_betrayal(task_data))
    frauds.extend(hunt_debris(diff, changed))

    if not claimed_checks:
        blind_spots.append(
            "nenhuma verificação re-executada — o relatório não afirma nenhum "
            "check que o juiz saiba reproduzir"
        )
    unreadable = _unreadable_test_files(changed)
    if unreadable:
        blind_spots.append(
            f"{len(unreadable)} arquivo(s) de teste sem padrão de enfraquecimento "
            "para a linguagem: " + ", ".join(unreadable[:5])
        )
    ignored = _ignored_code_files(_ignored_files(cwd=cwd))
    if ignored:
        blind_spots.append(
            f"{len(ignored)} arquivo(s) ignorado(s) com aparência de código/teste "
            "não puderam ser comparados com o baseline: " + ", ".join(ignored[:5])
        )

    high = [f for f in frauds if f.severity == "high"]
    caveats: list[str] = []
    oversized = _oversized_untracked(untracked_files(cwd=cwd), cwd=cwd)
    if oversized:
        caveats.append(
            f"{len(oversized)} arquivo(s) untracked não inspecionado(s) por tamanho: "
            + ", ".join(oversized[:5])
        )
    if unverifiable:
        caveats.append(
            f"{len(unverifiable)} claim(s) aceita(s) sem verificação (não re-executáveis)"
        )
    if any(not ok for ok in re_ran.values()):
        failed = [k for k, v in re_ran.items() if not v]
        caveats.append(f"re-execução falhou: {', '.join(failed)}")
    if high:
        verdict = "REFUTED"
        caveats.append(f"{len(high)} fraude(s) de alta severidade")
    elif frauds:
        verdict = "VERIFIED WITH CAVEATS"
        caveats.append(f"{len(frauds)} fraude(s) de média/baixa severidade")
    elif blind_spots:
        # A mesma doutrina de fit.untracked_stats: "não consegui olhar" não
        # pode virar "está tudo bem". Sem isto, um projeto cujas verificações
        # o juiz não sabe rodar — qualquer um que não seja Python — recebia
        # VERIFIED limpo, sem uma ressalva sequer, tendo re-executado nada.
        verdict = "UNVERIFIABLE"
    else:
        verdict = "VERIFIED"

    return JudgeResult(
        verdict=verdict,
        claims=claims,
        unverifiable_claims=unverifiable,
        caveats=caveats,
        frauds=frauds,
        re_ran_checks=re_ran,
        blind_spots=blind_spots,
        details={
            "changed_files": len(changed),
            "diff_lines": len(diff.split("\n")),
        },
    )
