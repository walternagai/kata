# Kata (型): quando uma skill não basta — a ferramenta que executa a disciplina

> Artigo técnico sobre o [Kata](https://github.com/walternagai/kata) — um quality
> gate para mudanças de código assistidas por IA. Classificação, demonstração
> hands-on com output real e referências técnicas.

## 1. O problema: agentes dizem "done". Como saber?

Agentes de IA (OpenCode, Claude Code, Cursor) mudam código com velocidade
impressionante. O problema não é a velocidade — é a **confiança**. Quando um
agente diz "pronto", o que sustenta essa afirmação?

- Uma skill diz: *"verifique seus testes antes de commitar"*. O modelo pode
  seguir, ignorar ou seguir pela metade — e ninguém fica sabendo.
- Um agente pode afirmar "ruff limpo, testes passando, coverage no gate" sem
  que nada disso tenha sido executado. Ou pior: pode ter executado, mas com um
  teste enfraquecido (`pass` no lugar da asserção) que "passa" sem verificar
  nada.

O ciclo de desenvolvimento na tradição de Andrej Karpathy ([karpathy.ai](https://karpathy.ai/))
propõe disciplina: pensar antes de codar, código mínimo, mudanças cirúrgicas,
verificação objetiva — uma prática que o kata herda via o agente mushin, onde o
ciclo foi primeiro implementado. O [The Fable Method](https://github.com/Sahir619/fable-method)
(Sahir619) propõe gates: classificar a tarefa antes de agir, evidência antes de
ação, verificação adversarial, relatório outcome-first.

Ambos são **metodologias** — texto que instrui. O problema: texto instrui, mas
não executa. É aqui que o kata entra.

## 2. O que o kata é (e o que não é)

> **Uma skill é uma instrução; o kata é uma ferramenta que executa a
> instrução.**

O kata (型, "forma/padrão" — como um kata marcial: sequência disciplinada e
repetível de movimentos) é um **quality gate para mudanças de código assistidas
por IA**: um pipeline executável que torna o processo invisível do agente
visível, verificável e auditável.

O ciclo:

```
FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT
                                                                            ↓ (opcional)
                                                                          JUDGE
```

Três argumentos sustentam a classificação:

### 2.1 Não é uma skill: a lógica objetiva vive em código Python testável

Uma skill é um arquivo de instruções que o modelo lê. O kata tem skills (as 10
de fase), mas a parte que importa — a que **decide** — vive em código:

| Módulo | O que executa |
|---|---|
| `src/kata/fit.py` | Mede o diff real (`git diff` contra HEAD) e aplica o triviality gate (≤1 arquivo, <10 linhas) |
| `src/kata/verify.py` | Roda ruff, pytest e coverage com gate numérico (`--cov-fail-under` ou `coverage_pattern`) |
| `src/kata/judge.py` | Re-executa as verificações afirmadas e caça fraudes em 7 categorias |
| `src/kata/cli.py` | Orquestra as 9 fases + audit + judge, persiste `.kata/<task>.yaml` |

Uma skill depende do modelo **obedecer**. O kata não depende: ele **executa**.
Quando o VERIFY roda `pytest`, o resultado é lido do exit code real — não da
intenção do agente. Quando o JUDGE re-executa um check, ele compara o resultado
com o que o relatório afirma.

### 2.2 É um meta-tool: consome skills e gera skills

O kata consome as 10 skills de fase (FIT, QUESTION, THINK, SIMPLIFY, INTENT,
SURGICAL, VERIFY, ARTIFACT, REPORT, JUDGE) e **gera** skills para dois
frontends a partir de uma fonte única (`phases/*.md` → `make build-skills` →
`opencode/` e `claude-code/`). 92,6% das linhas renderizadas são
compartilhadas (93% arredondado; `scripts/build_skills.py --stats`); o
restante é diferença declarada (nomes de ferramenta do host), não acidental.
Nenhuma skill faz isso.

### 2.3 É adversarial e se aplica a si mesmo

- O JUDGE trata o relatório da tarefa como um conjunto de **claims** e as
  confronta com o git real — inclusive arquivos committed e untracked, que
  `git diff` não mostra.
- O kata é dogfooding: lint + coverage são medidos no próprio código do ciclo
  (gate 70%), e 19 cenários de trap adversarial rodam no CI
  (`eval/run_traps.py`).

## 3. O ciclo em ação (demo 1)

Vamos ver o kata funcionando de verdade. Projeto de exemplo: uma calculadora
com um bug real — `dividir(1, 0)` levanta `ZeroDivisionError` sem tratamento.

**Estado inicial** (commitado):

```python
# src/calculadora.py
def dividir(a: float, b: float) -> float:
    return a / b
```

**A mudança** (no working tree, ainda não commitada):

```python
def dividir(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("divisão por zero")
    return a / b
```

```python
# tests/test_calculadora.py — novo teste
def test_dividir_por_zero():
    try:
        dividir(1, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("deveria levantar ValueError")
```

Rodamos `kata --task corrigir-divisao-zero`. O ciclo pergunta a cada fase:

### FIT — classificação da tarefa

```
┌──────────────────────────────────────────────────────────┐
│ 0. FIT — Classificação da tarefa                         │
└──────────────────────────────────────────────────────────┘

  diff: 2 arquivo(s), 11 linha(s) alteradas
  ↳ tarefa não-trivial

  Rotas disponíveis:
    [1] code-loop   — ciclo completo (THINK → SIMPLIFY → SURGICAL → VERIFY)
    [2] plan-first  — só planejamento (para e entrega um plano)
    [3] question    — só diagnóstico, sem alterar código
    [4] research    — precisa pesquisar antes de agir
    [5] inference   — baseado só em inferência (baixa confiança)

  Rota escolhida [1]: 1
  Justificativa breve (opcional): corrigir divisão por zero sem tratamento
```

O FIT mede o diff **real** (2 arquivos, 11 linhas) e classifica. Uma tarefa
trivial (≤1 arquivo, <10 linhas) pularia o planejamento e iria direto ao
VERIFY — o triviality gate do fable-method.

### THINK — declarar antes da evidência

```
┌──────────────────────────────────────────────────────────┐
│ 1. THINK — Antes de codificar, declare suas assumptions  │
└──────────────────────────────────────────────────────────┘

Pergunte-se:
  Qual o problema exato que estou resolvendo? a função dividir levanta ZeroDivisionError sem tratamento
  Quais assumptions estou fazendo? (separadas por ;) nenhuma; API estável
  Quais alternativas considerei? (separadas por ;) tratar com ValueError; retornar None
  O que NÃO sei? (preciso perguntar antes?) nenhuma
  O que é 'pronto'? (critério de sucesso + como vou verificar) teste test_dividir_por_zero passa e coverage >= 70%
```

O ponto-chave (Fable Step 1): o critério de sucesso é declarado **antes** da
evidência existir. O VERIFY vai confrontar esse critério com o resultado
final — não perguntar "está satisfeito?" a um critério que só existe depois.

### SIMPLIFY, INTENT, SURGICAL — os gates de minimalismo e intenção

```
┌──────────────────────────────────────────────────────────┐
│ 2. SIMPLIFY — O código é mínimo?                         │
└──────────────────────────────────────────────────────────┘

git diff --stat:
 src/calculadora.py        | 2 ++
 tests/test_calculadora.py | 9 +++++++++
 2 files changed, 11 insertions(+)

  O código mínimo resolve o problema? [S/n]: s
  Código livre de abstrações para uso único? [S/n]: s
  Código livre de configurabilidade não solicitada? [S/n]: s

┌──────────────────────────────────────────────────────────┐
│ 2.5 INTENT — Antes de mudar, verifique a intenção        │
└──────────────────────────────────────────────────────────┘

  Se esta tarefa muda comportamento, responda:
  O que o código FAZ hoje? dividir levanta ZeroDivisionError
  O que o teste/check ESPERA? teste espera ValueError
  O que a especificação/README DIZ? README não menciona o caso
  Código, teste e especificação concordam? [S/n]: s

┌──────────────────────────────────────────────────────────┐
│ 3. SURGICAL — Cada linha toca só o necessário            │
└──────────────────────────────────────────────────────────┘

Arquivos alterados:
  src/calculadora.py — necessário para esta tarefa? [S/n]: s
  tests/test_calculadora.py — necessário para esta tarefa? [S/n]: s
  Imports removidos são só os que sua mudança tornou inúteis? [S/n]: s
```

### VERIFY — a verificação objetiva

```
┌──────────────────────────────────────────────────────────┐
│ 4. GOAL-DRIVEN — Verificação de qualidade                │
└──────────────────────────────────────────────────────────┘

▶ /home/walternagai/dev/.venv/bin/python3.12 -m ruff check src/ tests/
  ✅ limpo

▶ /home/walternagai/dev/.venv/bin/python3.12 -m pytest tests/ --tb=short -q
  ✅ passou

▶ coverage (gate ≥ 70%)
  ✅ passou (100.0%)

▶ Critério de sucesso da tarefa
  (declarado no THINK: teste test_dividir_por_zero passa e coverage >= 70%)
  O critério de sucesso da tarefa está satisfeito? [S/n]: s

┌──────────────────────────────────────────────────────────┐
│  ✅  KATA CYCLE — APROVADO                             │
└──────────────────────────────────────────────────────────┘
```

### TWIN CHECK — o mesmo defeito existe em outro lugar?

```
  Um defeito foi corrigido? Deseja buscar padrão similar? [s/N]: s

┌──────────────────────────────────────────────────────────┐
│ TWIN CHECK — Busca de padrão recorrente                  │
└──────────────────────────────────────────────────────────┘

  Padrão a buscar (regex): a / b

  Buscando 'a / b' no projeto...

  ✅ Encontrado em 1 arquivo(s):
     ./src/calculadora.py:7  return a / b
  Corrigir as demais ocorrências agora? [s/N]: n
```

Registrar o resultado negativo também importa: é o que distingue "sem defeito"
de "não chequei".

### ARTIFACT e REPORT — as linhas devidas

```
┌──────────────────────────────────────────────────────────┐
│ 4.5 ARTIFACT — Verificação de linhas devidas             │
└──────────────────────────────────────────────────────────┘

  ✅ Todas as linhas devidas estão presentes

✅  KATA CYCLE — APROVADO: critério de sucesso satisfeito

  Problema: a função dividir levanta ZeroDivisionError sem tratamento
  Critério declarado: teste test_dividir_por_zero passa e coverage >= 70%
  Arquivos alterados: src/calculadora.py, tests/test_calculadora.py
  INTENT: code does dividir levanta ZeroDivisionError; check expects teste espera ValueError; spec says README não menciona o caso

  Verificações:
  ✅ ruff check limpo
  ✅ pytest passou
  ✅ coverage 100.0% ≥ gate
  ✅ critério de sucesso satisfeito

  TWINS: searched a / b - found 1 arquivo(s), 1 ocorrência(s) (1 file(s), 1 occurrence(s))
```

O relatório é **outcome-first** (Fable Step 6): resultado primeiro, detalhes
depois, com as linhas INTENT/AUTH/PENDING/TWINS. O ARTIFACT verifica que as
linhas **devidas** estão presentes — INTENT é devida quando comportamento
mudou; AUTH quando uma ação irreversível foi tomada; PENDING quando docs
prescrevem follow-up; TWINS quando um defeito foi corrigido.

### O artefato: `.kata/corrigir-divisao-zero.yaml`

O ciclo inteiro fica registrado num YAML — a evidência é persistida, não
conversada:

```yaml
task: corrigir-divisao-zero
status: approved
done: teste test_dividir_por_zero passa e coverage >= 70%
fit:
  trivial: false
  route: code-loop
  reason: corrigir divisão por zero sem tratamento
  answered: true
think:
  problem: a função dividir levanta ZeroDivisionError sem tratamento
  assumptions: [nenhuma, API estável]
  alternatives: [tratar com ValueError, retornar None]
  unknowns: nenhuma
  answered: true
simplify:
  minimum_code: true
  no_single_use_abstractions: true
  no_speculative_config: true
  answered: true
intent:
  code_does: dividir levanta ZeroDivisionError
  check_expects: teste espera ValueError
  spec_says: README não menciona o caso
  all_agree: true
  answered: true
surgical:
  files:
  - path: src/calculadora.py
    necessary: true
  - path: tests/test_calculadora.py
    necessary: true
  removed_imports_clean: true
  answered: true
verify:
  ruff_clean: true
  tests_pass: true
  coverage_pct: 100.0
  coverage_pass: true
  success_criteria_met: true
  attempts: 0
  hand_back: false
twins:
  pattern: a / b
  result: 1 arquivo(s), 1 ocorrência(s)
  searched: true
  defect_fixed: true
  matches_count: 1
  files_count: 1
  fix_applied: false
preflight:
  skills_missing: []
artifact:
  intent_owed: true
  intent_present: true
  auth_owed: false
  auth_present: false
  pending_owed: false
  pending_present: false
  twins_owed: true
  twins_present: true
base_commit: 762b73cb7343462235d08db2aba13e7f1022c392
approved_commit: 762b73cb7343462235d08db2aba13e7f1022c392
```

Repare em `base_commit` e `approved_commit`: o HEAD capturado no início da
tarefa e no momento da aprovação. São eles que permitem ao JUDGE difar
`base..approved` mesmo depois de a tarefa ter sido commitada — mudanças de
tarefas **posteriores** não contam como escopo não declarado desta.

**Ressalva (2026-09-15):** nesta demonstração os dois commits são iguais,
porque a tarefa foi aprovada antes de a mudança ser commitada. A janela
`base..approved` fica vazia e o JUDGE, na versão 0.7.0, não compara as
afirmações de escopo e de testes com diff nenhum — e devolve VERIFIED mesmo com
um teste enfraquecido. O defeito foi reproduzido e está documentado na §6.4 do
artigo JSERD; a correção é a task `judge-janela-vazia`.

## 4. A camada adversarial (demo 2)

Agora a parte que nenhuma skill faz: o JUDGE. Ele trata o YAML como um
conjunto de claims e as confronta com a realidade.

### 4.1 Trabalho honesto → `VERIFIED`

Depois de commitar a tarefa do demo 1, rodamos `kata --task
corrigir-divisao-zero --judge`:

```
┌──────────────────────────────────────────────────────────┐
│ JUDGE — Verificação adversarial de 'corrigir-divisao-zero'│
└──────────────────────────────────────────────────────────┘

✅  VEREDITO: VERIFIED

  Claims verificadas:
    • ruff check limpo (sem erros de lint)
    • todos os testes passam
    • coverage ≥ gate (100.0%)
    • 2 arquivo(s) alterado(s) cirurgicamente (necessários)
    • intenção alinhada: código, teste e spec concordam

  Claims aceitas sem verificação (não re-executáveis):
    • critério de sucesso satisfeito

  Ressalvas:
    • 1 claim(s) aceita(s) sem verificação (não re-executáveis)

  Re-execução:
    ✅ lint
    ✅ teste
    ✅ coverage
```

Detalhe importante: o critério de sucesso é listado como **aceito sem
verificação** — é uma confirmação subjetiva do usuário, nenhum comando a
reproduz. Apresentá-lo como "verificado" seria exatamente a fraude que o
judge existe para caçar.

### 4.2 Trabalho fraudulento → `REFUTED`

Agora o cenário de trap s03 do eval do kata: um relatório que **afirma** ruff
limpo, testes passando e coverage no gate — mas a re-execução reprova os três
(um `import os` não usado no `src/`, um teste que falha, e coverage pulado
porque o pytest falhou):

```
┌──────────────────────────────────────────────────────────┐
│ JUDGE — Verificação adversarial de 'corrigir-parser'     │
└──────────────────────────────────────────────────────────┘

❌  VEREDITO: REFUTED

  Claims verificadas:
    • ruff check limpo (sem erros de lint)
    • todos os testes passam
    • coverage ≥ gate (91.0%)
    • 2 arquivo(s) alterado(s) cirurgicamente (necessários)
    • intenção alinhada: código, teste e spec concordam

  Claims aceitas sem verificação (não re-executáveis):
    • critério de sucesso satisfeito

  Fraudes encontradas:
    🔴 [high] false_completion
       ruff check re-executado falhou, mas relatório afirma que passou
       → relatório: ruff_clean=True → reality: ruff check falhou
    🔴 [high] false_completion
       pytest re-executado falhou, mas relatório afirma que passou
       → relatório: tests_pass=True → reality: pytest falhou
    🔴 [high] false_completion
       coverage re-executado falhou, mas relatório afirma que passou
       → relatório: coverage_pass=True → reality: coverage falhou

  Ressalvas:
    • 1 claim(s) aceita(s) sem verificação (não re-executáveis)
    • re-execução falhou: ruff, pytest, coverage
    • 3 fraude(s) de alta severidade

  Re-execução:
    ❌ lint
    ❌ teste
    ❌ coverage
```

O veredito é `REFUTED` — e o exit code 1. Uma skill diria "seja honesto"; o
kata **pega a mentira**.

O JUDGE caça 7 categorias de fraude: weakened checks (teste com corpo trocado
por `pass`), false completion (afirma que passou, não passou), scope creep
(arquivos alterados não declarados), unauthorized action (ação irreversível
sem AUTH line), spec betrayal (intent registrou discordância e a tarefa foi
aprovada mesmo assim), debris (arquivos temporários no diff) e baseline
tampering (`base_commit` divergindo da âncora git registrada no início).

E há os **pontos cegos confessados**: se o judge não consegue observar algo
(linguagem de teste sem sondas, arquivo fora do diff), o veredito é
`UNVERIFIABLE`, não `VERIFIED` — "não consegui olhar" nunca é reportado como
"está tudo certo".

## 5. A auditoria (demo 3)

O `kata --audit` gradua cada fase da tarefa como `followed` / `skipped` /
`faked` — e nomeia o risco concreto de cada skip/fake. O padrão `faked` (R7-1)
é a fase marcada como respondida sem conteúdo real:

```
┌──────────────────────────────────────────────────────────┐
│ AUDIT — Graduação das fases de 'tarefa-faked'            │
└──────────────────────────────────────────────────────────┘

  ❌ FIT: faked
     ⚠ rota e trivialidade não classificadas por humano — esforço pode ser desperdiçado em tarefa trivial ou mal roteada
  ❌ THINK: faked
     ⚠ assumptions nunca declaradas — qualquer solução pode atacar o problema errado
  ❌ INTENT: faked
     ⚠ código, teste e spec podem discordar sem registro — comportamento muda sem intenção verificada
  ✅ SIMPLIFY: followed
  ✅ SURGICAL: followed
  ✅ VERIFY: followed

  ⚠  Audit encontrou 3 fake(s) e 0 skip(s).
```

Isso só é possível porque há **lógica objetiva** por trás: o audit lê o YAML e
detecta `answered: true` com conteúdo vazio. Uma skill não tem como saber se a
fase foi "fingida" — o kata tem.

## 6. A engenharia por trás

- **Fonte única**: `phases/*.md` gera os dois frontends (`opencode/` e
  `claude-code/`) via `make build-skills`. `tests/test_skills_build.py` reprova
  se o gerado ficar desatualizado. Antes disso, as fases viviam em duplicata
  mantida à mão — e a disciplina falhou: 395 linhas divergentes.
- **Dogfooding**: `make lint && make test` medem o próprio `cli.py` (gate 70%);
  o CI roda o Makefile, não comandos reescritos — o que é verificado local e
  remotamente não pode divergir.
- **Eval adversarial**: 19 cenários de trap (`eval/run_traps.py`) plantam
  fraudes que o judge **precisa** pegar e trabalho honesto que ele **não pode**
  acusar. Falso negativo esconde fraude; falso positivo destrói a confiança no
  veredito.
- **Compatibilidade**: o schema `.kata/<task>.yaml` é compatível com
  `.karpathy/` do mushin (`ln -s .karpathy .kata`).

## 7. Limitações honestas

- **É um gate, não uma bala de prata**: o kata garante que o que foi afirmado
  foi verificado — não que a solução seja a melhor possível.
- **É interativo**: o ciclo pergunta a cada fase. Em modo headless
  (`--check-only`), as fases de julgamento usam defaults e o relatório diz
  explicitamente que ninguém respondeu.
- **Requer git**: diff e branch detection dependem dele.
- **O critério de sucesso é subjetivo**: o JUDGE o aceita sem verificação e
  diz isso em voz alta.
- **O JUDGE tem pontos cegos**: linguagens de teste sem sondas, arquivos fora
  do diff — confessados como `UNVERIFIABLE`, nunca silenciados.

## 8. Conclusão

O kata não é uma skill — é a ferramenta que **executa** a disciplina que as
skills pedem. A distinção é a tese deste artigo:

| | Skill | Kata |
|---|---|---|
| O que é | Instrução em texto | Pipeline executável (CLI + agentes + skills) |
| Verificação | Depende do modelo obedecer | Executa ruff/pytest/coverage e lê exit codes |
| Honestidade | Pede | Detecta (JUDGE, 7 fraudes) |
| Evidência | Conversada | Persistida em `.kata/<task>.yaml` |
| Auditoria | Não existe | `--audit` gradua followed/skipped/faked/degraded |
| Aplica-se a si mesmo | Não | Sim (lint+coverage+19 traps no CI) |

Se você usa agentes de IA para mudar código e quer saber **de verdade** se o
que foi afirmado é verdade, o kata é uma resposta concreta: ele re-executa,
compara e recusa. O resto é conversa.

## Referências técnicas

### Fontes primárias (o próprio kata)

- [Kata — repositório](https://github.com/walternagai/kata): código-fonte,
  CLI, agentes e skills.
- [`DOCUMENTATION.md`](DOCUMENTATION.md): referência técnica completa — schema
  do task file, contrato dos frontends, vereditos do JUDGE, pontos cegos.
- [`COMPETITIVE.md`](COMPETITIVE.md): análise comparativa com projetos
  similares (fable-method, claude-wizard, ring, nova, pre-commit-review).
- [`eval/README.md`](eval/README.md): schema dos cenários de trap e a regra de
  que um cenário novo deve reprovar quando o defeito volta.
- [`AGENTS.md`](AGENTS.md): instruções de desenvolvimento — fonte única das
  fases, convenções de código, cobertura de testes.

### Metodologias que inspiraram o kata

- **Ciclo de desenvolvimento na tradição Karpathy** — pensar antes de codar,
  código mínimo, mudanças cirúrgicas, verificação objetiva. O ciclo foi
  primeiro implementado no agente mushin (repositório privado do autor) e
  herdado pelo kata; a referência geral é o site de
  [Andrej Karpathy](https://karpathy.ai/).
- **The Fable Method** — [Sahir619/fable-method](https://github.com/Sahir619/fable-method):
  fit gate, triviality gate, evidência antes de ação, verificação adversarial,
  relatório outcome-first. O fit gate e o modo `--plan` do kata são adaptações
  diretas dos gates do fable-method. O repo documenta 15 rodadas de eval com
  mais de 260 execuções de agentes, juízes LLM cegos que verificam por diff e
  execução (nunca lendo relatórios), e o achado central: *"modelos fracos
  seguem regras em pontos de decisão, não regras em listas"* — a razão de
  existir do INTENT line forçado do kata.

### Trabalhos fundamentais (verificação adversarial de agentes)

- **SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents** —
  Zhao et al., arXiv:2605.21384 (2026). Mede reward hacking em agentes de
  código: o agente otimiza para passar nos testes visíveis enquanto desvia do
  objetivo real. O gap entre suíte visível e suíte held-out cresce 28 pontos
  percentuais a cada aumento de 10x no tamanho do código — incluindo um
  "compilador" de hash-table de 2.900 linhas que memoriza entradas de teste.
  É a evidência empírica do problema que o JUDGE do kata ataca.
- **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?** —
  Jimenez et al., arXiv:2310.06770 (ICLR 2024). O benchmark padrão de agentes
  de código: 2.294 issues reais do GitHub. O melhor modelo resolvia 1,96% na
  publicação — o ponto de partida da medição de agentes de engenharia de
  software.
- **Large Language Models Cannot Self-Correct Reasoning Yet** — Huang et al.,
  arXiv:2310.01798 (ICLR 2024). LLMs não conseguem se autocorrigir sem
  feedback externo — e às vezes pioram após a autocorreção. É o argumento
  teórico para a arquitetura do kata: a verificação não pode ser "o modelo
  conferindo a si mesmo"; precisa ser execução objetiva (exit codes, diff,
  re-execução).
- **Chain-of-Verification Reduces Hallucination in Large Language Models** —
  Dhuliawala et al., arXiv:2309.11495 (2023). O método CoVe: o modelo planeja
  perguntas de verificação, responde-as independentemente e gera a resposta
  final verificada. Parente próximo do JUDGE — mas ainda dentro do modelo; o
  kata leva a verificação para fora dele.
- **Reflexion: Language Agents with Verbal Reinforcement Learning** — Shinn
  et al., arXiv:2303.11366 (NeurIPS 2023). Agentes que refletem sobre feedback
  e mantêm memória episódica textual — 91% pass@1 no HumanEval. O hard bound
  do VERIFY (3 tentativas → hand back) é a versão disciplinada do loop de
  reflexão, com limite explícito.
- **Executable Code Actions Elicit Better LLM Agents** — Wang et al.,
  arXiv:2402.01030 (ICML 2024). CodeAct: ações executáveis (código Python)
  superam JSON/texto em até 20% de taxa de sucesso. Suporta a escolha do kata
  de executar verificações reais em vez de instruir o agente a "rodar testes".
- **Long-form factuality in large language models** — Wei et al.,
  arXiv:2403.18802 (NeurIPS 2024). SAFE: agentes LLM como avaliadores
  automatizados de factualidade, quebrando respostas longas em fatos
  individuais verificados por busca. Referência para a ideia de verificação
  por decomposição em claims — o mesmo princípio do JUDGE (o relatório é um
  conjunto de claims a confrontar com a realidade).

### Ferramentas e padrões relacionados

- **mushin**: agente local (repositório privado do autor) com o ciclo
  Karpathy (`scripts/karpathy_cycle.py`), schema `.karpathy/` compatível com
  `.kata/` via `ln -s .karpathy .kata`.
- [claude-wizard](https://github.com/vlad-ko/claude-wizard): 8 fases de
  desenvolvimento com TDD e revisão adversarial — similar, mas sem backend
  unificado (71 stars).
- [ring](https://github.com/LerianStudio/ring): 76 skills e 33 agentes que
  impõem boas práticas de engenharia, com ciclos de 10 gates (212 stars).
- [nova](https://github.com/TeamSPWK/nova): avaliador independente com revisão
  adversarial e pre-commit quality gate.
- [intent-audit-harness](https://github.com/jeremylongshore/intent-audit-harness):
  test-policy enforcement determinístico para quality gates — complementar ao
  kata.

### Conceitos técnicos citados

- **Triviality gate**: classificação de tarefa por tamanho de diff (≤1 arquivo,
  <10 linhas) — do fable-method.
- **Outcome-first report**: relatório que começa pelo resultado (Fable Step 6).
- **Adversarial verification**: re-execução de verificações afirmadas e caça a
  fraudes — ver [fable-method](https://github.com/Sahir619/fable-method).
- **Reward hacking**: otimizar a métrica visível (testes) desviando do objetivo
  real — ver SpecBench (arXiv:2605.21384).
- **Dogfooding**: usar a própria ferramenta para verificar a si mesma.
- **YAGNI** (You Aren't Gonna Need It): princípio de minimalismo aplicado no
  SIMPLIFY.
