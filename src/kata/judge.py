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

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kata.verify import VerifyResult, _run, is_inspectable, run_all, untracked_files

# ── regex patterns ────────────────────────────────────────────────────────

_WEAKENED_PATTERNS: list[tuple[str, str]] = [
    (r"^-.*assert\s+True\b", "assert True (sempre passa se True for literal)"),
    (r"^-.*assert\s+False\b", "assert False (sempre falha ou foi removido)"),
    (r"^\+#\s+.*(?:assert|def test|expect|self\.)", "teste virado em comentário"),
    (r"^\+\s*pass\s*$", "corpo de teste substituído por pass"),
    (r"^\+.*#\s*noqa", "noqa adicionado — pode esconder erro de lint"),
]

# Extensões cujos testes _WEAKENED_PATTERNS sabe ler. Os padrões acima são
# sintaxe Python (`assert`, `pass`, o supressor de lint): num teste .js/.go/.rs
# eles não casam nunca. Sem esta lista, "nenhuma fraude encontrada" viraria uma
# afirmação sobre código que o hunter jamais conseguiu ler.
_WEAKENED_PATTERN_EXTS = frozenset({".py"})

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
    (r"^\+.*#\s*TODO\b", "TODO deixado no código"),
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


def _base_commit_resolves(base_commit: str, cwd: Path | None = None) -> bool:
    """Confirma que base_commit ainda existe no histórico (não foi rebaseado/podado)."""
    result = _run(["git", "cat-file", "-e", f"{base_commit}^{{commit}}"], cwd=cwd)
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

    Sem base_commit (tarefas antigas, ou geradas fora do ciclo FIT), cai
    no comportamento anterior: unstaged, com fallback para staged — que
    só enxerga mudanças ainda não commitadas.

    Em ambos os casos, o conteúdo dos arquivos untracked é anexado como
    diff sintético: `git diff` nunca os mostra, e sem isso um arquivo novo
    ficaria invisível aos hunters.
    """
    if base_commit and _base_commit_resolves(base_commit, cwd=cwd):
        diff = _run(["git", "diff", base_commit], cwd=cwd).stdout
    else:
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
        result = _run(["git", "diff", "--name-only"], cwd=cwd)
        if not result.stdout.strip():
            result = _run(["git", "diff", "--cached", "--name-only"], cwd=cwd)

    tracked = [f for f in result.stdout.strip().split("\n") if f.strip()]
    seen = set(tracked)
    return tracked + [f for f in untracked_files(cwd=cwd) if f not in seen]


# ── fraud hunters ─────────────────────────────────────────────────────────


def _is_test_file(filepath: str) -> bool:
    return filepath.startswith("tests/") or "/test_" in filepath or "_test." in filepath


# Convenções de nome de teste em várias linguagens: test_x.py, x_test.go,
# x.test.js, x.spec.ts, x_spec.rb. Casa no basename e exige separador antes
# do token, senão "latest.py", "contest.py" e "attempt_parser.py" entram.
_TEST_BASENAME = re.compile(r"^(?:test|spec)[_.\-]|[_.\-](?:test|spec)s?\.", re.IGNORECASE)


def _unreadable_test_files(changed: list[str]) -> list[str]:
    """Testes que _WEAKENED_PATTERNS não tem como ler, por serem de outra linguagem.

    Existe para o juiz confessar, não para acusar: num repositório poliglota
    o ruff e o pytest podem passar e ser re-executados — desarmando o outro
    ponto cego — enquanto um teste .js do mesmo diff foi esvaziado sem que
    hunt_weakened_checks pudesse enxergar. "Nenhuma fraude" ali é ausência
    de leitura, não ausência de fraude.

    Reconhece teste pela convenção do nome, e não por morar em `tests/`:
    incluir todo arquivo do diretório marcaria `tests/fixtures/dados.json`
    como teste ilegível em todo projeto que tem fixture, e uma ressalva que
    aparece sempre é uma ressalva que ninguém lê. O preço é não flagrar
    `__tests__/index.js`, que não traz token nenhum no nome.
    """
    return [
        f
        for f in changed
        if _TEST_BASENAME.search(f.rsplit("/", 1)[-1])
        and Path(f).suffix.lower() not in _WEAKENED_PATTERN_EXTS
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


_TEST_DECLARATION = re.compile(r"^\+\s*(?:async\s+)?def\s+test\w*\s*\(")
_ONLY_PASS = re.compile(r"^\+\s*pass\s*$")
_SKIPPABLE = re.compile(r"^\+\s*(?:#.*)?$")


def _empty_test_bodies(added_lines: list[str]) -> list[str]:
    """Funções de teste cujo corpo inteiro é `pass`.

    Substitui, para arquivos novos, os padrões de _WEAKENED_PATTERNS — que
    pressupõem modificação ("o corpo virou pass" exige que houvesse corpo).
    Num arquivo novo o que é de fato suspeito é uma função de teste que não
    faz nada. Discrimina pelo que importa: `pass` como corpo de um `def
    test_*` é fraude; `pass` num stub de classe ou num `except ...:` é
    código honesto e não cai aqui.
    """
    achados: list[str] = []
    for i, line in enumerate(added_lines):
        if not _TEST_DECLARATION.match(line):
            continue
        for seguinte in added_lines[i + 1:]:
            if _SKIPPABLE.match(seguinte):
                continue
            if _ONLY_PASS.match(seguinte):
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
        if is_new_file:
            if line.startswith("+"):
                new_test_bodies.setdefault(current_file, []).append(line)
            continue
        for pattern, desc in _WEAKENED_PATTERNS:
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
        for vazio in _empty_test_bodies(added):
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
) -> JudgeResult:
    """Executa verificação adversarial completa em uma tarefa.

    1. Coleta claims do YAML da tarefa
    2. Estabelece verdade material (git diff)
    3. Re-executa verificações que o relatório afirma que passaram
    4. Caça fraudes em 6 categorias
    5. Registra o que não conseguiu observar (pontos cegos)
    6. Entrega veredito
    """
    base_commit = task_data.get("base_commit")
    diff = _run_git_diff(cwd=cwd, base_commit=base_commit)
    changed = _changed_files(cwd=cwd, base_commit=base_commit)
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
        )
        for key in claimed_checks:
            if key in results:
                verify_results[key] = results[key]
                re_ran[key] = results[key].ok

    frauds: list[JudgeFraud] = []
    frauds.extend(hunt_weakened_checks(diff))
    frauds.extend(hunt_false_completion(task_data, verify_results))
    frauds.extend(hunt_scope_creep(task_data, changed))
    frauds.extend(hunt_unauthorized_action(task_data))
    frauds.extend(hunt_spec_betrayal(task_data))
    frauds.extend(hunt_debris(diff, changed))

    # Pontos cegos: o que o juiz não teve como observar. Separados das
    # caveats porque governam o veredito, e das fraudes porque não são
    # acusação — não observar não é evidência de fraude nem de honestidade.
    blind_spots: list[str] = []
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
