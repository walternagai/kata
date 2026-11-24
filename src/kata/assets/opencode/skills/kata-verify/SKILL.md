---
name: kata-verify
description: "Fase VERIFY (GOAL-DRIVEN) do ciclo Karpathy (kata). Use quando o agente @kata estiver na fase 4 — executar lint, teste e coverage do projeto (declarados em .kata/config.yaml ou os defaults Python), interpretar resultados e verificar o critério de sucesso. Triggers: VERIFY, GOAL-DRIVEN, ruff, pytest, coverage, eslint, vitest, go test, gate, CI, verificação de qualidade."
---
<!-- Gerado por scripts/build_skills.py a partir de phases/kata-verify.md. Não edite aqui. -->

# Skill: kata-verify

Fase 4 do Karpathy Development Cycle — **GOAL-DRIVEN**.

## Objetivo

Rodar os checks aplicáveis ao projeto e confrontar o resultado com o `done`:
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
  profile: declared
  lint: npx eslint src tests
  typecheck: npx tsc --noEmit
  test: npx vitest run
  coverage: npx vitest run --coverage
  coverage_pattern: 'All files\s+\|\s+([\d.]+)'
  gate: 80
```

Cada papel aceita string ou lista. Com `profile: declared`, roda só o que
for declarado (ao menos um comando); não há fallback. No perfil padrão
`python`, papéis omitidos usam Ruff/pytest/pytest-cov, exceto `typecheck`.
Uma checagem não configurada não conta como sucesso.

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

- **`question`** (via `kata-question`): pergunte ao usuário se o critério de sucesso foi satisfeito.
- **`bash`**: execute `kata --verify-task <tarefa>` e repasse essa resposta via `--criterion-met` ou `--no-criterion-met`. O CLI roda os checks do projeto e grava as evidências e o status; não os transcreva à mão. Para CI sem tarefa, use `kata --check-only`.

## Referência dos checks (defaults apenas para o perfil Python)

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
declaração, o passo não roda e não há resultado em `verify.typecheck_clean`.
Isso significa "não há gate de tipos", nunca "passou".

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
e pergunte ao usuário via `question`:
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

Reporte apenas os checks aplicáveis: exemplos abaixo para um projeto Python.

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
  typecheck_clean: true   # ausente quando o projeto não declara o papel
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
  command_argv:         # a lista exata é gravada para cada comando executado
    lint: ["/venv/bin/python", "-m", "ruff", "check", "src/", "tests/"]
  coverage_pattern_used: null  # null para o default Python
  ran_at: "2026-10-28T12:34:56+00:00"
```

O CLI grava a evidência de execução, incluindo o gate, a lista de argumentos
por papel e o horário. Coverage ausente ou sem medição fica `null`, não `0%`.

## Modo --check-only (CI)

Quando invocado com `--check-only`, pula THINK/SIMPLIFY/SURGICAL e executa
só as verificações objetivas aplicáveis ao perfil do projeto. O critério de
sucesso é assumido satisfeito. Útil para CI/CD pipelines — nesse modo, a
skill nem precisa ser carregada: chame o CLI diretamente via `bash`.

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
