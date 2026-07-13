"""Kata CLI — Karpathy Development Cycle.

Modos:
  --init <task>     Cria .kata/<task>.yaml com template
  (sem args)        Ciclo interativo completo (THINK → SIMPLIFY → SURGICAL → VERIFY)
  --check-only      Roda só o passo 4 (lint + test + coverage)
  --task <name>     Retoma tarefa específica

Port do `scripts/karpathy_cycle.py` do mushin, usando `.kata/` e
lógica de verificação modularizada em `kata.verify`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from kata.verify import VerifyResult, run_all

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


def _task_path(task: str) -> Path:
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
    return input("Nome da tarefa: ").strip().replace(" ", "-") or "untitled"


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=_cwd(), **kwargs)


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
    print("┌─" + "─" * (width - 2) + "┐")
    for line in text.split("\n"):
        print(f"│ {line:<{width - 3}}│")
    print("└" + "─" * (width - 2) + "┘")
    print()


# ── step implementations ────────────────────────────────────────────────


def _step_think(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 1: THINK — declarar assumptions antes de codar."""
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
    """Fase 2: SIMPLIFY — o código é mínimo?"""
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
    simplify["no_single_use_abstractions"] = not _confirm(
        "  Alguma abstração para uso único?", default=False
    )
    simplify["no_speculative_config"] = not _confirm(
        "  Configurabilidade/flexibilidade não solicitada?", default=False
    )
    notes = input("  Observações (opcional): ").strip()
    if notes:
        simplify["notes"] = notes
    data["simplify"] = simplify
    return data


def _step_surgical(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 3: SURGICAL — cada linha toca só o necessário."""
    _print_header("3. SURGICAL — Cada linha toca só o necessário")

    if not sys.stdin.isatty():
        print("(modo não-interativo — pulando SURGICAL)")
        data["surgical"] = {"files": [], "removed_imports_clean": True}
        return data

    # Lista arquivos alterados
    result = _run(["git", "diff", "--name-only"])
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    if not files:
        result = _run(["git", "diff", "--cached", "--name-only"])
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
        for line in ruff_res.output.split("\n")[:10]:
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
        for line in pytest_res.output.split("\n")[-10:]:
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
        for line in cov_res.output.split("\n")[-5:]:
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
        "think": {
            "problem": "",
            "assumptions": [],
            "alternatives": [],
            "unknowns": "",
            "answered": False,
        },
        "simplify": {},
        "surgical": {},
        "verify": {},
    }
    path.write_text(_serialize(template), encoding="utf-8")
    print(f"✅  {path} criado. Preencha as respostas com o modo interativo.")


# ── main ────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point do CLI kata."""
    parser = argparse.ArgumentParser(
        description="Kata (型) — Karpathy Development Cycle",
    )
    parser.add_argument("--init", metavar="TASK", help="Cria checklist para nova tarefa")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Roda só o passo 4 (lint + test + coverage)",
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
        help="Gate mínimo de coverage em%% (default: 70)",
    )
    args = parser.parse_args()

    _kata_dir().mkdir(parents=True, exist_ok=True)

    # Modo --init
    if args.init:
        _init_task(args.init)
        return

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

    data = _step_think(task, data)
    data = _step_simplify(task, data)
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

    path.write_text(_serialize(data), encoding="utf-8")
    print(f"\n📝  Resultado salvo em {path}")

    if data.get("status") == "rejected":
        sys.exit(1)


if __name__ == "__main__":
    main()
