# Kata (型) — Agent Instructions

> Python 3.11+ | CLI + OpenCode Agent + Claude Code Skills | Karpathy Development Cycle + Fable Method

## O que é este repo

Kata é a ferramenta que implementa o ciclo FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT, com AUDIT e JUDGE adversarial.
Este repositório contém o **código da ferramenta** (CLI + agente OpenCode +
skills do Claude Code), não um projeto onde o kata é aplicado.

A referência técnica detalhada está em [`DOCUMENTATION.md`](DOCUMENTATION.md).

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
src/kata/       código Python (cli.py, fit.py, verify.py, judge.py, __init__.py, __main__.py)
tests/          testes pytest (test_cli.py, test_fit.py, test_verify.py, test_judge.py,
                test_install.py — roda os instaladores .sh de verdade;
                test_eval_harness.py — parser de fraudes do run_traps.py;
                test_schema_contract.py — schema documentado no DOCUMENTATION.md
                contra o código e o template do --init)
opencode/       definição do agente e skills para o OpenCode
  agent/kata.md          prompt do agente @kata
  skills/kata-*/SKILL.md 10 skills (fit, think, simplify, intent, surgical,
                         verify, artifact, report, question, judge; TWIN CHECK
                         vive no orquestrador)
claude-code/    skills para o Claude Code
  skills/kata/SKILL.md   orquestrador (papel equivalente ao agente @kata)
  skills/kata-*/SKILL.md as mesmas 10 skills (mesmo procedimento,
                         nomes de ferramenta do host — não são texto idêntico)
eval/           cenários de trap adversarial (python3 eval/run_traps.py)
scripts/install.sh                instala via symlinks em ~/.config/opencode/
scripts/install-claude-code.sh    instala via symlinks em ~/.claude/
```

Os dois frontends compartilham o mesmo backend Python: só a camada de
orquestração/interação muda. Lint, teste, coverage e o judge sempre rodam
pelo pacote `kata` — e os comandos de cada papel saem de `.kata/config.yaml`
do projeto alvo, com os defaults Python (ruff/pytest/pytest-cov) valendo
para o que não for declarado.

Diferente do OpenCode, a versão Claude Code é só skills (sem subagente): o
ciclo pergunta a cada fase, e isso funciona melhor na conversa principal do
que num subagente isolado que só reporta um resumo no fim.

**A fonte de uma fase é uma só: `phases/kata-<fase>.md`.** Os arquivos em
`opencode/` e `claude-code/` são **gerados** por `scripts/build_skills.py` —
não os edite à mão; `make build-skills` os regrava e
`tests/test_skills_build.py` reprova se ficarem desatualizados.

Antes disto a fase vivia em duplicata mantida por disciplina manual, e a
disciplina falhou: 395 linhas divergentes, parte delas melhoria aplicada num
frontend e esquecida no outro. Hoje 93% da fonte é compartilhada; os 7%
restantes são diferença declarada, não acidental.

Na fonte, o que muda por frontend se escreve de três formas:

- `{{RUN}}`, `{{READ}}`, `{{ASK}}`, `{{LOAD_PHASE}}`… — como o host chama
  cada **papel** de `REQUIRED_ROLES`. São papéis, não nomes de ferramenta:
  `RUN` é "executar um comando", não "bash". Variável não declarada é erro
  de build, nunca texto literal.
- `<!--if:closed_choice_ask-->` / `<!--ifnot:...-->` — bloco que depende de uma
  **capacidade** do host. É a forma preferida: quase todo conteúdo condicional
  deste repositório existe porque a ferramenta de perguntar é de escolha
  fechada, e não porque o frontend se chama Claude Code.
- `<!--only:opencode-->` — bloco por **identidade**. Só para o que de fato é
  identidade: frontmatter, título, prefixo de invocação. Escrever um bloco de
  capacidade como `only:` obriga um terceiro host com a mesma forma a ser
  adicionado a cada bloco à mão — a duplicata voltando por outra porta.

Cuidado com concordância: `{{ESTE_ORQUESTRADOR}}` e `{{AGENTE_CAP}}` mudam de
gênero entre os frontends ("O prompt do agente" / "Esta skill"), e o
adjetivo seguinte tem de concordar com os dois. Quando não der, escreva a
frase sem a variável — "o orquestrador" descreve ambos e não flexiona.

Cuidado com `question`: a **rota** `question` é valor de `fit.route` e se
escreve igual nos dois frontends; só a **ferramenta** de perguntar vira
`{{ASK}}`. Trocar uma pela outra faz o frontend instruir `route:
AskUserQuestion`, que o CLI não reconhece.

Fases com lógica objetiva (FIT, VERIFY, JUDGE) continuam existindo também em
`src/kata/` — mudança de comportamento ali tem de acompanhar a fonte.

- `fit.py` é a lógica do fit gate (diff_stats, is_trivial) modularizada para
  testes independentes.
- `verify.py` é a lógica de verificação (ruff/pytest/coverage via
  `--cov-fail-under`) modularizada para testes independentes.
- `judge.py` é a lógica adversarial que verifica fraudes e inconsistências.
- `skills.py` é o preflight: a lista canônica de skills que o ciclo precisa e
  a checagem de instalação por frontend (`kata --doctor`). Instalação parcial
  reprova; ausente não. Uma fase rodada sem a skill dela vai para
  `preflight.skills_missing` e o `--audit` a gradua como `degraded`.
- O CLI (`cli.py`) orquestra as 9 fases + audit + judge opcional e chama
  `fit.py`, `verify.py`, `judge.py`.
- Entry point do CLI: `kata.cli:main` (declarado em `pyproject.toml`).

## Desenvolvimento

```bash
make build-skills  # gera opencode/ e claude-code/ a partir de phases/
make check-skills  # falha se o gerado estiver desatualizado
make test      # pytest + coverage (gate 70%)
make lint      # ruff check src/ tests/ eval/ scripts/
make format    # ruff format src/ tests/ eval/ scripts/

make install                 # symlinks do agente + skills em ~/.config/opencode/
make uninstall               # remove os symlinks
make install-claude-code     # symlinks das skills em ~/.claude/
make uninstall-claude-code   # remove os symlinks
```

Rodar um único teste: `python3 -m pytest tests/test_verify.py::TestRunRuff -v`

Ordem recomendada: `make lint && make test`.

`.github/workflows/ci.yml` roda exatamente esses dois alvos mais
`python3 eval/run_traps.py`, em Python 3.11 e 3.12, a cada push na `main` e
em todo PR. O CI chama o Makefile de propósito: o que é verificado local e
o que é verificado remoto não devem poder divergir.

## Instalação — symlinks, não cópias

`scripts/install.sh` cria **symlinks** de `opencode/` para `~/.config/opencode/`;
`scripts/install-claude-code.sh` faz o mesmo de `claude-code/skills/` para
`~/.claude/skills/`. Isso significa que rodar `make build-skills` reflete
imediatamente na instalação, sem reinstalar. Use `make reinstall` /
`make reinstall-claude-code` só se criar **novos** arquivos de skill/agent.

Ambos respeitam `OPENCODE_CONFIG_DIR` / `CLAUDE_CONFIG_DIR` quando definidos.
Há instaladores PowerShell equivalentes (`scripts/*.ps1`) com `-Copy` para
ambientes sem symlink e `-Uninstall`.

## Cobertura de testes

- `pyproject.toml` omite só `__main__.py` — **`cli.py` é medido**.
- Gate: `fail_under = 70`. Cobertura atual: alta (ver `make test` para número exato).
- Testes mockam `kata.verify._run` (wrapper de subprocess) — ruff e pytest
  reais nunca são invocados pela suíte.
- Exceção deliberada: as classes que exercitam o JUDGE contra o git
  (`TestJudgeTaskDetectsCommittedFraud`, `TestJudgeSeesUntrackedFiles`) criam
  um repositório real em `tmp_path` e chamam `git` de verdade. Cegueira a
  commit/untracked não é reproduzível com mock — o mock é justamente o que
  esconderia o defeito.
- `test_schema_contract.py` lê o `DOCUMENTATION.md` e cobra que o schema
  documentado cubra o que o código lê/grava e o template do `--init`. Mudar
  qualquer um dos três sem sincronizar os outros quebra a suíte.
- Fixtures de eval (`eval/scenarios/*/fixture`) são projetos deliberadamente
  quebrados e ficam fora do ruff (`extend-exclude` no `pyproject.toml`) — o
  s03 planta um F401 de propósito. Não "consertar" nem lintá-los.

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
