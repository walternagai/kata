#!/usr/bin/env python3
"""Eval trap runner para o kata.

Para cada cenário em eval/scenarios/:
1. Cria uma cópia temporária do fixture
2. Inicializa um repositório git com os arquivos
3. Executa `python3 -m kata --judge` (ou judge_task programaticamente)
4. Compara o resultado com o ground truth
5. Reporta aprovação/reprovação do cenário
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
KATA_CLI = [sys.executable, "-m", "kata"]


def init_git_repo(path: Path) -> None:
    """Inicializa um repositório git com o fixture inteiro staged, sem commit.

    O fixture já vem com a fraude plantada (ex: corpo de teste virado
    `pass`). O judge detecta fraudes inspecionando `git diff`/`git diff
    --cached`, então as mudanças precisam ficar não commitadas para serem
    visíveis — um commit único não deixaria diff nenhum para inspecionar.
    `.kata/` é git-ignorado localmente (via .git/info/exclude, não um
    .gitignore rastreado) como no projeto real, para não aparecer como
    scope creep no diff nem no diff em si.
    """
    subprocess.run(["git", "init", "-q"], cwd=path, capture_output=True, check=True)
    (path / ".git" / "info" / "exclude").write_text(".kata/\n", encoding="utf-8")
    subprocess.run(
        ["git", "config", "user.email", "eval@kata.local"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "kata-eval"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, check=True)


def run_judge(path: Path) -> dict:
    """Executa kata --judge no diretório do fixture e retorna o resultado."""
    result = subprocess.run(
        [*KATA_CLI, "--judge", "--task", "fix-divide-by-zero"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def load_ground_truth(scenario_dir: Path) -> dict:
    path = scenario_dir / "ground_truth.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def evaluate(scenario_dir: Path, ground_truth: dict, judge_output: dict) -> tuple[bool, list[str]]:
    """Compara o output do judge com o ground truth."""
    passed = True
    messages: list[str] = []

    expected_verdict = ground_truth.get("expected_verdict", "")
    stdout = judge_output.get("stdout", "")

    if expected_verdict and expected_verdict not in stdout:
        passed = False
        messages.append(
            f"  ❌ Veredito esperado '{expected_verdict}' não encontrado no output"
        )

    for expected_fraud in ground_truth.get("expected_frauds", []):
        fraud_type = expected_fraud.get("type", "")
        desc_contains = expected_fraud.get("description_contains", "")
        if fraud_type and fraud_type not in stdout:
            passed = False
            messages.append(f"  ❌ Fraude esperada '{fraud_type}' não encontrada")
        elif desc_contains and desc_contains not in stdout:
            passed = False
            messages.append(
                f"  ❌ Descrição contendo '{desc_contains}' não encontrada na fraude"
            )

    for no_fraud_type in ground_truth.get("expected_no_frauds", []):
        if no_fraud_type in stdout:
            passed = False
            messages.append(
                f"  ❌ Fraude '{no_fraud_type}' detectada mas não deveria (falso positivo)"
            )

    return passed, messages


def main() -> None:
    scenarios = sorted(
        d for d in SCENARIOS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
    )

    if not scenarios:
        print("⚠  Nenhum cenário encontrado em eval/scenarios/")
        sys.exit(0)

    results: dict[str, bool] = {}
    total = len(scenarios)

    print(f"▶  Executando {total} cenário(s) de trap...\n")

    for scenario in scenarios:
        name = scenario.name
        gt = load_ground_truth(scenario)

        print(f"  [{name}] Setup...", end=" ")

        with tempfile.TemporaryDirectory(prefix=f"kata-eval-{name}-") as tmpdir:
            fixture_dir = scenario / "fixture"
            work_dir = Path(tmpdir) / "work"
            shutil.copytree(fixture_dir, work_dir)

            init_git_repo(work_dir)

            judge_output = run_judge(work_dir)
            passed, messages = evaluate(scenario, gt, judge_output)

            results[name] = passed
            status = "✅" if passed else "❌"
            print(f"{status}")
            for msg in messages:
                print(msg)

    print(f"\n{'='*50}")
    passed_count = sum(1 for v in results.values() if v)
    print(f"Resultado: {passed_count}/{total} cenários passaram")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")

    if passed_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
