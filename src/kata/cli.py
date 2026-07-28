"""Kata CLI — Karpathy Development Cycle + Fable Method.

Modos:
  --init <task>     Cria .kata/<task>.yaml com template
  (sem args)        Ciclo: FIT, THINK, SIMPLIFY, INTENT, SURGICAL, VERIFY, ARTIFACT, REPORT
  --check-only      Roda só o passo 4 (lint + test + coverage)
  --plan            Modo planejamento (FIT → THINK, para)
  --task <name>     Retoma tarefa específica
  --judge           Modo adversarial verification (caça fraudes em tarefa concluída)
  --task <name> --judge     Verifica tarefa específica adversarialmente
  --report          Gera relatório outcome-first de tarefa concluída (usa --task ou branch)

Port do `scripts/karpathy_cycle.py` do mushin, usando `.kata/` e
lógica de verificação modularizada em `kata.verify` e `kata.fit`.

Inspirado no Karpathy Development Cycle e no The Fable Method
(https://github.com/Sahir619/fable-method).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from kata import __version__
from kata.fit import diff_stats, is_trivial
from kata.judge import JudgeResult, judge_task
from kata.verify import VerifyResult, run_all, search_pattern

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# ── helpers ──────────────────────────────────────────────────────────────


def _cwd() -> Path:
    """Retorna o diretório de trabalho atual."""
    return Path.cwd()


def _kata_dir() -> Path:
    """Retorna o diretório .kata/ no CWD."""
    return _cwd() / ".kata"


def _serialize(data: dict[str, Any]) -> str:
    if _HAS_YAML:
        return yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _deserialize(text: str) -> dict[str, Any]:
    if _HAS_YAML:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def _ext() -> str:
    return ".yaml" if _HAS_YAML else ".json"


def _validate_task_name(task: str) -> None:
    """Impede path traversal via nome de tarefa (--task/--init/--judge/--report).

    Sem isso, um nome como '../../etc/foo' escreve/lê fora de .kata/, já que
    _task_path só concatena o nome ao diretório sem checar separadores.
    """
    if not task or "/" in task or "\\" in task or ".." in task:
        print(f"⚠  Nome de tarefa inválido: '{task}'. Não pode conter '/', '\\' ou '..'.")
        sys.exit(1)


def _task_path(task: str) -> Path:
    _validate_task_name(task)
    return _kata_dir() / f"{task}{_ext()}"


def _detect_task_from_branch() -> str | None:
    """Detecta o nome da tarefa a partir do branch git atual."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=_cwd(),
        )
        branch = result.stdout.strip()
        if branch and branch != "HEAD":
            return branch.replace("/", "-").replace("_", "-")
    except subprocess.CalledProcessError:
        pass
    return None


def _pick_task() -> str:
    """Escolhe a tarefa interativamente (branch, menu existente, ou nova)."""
    if not sys.stdin.isatty():
        return "untitled"
    branch_task = _detect_task_from_branch()
    existing = sorted(
        p.stem for p in _kata_dir().glob(f"*{_ext()}") if p.stem != ".gitkeep"
    )
    if branch_task and branch_task in existing:
        return branch_task
    if existing:
        print("Tarefas existentes em .kata/:")
        for i, name in enumerate(existing, 1):
            print(f"  {i}. {name}")
        print(f"  {len(existing) + 1}. [Nova tarefa]")
        choice = input("\nEscolha (número ou nome): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(existing):
                return existing[idx]
        elif choice in existing:
            return choice
    name = input("Nome da tarefa: ").strip().replace(" ", "-") or "untitled"
    if "/" in name or "\\" in name or ".." in name:
        print("⚠  Nome de tarefa inválido. Usando 'untitled'")
        return "untitled"
    return name


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Executa comando capturando saída, com defaults sobrescreíveis pelo caller.

    Defaults (capture_output, text, cwd) podem ser sobrescritos via kwargs
    sem causar colisão de argumentos.
    """
    defaults: dict[str, Any] = {"capture_output": True, "text": True, "cwd": _cwd()}
    defaults.update(kwargs)
    return subprocess.run(cmd, **defaults)


def _confirm(prompt: str, default: bool = True) -> bool:
    if not sys.stdin.isatty():
        return default
    opts = " [S/n]" if default else " [s/N]"
    try:
        answer = input(f"{prompt}{opts}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not answer:
        return default
    return answer in ("s", "sim", "y", "yes")


def _print_header(text: str) -> None:
    width = 60
    print()
    print("┌" + "─" * (width - 2) + "┐")
    for line in text.split("\n"):
        print(f"│ {line:<{width - 3}}│")
    print("└" + "─" * (width - 2) + "┘")
    print()


def _print_judge_verdict(result: JudgeResult) -> None:
    """Imprime o veredito do juiz adversarial."""
    verdict_icon = {"VERIFIED": "✅", "VERIFIED WITH CAVEATS": "⚠️", "REFUTED": "❌"}
    icon = verdict_icon.get(result.verdict, "❓")
    print(f"\n{icon}  VEREDITO: {result.verdict}")
    print()

    if result.claims:
        print("  Claims verificadas:")
        for c in result.claims:
            print(f"    • {c}")
        print()

    if result.frauds:
        print("  Fraudes encontradas:")
        for f in result.frauds:
            sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            print(f"    {sev_icon.get(f.severity, '⚪')} [{f.severity}] {f.type}")
            print(f"       {f.description}")
            if f.evidence:
                print(f"       → {f.evidence}")
        print()

    if result.caveats:
        print("  Ressalvas:")
        for c in result.caveats:
            print(f"    • {c}")
        print()

    if result.re_ran_checks:
        print("  Re-execução:")
        for check, ok in result.re_ran_checks.items():
            status = "✅" if ok else "❌"
            print(f"    {status} {check}")
        print()

    print("─" * 58)
    print(f"\n{icon}  KATA JUDGE — {result.verdict}")
    print()


# ── step implementations ────────────────────────────────────────────────


def _capture_base_commit(data: dict[str, Any]) -> dict[str, Any]:
    """Registra o HEAD do git no início da tarefa, uma única vez.

    O JUDGE usa esse commit como ponto de comparação. Sem ele, o JUDGE só
    enxerga o diff não commitado (unstaged/staged) e fica cego assim que
    a tarefa é commitada — exatamente o estado de uma tarefa "concluída",
    que é o caso que o JUDGE existe para verificar.
    """
    if data.get("base_commit"):
        return data
    result = _run(["git", "rev-parse", "HEAD"])
    sha = result.stdout.strip()
    if result.returncode == 0 and sha:
        data["base_commit"] = sha
    return data


def _step_fit(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 0: FIT — triviality gate + classificação da tarefa antes do THINK.

    Inspirado no fit gate do fable-method (think → act → prove → grow)
    e no Karpathy Development Cycle.
    """
    fit = data.get("fit", {})
    if fit.get("answered"):
        print("(fit gate já respondido)")
        return data

    if not sys.stdin.isatty():
        print("(modo não-interativo — assumindo code-loop)")
        data["fit"] = {
            "trivial": False,
            "route": "code-loop",
            "reason": "non-interactive mode",
        }
        return data

    _print_header("0. FIT — Classificação da tarefa")

    files, lines = diff_stats()
    trivial = is_trivial(files, lines)

    print(f"  diff: {len(files)} arquivo(s), {lines} linha(s) alteradas")
    if trivial:
        print("  ↳ tarefa parece trivial (<=1 arquivo, <10 linhas)")
    else:
        print("  ↳ tarefa não-trivial")

    print()
    print("  Rotas disponíveis:")
    print("    [1] code-loop   — ciclo completo (THINK → SIMPLIFY → SURGICAL → VERIFY)")
    print("    [2] plan-first  — só planejamento (para e entrega um plano)")
    print("    [3] question    — só diagnóstico, sem alterar código")
    print("    [4] research    — precisa pesquisar antes de agir")
    print("    [5] inference   — baseado só em inferência (baixa confiança)")

    choice = input("\n  Rota escolhida [1]: ").strip() or "1"
    route_map = {
        "1": "code-loop",
        "2": "plan-first",
        "3": "question",
        "4": "research",
        "5": "inference",
    }
    route = route_map.get(choice, "code-loop")
    reason = input("  Justificativa breve (opcional): ").strip()

    data["fit"] = {
        "trivial": trivial,
        "route": route,
        "reason": reason or f"Rota {choice} escolhida pelo usuário",
    }
    return data


def _step_think(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 1: THINK — declarar assumptions antes de codar.

    O parâmetro `task` é mantido por simetria com as demais fases e para
    identificação no YAML, mas não é usado na lógica desta fase.
    """
    _print_header("1. THINK — Antes de codificar, declare suas assumptions")
    think = data.get("think", {})
    if think.get("answered"):
        print("(já respondido — recarregue para reabrir)")
        return data

    if not sys.stdin.isatty():
        print("(modo não-interativo — pulando THINK)")
        data["think"] = {
            "problem": "",
            "assumptions": [],
            "alternatives": [],
            "unknowns": "",
            "answered": True,
        }
        return data

    print("Pergunte-se:")
    problem = input("  Qual o problema exato que estou resolvendo? ").strip()
    assumptions_raw = input("  Quais assumptions estou fazendo? (separadas por ;) ").strip()
    alternatives_raw = input("  Quais alternativas considerei? (separadas por ;) ").strip()
    unknowns = input("  O que NÃO sei? (preciso perguntar antes?) ").strip()

    data["think"] = {
        "problem": problem,
        "assumptions": [a.strip() for a in assumptions_raw.split(";") if a.strip()],
        "alternatives": [a.strip() for a in alternatives_raw.split(";") if a.strip()],
        "unknowns": unknowns,
        "answered": True,
    }
    data["status"] = "think-complete"
    return data


def _step_simplify(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 2: SIMPLIFY — o código é mínimo?

    O parâmetro `task` é mantido por simetria com as demais fases e para
    identificação no YAML, mas não é usado na lógica desta fase.
    """
    _print_header("2. SIMPLIFY — O código é mínimo?")

    if not sys.stdin.isatty():
        print("(modo não-interativo — pulando SIMPLIFY)")
        data["simplify"] = {
            "minimum_code": True,
            "no_single_use_abstractions": True,
            "no_speculative_config": True,
        }
        return data

    # Mostra diff stat
    result = _run(["git", "diff", "--stat"])
    if result.stdout.strip():
        print("git diff --stat:")
        print(result.stdout)
    else:
        result = _run(["git", "diff", "--cached", "--stat"])
        if result.stdout.strip():
            print("git diff --cached --stat (staged):")
            print(result.stdout)
        else:
            print("(nenhuma alteração detectada — prossiga mesmo assim)")

    simplify = data.get("simplify", {})
    simplify["minimum_code"] = _confirm("  O código mínimo resolve o problema?")
    simplify["no_single_use_abstractions"] = _confirm(
        "  Código livre de abstrações para uso único?", default=True
    )
    simplify["no_speculative_config"] = _confirm(
        "  Código livre de configurabilidade não solicitada?", default=True
    )
    notes = input("  Observações (opcional): ").strip()
    if notes:
        simplify["notes"] = notes
    data["simplify"] = simplify
    return data


def _step_intent(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 2.5: INTENT — verificar intenção antes de mudar comportamento.

    Inspirado no intent gate do fable-method: antes de qualquer mudança
    de comportamento, registrar o que o código faz, o que o teste espera,
    e o que a especificação diz.
    """
    intent = data.get("intent", {})
    if intent.get("answered"):
        print("(intent gate já respondido)")
        return data

    if not sys.stdin.isatty():
        print("(modo não-interativo — assumindo intenção alinhada)")
        data["intent"] = {
            "code_does": "",
            "check_expects": "",
            "spec_says": "",
            "all_agree": True,
            "answered": True,
        }
        return data

    _print_header("2.5 INTENT — Antes de mudar, verifique a intenção")

    print("  Se esta tarefa muda comportamento, responda:")
    code_does = input("  O que o código FAZ hoje? ").strip()
    check_expects = input("  O que o teste/check ESPERA? ").strip()
    spec_says = input("  O que a especificação/README DIZ? ").strip()

    all_agree = _confirm("  Código, teste e especificação concordam?", default=True)
    if not all_agree:
        print("  ⚠  Conflito detectado! A ordem de autoridade é:")
        print("     declaração do usuário > spec > testes > código")
        resolve = input("  Como resolver o conflito? ").strip()
    else:
        resolve = ""

    data["intent"] = {
        "code_does": code_does,
        "check_expects": check_expects,
        "spec_says": spec_says,
        "all_agree": all_agree,
        "conflict_resolution": resolve,
        "answered": True,
    }
    return data


def _step_surgical(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 3: SURGICAL — cada linha toca só o necessário.

    O parâmetro `task` é mantido por simetria com as demais fases e para
    identificação no YAML, mas não é usado na lógica desta fase.
    """
    _print_header("3. SURGICAL — Cada linha toca só o necessário")

    if not sys.stdin.isatty():
        print("(modo não-interativo — pulando SURGICAL)")
        data["surgical"] = {"files": [], "removed_imports_clean": True}
        return data

    # Lista arquivos alterados (incluindo untracked)
    result = _run(["git", "diff", "--name-only"])
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    if not files:
        result = _run(["git", "diff", "--cached", "--name-only"])
        files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    if not files:
        result = _run(["git", "ls-files", "--others", "--exclude-standard"])
        files = [f for f in result.stdout.strip().split("\n") if f.strip()]

    surgical = data.get("surgical", {})
    file_checks: list[dict[str, Any]] = []

    if files:
        print("Arquivos alterados:")
        for f in files:
            necessary = _confirm(f"  {f} — necessário para esta tarefa?", default=True)
            file_checks.append({"path": f, "necessary": necessary})
    else:
        print("(nenhum arquivo alterado detectado)")

    surgical["files"] = file_checks
    surgical["removed_imports_clean"] = _confirm(
        "  Imports removidos são só os que sua mudança tornou inúteis?"
    )
    data["surgical"] = surgical
    return data


def _step_verify(
    task: str,
    data: dict[str, Any],
    ruff_paths: list[str] | None = None,
    test_paths: list[str] | None = None,
    ignore: list[str] | None = None,
    cov_source: str = "src",
    gate: float = 70.0,
) -> dict[str, Any]:
    """Fase 4: GOAL-DRIVEN — verificação de qualidade (ruff + pytest + coverage)."""
    _print_header("4. GOAL-DRIVEN — Verificação de qualidade")
    verify: dict[str, Any] = {}
    all_ok = True

    results = run_all(
        ruff_paths=ruff_paths,
        test_paths=test_paths,
        ignore=ignore,
        cov_source=cov_source,
        gate=gate,
    )

    # ── ruff ──
    ruff_res: VerifyResult = results["ruff"]
    print(f"▶ ruff check {' '.join(ruff_paths) if ruff_paths else 'src/ tests/'}")
    verify["ruff_clean"] = ruff_res.ok
    if ruff_res.ok:
        print("  ✅ limpo")
    else:
        all_ok = False
        print("  ❌ falhou — saída:")
        for line in ruff_res.output.split("\n"):
            print(f"     {line}")

    # ── pytest ──
    pytest_res: VerifyResult = results["pytest"]
    print(f"\n▶ pytest {' '.join(test_paths) if test_paths else 'tests/'}")
    verify["tests_pass"] = pytest_res.ok
    if pytest_res.ok:
        print("  ✅ passou")
    else:
        all_ok = False
        print("  ❌ falhou — últimas linhas:")
        for line in pytest_res.output.split("\n"):
            print(f"     {line}")

    # ── coverage ──
    cov_res: VerifyResult = results["coverage"]
    cov_pct = cov_res.details.get("coverage_pct", 0.0)
    print(f"\n▶ coverage (gate ≥ {gate:.0f}%)")
    verify["coverage_pct"] = cov_pct
    verify["coverage_pass"] = cov_res.ok
    if cov_res.ok:
        print(f"  ✅ passou ({cov_pct:.1f}%)")
    else:
        all_ok = False
        print(f"  ❌ falhou ({cov_pct:.1f}% — gate: {gate:.0f}%)")
        for line in cov_res.output.split("\n"):
            print(f"     {line}")

    # ── success criteria ──
    print("\n▶ Critério de sucesso da tarefa")
    if task == "check-only":
        success_met = True
        print("  (modo check-only — assumido satisfeito)")
    else:
        success_met = _confirm("  O critério de sucesso da tarefa está satisfeito?")
    verify["success_criteria_met"] = success_met
    if not success_met:
        all_ok = False

    data["verify"] = verify
    data["status"] = "approved" if all_ok else "rejected"

    # Resumo
    print()
    if all_ok:
        print("┌" + "─" * 58 + "┐")
        print("│  ✅  KATA CYCLE — APROVADO                             │")
        print("└" + "─" * 58 + "┘")
    else:
        print("┌" + "─" * 58 + "┐")
        print("│  ❌  KATA CYCLE — REJEITADO                            │")
        print("│     Corrija os problemas e rode novamente.              │")
        print("└" + "─" * 58 + "┘")

    return data


def _step_twin(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase pós-VERIFY: TWIN CHECK — busca automática de padrão recorrente.

    Inspirado no twin check do fable-method: quando um defeito é corrigido,
    busca o mesmo padrão no projeto inteiro para evitar recorrências.
    """
    if data.get("status") != "approved":
        return data

    twins = data.get("twins", {})
    if twins.get("searched"):
        return data

    intent = data.get("intent", {})
    defect_fixed = (
        not intent.get("all_agree", True)
        or _confirm("  Um defeito foi corrigido? Deseja buscar padrão similar?", default=False)
    )

    if not defect_fixed:
        data["twins"] = {"searched": False, "pattern": "", "result": ""}
        return data

    if not sys.stdin.isatty():
        data["twins"] = {"searched": False, "pattern": "", "result": ""}
        return data

    _print_header("TWIN CHECK — Busca de padrão recorrente")

    pattern = input("  Padrão a buscar (regex): ").strip()
    if not pattern:
        data["twins"] = {"searched": False, "pattern": "", "result": ""}
        return data

    print(f"\n  Buscando '{pattern}' no projeto...")
    search_result = search_pattern(pattern, cwd=_cwd())

    if search_result.matches:
        print(f"\n  ✅ Encontrado em {search_result.total_files} arquivo(s):")
        for match in search_result.matches[:20]:
            print(f"     {match.file}:{match.line}  {match.content[:80]}")
        if len(search_result.matches) > 20:
            print(f"     ... e mais {len(search_result.matches) - 20} ocorrência(s)")
    else:
        print("  Nenhuma ocorrência encontrada.")

    fix_others = False
    if search_result.matches:
        fix_others = _confirm("  Corrigir as demais ocorrências agora?", default=False)

    result_str = (
        f"{search_result.total_files} arquivo(s), "
        f"{len(search_result.matches)} ocorrência(s)"
    )
    data["twins"] = {
        "pattern": pattern,
        "result": result_str,
        "searched": True,
        "matches_count": len(search_result.matches),
        "files_count": search_result.total_files,
        "fix_applied": fix_others,
    }
    return data


def _has_deploy_docs() -> bool:
    """Detecta se README menciona passos de deploy."""
    readme = _cwd() / "README.md"
    if not readme.exists():
        return False
    deploy_keywords = ["deploy", "docker", "push", "publish", "rollout", "release"]
    try:
        text = readme.read_text(encoding="utf-8").lower()
        return any(kw in text for kw in deploy_keywords)
    except Exception:
        return False


def _detect_auth_owed(data: dict[str, Any]) -> bool:
    """Detecta se AUTH line é devida (ação irreversível realizada).

    Não há como inferir de forma confiável, só a partir do estado local do
    git, que uma ação irreversível (push, deploy, publish) foi tomada:
    commits locais não enviados ao remote são o estado normal e reversível
    de qualquer branch em progresso, não evidência de uma ação irreversível.
    Por isso a detecção depende de quem executou a ação (o agente ou o
    usuário) registrar `auth.action_taken` explicitamente.
    """
    auth = data.get("auth", {})
    return bool(auth.get("action_taken"))


def _detect_pending_owed(data: dict[str, Any]) -> bool:
    """Detecta se PENDING line é devida (follow-up prescrito não tomado)."""
    # Heurística 1: README tem instruções de deploy e tarefa está aprovada
    if data.get("status") == "approved" and _has_deploy_docs():
        return True
    # Heurística 2: dados de pending já existentes
    pending = data.get("pending", {})
    if pending.get("action"):
        return True
    return False


def _detect_twins_owed(data: dict[str, Any]) -> bool:
    """Detecta se TWINS line é devida (defeito corrigido, padrão pode se repetir)."""
    # Heurística 1: intent teve conflito (spec betrayal potencial)
    intent = data.get("intent", {})
    if intent.get("answered") and not intent.get("all_agree"):
        return True
    # Heurística 2: verify passou (defeito possivelmente corrigido)
    verify = data.get("verify", {})
    if verify.get("tests_pass") and verify.get("coverage_pass"):
        return True
    # Heurística 3: dados de twins já existentes
    twins = data.get("twins", {})
    if twins.get("pattern"):
        return True
    return False


def _step_artifact(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 4.5: ARTIFACT — verificar linhas devidas no relatório.

    Inspirado no artifact gate do fable-method: antes de finalizar, verificar
    se INTENT, AUTH, PENDING e TWINS estão presentes quando devidos.
    """
    _print_header("4.5 ARTIFACT — Verificação de linhas devidas")

    intent = data.get("intent", {})
    verify = data.get("verify", {})

    # Intent: devida se verify foi executado com mudança de comportamento
    intent_owed = verify.get("tests_pass") is not None
    intent_present = bool(intent.get("answered")) and intent.get("code_does", "") != ""

    # AUTH: devida se ação irreversível foi tomada
    auth_owed = _detect_auth_owed(data)
    auth_present = bool(data.get("auth", {}).get("authorized"))

    # PENDING: devida se docs prescrevem follow-up e não foi tomado
    pending_owed = _detect_pending_owed(data)
    pending_present = bool(data.get("pending", {}).get("documented"))

    # TWINS: devida se defeito foi corrigido
    twins_owed = _detect_twins_owed(data)
    twins_present = bool(data.get("twins", {}).get("searched"))

    checks: dict[str, Any] = {
        "intent_owed": intent_owed,
        "intent_present": intent_present,
        "auth_owed": auth_owed,
        "auth_present": auth_present,
        "pending_owed": pending_owed,
        "pending_present": pending_present,
        "twins_owed": twins_owed,
        "twins_present": twins_present,
    }

    missing = []
    if intent_owed and not intent_present:
        missing.append("INTENT: código/teste/spec não documentados")
    if auth_owed and not auth_present:
        missing.append("AUTH: ação externa sem autorização documentada")
    if pending_owed and not pending_present:
        missing.append("PENDING: follow-up não documentado")
    if twins_owed and not twins_present:
        missing.append("TWINS: busca de padrão recorrente não realizada")

    if missing:
        print("  ⚠  Linhas devidas ausentes:")
        for msg in missing:
            print(f"     • {msg}")
        if sys.stdin.isatty():
            print()
            for msg in missing:
                if msg.startswith("AUTH"):
                    action = input("  Ação realizada: ").strip()
                    auth_line = input("  Citação exata da autorização: ").strip()
                    data["auth"] = {
                        "action_taken": True, "authorized": True,
                        "action": action, "quote": auth_line,
                    }
                elif msg.startswith("PENDING"):
                    action = input("  Ação pendente: ").strip()
                    data["pending"] = {"action": action, "documented": True}
                elif msg.startswith("TWINS"):
                    pattern = input("  Padrão buscado: ").strip()
                    result = input("  Resultado: ").strip()
                    data["twins"] = {"pattern": pattern, "result": result, "searched": True}
                elif msg.startswith("INTENT"):
                    code = input("  O que o código FAZ hoje? ").strip()
                    check = input("  O que o teste/check ESPERA? ").strip()
                    spec = input("  O que a especificação DIZ? ").strip()
                    data["intent"] = {
                        "code_does": code, "check_expects": check,
                        "spec_says": spec, "all_agree": True, "answered": True,
                    }
    else:
        print("  ✅ Todas as linhas devidas estão presentes")

    data["artifact"] = checks
    return data


def _detect_scratch_files() -> list[str]:
    """Detecta arquivos temporários/de lixo no diff."""
    diff = _run(["git", "diff", "--name-only"])
    if not diff.stdout.strip():
        diff = _run(["git", "diff", "--cached", "--name-only"])
    if not diff.stdout.strip():
        return []
    scratch_patterns = [".tmp", ".bak", "scratch/", "temp"]
    files = diff.stdout.strip().split("\n")
    return [f for f in files if any(p in f for p in scratch_patterns)]


def _format_intent_line(intent: dict[str, Any]) -> str:
    """Formata a linha INTENT no formato fable."""
    code = intent.get("code_does", "")
    check = intent.get("check_expects", "")
    spec = intent.get("spec_says", "")
    if code or check or spec:
        return f"INTENT: code does {code}; check expects {check}; spec says {spec}"
    return ""


def _format_auth_line(auth: dict[str, Any]) -> str:
    """Formata a linha AUTH no formato fable."""
    if auth.get("authorized") and auth.get("quote"):
        return f'AUTH: user said "{auth["quote"]}"'
    return ""


def _format_pending_line(pending: dict[str, Any]) -> str:
    """Formata a linha PENDING no formato fable."""
    if pending.get("documented") and pending.get("action"):
        return f"PENDING: {pending['action']} - awaiting your authorization"
    return ""


def _format_twins_line(twins: dict[str, Any]) -> str:
    """Formata a linha TWINS no formato fable."""
    if twins.get("searched") and twins.get("pattern"):
        found = twins.get("result", "none")
        files = twins.get("files_count", 0)
        matches = twins.get("matches_count", 0)
        detail = f" ({files} file(s), {matches} occurrence(s))" if files else ""
        return f"TWINS: searched {twins['pattern']} - found {found}{detail}"
    return ""


def _step_report(task: str, data: dict[str, Any]) -> None:
    """Fase 5: REPORT — relatório outcome-first.

    Inspirado no Step 6 do fable-method: primeira frase = resultado,
    detalhes depois, sem números de passo, com linhas INTENT/AUTH/PENDING/TWINS.
    """
    status = data.get("status", "unknown")
    icon = "✅" if status == "approved" else "❌"
    verify = data.get("verify", {})

    # Outcome first
    print()
    if status == "approved":
        print(f"{icon}  KATA CYCLE — APROVADO: critério de sucesso satisfeito")
    elif status == "rejected":
        print(f"{icon}  KATA CYCLE — REJEITADO: verifique os problemas abaixo")
    else:
        print(f"  ⏳  Tarefa '{task}' está em andamento (status: {status})")
        return

    # O que foi feito
    intent = data.get("intent", {})
    surgical = data.get("surgical", {})
    think = data.get("think", {})

    print()
    if think.get("problem"):
        print(f"  Problema: {think['problem']}")

    files = surgical.get("files", [])
    if files:
        needed = [f.get("path") for f in files if f.get("necessary")]
        if needed:
            print(f"  Arquivos alterados: {', '.join(needed)}")

    # INTENT line
    intent_line = _format_intent_line(intent)
    if intent_line:
        print(f"  {intent_line}")

    # Verificações
    print()
    checks = []
    ruff = verify.get("ruff_clean")
    if ruff is not None:
        checks.append(f"  {'✅' if ruff else '❌'} ruff check {'limpo' if ruff else 'com erros'}")
    tests = verify.get("tests_pass")
    if tests is not None:
        checks.append(f"  {'✅' if tests else '❌'} pytest {'passou' if tests else 'falhou'}")
    cov = verify.get("coverage_pass")
    cov_pct = verify.get("coverage_pct", 0)
    if cov is not None:
        label = f"  {'✅' if cov else '❌'} coverage {cov_pct:.1f}% {'≥' if cov else '<'} gate"
        checks.append(label)
    success = verify.get("success_criteria_met")
    if success is not None:
        checks.append(f"  {'✅' if success else '❌'} critério de sucesso satisfeito")
    if checks:
        print("  Verificações:")
        for c in checks:
            print(c)

    # Caveats
    caveats: list[str] = []
    if status == "rejected":
        caveats.append("Ciclo rejeitado — problemas de qualidade pendentes")
    scratch = _detect_scratch_files()
    if scratch:
        caveats.append(f"Arquivos temporários detectados: {', '.join(scratch)}")
    artifact = data.get("artifact", {})
    if artifact.get("intent_owed") and not artifact.get("intent_present"):
        caveats.append("INTENT não documentada — comportamento alterado sem registro de intenção")
    if artifact.get("auth_owed") and not artifact.get("auth_present"):
        caveats.append("AÇÃO EXTERNA sem autorização documentada (AUTH ausente)")

    if caveats:
        print()
        print("  Caveats:")
        for c in caveats:
            print(f"    ⚠ {c}")

    # Forced artifact lines
    lines: list[str] = []
    auth_line = _format_auth_line(data.get("auth", {}))
    if auth_line:
        lines.append(auth_line)
    pending_line = _format_pending_line(data.get("pending", {}))
    if pending_line:
        lines.append(pending_line)
    twins_line = _format_twins_line(data.get("twins", {}))
    if twins_line:
        lines.append(twins_line)
    if lines:
        print()
        for line in lines:
            print(f"  {line}")

    print()
    print("─" * 58)


# ── init ────────────────────────────────────────────────────────────────


def _init_task(task: str) -> None:
    """Cria template .kata/<task>.yaml para uma nova tarefa."""
    path = _task_path(task)
    if path.exists():
        print(f"⚠  {path} já existe. Use o modo interativo para continuar.")
        return

    template: dict[str, Any] = {
        "task": task,
        "status": "draft",
        "fit": {
            "trivial": False,
            "route": "code-loop",
            "reason": "",
        },
        "think": {
            "problem": "",
            "assumptions": [],
            "alternatives": [],
            "unknowns": "",
            "answered": False,
        },
        "simplify": {
            "minimum_code": True,
            "no_single_use_abstractions": True,
            "no_speculative_config": True,
        },
        "intent": {
            "code_does": "",
            "check_expects": "",
            "spec_says": "",
            "all_agree": True,
            "answered": False,
        },
        "surgical": {
            "files": [],
            "removed_imports_clean": True,
        },
        "verify": {
            "ruff_clean": None,
            "tests_pass": None,
            "coverage_pct": None,
            "coverage_pass": None,
            "success_criteria_met": None,
        },
        "auth": {"action_taken": False, "authorized": False},
        "pending": {"action": "", "documented": False},
        "twins": {
            "searched": False, "pattern": "", "result": "",
            "matches_count": 0, "files_count": 0, "fix_applied": False,
        },
    }
    template = _capture_base_commit(template)
    path.write_text(_serialize(template), encoding="utf-8")
    print(f"✅  {path} criado. Preencha as respostas com o modo interativo.")


# ── main ────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point do CLI kata."""
    parser = argparse.ArgumentParser(
        description="Kata (型) — Karpathy Development Cycle",
    )
    parser.add_argument("--version", action="version", version=f"kata {__version__}")
    parser.add_argument("--init", metavar="TASK", help="Cria checklist para nova tarefa")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Roda só o passo 4 (lint + test + coverage)",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Modo planejamento: executa THINK e para (não modifica código)",
    )
    parser.add_argument(
        "--task",
        metavar="NAME",
        help="Retoma tarefa específica existente",
    )
    parser.add_argument(
        "--ruff-paths",
        nargs="*",
        default=None,
        help="Caminhos para ruff check (default: src/ tests/)",
    )
    parser.add_argument(
        "--test-paths",
        nargs="*",
        default=None,
        help="Caminhos para pytest (default: tests/)",
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=None,
        help="Caminhos para ignorar no pytest (--ignore)",
    )
    parser.add_argument(
        "--cov-source",
        default="src",
        help="Pacote fonte para coverage (default: src)",
    )
    parser.add_argument(
        "--gate",
        type=float,
        default=70.0,
        help="Gate mínimo de coverage, em %% (default: %(default)s)",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Modo adversarial verification — re-executa verificações e caça fraudes",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Gera relatório outcome-first de tarefa concluída",
    )
    args = parser.parse_args()

    if args.plan and args.check_only:
        parser.error("--plan e --check-only são mutuamente exclusivos")
    if args.judge and (args.plan or args.check_only):
        parser.error("--judge é mutuamente exclusivo com --plan e --check-only")
    if args.report and args.judge:
        parser.error("--report e --judge são mutuamente exclusivos")
    if args.report and (args.plan or args.check_only):
        parser.error("--report é mutuamente exclusivo com --plan e --check-only")

    if args.plan and args.task:
        # --plan e --task: carrega tarefa existente, executa só think
        pass

    _kata_dir().mkdir(parents=True, exist_ok=True)

    # Modo --init
    if args.init:
        _init_task(args.init)
        return

    # Modo --report (outcome-first)
    if args.report:
        task = args.task or _pick_task()
        path = _task_path(task)
        if not path.exists():
            print(f"⚠  {path} não encontrado. Execute o ciclo primeiro.")
            sys.exit(1)
        data = _deserialize(path.read_text(encoding="utf-8"))
        _step_report(task, data)
        sys.exit(0 if data.get("status") == "approved" else 1)

    # Modo --judge (adversarial verification)
    if args.judge:
        task = args.task or _pick_task()
        path = _task_path(task)
        if not path.exists():
            print(f"⚠  {path} não encontrado. Execute o ciclo primeiro.")
            sys.exit(1)
        data = _deserialize(path.read_text(encoding="utf-8"))
        _print_header(f"JUDGE — Verificação adversarial de '{task}'")
        result = judge_task(
            data,
            ruff_paths=args.ruff_paths,
            test_paths=args.test_paths,
            ignore=args.ignore,
            cov_source=args.cov_source,
            gate=args.gate,
        )
        _print_judge_verdict(result)
        sys.exit(0 if result.verdict == "VERIFIED" else 1)

    # Modo --check-only (CI)
    if args.check_only:
        data: dict[str, Any] = {"task": "check-only", "status": "draft"}
        data = _step_verify(
            "check-only",
            data,
            ruff_paths=args.ruff_paths,
            test_paths=args.test_paths,
            ignore=args.ignore,
            cov_source=args.cov_source,
            gate=args.gate,
        )
        sys.exit(0 if data.get("status") == "approved" else 1)

    # Modo interativo: escolher ou criar tarefa
    if args.task:
        task = args.task
    else:
        task = _pick_task()

    path = _task_path(task)

    if not path.exists():
        _init_task(task)

    data = (
        _deserialize(path.read_text(encoding="utf-8"))
        if path.exists()
        else {"task": task, "status": "draft"}
    )
    data = _capture_base_commit(data)

    data = _step_fit(task, data)
    data = _step_think(task, data)

    if args.plan:
        path.write_text(_serialize(data), encoding="utf-8")
        print(f"\n📝  Plano salvo em {path}")
        print("    Próximas fases: SIMPLIFY → SURGICAL → VERIFY")
        return

    data = _step_simplify(task, data)
    data = _step_intent(task, data)
    data = _step_surgical(task, data)
    data = _step_verify(
        task,
        data,
        ruff_paths=args.ruff_paths,
        test_paths=args.test_paths,
        ignore=args.ignore,
        cov_source=args.cov_source,
        gate=args.gate,
    )
    data = _step_twin(task, data)
    data = _step_artifact(task, data)
    _step_report(task, data)

    path.write_text(_serialize(data), encoding="utf-8")
    print(f"\n📝  Resultado salvo em {path}")

    if data.get("status") == "rejected":
        sys.exit(1)


if __name__ == "__main__":
    main()
