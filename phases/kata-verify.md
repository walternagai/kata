---
name: kata-verify
description: Fase VERIFY (GOAL-DRIVEN) do ciclo Karpathy (kata). Use quando {{AGENTE}} estiver na fase 4 — executar lint, teste e coverage do projeto (declarados em .kata/config.yaml ou os defaults Python), interpretar resultados e verificar o critério de sucesso. Triggers: VERIFY, GOAL-DRIVEN, ruff, pytest, coverage, eslint, vitest, go test, gate, CI, verificação de qualidade.
---

# Skill: kata-verify

Fase 4 do Karpathy Development Cycle — **GOAL-DRIVEN**.

## Objetivo

Verificar a qualidade do código com critérios objetivos:
1. **Lint** — limpo
2. **Teste** — todos passam
3. **Coverage** — ≥ gate (default 70%)
4. **Critério de sucesso** — a tarefa resolve o problema declarado na fase THINK

## Antes de tudo: que comandos verificam ESTE projeto?

**Leia `.kata/config.yaml` antes de rodar qualquer coisa.** Se existir, os
comandos declarados ali são os do projeto e devem ser usados verbatim:

```yaml
verify:
  lint: npx eslint src tests
  test: npx vitest run
  coverage: npx vitest run --coverage
  coverage_pattern: 'All files\s+\|\s+([\d.]+)'
  gate: 80
```

Cada papel aceita string ou lista. Papel omitido cai no default Python
(ruff/pytest/pytest-cov). `python -m kata --check-only` já lê esse arquivo
sozinho — prefira-o a montar os comandos à mão.

Sem `.kata/config.yaml`, valem os defaults Python descritos abaixo. **Se o
projeto não for Python e não houver config**, não invente um comando nem
declare sucesso: proponha ao usuário criar o `.kata/config.yaml` e registre
o bloqueio como caveat. Verificação que não rodou não é verificação que
passou.

## Ferramentas

Para esta fase, use:

- **{{RUN}}**: execute `ruff`, `pytest` e `coverage` (ou `python -m kata --check-only`; no Windows, use `py -m kata` se necessário).
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
verify:
  ruff_clean: true
  tests_pass: true
  coverage_pct: 87.0
  coverage_pass: true
  success_criteria_met: true
  attempts: 1          # contador de execuções do VERIFY (hard bound)
  hand_back: false     # true após 3 tentativas falhas — tarefa devolvida
```

## Modo --check-only (CI)

Quando invocado com `--check-only`, pula THINK/SIMPLIFY/SURGICAL e executa
só as 3 verificações objetivas (ruff + pytest + coverage). O critério de
sucesso é assumido satisfeito. Útil para CI/CD pipelines — nesse modo, a
skill nem precisa ser carregada: chame o CLI diretamente via {{RUN}}.

Para executar via CLI:
```bash
python -m kata --check-only
```

## Princípios

- **Gate é inegociável**: coverage < 70% = rejeitado, sem exceção
- **Falso verde é pior que vermelho**: se os testes passam mas não testam nada, é pior que falhar
- **Critério de sucesso é subjetivo mas obrigatório**: o humano precisa confirmar que resolveu
- **Exit code**: 0 = aprovado, 1 = rejeitado — para integração com CI (via o CLI `python -m kata`)
