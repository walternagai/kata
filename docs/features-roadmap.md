# Features do Kata — inventário e roadmap

> Derivado do código real no HEAD `fa1a0a2` (v0.6.0), 2026-08-24.
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
| `--init`, `--plan`, `--check-only`, `--task`, `--judge`, `--report`, `--audit`, `--doctor` | `cli.py` `main()` | ✅ |
| FIT gate + triviality gate | `fit.py` (lógica), `cli.py` (fluxo) | ✅ |
| Verificação ruff/pytest/coverage com gate (default 70%) e `--cov-fail-under` | `verify.py` | ✅ |
| Múltiplos sources de coverage via `--cov-source` | `verify.py`/`cli.py` (R12-02) | ✅ |
| JUическое adversarial: 7 fraudes, pontos cegos, vereditos VERIFIED/CAVEATS/UNVERIFIABLE/REFUTED | `judge.py` | ✅ |
| Sondas de linguagem (10 linguagens, 15 extensões: Python, JS, TS, Go, Ruby, Rust, Java, Kotlin, C#, PHP, Swift) | `judge.py` `_LANGUAGES` | ✅ |
| `approved_commit` limita o diff do JUDGE ao fim da tarefa (R14) | `judge.py`/`cli.py` | ✅ |
| AUDIT — graduação de fases followed/skipped/faked | `cli.py` `_audit_task` | ✅ |
| Config por projeto `.kata/config.yaml` (lint/test/coverage verbatim) | `config.py` | ✅ |
| Schema versionado da task (`schema_version: 1`) | `cli.py` `SCHEMA_VERSION` | ✅ |
| Detecção de domínio + adapter `kata-devops` | `domains.py`/`domains/kata-devops.md` | ✅ |
| Doctor: checa instalação das skills de fase | `skills.py` | ✅ |

### 2.2 Frontends

| Frontend | Onde | Estado |
|---|---|---|
| Agente `@kata` OpenCode | `opencode/agent/kata.md` + 11 skills `opencode/skills/` | ✅ |
| Skill `kata` Claude Code | `claude-code/skills/` (12 skills) | ✅ |
| Fonte única das fases | `phases/kata-*.md` (11 arquivos) | ✅ |
| Build de skills (`build-skills`/`check-skills`) | `scripts/build_skills.py` | ✅ |
| Instaladores symlink (sh/ps1, OpenCode + Claude Code) | `scripts/install*.sh/.ps1` | ✅ |

### 2.3 Adversarial eval

| Feature | Onde | Estado |
|---|---|---|
| Harness de traps | `eval/run_traps.py` | ✅ |
| 19 cenários de trap (s01–s19) | `eval/scenarios/` | ✅ |
| Guarda de contagem de cenários em docs | `tests/test_docs_eval.py` (R12-04) | ✅ |

### 2.4 Instalação

| Rota | Onde | Estado |
|---|---|---|
| `pip install -e '.[dev]'` | README/DOCUMENTATION | ✅ |
| `pipx run --spec .` / `uv tool run --from .` (uso pontual) | README/DOCUMENTATION (R12 docs) | ✅ |
| `pipx install .` / `uv tool install .` (permanente) | README/DOCUMENTATION | ✅ |

## 3. Pendências registradas (roadmap)

| # | Item | Origem | Status |
|---|---|---|---|
| 1 | **Fix falso positivo estrutural do JUDGE**: `surgical.files` com paths de diretório não é expandido (s4-testes-divida, s5-docs-build REFUTED mesmo com `approved_commit`) | Auditoria S8 (`judge-batch-2026.md`) | aberto → fix-round-13 |
| 2 | **Backfill `approved_commit`** em tasks antigas pré-R14 (26 tasks colhem REFUTED por diff até HEAD) | Auditoria S8 | aberto → fix-round-13 |
| 3 | **Refactor do cli.py** (2047 linhas → módulos coesos) | plano 2026-08-10 (não-objetivo) | task `s7-refactor-cli` |
| 4 | **Domain adapters** `kata-data-analysis`, `kata-research`, `kata-docs` | AGENTS.md "futuros" | task `s9-domain-adapters` |
| 5 | **Publish PyPI** (viabiliza `pipx run kata` sem repo) | task `npx-install` (Alt D) | task `s9-publish-pypi` (plan-first, AUTH pendente) |
| 6 | **Sondas de mais linguagens** (ex.: Elixir `.exs` hoje é ponto cego) | s12-unreadable-language | ideia registrada; requer demanda |
| 7 | **`fix-m3-m4` arquivada** (M3/M4 fechados por e9f4b35) | auditoria S8 | arquivado (nada a fazer) |
| 8 | **Política triviality × scope_creep** documentada (S2/CR-002) — YAMLs antigos (backlog, fix-round-11) reconciliados | task `s7-politica` | task `s7-politica` |

## 4. Não-objetivos (fora de escopo até decisão)

- i18n das mensagens (plano 2026-07-10)
- Migrar para outro framework CLI (Typer/Click)
- Pydantic v2
- Adapter npm/npx (descartado pelo usuário em 2026-08-24 — "mantenha somente pipx/uv")

## 5. Critério de uso

`done` de cada sprint: `make lint && make format-check && make check-skills && make test` verdes, traps 19/19, e — quando o item toca o judge — re-auditoria das tasks de `.kata/` (batch `--judge`) sem novas regressões.
