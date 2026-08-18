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

from kata.judge import baseline_ref

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
KATA_CLI = [sys.executable, "-m", "kata"]

# Folgado para o cenário mais lento (s03 roda ruff e pytest de verdade no
# fixture), apertado o bastante para não pendurar o CI.
JUDGE_TIMEOUT_S = 180

# Config escrita em cada fixture, git-ignorada como .kata/, para fixar as
# regras que o ruff do judge aplica lá dentro.
#
# Sem isto o veredito do cenário dependia das regras-padrão do ruff instalado:
# a 0.16 passou a habilitar I001 por padrão, o fixture do s01 deixou de ser
# lint-clean, e o judge — corretamente — acusou false_completion contra a claim
# `ruff_clean: true`. Como `ruff>=0.1.0` no pyproject não tem teto, o CI
# instala o mais novo e local não. Um cenário de trap não pode mudar de
# veredito por causa disso.
_FIXTURE_CONFIG = """\
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F"]
"""


class ScenarioError(Exception):
    """Falha ao preparar ou executar um cenário.

    Distinta de SystemExit de propósito: o problema é de um cenário, e derrubar
    a suíte inteira por causa dele esconderia o resultado dos outros sete.
    """


def task_name(fixture_dir: Path) -> str:
    """Descobre o nome da tarefa a partir do próprio fixture.

    Antes era fixo ("fix-divide-by-zero"), o que obrigava todo cenário novo a
    reusar o nome do primeiro.
    """
    tarefas = sorted(p.stem for p in (fixture_dir / ".kata").glob("*.yaml") if p.stem != "config")
    if len(tarefas) != 1:
        raise ScenarioError(f"esperado exatamente 1 task em .kata/, encontrado {tarefas}")
    return tarefas[0]


def _git_em(path: Path):
    """Executor de git ligado a um diretório, com falha virando ScenarioError."""

    def git(*args: str) -> None:
        try:
            subprocess.run(["git", *args], cwd=path, capture_output=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise ScenarioError(
                f"git {' '.join(args)} falhou: {exc.stderr.decode(errors='replace').strip()}"
            ) from exc

    return git


def _aplica_baseline(
    path: Path,
    baseline: Path,
    task: str,
    git,
    leave_untracked: list[str] | None = None,
) -> None:
    """Commita um estado limpo, reaplica o fixture por cima e commita também.

    Sem isto todo fixture é arquivo novo (o harness faz `git add -A` num repo
    sem commit), e desde o fix do R4-1 arquivo novo pula _WEAKENED_PATTERNS.
    Os cinco padrões originais — assert removido, teste comentado, corpo virado
    pass, noqa adicionado — e o caminho base_commit não tinham cenário nenhum.

    O SHA do baseline é gravado no task YAML: só ele existe em tempo de
    execução, então o fixture não pode trazê-lo pronto.
    """
    posterior = {
        arquivo: arquivo.read_bytes()
        for arquivo in path.rglob("*")
        if arquivo.is_file() and ".git" not in arquivo.parts
    }

    shutil.copytree(baseline, path, dirs_exist_ok=True)
    git("add", "-A")
    git("commit", "-q", "-m", "baseline limpo")
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    ).stdout.strip()
    git("update-ref", baseline_ref(task), sha)

    for arquivo, conteudo in posterior.items():
        arquivo.write_bytes(conteudo)
    git("add", "-A")
    git("commit", "-q", "-m", "tarefa concluida")

    # O `git add -A` acima re-stageia o que o init_git_repo tinha tirado do
    # índice (leave_untracked) — sem reaplicar o rm --cached, a fraude plantada
    # num arquivo untracked entraria nos DOIS commits e sumiria do diff que o
    # judge inspeciona (R10-5). O estado untracked tem de sobreviver ao baseline.
    for caminho in leave_untracked or []:
        git("rm", "--cached", "-q", caminho)

    # Arquivos do fixture que NÃO existem no baseline entram no commit de
    # baseline já no estado pós-tarefa (copytree só sobrescreve os comuns).
    # Se o cenário planta mudança num desses arquivos (ex.: noqa adicionado
    # em src/), ela some do diff e o trap deixa de testar o que diz testar —
    # falha cedo com diagnóstico (P2-6), em vez de "fraude esperada não
    # encontrada" no evaluate.
    baseline_rel = {str(f.relative_to(baseline)) for f in baseline.rglob("*") if f.is_file()}
    rastreados = set(
        subprocess.run(
            ["git", "ls-files"], cwd=path, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    )
    for arquivo, conteudo in posterior.items():
        rel = str(arquivo.relative_to(path))
        if rel in baseline_rel or rel not in rastreados:
            continue
        antes = subprocess.run(
            ["git", "show", f"HEAD~1:{rel}"], cwd=path, capture_output=True
        ).stdout
        if antes != conteudo:
            raise ScenarioError(
                f"{rel} difere entre o baseline e a tarefa mas não está em "
                "baseline/ — a mudança foi embutida no commit de baseline e "
                "fica invisível ao judge. Ponha a versão pré-tarefa do "
                "arquivo em baseline/ (ou torne os dois commits idênticos)."
            )

    caminho_task = path / ".kata" / f"{task}.yaml"
    dados = yaml.safe_load(caminho_task.read_text(encoding="utf-8"))
    dados["base_commit"] = sha
    caminho_task.write_text(yaml.dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")


def init_git_repo(
    path: Path,
    leave_untracked: list[str] | None = None,
    kata_visivel: bool = False,
) -> None:
    """Inicializa um repositório git com o fixture staged, sem commit.

    O fixture já vem com a fraude plantada (ex: corpo de teste virado
    `pass`). O judge detecta fraudes inspecionando `git diff`/`git diff
    --cached`, então as mudanças precisam ficar não commitadas para serem
    visíveis — um commit único não deixaria diff nenhum para inspecionar.
    `.kata/` é git-ignorado localmente (via .git/info/exclude, não um
    .gitignore rastreado), para não aparecer como scope creep no diff nem no
    diff em si.

    `kata_visivel` desliga essa exclusão. Ela imitava um projeto que ignora
    `.kata/`, mas o kata não pede isso a ninguém: `--init` não mexe no
    .gitignore e nenhum doc instrui a ignorá-lo. O efeito colateral foi que
    os 14 cenários rodavam num ambiente onde o arquivo da própria tarefa era
    invisível ao git — e o judge contá-lo como scope creep passou dez rodadas
    sem ser visto, inclusive pelo s07, que existe para pegar falso positivo
    (R11-3). Com isto, um cenário pode exigir o ambiente real.

    `leave_untracked` remove caminhos do índice depois do `git add -A`, para
    que fiquem só na árvore de trabalho. É o estado que o judge era cego a
    enxergar, e o único jeito de exercitá-lo aqui.
    """
    git = _git_em(path)

    git("init", "-q")
    excluidos = "pyproject.toml\n" if kata_visivel else ".kata/\npyproject.toml\n"
    (path / ".git" / "info" / "exclude").write_text(excluidos, encoding="utf-8")
    (path / "pyproject.toml").write_text(_FIXTURE_CONFIG, encoding="utf-8")
    git("config", "user.email", "eval@kata.local")
    git("config", "user.name", "kata-eval")
    git("add", "-A")
    for caminho in leave_untracked or []:
        git("rm", "--cached", "-q", caminho)


def _tampera_base_commit(path: Path, task: str) -> None:
    """Planta baseline_tampering: base_commit do YAML passa a apontar para o
    HEAD (commit da tarefa) enquanto a âncora refs/kata/base/<hash> continua
    no baseline — o judge tem de acusar a divergência (P2-4/s14)."""
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    ).stdout.strip()
    caminho_task = path / ".kata" / f"{task}.yaml"
    dados = yaml.safe_load(caminho_task.read_text(encoding="utf-8"))
    dados["base_commit"] = sha
    caminho_task.write_text(yaml.dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _grava_approved_commit(path: Path, task: str) -> None:
    """Grava approved_commit = HEAD do commit da tarefa no YAML (s17/K-20).

    É o mesmo estado que _step_verify produz no approve: o teto do diff.
    Sem isto o approved_commit só era exercitado em teste unitário — um
    regresso na leitura ou nas validações do K-04 passaria no CI.
    """
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    ).stdout.strip()
    caminho_task = path / ".kata" / f"{task}.yaml"
    dados = yaml.safe_load(caminho_task.read_text(encoding="utf-8"))
    dados["approved_commit"] = sha
    caminho_task.write_text(yaml.dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _aplica_posterior(path: Path, arquivos: list[str]) -> None:
    """Planta a 'task posterior': altera arquivos DEPOIS do approved_commit.

    É o estado que o R14 existe para isolar: mudanças feitas por tasks
    posteriores não podem contar como scope_creep para esta. Sem o
    approved_commit (regresso), o judge diffa até HEAD e vê o arquivo
    alterado como não declarado.
    """
    for nome in arquivos:
        caminho = path / nome
        if caminho.exists():
            conteudo = caminho.read_text(encoding="utf-8")
            caminho.write_text(conteudo + "# mudança de task posterior\n", encoding="utf-8")
        else:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text("# criado por task posterior\n", encoding="utf-8")
    git = _git_em(path)
    git("add", "-A")
    git("commit", "-q", "-m", "task posterior")


def run_judge(path: Path, task: str) -> dict:
    """Executa kata --judge no diretório do fixture e retorna o resultado.

    Com timeout: o judge roda ruff e pytest dentro do fixture quando a tarefa
    afirma que passaram, e um teste que trava lá pendura a suíte inteira —
    no CI, até o limite do job.
    """
    try:
        result = subprocess.run(
            [*KATA_CLI, "--judge", "--task", task],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=JUDGE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScenarioError(f"judge não terminou em {JUDGE_TIMEOUT_S}s") from exc
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def load_ground_truth(scenario_dir: Path) -> dict:
    path = scenario_dir / "ground_truth.yaml"
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ScenarioError("ground_truth.yaml deve conter um mapa")
        verdicts = {"VERIFIED", "VERIFIED WITH CAVEATS", "UNVERIFIABLE", "REFUTED"}
        if data.get("expected_verdict") not in verdicts:
            raise ScenarioError("ground_truth.yaml deve declarar expected_verdict válido")
        if not isinstance(data.get("expected_frauds", []), list):
            raise ScenarioError("expected_frauds deve ser uma lista")
        for chave in ("leave_untracked", "expected_absent"):
            valor = data.get(chave)
            if valor is not None and not isinstance(valor, list):
                raise ScenarioError(f"ground_truth.yaml: {chave} deve ser uma lista")
        for chave in ("tamper_base_commit", "kata_visivel", "approved_commit"):
            valor = data.get(chave)
            if valor is not None and not isinstance(valor, bool):
                raise ScenarioError(f"ground_truth.yaml: {chave} deve ser booleano")
        if data.get("posterior") is not None and not isinstance(data.get("posterior"), list):
            raise ScenarioError("ground_truth.yaml: posterior deve ser uma lista")
        return data
    except (OSError, yaml.YAMLError) as exc:
        raise ScenarioError(f"ground_truth.yaml ilegível: {exc}") from exc


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

    expected_verdict = ground_truth["expected_verdict"]
    stdout = judge_output.get("stdout", "")

    verdict_match = re.search(r"KATA JUDGE — (.+)", stdout)
    actual_verdict = verdict_match.group(1).strip() if verdict_match else ""
    if actual_verdict != expected_verdict:
        passed = False
        messages.append(
            f"  ❌ Veredito esperado '{expected_verdict}', obtido '{actual_verdict or 'ausente'}'"
        )

    expected_returncode = 1 if expected_verdict == "REFUTED" else 0
    if judge_output.get("returncode") != expected_returncode:
        passed = False
        messages.append(
            f"  ❌ Código de saída esperado {expected_returncode}, "
            f"obtido {judge_output.get('returncode')}"
        )

    problemas = _match_frauds(ground_truth.get("expected_frauds", []), parse_frauds(stdout))
    if problemas:
        passed = False
        messages.extend(problemas)
        if (scenario_dir / "baseline").is_dir():
            # P2-6: a causa mais comum de fraude esperada não vista com
            # baseline presente é a mudança plantada em arquivo fora de
            # baseline/ — o estado pós-tarefa vira o baseline e o diff some.
            messages.append(
                "  💡 Mudança não vista com baseline presente? Arquivos que a "
                "tarefa altera precisam de versão pré-mudança em baseline/ — "
                "senão a mudança é embutida no baseline e fica invisível ao judge."
            )

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
        print(f"  [{name}] Setup...", end=" ")

        with tempfile.TemporaryDirectory(prefix=f"kata-eval-{name}-") as tmpdir:
            # Só ScenarioError é contido. Erro de programação no harness
            # (AttributeError, TypeError) tem de estourar: reportá-lo como
            # "cenário reprovou" esconderia um defeito da ferramenta atrás de
            # um resultado de teste.
            try:
                gt = load_ground_truth(scenario)
                work_dir = Path(tmpdir) / "work"
                try:
                    shutil.copytree(scenario / "fixture", work_dir)
                except OSError as exc:
                    raise ScenarioError(f"fixture não pôde ser copiado: {exc}") from exc

                init_git_repo(
                    work_dir,
                    gt.get("leave_untracked"),
                    kata_visivel=bool(gt.get("kata_visivel")),
                )

                tarefa = task_name(work_dir)
                baseline = scenario / "baseline"
                if baseline.is_dir():
                    _aplica_baseline(
                        work_dir,
                        baseline,
                        tarefa,
                        _git_em(work_dir),
                        gt.get("leave_untracked"),
                    )
                if gt.get("tamper_base_commit"):
                    _tampera_base_commit(work_dir, tarefa)
                if gt.get("approved_commit"):
                    _grava_approved_commit(work_dir, tarefa)
                if gt.get("posterior"):
                    _aplica_posterior(work_dir, gt["posterior"])

                judge_output = run_judge(work_dir, tarefa)
                passed, messages = evaluate(scenario, gt, judge_output)
            except ScenarioError as exc:
                passed, messages = False, [f"  ❌ {exc}"]

            results[name] = passed
            status = "✅" if passed else "❌"
            print(f"{status}")
            for msg in messages:
                print(msg)

    print(f"\n{'=' * 50}")
    passed_count = sum(1 for v in results.values() if v)
    print(f"Resultado: {passed_count}/{total} cenários passaram")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")

    if passed_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
