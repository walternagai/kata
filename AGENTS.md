# Kata (型) — Agent Instructions

> Python 3.11+ | CLI + OpenCode Agent | Karpathy Development Cycle + Fable Method

## O que é este repo

Kata é a ferramenta que implementa o ciclo FIT → THINK → SIMPLIFY → SURGICAL → VERIFY.
Este repositório contém o **código da ferramenta** (CLI + agente OpenCode), não
um projeto onde o kata é aplicado.

O ciclo é inspirado em duas fontes complementares:

1. **Karpathy Development Cycle** (Andrej Karpathy): pensar antes de codar,
   manter o código mínimo, mudanças cirúrgicas, verificação objetiva.
2. **The Fable Method** (Sahir619/fable-method): classificar a tarefa antes de
   agir (fit gate), triviality gate, evidência antes de ação, verificação
   adversarial, relatório outcome-first. O fit gate e o modo `--plan` do kata
   são adaptações diretas dos gates do fable-method.
   Repositório: https://github.com/Sahir619/fable-method

## Arquitetura

```
src/kata/       código Python (cli.py, fit.py, verify.py, __init__.py, __main__.py)
tests/          testes pytest (test_cli.py, test_fit.py, test_verify.py)
opencode/       definição do agente e skills para o OpenCode
  agent/kata.md          prompt do agente @kata
  skills/kata-*/SKILL.md 5 skills (uma por fase do ciclo)
scripts/install.sh       instala via symlinks em ~/.config/opencode/
```

- `fit.py` é a lógica do fit gate (diff_stats, is_trivial, classify_route),
  modularizada para testes independentes.
- `verify.py` é a lógica de verificação (ruff/pytest/coverage) modularizada para
  testes independentes. O CLI (`cli.py`) orquestra as 5 fases e chama `fit.py` e `verify.py`.
- Entry point do CLI: `kata.cli:main` (declarado em `pyproject.toml`).

## Desenvolvimento

```bash
make test      # pytest + coverage (gate 70%)
make lint      # ruff check src/ tests/
make format    # ruff format src/ tests/
make install   # symlinks do agente + skills em ~/.config/opencode/
make uninstall # remove os symlinks
```

Rodar um único teste: `python3 -m pytest tests/test_verify.py::TestRunRuff -v`

Ordem recomendada: `make lint && make test`.

## Instalação do agente — symlinks, não cópias

`scripts/install.sh` cria **symlinks** de `opencode/` para `~/.config/opencode/`.
Isso significa que editar arquivos em `opencode/` reflete imediatamente no
OpenCode sem reinstalar. Use `make reinstall` só se criar **novos** arquivos de
skill/agent.

## Cobertura de testes

- `pyproject.toml` omite só `__main__.py` — **`cli.py` é medido**.
- Gate: `fail_under = 70`. Cobertura atual: alta (ver `make test` para número exato).
- Testes mockam `kata.verify._run` (wrapper de subprocess) — nunca chamam
  ruff/pytest reais nos testes.

## Convenções de código

- `from __future__ import annotations` no topo de todo módulo.
- Docstrings e comentários em **Português (BR)**. Código (identificadores) em inglês.
- Type hints em todas as funções.
- Imports: stdlib → third-party → local (alfabético por grupo).
- `snake_case` funções/variáveis, `PascalCase` classes.
- Sem `print()` em código de biblioteca — só em CLI output direto. Logging via
  `logging` ou `rich.console.Console`.
- Ruff: `line-length=100`, `target-version=py311`, regras `E/F/W/I/UP/B`.

## Compatibilidade com mushin

O schema `.kata/<task>.yaml` é compatível com `.karpathy/` do mushin. Para
migrar: `ln -s .karpathy .kata`. O `scripts/karpathy_cycle.py` do mushin não é
removido — convive com o kata como fallback headless.
