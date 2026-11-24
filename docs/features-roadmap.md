# Features do Kata — inventário e roadmap

> Inventário revisado sobre a **v0.12.0**.
> As contagens de cenários e
> de extensões de linguagem são conferidas por `tests/test_docs_eval.py`; o
> commit exato de cada afirmação fica no histórico do Git.
> Fontes: `src/kata/*.py`, `phases/`, `eval/scenarios/`, `domains/`, `scripts/`.

## 1. O que o kata é hoje

Ferramenta de **qualidade para código gerado por agentes de IA**: um ciclo
Karpathy Development Cycle de 9 fases (FIT → THINK → SIMPLIFY → INTENT →
SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT) com verificação
adversarial (JUDGE) e auditoria de fases (AUDIT), entregue como CLI Python +
agente OpenCode + skills Claude Code.

## 2. Features existentes

### 2.1 CLI (`src/kata/`)

| Feature | Onde | Estado |
|---|---|---|
| Ciclo completo 9 fases (interativo e headless) | `cli.py` `_step_*` | ✅ |
| `--init`, `--plan`, `--check-only`, `--task`, `--judge`, `--report`, `--audit`, `--doctor`, `--stamp` | `cli.py` `main()` | ✅ |
| VERIFY e ARTIFACT avulsos: `--verify-task`, `--artifact-task` | `cli.py` `main()` | ✅ |
| Gate de CI por veredito exato: `--judge --require-verified` | `cli.py` `main()` | ✅ |
| REPORT, AUDIT e ARTIFACT independem do config de VERIFY e diagnosticam campos estruturais inválidos da tarefa | `cli.py` `_validate_task_view` e `main()` | ✅ |
| FIT gate + triviality gate | `fit.py` (lógica), `cli.py` (fluxo) | ✅ |
| Verificação ruff/pytest/coverage com gate (default 70%) e `--cov-fail-under` | `verify.py` | ✅ |
| Múltiplos sources de coverage via `--cov-source` | `verify.py`/`cli.py` (R12-02) | ✅ |
| JUDGE adversarial: 7 fraudes, pontos cegos, vereditos VERIFIED/CAVEATS/UNVERIFIABLE/REFUTED | `judge.py` | ✅ |
| Sondas de linguagem (10 famílias de sondas, 17 extensões: Python, JS/TS, Go, Ruby, Rust, Java/Kotlin, C#, PHP, Swift, Elixir/ExUnit) | `judge.py` `_LANGUAGES` | ✅ |
| Caminhos de teste declarados fora das convenções de nome (`verify.test_files`) | `config.py`, `judge.py` | ✅ |
| VERIFY → JUDGE com Node.js, Go e Rust reais no CI (`verify.profile: declared`) | `tests/test_verify_toolchain.py` | ✅ |
| `approved_commit` limita o diff do JUDGE ao fim da tarefa (R14) | `judge.py`/`cli.py` | ✅ |
| AUDIT — graduação de fases followed/skipped/faked/degraded | `report.py` `_audit_task` | ✅ |
| Config por projeto `.kata/config.yaml` (lint/typecheck/test/coverage) | `config.py` | ✅ |
| Config do advisor em `.kata/config.yaml` (`model`, `effort`, `skip_trivial`) | `config.py` `load_advisor_config` | ✅ |
| Verificação adversarial em 2 estágios (mecânica + semântica) | `judge.py` / `phases/kata-judge.md` | ✅ |
| Schema versionado da task (`schema_version: 1`) | `cli.py` `SCHEMA_VERSION` | ✅ |
| Quatro adapters opcionais: devops, data-analysis, research e docs | `domains/` e `skills.py` | ✅ |
| Doctor: checa instalação das skills de fase | `skills.py` | ✅ |

### 2.2 Frontends

| Frontend | Onde | Estado |
|---|---|---|
| Agente `@kata` OpenCode | `opencode/agent/kata.md` + 15 skills em `opencode/skills/` | ✅ |
| Subagente `kata-advisor` OpenCode (Hostile Reviewer) | `opencode/agents/kata-advisor.md` | ✅ |
| Orquestrador `kata` Claude Code | `claude-code/skills/` (16 skills, incluindo o orquestrador) | ✅ |
| Frontends Pi e Tau (`/skill:kata`, `/skill:kata-agile`) | `pi/skills/` e `tau/skills/` | ✅ |
| Frontend Codex (`$kata`, `$kata-agile`) | `codex/skills/` | ✅ |
| Ciclo curto opcional `kata-agile` | `phases/kata-agile.md` | ✅ |
| Fonte única das fases | `phases/` (12 arquivos) | ✅ |
| Build de skills (`build-skills`/`check-skills`) | `scripts/build_skills.py` | ✅ |
| Instaladores symlink (sh/ps1, OpenCode + Claude Code) | `scripts/install*.sh/.ps1` | ✅ |

### 2.3 Adversarial eval

| Feature | Onde | Estado |
|---|---|---|
| Harness de traps | `eval/run_traps.py` | ✅ |
| 26 cenários de trap (s01–s26) | `eval/scenarios/` | ✅ |
| Guarda de contagem de cenários em docs | `tests/test_docs_eval.py` (R12-04) | ✅ |

### 2.4 Instalação

| Rota | Onde | Estado |
|---|---|---|
| `pip install -e '.[dev]'` | README/DOCUMENTATION | ✅ |
| `pipx run --spec .` / `uv tool run --from .` (uso pontual) | README/DOCUMENTATION (R12 docs) | ✅ |
| `pipx install kata-dev` / `uv tool install kata-dev` (PyPI) | README/DOCUMENTATION | ✅ |
| `kata --install` empacota skills + agente + subagente `kata-advisor` | `install.py` / `src/kata/assets/` | ✅ |

## 3. Próximas melhorias propostas

| Prioridade | Item | Critério de aceite |
|---|---|---|
| Média | **Saída JSON versionada para JUDGE e AUDIT.** | Consumidores recebem veredito, achados e pontos cegos sem extrair texto do terminal. A saída humana e os códigos de saída padrão não mudam. |
| Média | **Diagnosticar o uso de diretórios em `surgical.files`.** JUDGE compara nomes de arquivos exatos; declarar um diretório não cobre seus descendentes. | O CLI explica a limitação antes do JUDGE e orienta a declarar os arquivos individualmente. Não aprovar subárvores por prefixo de forma implícita. |
| Baixa | **Sondas de mais linguagens**, conforme demanda. | Cada sonda vem com cenários de trabalho honesto, enfraquecimento detectável e limitações explícitas. |

Para tarefas antigas, não preencher `approved_commit` em massa por inferência:
carimbar apenas quando houver evidência do commit que realmente encerrou a
tarefa. As entregas anteriores (extração de `report.py`, quatro adapters e
publicação no PyPI) já constam no inventário, não no backlog.

## 4. Não-objetivos (fora de escopo até decisão)

- i18n das mensagens (plano 2026-07-10)
- Migrar para outro framework CLI (Typer/Click)
- Pydantic v2
- Adapter npm/npx (descartado pelo usuário em 2026-08-24 — "mantenha somente pipx/uv")

## 5. Critério de uso

`done` de cada sprint: `make check` verde, incluindo todos os cenários de trap.
Quando o item muda a lógica do JUDGE, reauditar também as tarefas de `.kata/`
em lote para descobrir regressões fora dos cenários.
