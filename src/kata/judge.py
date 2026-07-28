"""Adversarial verification (fable-judge) — caça fraudes em tarefas concluídas.

Inspirado no fable-judge do The Fable Method
(https://github.com/Sahir619/fable-method):

1. Collect claims — o que o relatório diz que foi feito
2. Establish ground truth — git diff contra o estado real
3. Re-run every claimed verification — executa de novo e compara
4. Hunt frauds — 6 categorias (weakened checks, false completion,
   scope creep, unauthorized action, spec betrayal, debris)
5. Deliver verdict — VERIFIED / VERIFIED WITH CAVEATS / REFUTED
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kata.verify import VerifyResult, _run, run_all

# ── regex patterns ────────────────────────────────────────────────────────

_WEAKENED_PATTERNS: list[tuple[str, str]] = [
    (r"^-.*assert\s+True\b", "assert True (sempre passa se True for literal)"),
    (r"^-.*assert\s+False\b", "assert False (sempre falha ou foi removido)"),
    (r"^\+#\s+.*(?:assert|def test|expect|self\.)", "teste virado em comentário"),
    (r"^\+\s*pass\s*$", "corpo de teste substituído por pass"),
    (r"^\+.*#\s*noqa", "noqa adicionado — pode esconder erro de lint"),
]

_DEBRIS_FILE_PATTERNS = [r"\.tmp$", r"\.bak$", r"scratch", r"temp\d*"]

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
        verdict: VERIFIED | VERIFIED WITH CAVEATS | REFUTED
        claims: Lista de claims extraídas do relatório da tarefa.
        caveats: Ressalvas sobre o resultado.
        frauds: Fraudes encontradas durante a verificação.
        re_ran_checks: Resultados da re-execução das verificações.
        details: Metadados extras.
    """

    verdict: str = "VERIFIED"
    claims: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    frauds: list[JudgeFraud] = field(default_factory=list)
    re_ran_checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


# ── claims ────────────────────────────────────────────────────────────────


def collect_claims(task_data: dict[str, Any]) -> list[str]:
    """Extrai claims explícitas do YAML da tarefa."""
    claims: list[str] = []
    verify = task_data.get("verify", {})
    if verify.get("ruff_clean"):
        claims.append("ruff check limpo (sem erros de lint)")
    if verify.get("tests_pass"):
        claims.append("todos os testes passam")
    if verify.get("coverage_pass"):
        claims.append(f"coverage ≥ gate ({verify.get('coverage_pct', '?')}%)")
    if verify.get("success_criteria_met"):
        claims.append("critério de sucesso satisfeito")

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


# ── git helpers ───────────────────────────────────────────────────────────


def _base_commit_resolves(base_commit: str, cwd: Path | None = None) -> bool:
    """Confirma que base_commit ainda existe no histórico (não foi rebaseado/podado)."""
    result = _run(["git", "cat-file", "-e", f"{base_commit}^{{commit}}"], cwd=cwd)
    return result.returncode == 0


def _run_git_diff(cwd: Path | None = None, base_commit: str | None = None) -> str:
    """Retorna o diff da tarefa.

    Se `base_commit` (o HEAD registrado quando a tarefa começou, na fase
    FIT) estiver disponível, usa `git diff <base_commit>` — cobre commits,
    staged e unstaged de uma vez, então continua funcionando depois que a
    tarefa é commitada (o caso normal de uma tarefa "concluída").

    Sem base_commit (tarefas antigas, ou geradas fora do ciclo FIT), cai
    no comportamento anterior: unstaged, com fallback para staged — que
    só enxerga mudanças ainda não commitadas.
    """
    if base_commit and _base_commit_resolves(base_commit, cwd=cwd):
        return _run(["git", "diff", base_commit], cwd=cwd).stdout

    result = _run(["git", "diff"], cwd=cwd)
    if not result.stdout.strip():
        result = _run(["git", "diff", "--cached"], cwd=cwd)
    return result.stdout


def _changed_files(cwd: Path | None = None, base_commit: str | None = None) -> list[str]:
    """Retorna a lista de arquivos alterados pela tarefa (mesma lógica de _run_git_diff)."""
    if base_commit and _base_commit_resolves(base_commit, cwd=cwd):
        result = _run(["git", "diff", "--name-only", base_commit], cwd=cwd)
        return [f for f in result.stdout.strip().split("\n") if f.strip()]

    result = _run(["git", "diff", "--name-only"], cwd=cwd)
    if not result.stdout.strip():
        result = _run(["git", "diff", "--cached", "--name-only"], cwd=cwd)
    return [f for f in result.stdout.strip().split("\n") if f.strip()]


# ── fraud hunters ─────────────────────────────────────────────────────────


def _is_test_file(filepath: str) -> bool:
    return filepath.startswith("tests/") or "/test_" in filepath or "_test." in filepath


def hunt_weakened_checks(diff: str) -> list[JudgeFraud]:
    """Caça 1: verificações enfraquecidas — asserts removidos/relaxados."""
    frauds: list[JudgeFraud] = []
    current_file = ""

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            parts = line.split()
            current_file = parts[3].replace("b/", "", 1) if len(parts) >= 4 else ""
        if not current_file or not _is_test_file(current_file):
            continue
        for pattern, desc in _WEAKENED_PATTERNS:
            if re.match(pattern, line):
                frauds.append(JudgeFraud(
                    type="weakened_checks",
                    severity="high",
                    description=f"{current_file}: {desc}",
                    evidence=line.strip(),
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
        for pat in _DEBRIS_FILE_PATTERNS:
            if re.search(pat, f, re.IGNORECASE):
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
    5. Entrega veredito
    """
    base_commit = task_data.get("base_commit")
    diff = _run_git_diff(cwd=cwd, base_commit=base_commit)
    changed = _changed_files(cwd=cwd, base_commit=base_commit)
    claims = collect_claims(task_data)

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

    high = [f for f in frauds if f.severity == "high"]
    caveats: list[str] = []
    if any(not ok for ok in re_ran.values()):
        failed = [k for k, v in re_ran.items() if not v]
        caveats.append(f"re-execução falhou: {', '.join(failed)}")
    if high:
        verdict = "REFUTED"
        caveats.append(f"{len(high)} fraude(s) de alta severidade")
    elif frauds:
        verdict = "VERIFIED WITH CAVEATS"
        caveats.append(f"{len(frauds)} fraude(s) de média/baixa severidade")
    else:
        verdict = "VERIFIED"

    return JudgeResult(
        verdict=verdict,
        claims=claims,
        caveats=caveats,
        frauds=frauds,
        re_ran_checks=re_ran,
        details={
            "changed_files": len(changed),
            "diff_lines": len(diff.split("\n")),
        },
    )
