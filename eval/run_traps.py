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

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
KATA_CLI = [sys.executable, "-m", "kata"]


def task_name(fixture_dir: Path) -> str:
    """Descobre o nome da tarefa a partir do próprio fixture.

    Antes era fixo ("fix-divide-by-zero"), o que obrigava todo cenário novo a
    reusar o nome do primeiro.
    """
    tarefas = sorted(p.stem for p in (fixture_dir / ".kata").glob("*.yaml"))
    if len(tarefas) != 1:
        raise SystemExit(
            f"{fixture_dir}: esperado exatamente 1 task em .kata/, encontrado {tarefas}"
        )
    return tarefas[0]


def init_git_repo(path: Path, leave_untracked: list[str] | None = None) -> None:
    """Inicializa um repositório git com o fixture staged, sem commit.

    O fixture já vem com a fraude plantada (ex: corpo de teste virado
    `pass`). O judge detecta fraudes inspecionando `git diff`/`git diff
    --cached`, então as mudanças precisam ficar não commitadas para serem
    visíveis — um commit único não deixaria diff nenhum para inspecionar.
    `.kata/` é git-ignorado localmente (via .git/info/exclude, não um
    .gitignore rastreado) como no projeto real, para não aparecer como
    scope creep no diff nem no diff em si.

    `leave_untracked` remove caminhos do índice depois do `git add -A`, para
    que fiquem só na árvore de trabalho. É o estado que o judge era cego a
    enxergar, e o único jeito de exercitá-lo aqui.
    """
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=path, capture_output=True, check=True)

    git("init", "-q")
    (path / ".git" / "info" / "exclude").write_text(".kata/\n", encoding="utf-8")
    git("config", "user.email", "eval@kata.local")
    git("config", "user.name", "kata-eval")
    git("add", "-A")
    for caminho in leave_untracked or []:
        git("rm", "--cached", "-q", caminho)


def run_judge(path: Path, task: str) -> dict:
    """Executa kata --judge no diretório do fixture e retorna o resultado."""
    result = subprocess.run(
        [*KATA_CLI, "--judge", "--task", task],
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


_LINHA_FRAUDE = re.compile(r"^\s*\S*\s*\[(high|medium|low)\]\s+(\w+)\s*$")


def parse_frauds(stdout: str) -> list[dict]:
    """Extrai a lista de fraudes que o judge relatou.

    O formato é estável (cli._print_judge_verdict): uma linha
    `<ícone> [severidade] tipo` seguida da descrição indentada. Parsear em
    vez de buscar substring é o que permite exigir correspondência exata —
    sem isso o ground truth só sabia dizer "contém pelo menos", e um cenário
    passava mesmo quando o judge relatava fraudes que ninguém previu.
    """
    frauds: list[dict] = []
    linhas = stdout.split("\n")
    for i, linha in enumerate(linhas):
        m = _LINHA_FRAUDE.match(linha)
        if not m:
            continue
        descricao = linhas[i + 1].strip() if i + 1 < len(linhas) else ""
        frauds.append({"severity": m.group(1), "type": m.group(2), "description": descricao})
    return frauds


def _match_frauds(esperadas: list[dict], obtidas: list[dict]) -> list[str]:
    """Casa esperadas contra obtidas, cada uma consumida uma única vez.

    Sobra em qualquer um dos lados é falha: faltar é falso negativo, exceder
    é falso positivo, e a suíte existe para pegar os dois.
    """
    messages: list[str] = []
    restantes = list(obtidas)

    for esperada in esperadas:
        tipo = esperada.get("type", "")
        sev = esperada.get("severity", "")
        desc = esperada.get("description_contains", "")
        achada = next(
            (
                f
                for f in restantes
                if (not tipo or f["type"] == tipo)
                and (not sev or f["severity"] == sev)
                and (not desc or desc in f["description"])
            ),
            None,
        )
        if achada is None:
            messages.append(
                f"  ❌ Fraude esperada não encontrada: [{sev}] {tipo}"
                + (f" contendo '{desc}'" if desc else "")
            )
        else:
            restantes.remove(achada)

    for extra in restantes:
        messages.append(
            f"  ❌ Fraude NÃO prevista: [{extra['severity']}] {extra['type']} "
            f"— {extra['description']}"
        )
    return messages


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

    problemas = _match_frauds(ground_truth.get("expected_frauds", []), parse_frauds(stdout))
    if problemas:
        passed = False
        messages.extend(problemas)

    # Falso positivo em arquivo específico: o tipo de fraude pode ser esperado
    # no cenário e ainda assim um arquivo honesto não deve aparecer nele.
    for texto in ground_truth.get("expected_absent", []):
        if texto in stdout:
            passed = False
            messages.append(f"  ❌ '{texto}' apareceu no output — falso positivo")

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

            init_git_repo(work_dir, gt.get("leave_untracked"))

            judge_output = run_judge(work_dir, task_name(work_dir))
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
