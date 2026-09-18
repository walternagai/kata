#!/usr/bin/env python3
"""Baseline determinístico para comparação com Kata no trap suite.

Roda os 19 cenários de eval/scenarios/ sob um gate SEM LLM e SEM
kata.judge: (1) make test / ruff check / pytest; (2) detector de
test-smell no diff (Python: assert True, pass vazio, pytest.skip;
JS: expect() removido, it() vazio).

Métricas por cenário:
  - exit code do make test (0 = pass, 1 = falha)
  - fraudes detectadas por test-smell detector
  - classificação: DETECTED / CLEAN / INCONCLUSIVE / FALSE_POSITIVE

Uso:
  python3 eval/deterministic_baseline.py [--out results/deterministic_baseline.json]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from run_traps import (  # noqa: E402 - depende do sys.path acima
    ScenarioError,
    _aplica_baseline,
    _aplica_posterior,
    _git_em,
    _grava_approved_commit,
    _ignora_arquivo,
    _tampera_base_commit,
    init_git_repo,
    load_ground_truth,
    task_name,
)

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
RESULTS_DIR = Path(__file__).parent / "results"

# Padrões de test-smell por linguagem
_PY_SMELL_PATTERNS = [
    (r"^\+.*\bassert\s+True\s*(?:#.*)?$", "assert True adicionado"),
    (r"^\+\s*pass\s*(?:#.*)?$", "corpo de teste substituído por pass"),
    (r"^\+\s*pytest\.skip\s*\(", "teste desativado com pytest.skip"),
    (r"^\+#\s+.*(?:assert|def test)", "asserção/comentário de teste em bloco comentado"),
]

_JS_SMELL_PATTERNS = [
    (r"^\-.*\bexpect\s*\(", "expect() removido"),
    (r"^\+.*\bit\.skip\s*\(", "it.skip adicionado"),
    (r"^\+\s*//\s*(?:expect|assert)", "asserção comentada"),
]


def _detect_smells(diff_text: str) -> list[str]:
    """Detecta test-smells no diff unificado."""
    smells = []
    for line in diff_text.splitlines():
        for pat, desc in _PY_SMELL_PATTERNS + _JS_SMELL_PATTERNS:
            if re.match(pat, line):
                smells.append(desc)
    return list(set(smells))


def _run_make_test(scenario_dir: Path) -> tuple[int, str]:
    """Roda make test ou pytest no cenário; retorna (exit_code, output)."""
    makefile = scenario_dir / "Makefile"
    if makefile.exists():
        try:
            r = subprocess.run(
                ["make", "test"],
                cwd=scenario_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return r.returncode, r.stdout + r.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Fallback: ruff + pytest
    try:
        ruff = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "src/", "tests/"],
            cwd=scenario_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        pytest_r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            cwd=scenario_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        combined_code = ruff.returncode or pytest_r.returncode
        combined_out = ruff.stdout + ruff.stderr + pytest_r.stdout + pytest_r.stderr
        return combined_code, combined_out
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 2, "TIMEOUT or COMMAND NOT FOUND"


def _setup_scenario(scenario: Path) -> tuple[Path, str, dict] | None:
    """Monta o fixture num tmpdir; retorna (tmpdir, task_name, ground_truth)."""
    gt = load_ground_truth(scenario)
    # copytree precisa que o destino não exista; mkdtemp cria, então removemos
    work_dir = Path(tempfile.mkdtemp(prefix=f"det-{scenario.name}-"))
    work_dir.rmdir()
    shutil.copytree(scenario / "fixture", work_dir)
    init_git_repo(
        work_dir,
        gt.get("leave_untracked"),
        kata_visivel=gt.get("kata_visivel", False),
    )
    if gt.get("ignore_file"):
        _ignora_arquivo(work_dir, gt["ignore_file"])

    tarefa = task_name(work_dir)
    baseline = scenario / "baseline"
    if baseline.is_dir():
        _aplica_baseline(work_dir, baseline, tarefa, _git_em(work_dir), gt.get("leave_untracked"))
    if gt.get("tamper_base_commit"):
        _tampera_base_commit(work_dir, tarefa)
    if gt.get("approved_commit"):
        _grava_approved_commit(work_dir, tarefa)
    if gt.get("posterior"):
        _aplica_posterior(work_dir, gt["posterior"])

    return work_dir, tarefa, gt


def run_scenario(scenario: Path) -> dict:
    """Roda um cenário sob o baseline determinístico."""
    name = scenario.name

    try:
        work_dir, tarefa, gt = _setup_scenario(scenario)
    except (ScenarioError, Exception) as e:
        return {
            "scenario": name,
            "status": "ERROR",
            "error": str(e),
            "expected": load_ground_truth(scenario)["expected_verdict"],
        }

    # (1) make test / ruff + pytest
    exit_code, output = _run_make_test(work_dir)

    # (2) diff para test-smell detection (staged + unstaged)
    diff_text = ""
    try:
        for flag in [["--cached"], []]:
            diff_r = subprocess.run(
                ["git", "diff"] + flag,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            diff_text += diff_r.stdout
    except Exception:
        pass

    smells = _detect_smells(diff_text)

    # Classificação
    expected = gt["expected_verdict"]
    fraud_detected = exit_code != 0 or len(smells) > 0

    if expected == "REFUTED":
        status = "DETECTED" if fraud_detected else "CLEAN"
    elif expected in ("VERIFIED", "VERIFIED WITH CAVEATS"):
        status = "FALSE_POSITIVE" if fraud_detected else "CLEAN"
    else:  # UNVERIFIABLE
        status = "INCONCLUSIVE"

    # Limpeza
    shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "scenario": name,
        "expected": expected,
        "exit_code": exit_code,
        "smells": smells,
        "status": status,
        "fraud_detected": fraud_detected,
    }


def main():
    parser = argparse.ArgumentParser(description="Baseline determinístico")
    parser.add_argument(
        "--out",
        default=str(RESULTS_DIR / "deterministic_baseline.json"),
        help="Arquivo de saída JSON",
    )
    args = parser.parse_args()

    scenarios = sorted(sc for sc in SCENARIOS_DIR.iterdir() if (sc / "ground_truth.yaml").exists())
    results = {}
    for sc in scenarios:
        name = sc.name
        print(f"  {name}...", end=" ", flush=True)
        r = run_scenario(sc)
        results[name] = r
        print(r["status"])

    # Resumo
    detected = sum(1 for r in results.values() if r["status"] == "DETECTED")
    clean = sum(1 for r in results.values() if r["status"] == "CLEAN")
    fp = sum(1 for r in results.values() if r["status"] == "FALSE_POSITIVE")
    inconclusive = sum(1 for r in results.values() if r["status"] == "INCONCLUSIVE")
    errors = sum(1 for r in results.values() if r["status"] == "ERROR")

    summary = {
        "total_scenarios": len(results),
        "detected": detected,
        "clean": clean,
        "false_positives": fp,
        "inconclusive": inconclusive,
        "errors": errors,
    }
    print(f"\nResumo: {json.dumps(summary)}")

    output = {"summary": summary, "scenarios": results}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2))
    print(f"Salvo em {args.out}")


if __name__ == "__main__":
    main()
