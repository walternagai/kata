# Kata (型) — Agent Instructions

> Python 3.11 | CLI + OpenCode Agent | Karpathy Development Cycle

## Sobre

Kata (型, "forma/padrão") é um agente OpenCode e CLI Python que implementa o
**Karpathy Development Cycle** — um ciclo de 4 passos para garantir qualidade
antes de commitar código:

```
THINK → SIMPLIFY → SURGICAL → VERIFY
```

Inspirado na filosofia de Andrej Karpathy: pensar antes de codar, manter o
código mínimo, fazer mudanças cirúrgicas e verificar com critérios objetivos.

## Arquitetura

```
kata/
├── opencode/
│   ├── agent/kata.md           ← Agente @kata (OpenCode)
│   └── skills/kata-*/SKILL.md  ← 4 skills (uma por fase)
├── src/kata/
│   ├── cli.py                  ← CLI headless (kata --init / --check-only)
│   └── verify.py              ← Lógica de verificação (ruff + pytest + coverage)
└── scripts/install.sh         ← Instala agente + skills via symlinks
```

### O que o agente faz

| Fase | Ação |
|------|------|
| THINK | Declara problema, assumptions, alternativas e unknowns antes de codar |
| SIMPLIFY | Verifica se o código é mínimo — sem abstrações especulativas |
| SURGICAL | Valida arquivo-por-arquivo que cada mudança rastreia ao pedido |
| VERIFY | Roda ruff + pytest + coverage (gate ≥ 70%) e checa critério de sucesso |

### Diretório de trabalho

O kata usa `.kata/` na raiz do projeto onde está sendo executado. Cada tarefa
é um arquivo `.kata/<task>.yaml` com o schema:

```yaml
task: nome-da-tarefa
status: draft | think-complete | approved | rejected
think:
  problem: ""
  assumptions: []
  alternatives: []
  unknowns: ""
  answered: false
simplify:
  minimum_code: true
  no_single_use_abstractions: true
  no_speculative_config: true
surgical:
  files: []
  removed_imports_clean: true
verify:
  ruff_clean: true
  tests_pass: true
  coverage_pct: 0.0
  coverage_pass: false
  success_criteria_met: false
```

## Comandos

```bash
# CLI Python (headless / CI)
kata --init <task>               # Cria .kata/<task>.yaml com template
kata                             # Ciclo interativo completo
kata --check-only                # Só VERIFY (lint + test + coverage)
kata --task <name>               # Retoma tarefa específica

# Instalação do agente OpenCode
make install                     # Symlinks em ~/.config/opencode/
make uninstall                   # Remove symlinks

# Desenvolvimento
make test                        # pytest + coverage
make lint                         # ruff check
make format                       # ruff format
```

### Uso no OpenCode

Após `make install` e reiniciar o OpenCode:

- `@kata` — inicia ciclo interativo completo
- `@kata --init nome-da-tarefa` — cria tarefa e executa THINK
- `@kata --check-only` — só verificação (CI/snapshot)
- `@kata --task nome` — retoma tarefa existente

## Convenções

- **Linguagem**: docstrings e comentários em Português (BR). Código em inglês.
- `from __future__ import annotations` no topo dos módulos.
- Type hints em todas as funções.
- Imports: stdlib → third-party → local (alfabético em cada grupo).
- `snake_case` funções/variáveis, `PascalCase` classes.
- Logging: `logging` ou `rich.console.Console` — nunca `print()` (exceto CLI output direto).

## Compatibilidade

O schema `.kata/<task>.yaml` é compatível com o `.karpathy/` do mushin. Para
migrar tarefas existentes:

```bash
ln -s .karpathy .kata   # symlink preserva acesso ao legado
```

O script `scripts/karpathy_cycle.py` do mushin não é removido — convive com o
kata como fallback headless.

## Instalação

```bash
# 1. Instalar o pacote Python (opcional, só se quiser o CLI)
pip install -e .

# 2. Instalar o agente OpenCode
make install

# 3. Reiniciar o OpenCode
```
