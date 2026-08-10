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
  --audit           Gradua as fases da tarefa: followed / skipped / faked (usa --task ou branch)
  --doctor          Confere se as skills de fase estão instaladas em cada frontend

Port do `scripts/karpathy_cycle.py` do mushin, usando `.kata/` e
lógica de verificação modularizada em `kata.verify` e `kata.fit`.

Inspirado no Karpathy Development Cycle e no The Fable Method
(https://github.com/Sahir619/fable-method).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from kata import __version__
from kata.config import (
    DEFAULT_GATE,
    ConfigError,
    VerifyConfig,
    config_path,
    load_verify_config,
)
from kata.fit import diff_stats, is_trivial, untracked_stats
from kata.judge import (
    JudgeResult,
    is_debris_file,
    judge_task,
    record_baseline_ref,
)
from kata.skills import DOMAIN_SKILLS, InstallStatus, doctor, doctor_domain
from kata.verify import VerifyResult, run_all, search_pattern, untracked_files

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# ── helpers ──────────────────────────────────────────────────────────────

_TASK_WHITESPACE = re.compile(r"\s")

# Hard bound (Fable Step 5): após este número de tentativas de verificação
# falhas, o ciclo devolve a tarefa ao usuário em vez de continuar o loop
# fix-verify indefinidamente.
MAX_VERIFY_ATTEMPTS = 3

# Extensões que _task_path pode concatenar, conforme PyYAML esteja
# presente ou não. A validação rejeita as duas independentemente.
_SERIALIZATION_EXTS = (".yaml", ".json")


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


def _save_task(path: Path, data: dict[str, Any]) -> None:
    """Persiste a tarefa com replace atômico para permitir retomada segura."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(_serialize(data))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _deserialize(text: str) -> dict[str, Any]:
    if _HAS_YAML:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def _ext() -> str:
    return ".yaml" if _HAS_YAML else ".json"


def _detect_cov_source() -> str:
    """Detecta o pacote fonte de coverage a partir de pyproject.toml.

    Lê `[tool.coverage.run] source` e retorna o primeiro item. Se não
    encontrar, cai no fallback "src".
    """
    pyproject = _cwd() / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            text = pyproject.read_text(encoding="utf-8")
            config = tomllib.loads(text)
            sources = config.get("tool", {}).get("coverage", {}).get("run", {}).get("source", [])
            if isinstance(sources, str):
                return sources
            if sources:
                return sources[0]
        except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as exc:
            # CR-009/S4: pyproject malformado ou ilegível não pode ser
            # engolido em silêncio — o --cov rodaria contra um source que o
            # projeto não declarou. Avisa e degrada para o fallback.
            logging.warning("pyproject.toml ilegível (%s); usando 'src' como fallback", exc)
    return "src"


def _is_invalid_task_name(task: str) -> bool:
    """Predicado de nome de tarefa, compartilhado entre CLI (--task/--init/...)
    e o prompt interativo de _pick_task — um único lugar para a regra em si.

    Rejeita, além de path traversal: espaços em branco (que produziriam
    `.kata/my task.yaml`), nomes iniciados por ponto (arquivo oculto, e
    cobre "." e "..") e nomes que já trazem a extensão de serialização
    (`--init foo.yaml` produziria `.kata/foo.yaml.yaml`, porque _task_path
    concatena a extensão).

    Ambas as extensões são rejeitadas sempre, e não só a de _ext(): amarrar a
    regra ao formato ativo fazia `--init foo.yaml` passar quando PyYAML está
    ausente, criando `.kata/foo.yaml.json`. Nome de tarefa é escolha do
    usuário e não deve depender de qual biblioteca está instalada.
    """
    if not task or not task.strip():
        return True
    if _TASK_WHITESPACE.search(task):
        return True
    if task.startswith("."):
        return True
    if task.endswith(_SERIALIZATION_EXTS):
        return True
    if task == "config":
        return True
    return "/" in task or "\\" in task or ".." in task


def _validate_task_name(task: str) -> None:
    """Impede path traversal via nome de tarefa (--task/--init/--judge/--report).

    Sem isso, um nome como '../../etc/foo' escreve/lê fora de .kata/, já que
    _task_path só concatena o nome ao diretório sem checar separadores.
    """
    if _is_invalid_task_name(task):
        print(
            f"⚠  Nome de tarefa inválido: '{task}'. "
            "Não pode ser vazio, conter espaços, começar com '.', "
            f"terminar em {' ou '.join(_SERIALIZATION_EXTS)}, "
            "nem ser 'config' ou conter '/', '\\' ou '..'."
        )
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
    existing = sorted(p.stem for p in _kata_dir().glob(f"*{_ext()}") if p.stem != "config")
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
    if _is_invalid_task_name(name):
        print("⚠  Nome de tarefa inválido. Usando 'untitled'")
        return "untitled"
    return name


def _resolve_task_or_suggest(task: str) -> Path | None:
    """Resolve o caminho da task ou imprime mensagem específica e retorna None.

    CR-004 (S1): três call sites (--report, --judge, --audit) caíam na mesma
    mensagem vaga "não encontrado. Execute o ciclo primeiro" para casos
    distintos. Esta função distingue:

      a) repo sem nenhuma task em .kata/  → sugere `kata --init <nome>`
      b) há tasks mas `task` (vindo de _pick_task ou --task) não bate       →
         lista as existentes
      c) a task existe mas o YAML não (improvável; corrida)                  →
         mensagem original

    Retorna o Path se a task existe, None se não existe (já tendo imprimido
    a mensagem de erro adequada). O caller decide se faz sys.exit(1).
    """
    path = _task_path(task)
    if path.exists():
        return path
    existentes = sorted(p.stem for p in _kata_dir().glob(f"*{_ext()}") if p.stem != "config")
    if not existentes:
        print(f"⚠  Nenhuma tarefa em {_kata_dir()}. Rode `kata --init <nome>` primeiro.")
        return None
    print(f"⚠  {path.name} não encontrado. Tarefas existentes em {_kata_dir()}:")
    for i, name in enumerate(existentes, 1):
        print(f"  {i}. {name}")
    print("Rode `kata --task <nome>`, ou crie uma nova com `kata --init <nome>`.")
    return None


def _run_git(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Executa um comando git capturando saída, com defaults sobrescreíveis.

    Nome distinto de kata.verify._run de propósito: são helpers diferentes,
    com assinaturas diferentes, e judge.py importa o de verify. Dois `_run`
    homônimos no mesmo projeto é convite a erro de manutenção.

    Defaults (capture_output, text, cwd) podem ser sobrescritos via kwargs
    sem causar colisão de argumentos.
    """
    defaults: dict[str, Any] = {"capture_output": True, "text": True, "cwd": _cwd()}
    defaults.update(kwargs)
    return subprocess.run(cmd, **defaults)


def _changed_paths() -> list[str]:
    """Arquivos que a tarefa alterou, segundo o git.

    Usa diff contra HEAD para incluir staged e unstaged, com fallback para
    repositórios sem commit. Untracked são somados sempre, porque arquivos
    novos nunca aparecem em `git diff`.
    """
    result = _run_git(["git", "diff", "HEAD", "--name-only"])
    if result.returncode == 0:
        rastreados = [f for f in result.stdout.strip().split("\n") if f.strip()]
    else:
        result = _run_git(["git", "diff", "--name-only"])
        rastreados = [f for f in result.stdout.strip().split("\n") if f.strip()]
    if result.returncode != 0 or not rastreados:
        rastreados = [
            f
            for f in _run_git(["git", "diff", "--cached", "--name-only"]).stdout.strip().split("\n")
            if f.strip()
        ]
    novos = untracked_files()
    vistos = set(rastreados)
    return rastreados + [f for f in novos if f not in vistos]


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


# As chaves de verificação são papéis, mas carregam nome de ferramenta Python
# por serem o mesmo vocabulário que o schema da tarefa persiste (`ruff_clean`,
# `tests_pass`). Renomear o schema é migração à parte; exibir o papel não é, e
# "✅ ruff" num projeto JS é ruído que confunde quem lê o veredito.
_ROLE_LABELS = {"ruff": "lint", "pytest": "teste", "coverage": "coverage"}


def _print_judge_verdict(result: JudgeResult) -> None:
    """Imprime o veredito do juiz adversarial."""
    verdict_icon = {
        "VERIFIED": "✅",
        "VERIFIED WITH CAVEATS": "⚠️",
        "UNVERIFIABLE": "❓",
        "REFUTED": "❌",
    }
    icon = verdict_icon.get(result.verdict, "❓")
    print(f"\n{icon}  VEREDITO: {result.verdict}")
    print()

    if result.claims:
        print("  Claims verificadas:")
        for c in result.claims:
            print(f"    • {c}")
        print()

    if result.unverifiable_claims:
        print("  Claims aceitas sem verificação (não re-executáveis):")
        for c in result.unverifiable_claims:
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

    if result.blind_spots:
        print("  Pontos cegos (o juiz não conseguiu observar):")
        for b in result.blind_spots:
            print(f"    ❓ {b}")
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
            print(f"    {status} {_ROLE_LABELS.get(check, check)}")
        print()

    print("─" * 58)
    print(f"\n{icon}  KATA JUDGE — {result.verdict}")
    print()


# ── step implementations ────────────────────────────────────────────────


def _capture_base_commit(data: dict[str, Any], task: str | None = None) -> dict[str, Any]:
    """Registra o HEAD do git no início da tarefa, uma única vez.

    O JUDGE usa esse commit como ponto de comparação. Sem ele, o JUDGE só
    enxerga o diff não commitado (unstaged/staged) e fica cego assim que
    a tarefa é commitada — exatamente o estado de uma tarefa "concluída",
    que é o caso que o JUDGE existe para verificar.
    """
    if data.get("base_commit"):
        return data
    result = _run_git(["git", "rev-parse", "HEAD"])
    sha = result.stdout.strip()
    if result.returncode == 0 and sha:
        data["base_commit"] = sha
        if task:
            record_baseline_ref(task, sha, cwd=_cwd())
    return data


def _avisa_domain_desconhecido(data: dict[str, Any]) -> None:
    """Avisa quando a tarefa declara um domínio sem adapter conhecido.

    O orquestrador só carrega adapters por nome `kata-<domínio>`; um valor
    fora da lista (typo, domínio futuro) roda o ciclo inteiro sem o adapter,
    em silêncio — exatamente o modo de falha que a Fase 0.5 manda não
    improvisar (R10-21). Aviso, não erro: o ciclo continua em `coding`.
    """
    domain = data.get("domain", "coding")
    if domain == "coding":
        return
    adapters = {d.removeprefix("kata-") for d in DOMAIN_SKILLS}
    if domain not in adapters:
        conhecidos = ", ".join(sorted(adapters | {"coding"}))
        print(
            f"  ⚠  Domínio '{domain}' não tem adapter conhecido "
            f"(disponíveis: {conhecidos}) — o ciclo roda sem ele."
        )


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
        # `skipped`, não `answered`: nenhum humano respondeu nada aqui. Marcar
        # como respondido fazia esta fase ser saltada para sempre, inclusive
        # num ciclo interativo posterior na mesma tarefa.
        data["fit"] = {
            "trivial": False,
            "route": "code-loop",
            "reason": "non-interactive mode",
            "answered": False,
            "skipped": True,
        }
        return data

    _print_header("0. FIT — Classificação da tarefa")

    files, lines = diff_stats()
    trivial = is_trivial(files, lines)

    print(f"  diff: {len(files)} arquivo(s), {lines} linha(s) alteradas")
    if trivial:
        print("  ↳ tarefa parece trivial (<=1 arquivo, <10 linhas)")
        trivial = _confirm(
            "  A mudança não altera comportamento e não exige pesquisa?",
            default=False,
        )
        if not trivial:
            print("  ↳ gates completos serão mantidos por segurança")
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

    # `answered` fecha o guard no topo desta função: sem gravá-la, FIT
    # repergunta a cada retomada da tarefa. think e intent já gravavam a sua.
    data["fit"] = {
        "trivial": trivial,
        "route": route,
        "reason": reason or f"Rota {choice} escolhida pelo usuário",
        "answered": True,
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
        # `skipped`, não `answered`: nenhum humano respondeu nada aqui. Marcar
        # como respondido fazia esta fase ser saltada para sempre, inclusive
        # num ciclo interativo posterior na mesma tarefa.
        data["think"] = {
            "problem": "",
            "assumptions": [],
            "alternatives": [],
            "unknowns": "",
            "answered": False,
            "skipped": True,
        }
        data["done"] = ""
        return data

    print("Pergunte-se:")
    problem = input("  Qual o problema exato que estou resolvendo? ").strip()
    assumptions_raw = input("  Quais assumptions estou fazendo? (separadas por ;) ").strip()
    alternatives_raw = input("  Quais alternativas considerei? (separadas por ;) ").strip()
    unknowns = input("  O que NÃO sei? (preciso perguntar antes?) ").strip()
    # Fable Step 1: definir "pronto" ANTES da evidência, com verificação
    # nomeada ("done = este teste passa, o build fica verde, esta página
    # renderiza"). O VERIFY confronta este critério declarado com o resultado
    # final — sem isso, o critério só existe depois que tudo já foi feito.
    done = input("  O que é 'pronto'? (critério de sucesso + como vou verificar) ").strip()

    data["think"] = {
        "problem": problem,
        "assumptions": [a.strip() for a in assumptions_raw.split(";") if a.strip()],
        "alternatives": [a.strip() for a in alternatives_raw.split(";") if a.strip()],
        "unknowns": unknowns,
        "answered": True,
    }
    data["done"] = done
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
        # `skipped`, não `answered`: nenhum humano respondeu nada aqui. Marcar
        # como respondido fazia a fase ser saltada para sempre, inclusive num
        # ciclo interativo posterior na mesma tarefa (mesmo padrão do R7-1
        # para FIT/THINK/INTENT).
        data["simplify"] = {
            "minimum_code": True,
            "no_single_use_abstractions": True,
            "no_speculative_config": True,
            "answered": False,
            "skipped": True,
        }
        return data

    # Mostra diff stat
    has_changes = False
    result = _run_git(["git", "diff", "HEAD", "--stat"])
    if result.returncode == 0 and result.stdout.strip():
        print("git diff --stat:")
        print(result.stdout)
        has_changes = True
    elif result.returncode != 0:
        result = _run_git(["git", "diff", "--stat"])
        if result.stdout.strip():
            print("git diff --stat:")
            print(result.stdout)
            has_changes = True
    if not has_changes:
        result = _run_git(["git", "diff", "--cached", "--stat"])
        if result.stdout.strip():
            print("git diff --cached --stat (staged):")
            print(result.stdout)
            has_changes = True

    # Arquivos novos não aparecem em nenhum `git diff`. Sem listá-los, uma
    # tarefa que só cria arquivos passava por SIMPLIFY sem uma pergunta
    # sequer, e o YAML registrava o checklist como aprovado.
    novos, linhas_novas = untracked_stats()
    if novos:
        print(f"arquivos novos (untracked) — {linhas_novas} linha(s):")
        for f in novos:
            print(f"  {f}")
        print()
        has_changes = True

    if not has_changes:
        print("(nenhuma alteração detectada — pulando confirmações)")

    simplify = data.get("simplify", {})
    if has_changes:
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
    else:
        simplify["minimum_code"] = True
        simplify["no_single_use_abstractions"] = True
        simplify["no_speculative_config"] = True
    # Interativo: alguém respondeu — o audit pode graduar como followed.
    simplify["answered"] = True
    simplify["skipped"] = False
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
        # `skipped`, não `answered`: nenhum humano respondeu nada aqui. Marcar
        # como respondido fazia esta fase ser saltada para sempre, inclusive
        # num ciclo interativo posterior na mesma tarefa.
        data["intent"] = {
            "code_does": "",
            "check_expects": "",
            "spec_says": "",
            "all_agree": True,
            "answered": False,
            "skipped": True,
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
        data["surgical"] = {
            "files": [],
            "removed_imports_clean": True,
            "answered": False,
            "skipped": True,
        }
        return data

    files = _changed_paths()

    surgical = data.get("surgical", {})
    file_checks: list[dict[str, Any]] = []

    if files:
        print("Arquivos alterados:")
        for f in files:
            necessary = _confirm(f"  {f} — necessário para esta tarefa?", default=True)
            file_checks.append({"path": f, "necessary": necessary})
        surgical["removed_imports_clean"] = _confirm(
            "  Imports removidos são só os que sua mudança tornou inúteis?"
        )
    else:
        print("(nenhum arquivo alterado detectado — pulando confirmações)")
        surgical["removed_imports_clean"] = True

    surgical["files"] = file_checks
    # Interativo: alguém respondeu — o audit pode graduar como followed.
    surgical["answered"] = True
    surgical["skipped"] = False
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
    config: VerifyConfig | None = None,
) -> dict[str, Any]:
    """Fase 4: GOAL-DRIVEN — verificação de qualidade (lint + teste + coverage)."""
    _print_header("4. GOAL-DRIVEN — Verificação de qualidade")
    # Parte do verify existente (ex.: attempts de uma execução anterior) para
    # que o contador de tentativas sobreviva entre retomadas da tarefa.
    verify: dict[str, Any] = dict(data.get("verify", {}))
    all_ok = True

    results = run_all(
        ruff_paths=ruff_paths,
        test_paths=test_paths,
        ignore=ignore,
        cov_source=cov_source,
        gate=gate,
        config=config,
    )

    # ── lint ──
    ruff_res: VerifyResult = results["ruff"]
    print(f"▶ {ruff_res.details.get('command', 'lint')}")
    verify["ruff_clean"] = ruff_res.ok
    if ruff_res.ok:
        print("  ✅ limpo")
    else:
        all_ok = False
        print("  ❌ falhou — saída:")
        for line in ruff_res.output.split("\n"):
            print(f"     {line}")

    # ── teste ──
    pytest_res: VerifyResult = results["pytest"]
    print(f"\n▶ {pytest_res.details.get('command', 'test')}")
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
    # Fable Step 1: o critério foi declarado no THINK, antes da evidência.
    # O VERIFY confronta o declarado com o resultado final em vez de apenas
    # perguntar "está satisfeito?" a um critério que só existe agora.
    done = data.get("done", "")
    if done:
        print(f"  (declarado no THINK: {done})")
    if task == "check-only":
        success_met = True
        print("  (modo check-only — assumido satisfeito)")
    else:
        success_met = _confirm("  O critério de sucesso da tarefa está satisfeito?")
    verify["success_criteria_met"] = success_met
    if not success_met:
        all_ok = False

    # Hard bound (Fable Step 5): contador de tentativas de verificação
    # persistido na tarefa. Após MAX_VERIFY_ATTEMPTS falhas, o ciclo devolve
    # a tarefa ao usuário com o que foi tentado, o output real e a hipótese
    # atual — não fica repetindo o mesmo fix-verify indefinidamente.
    attempts = int(verify.get("attempts") or 0) + 1
    verify["attempts"] = attempts
    verify["hand_back"] = not all_ok and attempts >= MAX_VERIFY_ATTEMPTS
    if verify["hand_back"]:
        print(
            f"  ⚠  {attempts} tentativas de verificação falharam — devolvendo a tarefa ao usuário."
        )

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
    defect_fixed = not intent.get("all_agree", True) or _confirm(
        "  Um defeito foi corrigido? Deseja buscar padrão similar?", default=False
    )

    # `defect_fixed` é gravado porque é a única evidência de que um defeito
    # foi corrigido: sem ele, _detect_twins_owed não tem como distinguir uma
    # correção de defeito de uma tarefa aprovada qualquer.
    if not defect_fixed:
        data["twins"] = {
            "searched": False,
            "pattern": "",
            "result": "",
            "defect_fixed": False,
        }
        return data

    if not sys.stdin.isatty():
        # Mesmo contrato dos ramos de erro e padrão vazio (R10-13): nada foi
        # confirmado — `defect_fixed: True` aqui faria o audit graduar a
        # tarefa como faked por uma busca que ninguém pôde fazer.
        data["twins"] = {
            "searched": False,
            "pattern": "",
            "result": "",
            "defect_fixed": False,
        }
        return data

    _print_header("TWIN CHECK — Busca de padrão recorrente")

    pattern = input("  Padrão a buscar (regex): ").strip()
    if not pattern:
        data["twins"] = {
            "searched": False,
            "pattern": "",
            "result": "",
            "defect_fixed": False,
        }
        return data

    print(f"\n  Buscando '{pattern}' no projeto...")
    search_result = search_pattern(pattern, cwd=_cwd())

    if search_result.error:
        print(f"  ❌ Busca inválida ou interrompida: {search_result.error}")
        # `defect_fixed` fica False: a busca falhou, nada foi confirmado.
        # Com True, o audit graduaria "faked" (defeito declarado corrigido
        # sem busca) por uma falha de ferramenta (R10-13).
        data["twins"] = {
            "pattern": pattern,
            "result": search_result.error,
            "searched": False,
            "defect_fixed": False,
            "matches_count": 0,
            "files_count": 0,
            "fix_applied": False,
        }
        return data

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
        if fix_others:
            print("  ⚠  O CLI não edita ocorrências; a correção não foi aplicada.")
            fix_others = False

    result_str = (
        f"{search_result.total_files} arquivo(s), {len(search_result.matches)} ocorrência(s)"
    )
    data["twins"] = {
        "pattern": pattern,
        "result": result_str,
        "searched": True,
        "defect_fixed": True,
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


_DOC_SUFFIXES = frozenset({".md", ".rst", ".txt"})


def _detect_intent_owed(data: dict[str, Any]) -> bool:
    """Detecta se INTENT line é devida (comportamento mudou).

    Devida quando pelo menos um arquivo alterado não é documentação. Antes
    bastava VERIFY ter rodado, o que tornava INTENT devida em toda tarefa —
    inclusive numa mudança só de docs, onde não há "o que o código FAZ" a
    declarar.

    A fonte preferida é surgical.files, porque SURGICAL é a fase que
    estabelece o que mudou. Mas em modo não-interativo SURGICAL grava uma
    lista vazia, e olhar só para ela fazia INTENT nunca ser devida em
    execuções headless — o caveat "INTENT não documentada" sumia
    justamente onde não há ninguém para notar a ausência. Sem declaração,
    cai para o git.
    """
    declared = [f.get("path", "") for f in data.get("surgical", {}).get("files", [])]
    paths = [p for p in declared if p] or _changed_paths()
    return any(Path(p).suffix.lower() not in _DOC_SUFFIXES for p in paths)


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
    """Detecta se TWINS line é devida (defeito corrigido, padrão pode se repetir).

    "Testes e coverage passaram" era um dos sinais, o que tornava TWINS
    devida em toda tarefa aprovada — passar nas verificações é o estado
    normal de uma tarefa concluída, não evidência de defeito corrigido.
    Sobram os sinais que de fato indicam correção de defeito.
    """
    # Sinal 1: intent teve conflito (spec betrayal potencial)
    intent = data.get("intent", {})
    if intent.get("answered") and not intent.get("all_agree"):
        return True
    # Sinal 2: o TWIN CHECK registrou que um defeito foi corrigido
    twins = data.get("twins", {})
    return bool(twins.get("defect_fixed") or twins.get("pattern"))


def _step_artifact(task: str, data: dict[str, Any]) -> dict[str, Any]:
    """Fase 4.5: ARTIFACT — verificar linhas devidas no relatório.

    Inspirado no artifact gate do fable-method: antes de finalizar, verificar
    se INTENT, AUTH, PENDING e TWINS estão presentes quando devidos.
    """
    _print_header("4.5 ARTIFACT — Verificação de linhas devidas")

    intent = data.get("intent", {})

    # INTENT: devida se a tarefa alterou algum arquivo que não é documentação
    intent_owed = _detect_intent_owed(data)
    intent_present = bool(_format_intent_line(intent))

    # AUTH: devida se ação irreversível foi tomada
    auth_owed = _detect_auth_owed(data)
    auth_present = bool(_format_auth_line(data.get("auth", {})))

    # PENDING: devida se docs prescrevem follow-up e não foi tomado
    pending_owed = _detect_pending_owed(data)
    pending_present = bool(_format_pending_line(data.get("pending", {})))

    # TWINS: devida se defeito foi corrigido
    twins_owed = _detect_twins_owed(data)
    twins_present = bool(_format_twins_line(data.get("twins", {})))

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
                        "action_taken": True,
                        "authorized": True,
                        "action": action,
                        "quote": auth_line,
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
                        "code_does": code,
                        "check_expects": check,
                        "spec_says": spec,
                        "all_agree": True,
                        "answered": True,
                    }

        # Recompute present flags after user input so YAML reflects reality.
        intent = data.get("intent", {})
        checks["intent_present"] = bool(_format_intent_line(intent))
        checks["auth_present"] = bool(_format_auth_line(data.get("auth", {})))
        checks["pending_present"] = bool(_format_pending_line(data.get("pending", {})))
        checks["twins_present"] = bool(_format_twins_line(data.get("twins", {})))
    else:
        print("  ✅ Todas as linhas devidas estão presentes")

    data["artifact"] = checks
    return data


def _detect_scratch_files() -> list[str]:
    """Detecta arquivos temporários/de lixo no diff.

    Usa is_debris_file (kata.judge) para que CLI e JUDGE apliquem a mesma
    regra. A cópia que existia aqui casava a substring "temp" e marcava
    `templates/`, `temperature.py` e `attempt_parser.py` como detrito.

    A lista vem de _changed_paths, que inclui untracked: detrito recém-criado
    e ainda não adicionado ao índice é justamente o caso mais comum.
    """
    return [f for f in _changed_paths() if is_debris_file(f)]


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
    domain = data.get("domain", "coding")
    if domain != "coding":
        print(f"  Domínio: {domain}")

    if think.get("problem"):
        print(f"  Problema: {think['problem']}")

    # Fable Step 1: o critério de sucesso declarado no THINK aparece no
    # relatório — o leitor vê o que era "pronto" e pode confrontar com o
    # resultado.
    done = data.get("done", "")
    if done:
        print(f"  Critério declarado: {done}")

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
    # `or 0.0` e não `get(..., 0)`: a chave existe com valor None no template
    # de --init e nos YAMLs escritos à mão pelas skills, então o default do
    # get nunca entra e o format de None levanta TypeError.
    cov_pct = verify.get("coverage_pct") or 0.0
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
    # Hard bound (Fable Step 5): estourado o limite de tentativas, o relatório
    # diz explicitamente que a tarefa foi devolvida ao usuário — com o que foi
    # tentado, o output real e a hipótese atual — em vez de um "rejeitado"
    # genérico que convida a mais um ciclo fix-verify.
    if verify.get("hand_back"):
        caveats.append(
            f"hand back: {verify.get('attempts', 0)} tentativa(s) de verificação "
            "falharam — devolvendo ao usuário com o que foi tentado, o output "
            "real e a hipótese atual"
        )
    # Fase preenchida com default em modo não-interativo não foi verificada por
    # ninguém. Um relatório que não diz isso apresenta como cumprido um gate
    # que só foi contornado. As cinco fases com default headless: FIT, THINK,
    # INTENT (R7-1) e SIMPLIFY, SURGICAL (R9-2).
    puladas = [
        nome.upper()
        for nome in ("fit", "think", "intent", "simplify", "surgical")
        if data.get(nome, {}).get("skipped")
    ]
    if puladas:
        caveats.append(
            f"{', '.join(puladas)} preenchida(s) com default em modo não-interativo — "
            "ninguém respondeu"
        )
    scratch = _detect_scratch_files()
    if scratch:
        caveats.append(f"Arquivos temporários detectados: {', '.join(scratch)}")
    artifact = data.get("artifact", {})
    if artifact.get("intent_owed") and not artifact.get("intent_present"):
        caveats.append("INTENT não documentada — comportamento alterado sem registro de intenção")
    if artifact.get("auth_owed") and not artifact.get("auth_present"):
        caveats.append("AÇÃO EXTERNA sem autorização documentada (AUTH ausente)")
    if artifact.get("pending_owed") and not artifact.get("pending_present"):
        caveats.append("PENDING não documentada — follow-up prescrito sem registro")
    if artifact.get("twins_owed") and not artifact.get("twins_present"):
        caveats.append("TWINS não documentada — busca de recorrência ausente")

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


def _init_task(task: str) -> bool:
    """Cria template .kata/<task>.yaml para uma nova tarefa."""
    path = _task_path(task)
    if path.exists():
        print(f"⚠  {path} já existe. Use o modo interativo para continuar.")
        return False

    template: dict[str, Any] = {
        "task": task,
        "status": "draft",
        "domain": "coding",
        # Fable Step 1: critério de sucesso declarado no THINK, antes da
        # evidência; exibido no VERIFY e no relatório.
        "done": "",
        "fit": {
            "trivial": False,
            "route": "code-loop",
            "reason": "",
            "answered": False,
            "skipped": False,
        },
        "think": {
            "problem": "",
            "assumptions": [],
            "alternatives": [],
            "unknowns": "",
            "answered": False,
            "skipped": False,
        },
        "simplify": {
            "minimum_code": True,
            "no_single_use_abstractions": True,
            "no_speculative_config": True,
            "notes": "",
            "answered": False,
            "skipped": False,
        },
        "intent": {
            "code_does": "",
            "check_expects": "",
            "spec_says": "",
            "all_agree": True,
            "conflict_resolution": "",
            "answered": False,
            "skipped": False,
        },
        "surgical": {
            "files": [],
            "removed_imports_clean": True,
            "answered": False,
            "skipped": False,
        },
        "verify": {
            "ruff_clean": None,
            "tests_pass": None,
            "coverage_pct": None,
            "coverage_pass": None,
            "success_criteria_met": None,
            # Fable Step 5: hard bounds. attempts conta execuções do VERIFY;
            # hand_back é true quando o limite foi estourado com falha e a
            # tarefa foi devolvida ao usuário.
            "attempts": 0,
            "hand_back": False,
        },
        "auth": {"action_taken": False, "authorized": False, "action": "", "quote": ""},
        "pending": {"action": "", "documented": False},
        "twins": {
            "searched": False,
            "pattern": "",
            "result": "",
            "defect_fixed": False,
            "matches_count": 0,
            "files_count": 0,
            "fix_applied": False,
        },
        "preflight": {"skills_missing": []},
        "artifact": {
            "intent_owed": False,
            "intent_present": False,
            "auth_owed": False,
            "auth_present": False,
            "pending_owed": False,
            "pending_present": False,
            "twins_owed": False,
            "twins_present": False,
        },
    }
    template = _capture_base_commit(template, task=task)
    _save_task(path, template)
    print(f"✅  {path} criado. Preencha as respostas com o modo interativo.")
    return True


# ── audit ────────────────────────────────────────────────────────────────


# Risco concreto que cada fase faked/skipped cria, no estilo do
# `/fable-method audit` do The Fable Method: cada skip/fake nomeia o que
# deixou de ser observado e o que isso permite que aconteça.
_AUDIT_RISKS: dict[str, str] = {
    "fit": "rota e trivialidade não classificadas por humano — esforço pode ser "
    "desperdiçado em tarefa trivial ou mal roteada",
    "think": "assumptions nunca declaradas — qualquer solução pode atacar o problema errado",
    "simplify": "minimalidade afirmada sem ninguém confrontar o diff com o "
    "pedido — abstrações especulativas podem passar sem revisão",
    "surgical": "cada arquivo declarado necessário sem ninguém conferir — "
    "escopo extra pode entrar sem ser notado",
    "intent": "código, teste e spec podem discordar sem registro — "
    "comportamento muda sem intenção verificada",
    "verify": "sucesso afirmado sem evidência de execução — a tarefa pode "
    "estar aprovada sobre nada",
    "twins": "defeito corrigido sem busca de recorrência — o mesmo padrão "
    "pode se repetir em outros lugares",
    "preflight": "fase(s) executada(s) sem a skill correspondente — as "
    "instruções da fase não foram carregadas, e o que ficou registrado "
    "veio de improviso",
}

# Para cada fase com semântica answered/skipped, a chave cujo conteúdo real
# prova que a fase foi de fato respondida (não preenchida com default).
# simplify/surgical entram no mesmo contrato (R10-22): um bloco `answered:
# true` escrito à mão SEM as chaves de conteúdo é tão faked quanto um THINK
# com problem vazio.
_AUDIT_CONTENT_KEY: dict[str, str] = {
    "fit": "reason",
    "think": "problem",
    "intent": "code_does",
    "simplify": "minimum_code",
    "surgical": "files",
}


def _audit_task(data: dict[str, Any]) -> list[dict[str, str]]:
    """Gradua as fases da tarefa como followed / skipped / faked.

    Inspirado no `/fable-method audit` do Fable Method: cada passo é
    *followed* (observado), *skipped* (pulado com registro) ou *faked*
    (afirmado sem observação). Para cada skip/fake, nomeia o risco concreto
    que criou.

    - followed: fase com `answered: true` e conteúdo real (ex.: think.problem
      não vazio);
    - skipped: fase com `skipped: true` (documentado);
    - faked: fase com `answered: true` mas conteúdo default/vazio (o padrão
      do R7-1) OU verify afirmando sucesso sem evidência correspondente OU
      twins declarando defeito sem busca.

    Fases não iniciadas (nem answered nem skipped) ficam de fora: uma tarefa
    em andamento não tem skip/fake a auditar.
    """
    achados: list[dict[str, str]] = []

    # Tarefa malformada não pode derrubar a graduação com traceback: YAML
    # escrito à mão é entrada suportada e o CLI não valida schema antes de
    # auditar. Uma seção que não é mapa (`surgical: true`) ou uma lista no
    # topo do arquivo davam AttributeError — e traceback sai com código 1, o
    # mesmo de "audit sujo", tornando arquivo quebrado indistinguível de fase
    # fingida (R11-1). Sem seção legível não há o que graduar: lista vazia.
    if not isinstance(data, dict):
        return achados

    def bloco(nome: str) -> dict[str, Any]:
        secao = data.get(nome)
        return secao if isinstance(secao, dict) else {}

    # Preflight primeiro: se as instruções de uma fase não foram sequer
    # carregadas, o que as outras graduações leem foi escrito sem elas.
    faltando = bloco("preflight").get("skills_missing") or []
    if faltando:
        achados.append(
            {
                "fase": "preflight",
                "status": "degraded",
                "risco": f"{_AUDIT_RISKS['preflight']} — faltou: {', '.join(faltando)}",
            }
        )

    for fase in ("fit", "think", "intent"):
        secao = bloco(fase)
        if secao.get("skipped"):
            achados.append({"fase": fase, "status": "skipped", "risco": _AUDIT_RISKS[fase]})
            continue
        if not secao.get("answered"):
            continue
        if str(secao.get(_AUDIT_CONTENT_KEY[fase], "")).strip():
            achados.append({"fase": fase, "status": "followed", "risco": ""})
        else:
            achados.append({"fase": fase, "status": "faked", "risco": _AUDIT_RISKS[fase]})

    for fase in ("simplify", "surgical"):
        secao = bloco(fase)
        if secao.get("skipped"):
            achados.append({"fase": fase, "status": "skipped", "risco": _AUDIT_RISKS[fase]})
            continue
        if not secao.get("answered"):
            continue
        if _AUDIT_CONTENT_KEY[fase] in secao:
            achados.append({"fase": fase, "status": "followed", "risco": ""})
        else:
            achados.append({"fase": fase, "status": "faked", "risco": _AUDIT_RISKS[fase]})

    verify = bloco("verify")
    evidencias = [verify.get(chave) for chave in ("ruff_clean", "tests_pass", "coverage_pass")]
    if verify.get("success_criteria_met") and not any(evidencias):
        achados.append({"fase": "verify", "status": "faked", "risco": _AUDIT_RISKS["verify"]})
    elif any(evidencias):
        achados.append({"fase": "verify", "status": "followed", "risco": ""})

    twins = bloco("twins")
    if twins.get("defect_fixed") and not twins.get("searched"):
        achados.append({"fase": "twins", "status": "faked", "risco": _AUDIT_RISKS["twins"]})
    elif twins.get("searched"):
        achados.append({"fase": "twins", "status": "followed", "risco": ""})

    return achados


def _print_audit(achados: list[dict[str, str]]) -> None:
    """Imprime a graduação followed/skipped/faked com os riscos concretos."""
    icones = {"followed": "✅", "skipped": "⏭️", "faked": "❌", "degraded": "⚠️"}
    if not achados:
        print("  (nenhuma fase iniciada — tarefa em andamento)")
        print()
        return
    for a in achados:
        print(f"  {icones.get(a['status'], '•')} {a['fase'].upper()}: {a['status']}")
        if a["risco"]:
            print(f"     ⚠ {a['risco']}")
    print()
    fakes = [a for a in achados if a["status"] == "faked"]
    skips = [a for a in achados if a["status"] == "skipped"]
    degradadas = [a for a in achados if a["status"] == "degraded"]
    if fakes or skips or degradadas:
        resumo = f"{len(fakes)} fake(s) e {len(skips)} skip(s)"
        if degradadas:
            resumo += f", {len(degradadas)} degradada(s)"
        print(f"  ⚠  Audit encontrou {resumo}.")
    else:
        print("  ✅  Audit limpo — todas as fases foram seguidas.")


def _print_doctor(estados: list[InstallStatus]) -> int:
    """Imprime o estado de instalação. Devolve o exit code.

    Instalação **parcial** é o que reprova, e não a ausente: quem nunca
    instalou um frontend não perde nada, mas quem tem 9 das 10 skills roda o
    ciclo inteiro e perde uma fase sem ser avisado — o orquestrador tenta
    carregar a que falta, falha, e o modelo improvisa a fase a partir do
    nome dela.
    """
    parciais = 0
    for e in estados:
        if e.completo:
            print(f"  ✅ {e.frontend}: {len(e.instaladas)} skill(s) em {e.config_dir}")
        elif e.ausente:
            print(f"  •  {e.frontend}: não instalado ({e.config_dir})")
        else:
            parciais += 1
            print(f"  ❌ {e.frontend}: instalação PARCIAL em {e.config_dir}")
            faltando = list(e.faltando)
            if e.agente_esperado and not e.agente_instalado:
                faltando.append("agent/kata.md")
            print(f"     {len(e.instaladas)} instalada(s), faltando: {', '.join(faltando)}")
    print()

    # Domain skills são opcionais: avisar, mas não reprovar.
    domain_missing = doctor_domain()
    domain_warnings = 0
    for frontend, faltando in domain_missing.items():
        if faltando:
            domain_warnings += 1
            print(f"  ℹ️  {frontend}: domain skills opcionais faltando: {', '.join(faltando)}")
    if domain_warnings:
        print("     Domain adapters só são necessárias quando a tarefa usa um")
        print("     domínio diferente de coding. Instale com `make reinstall` /")
        print("     `make reinstall-claude-code` se for usar devops/data-analysis/etc.")
        print()

    if parciais:
        print(f"  ⚠  {parciais} frontend(s) com instalação parcial.")
        print("     O ciclo vai tentar carregar a skill que falta, não conseguir,")
        print("     e improvisar a fase — que é o que o --audit chama de fase fingida.")
        print("     Rode `make reinstall` / `make reinstall-claude-code`.")
    elif all(e.ausente for e in estados):
        print("  ⚠  Nenhum frontend instalado. Rode `make install` ou")
        print("     `make install-claude-code`. O CLI `kata` funciona sem isso.")
    else:
        print("  ✅  Instalação completa.")
    print()
    return 1 if parciais else 0


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
        default=_detect_cov_source(),
        help="Pacote fonte para coverage (default: %(default)s)",
    )
    parser.add_argument(
        "--gate",
        type=float,
        default=None,
        help=(
            "Gate mínimo de coverage, em %%. Default: o `verify.gate` de "
            f".kata/config.yaml, ou {DEFAULT_GATE:.0f}"
        ),
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Confere se as skills de fase estão instaladas em cada frontend",
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
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Gradua as fases da tarefa: followed / skipped / faked (com risco concreto)",
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
    if args.audit and (args.init or args.plan or args.check_only or args.judge or args.report):
        parser.error(
            "--audit é mutuamente exclusivo com --init, --plan, --check-only, --judge e --report"
        )

    # --doctor não toca em tarefa nem precisa de .kata/: é sobre a
    # instalação das skills, e tem de funcionar de qualquer diretório.
    if args.doctor:
        _print_header("DOCTOR — Instalação das skills de fase")
        sys.exit(_print_doctor(doctor()))

    _kata_dir().mkdir(parents=True, exist_ok=True)

    # Comandos de verificação declarados pelo projeto alvo. Config quebrada
    # aborta em vez de cair no default: quem escreveu .kata/config.yaml quis
    # verificar de um jeito específico, e verificar de outro calado seria
    # reportar sucesso de algo que o projeto nunca pediu.
    try:
        config = load_verify_config()
    except ConfigError as exc:
        print(f"⚠  {exc}")
        sys.exit(1)

    # Precedência do gate: flag explícita > config do projeto > 70%.
    gate = args.gate if args.gate is not None else config.gate
    if gate is None:
        gate = DEFAULT_GATE

    if config.customizado:
        print(f"▶ verificações de {config_path()} (declaradas pelo projeto)")

    # Modo --init
    if args.init:
        created = _init_task(args.init)
        path = _task_path(args.init)
        if not created or not path.exists():
            return
        data = _deserialize(path.read_text(encoding="utf-8"))
        data = _capture_base_commit(data, task=args.init)
        _avisa_domain_desconhecido(data)
        _save_task(path, data)
        data = _step_fit(args.init, data)
        _save_task(path, data)
        data = _step_think(args.init, data)
        _save_task(path, data)
        print(f"\n📝  FIT + THINK salvos em {path}")
        return

    # Modo --report (outcome-first)
    if args.report:
        task = args.task or _pick_task()
        path = _resolve_task_or_suggest(task)
        if path is None:
            sys.exit(1)
        data = _deserialize(path.read_text(encoding="utf-8"))
        _step_report(task, data)
        # Só `rejected` é falha. Uma tarefa em andamento (draft,
        # think-complete — o estado normal de `--plan`) está funcionando como
        # esperado; sair 1 ao consultar seu relatório equipara planejar a
        # falhar.
        sys.exit(1 if data.get("status") == "rejected" else 0)

    # Modo --judge (adversarial verification)
    if args.judge:
        task = args.task or _pick_task()
        path = _resolve_task_or_suggest(task)
        if path is None:
            sys.exit(1)
        data = _deserialize(path.read_text(encoding="utf-8"))
        _print_header(f"JUDGE — Verificação adversarial de '{task}'")
        result = judge_task(
            data,
            ruff_paths=args.ruff_paths,
            test_paths=args.test_paths,
            ignore=args.ignore,
            cov_source=args.cov_source,
            gate=gate,
            config=config,
        )
        _print_judge_verdict(result)
        # Só REFUTED é falha. "VERIFIED WITH CAVEATS" significa que o juiz
        # verificou e aprovou com ressalvas de severidade baixa/média;
        # tratá-lo como falha equipara ressalva a fraude grave e leva o CI
        # a ignorar o exit code por inútil.
        #
        # UNVERIFIABLE também sai 0, e a escolha é deliberada: o juiz não
        # encontrou nada errado, apenas não teve como olhar. Reprovar por
        # isso quebraria o `--judge` de todo projeto não-Python — que é
        # justamente quem mais o recebe — antes que houvesse alternativa a
        # oferecer. O veredito e a seção de pontos cegos dizem em voz alta
        # o que não foi observado; quem quiser barrar no CI lê o veredito.
        sys.exit(1 if result.verdict == "REFUTED" else 0)

    # Modo --audit (graduação followed/skipped/faked)
    if args.audit:
        task = args.task or _pick_task()
        path = _resolve_task_or_suggest(task)
        if path is None:
            sys.exit(1)
        data = _deserialize(path.read_text(encoding="utf-8"))
        _print_header(f"AUDIT — Graduação das fases de '{task}'")
        achados = _audit_task(data)
        _print_audit(achados)
        # 0 = audit limpo (nenhum fake/skip); 1 = há fakes/skips.
        sys.exit(1 if any(a["status"] != "followed" for a in achados) else 0)

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
            gate=gate,
            config=config,
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
    data = _capture_base_commit(data, task=task)
    _avisa_domain_desconhecido(data)
    _save_task(path, data)

    data = _step_fit(task, data)
    _save_task(path, data)

    fit_route = data.get("fit", {}).get("route", "code-loop")
    fit_trivial = data.get("fit", {}).get("trivial", False)

    if not fit_trivial or args.plan or fit_route in {"question", "plan-first"}:
        data = _step_think(task, data)
        _save_task(path, data)

    if fit_route == "question":
        _save_task(path, data)
        print(f"\n📝  Resultado salvo em {path}")
        return

    if args.plan or fit_route == "plan-first":
        _save_task(path, data)
        print(f"\n📝  Plano salvo em {path}")
        print("    Próximas fases: SIMPLIFY → SURGICAL → VERIFY")
        return

    if not fit_trivial:
        data = _step_simplify(task, data)
        _save_task(path, data)
        data = _step_intent(task, data)
        _save_task(path, data)
        data = _step_surgical(task, data)
        _save_task(path, data)

    data = _step_verify(
        task,
        data,
        ruff_paths=args.ruff_paths,
        test_paths=args.test_paths,
        ignore=args.ignore,
        cov_source=args.cov_source,
        gate=gate,
        config=config,
    )
    _save_task(path, data)
    if not fit_trivial:
        data = _step_twin(task, data)
        _save_task(path, data)
    data = _step_artifact(task, data)
    _save_task(path, data)
    _step_report(task, data)

    _save_task(path, data)
    print(f"\n📝  Resultado salvo em {path}")

    if data.get("status") == "rejected":
        sys.exit(1)


if __name__ == "__main__":
    main()
