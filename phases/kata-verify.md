---
name: kata-verify
description: Fase VERIFY (GOAL-DRIVEN) do ciclo Karpathy (kata). Use quando {{AGENTE}} estiver na fase 4 — executar lint, teste e coverage do projeto (declarados em .kata/config.yaml ou os defaults Python), interpretar resultados e verificar o critério de sucesso. Triggers: VERIFY, GOAL-DRIVEN, ruff, pytest, coverage, eslint, vitest, go test, gate, CI, verificação de qualidade.
---

# Skill: kata-verify

Fase 4 do Karpathy Development Cycle — **GOAL-DRIVEN**.

## Objetivo

Verificar a qualidade do código com critérios objetivos:
1. **Lint** — limpo
2. **Typecheck** — quando o projeto declara o comando (não há default: não
   existe verificador de tipos universal)
3. **Teste** — todos passam
4. **Coverage** — ≥ gate (default 70%)
5. **Critério de sucesso** — a tarefa resolve o problema declarado na fase THINK

## Antes de tudo: que comandos verificam ESTE projeto?

**Leia `.kata/config.yaml` antes de rodar qualquer coisa.** Se existir, os
comandos declarados ali são os do projeto e devem ser usados verbatim:

```yaml
verify:
  lint: npx eslint src tests
  typecheck: npx tsc --noEmit
  test: npx vitest run
  coverage: npx vitest run --coverage
  coverage_pattern: 'All files\s+\|\s+([\d.]+)'
  gate: 80
```

Cada papel aceita string ou lista. Papel omitido cai no default Python
(ruff/pytest/pytest-cov) — exceto `typecheck`, que não tem default: sem
declaração, não existe gate de tipos. `python -m kata --check-only` já lê
esse arquivo sozinho — prefira-o a montar os comandos à mão.

**Sem shell.** O comando é executado sem shell, então `&&`, `||`, `|`, `;`,
`>` e `<` viram argumento do primeiro processo. `verify.test: "npm run check
&& npm run test:db"` devolve **exit 0 com o tier 2 não executado** — verde
que esconde a metade. O kata recusa esses operadores como token solto e diz
o que fazer: declare um script do projeto (`npm run check:all`) ou um shell
explícito (`bash -c "npm run check && npm run test:db"`).

**Chave desconhecida em `verify` é erro**, não default: `typechek` (typo) ou
uma chave de um kata mais novo reprovam o carregamento em vez de sumir em
silêncio.

Sem `.kata/config.yaml`, valem os defaults Python descritos abaixo. **Se o
projeto não for Python e não houver config**, não invente um comando nem
declare sucesso: proponha ao usuário criar o `.kata/config.yaml` e registre
o bloqueio como caveat. Verificação que não rodou não é verificação que
passou.

## Ferramentas

Para esta fase, use:

- **{{RUN}}**: execute `ruff`, `pytest` e `coverage` (ou `python -m kata --verify-task <tarefa>` quando há tarefa, que roda o mesmo e grava a evidência; `python -m kata --check-only` para CI sem tarefa; no Windows, use `py -m kata` se necessário).
- **{{ASK}}** (via `kata-question`): pergunte ao usuário se o critério de sucesso foi satisfeito.
- **{{WRITE}} / {{EDIT}}**: registre o resultado em `.kata/<task>.yaml` e atualize `status` para `approved` ou `rejected`.

## Comandos

### Ruff

```bash
python -m ruff check src/ tests/
```

Para projetos com estrutura diferente:
```bash
python -m ruff check app/ services/ tests/
```

**Interpretando resultado:**
- `returncode == 0` → ✅ limpo
- `returncode != 0` → ❌ falhou — mostrar output completo

**Problemas comuns:**
- `F401` — import não utilizado → remover ou adicionar `# noqa: F401`
- `E501` — linha longa → quebrar ou aumentar `line-length` no ruff config
- `I001` — import desordenado → `ruff format` ou `ruff check --fix`

### Typecheck

Só existe quando o projeto declara `verify.typecheck`. Não há default: sem
declaração, o passo não roda e `verify.typecheck_clean` fica `null` — que é
"não há gate de tipos", nunca "passou".

```bash
npx tsc --noEmit          # TypeScript (o que o `npm run typecheck` faz)
mypy src                  # Python tipado
go vet ./...              # Go
cargo check               # Rust
```

**Interpretando resultado:**
- `returncode == 0` → ✅ passou
- `returncode != 0` → ❌ falhou — mostrar output completo e reprovar o ciclo

Não declare a implementação validada sem este passo quando o projeto tem um
typechecker: um lint limpo em projeto tipado convive com erros de tipo, e o
`schema_version` do YAML não muda por isso.

### Pytest

```bash
python -m pytest tests/ --tb=short -q
```

Para projetos com testes que precisam de ignore (ex: um que exija GPU):
```bash
python -m pytest tests/unit/ --ignore=tests/unit/test_memory_service.py --tb=short -q
```

**Interpretando resultado:**
- `returncode == 0` → ✅ passou
- `returncode != 0` → ❌ falhou — mostrar output completo

**Problemas comuns:**
- `ModuleNotFoundError: faiss` → usar `--ignore` ou instalar a dependência no
  ambiente do projeto (`python -m pip install faiss-cpu`; no Windows, `py -m pip`).
- `ImportError` circular → checar ordem de imports
- `AssertionError` em teste → investigar se a mudança quebrou comportamento

### Coverage

```bash
python -m pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=70 -q
```

Exemplo:
```bash
python -m pytest tests/unit/ --ignore=tests/unit/test_pesado.py --cov=app --cov-report=term-missing --cov-fail-under=70 -q
```

O `--cov-fail-under` faz o pytest-cov verificar o gate automaticamente:
returncode com erro se coverage < gate.

**Extraindo percentual (para exibição):**
```
TOTAL                 850      42     95%
```

Extraia do output com regex: `TOTAL\s+\d+\s+\d+\s+(\d+)%`. Não infira o valor
visualmente; se o regex não encontrar, trate como falha.

**Interpretando resultado:**
- `returncode == 0` → ✅ passou (gate verificado pelo próprio `--cov-fail-under`)
- `returncode != 0` → ❌ falhou

**Gate padrão: 70%**

Se coverage < gate:
1. Identificar linhas não cobertas (coluna `Missing` no output)
2. Adicionar testes para essas linhas
3. Ou marcar com `# pragma: no cover` se for código não-testável

### Critério de sucesso

Confronte o critério declarado no THINK (chave `done`) com o resultado final
e pergunte ao usuário via {{ASK}}:
> "O critério de sucesso da tarefa está satisfeito?"

O critério volta à fase THINK — o problema declarado foi resolvido?

**Exemplo:**
- THINK `done`: "warn no startup + /health retorna degraded quando misconfig (via curl)"
- Sucesso: o teste/manual confirma exatamente isso

Se o `done` declarado não foi alcançado, o ciclo é **rejeitado** — o critério
não pode ser reescrito depois do fato.

### Depois do commit: carimbe a janela

A aprovação acontece sobre a árvore de trabalho, então `approved_commit` não
pode ser gravado aqui (teto igual ao piso é janela vazia). Assim que o commit
existir, rode `python -m kata --stamp <task>`: sem o carimbo, o JUDGE difa
`base..HEAD` e a task seguinte passa a contaminar a anterior — a task
aprovada volta REFUTED por escopo que não é dela (P-1).

### Hard bound (Fable Step 5)

Registre `verify.attempts` (contador de execuções do VERIFY). Após **3
tentativas falhas**, grave `verify.hand_back: true` e **devolva a tarefa ao
usuário** com o que foi tentado, o output real e a hipótese atual — não fique
repetindo o mesmo fix-verify indefinidamente.

## Resumo final

Após as 4 verificações, reporte ao usuário no formato:

```
✅ ruff limpo
✅ pytest 850 passaram
✅ coverage 87.0% (gate: 70%)
✅ critério de sucesso satisfeito

┌──────────────────────────────────────────────────────────┐
│  ✅  KATA CYCLE — APROVADO                               │
└──────────────────────────────────────────────────────────┘
```

Ou:

```
❌ ruff: 3 erros (F401 x2, E501 x1)
✅ pytest: 850 passaram
❌ coverage: 65.0% (gate: 70%)
✅ critério de sucesso satisfeito

┌──────────────────────────────────────────────────────────┐
│  ❌  KATA CYCLE — REJEITADO                               │
│     Corrija os problemas e rode novamente.               │
└──────────────────────────────────────────────────────────┘
```

## Output no YAML

```yaml
status: approved
done: "warn no startup + /health degraded quando misconfig (verificado via curl)"
kata_version: "0.8.0"
verify:
  ruff_clean: true
  typecheck_clean: true   # null quando o projeto não declara o papel
  tests_pass: true
  coverage_pct: 87.0
  coverage_pass: true
  success_criteria_met: true
  attempts: 1          # contador de execuções do VERIFY (hard bound)
  hand_back: false     # true após 3 tentativas falhas — tarefa devolvida
  gate_used: 70        # gate em vigor na aprovação
  commands:            # o que rodou, por papel
    lint: "python -m ruff check src/ tests/"
    typecheck: "npx tsc --noEmit"
    test: "python -m pytest tests/ --tb=short -q"
    coverage: "python -m pytest tests/ --cov=src --cov-fail-under=70 -q"
  ran_at: "2026-10-28T12:34:56+00:00"
```

`gate_used`, `commands` e `ran_at` são a evidência de execução: sem eles o
arquivo diz que passou, mas não diz com que gate, com que comandos nem
quando — e o relatório do Fable Step 6 pede exatamente isso. O CLI grava os
três sozinho; preencha à mão só se estiver rodando as verificações fora
dele.

## Modo --check-only (CI)

Quando invocado com `--check-only`, pula THINK/SIMPLIFY/SURGICAL e executa
só as verificações objetivas (lint + typecheck quando declarado + teste +
coverage). O critério de
sucesso é assumido satisfeito. Útil para CI/CD pipelines — nesse modo, a
skill nem precisa ser carregada: chame o CLI diretamente via {{RUN}}.

Para executar via CLI:
```bash
python -m kata --check-only
```

## Modo --verify-task (o gate de um ciclo curto)

`python -m kata --verify-task <tarefa> --criterion-met` roda as mesmas
verificações e **grava** `verify.*`, `status` e `kata_version` na tarefa.
`--check-only` não grava nada (o resultado morre num dict local): use-o para
CI sem tarefa, e `--verify-task` quando existe arquivo de tarefa para carregar
a evidência. Sem `--criterion-met` (ou `--no-criterion-met`) e sem terminal, o
comando **recusa** em vez de assumir o critério satisfeito — e aprovar sem
`done` declarado também é recusado.

Transcrever o resultado à mão é a alternativa que este modo existe para
evitar: evidência digitada é afirmação, e é isso que o JUDGE chama de
`false_completion`.

## Princípios

- **Gate é inegociável**: coverage < 70% = rejeitado, sem exceção
- **Falso verde é pior que vermelho**: se os testes passam mas não testam nada, é pior que falhar
- **Critério de sucesso é subjetivo mas obrigatório**: o humano precisa confirmar que resolveu
- **Exit code**: 0 = aprovado, 1 = rejeitado — para integração com CI (via o CLI `python -m kata`)
