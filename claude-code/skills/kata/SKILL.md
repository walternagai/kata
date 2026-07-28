---
name: kata
description: "Kata (型) — Karpathy Development Cycle: orquestra FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → ARTIFACT → REPORT (+ JUDGE opcional). Use quando precisar garantir qualidade antes de commitar: classificar tarefa, declarar assumptions, validar minimalismo, verificar intenção, mudanças cirúrgicas, relatório outcome-first, verificação adversarial, e rodar lint+test+coverage. Triggers: kata, karpathy cycle, fable method, antes de commitar, ciclo de qualidade."
---

# Skill: kata — Karpathy Development Cycle

Você está executando o **kata** (型, "forma/padrão"), que orquestra o
**Karpathy Development Cycle** — um ciclo de 8 fases (+ judge opcional) para
garantir qualidade de código antes de commitar.

Esta skill é a versão para Claude Code do agente `@kata` do OpenCode. A
lógica de verificação (ruff + pytest + coverage + judge adversarial) vive no
pacote Python `kata` (`pip install -e .` neste repo), reutilizado por ambas
as versões — só a camada de orquestração/interação muda.

## Filosofia

O kata combina duas influências complementares:

1. **Karpathy Development Cycle** (Andrej Karpathy): pensar antes de codar,
   manter o código mínimo, fazer mudanças cirúrgicas e verificar com critérios
   objetivos. Como um kata marcial, é uma sequência disciplinada e repetível.
2. **The Fable Method** (Sahir619/fable-method): classificar a tarefa antes de
   agir, definir "pronto" com verificação nomeada, reunir evidências em paralelo,
   mudar o mínimo, verificar por observação e reportar resultado primeiro.
   O fit gate e o triviality gate do kata são adaptações diretas do fable-method.

## As Fases

```
FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → ARTIFACT → REPORT
                                                             ↓ (opcional)
                                                           JUDGE
```

| Fase | Objetivo |
|------|----------|
| FIT | Classificar a tarefa e aplicar triviality gate antes de investir esforço |
| THINK | Declarar problema, assumptions, alternativas e unknowns antes de codar |
| SIMPLIFY | Verificar se o código é mínimo — sem abstrações especulativas |
| INTENT | Verificar alinhamento entre código, teste e spec antes de mudar comportamento |
| SURGICAL | Validar arquivo-por-arquivo que cada mudança rastreia ao pedido |
| VERIFY | Rodar ruff + pytest + coverage (gate ≥ 70%) e checar critério de sucesso |
| ARTIFACT | Verificar que todas as linhas devidas (INTENT/AUTH/PENDING/TWINS) estão presentes |
| REPORT | Relatório outcome-first: resultado na primeira linha, verificações, caveats honestos, INTENT/AUTH/PENDING/TWINS lines |
| JUDGE *(opcional)* | Verificação adversarial — re-executa verificações, caça 6 tipos de fraude, entrega veredito VERIFIED/CAVEATS/REFUTED |

A fase FIT é inspirada no **triviality gate** e **fit gate**; a fase JUDGE
é inspirada no **fable-judge** do
[The Fable Method](https://github.com/Sahir619/fable-method), que prova
empiricamente que classificar a tarefa antes de agir reduz falhas procedurais
em agentes de código.

## Ferramentas

Mapeamento de ferramentas do Claude Code para cada tarefa do kata:

| Tarefa | Ferramenta | Uso |
|--------|------------|-----|
| Carregar instruções da fase | `Skill` | `skill: "kata-fit"`, `"kata-question"`, `"kata-think"`, `"kata-simplify"`, `"kata-intent"`, `"kata-surgical"`, `"kata-verify"`, `"kata-artifact"`, `"kata-report"`, `"kata-judge"` |
| Perguntar ao usuário | Texto livre (aberta) ou `AskUserQuestion` (fechada) + `kata-question` | Uma pergunta por vez; consulte a skill `kata-question` para a regra de qual ferramenta usar |
| Executar comandos | `Bash` | `git diff`, `ruff`, `pytest`, `python -m kata --check-only` etc. |
| Ler arquivos | `Read` | Inspecionar diff/código de arquivos específicos |
| Buscar no código | `Grep` / `Glob` | Encontrar callers, imports, patterns, arquivos |
| Editar arquivos | `Edit` | Aplicar correções pontuais |
| Criar/escrever YAML | `Write` | Criar/atualizar `.kata/<task>.yaml` |
| Rastrear progresso (opcional) | `TaskCreate` / `TaskUpdate` | Visualizar as 8 fases como uma lista de tarefas na UI — suplementar, não substitui o YAML |

**Regra**: em cada fase, carregue primeiro a skill correspondente com `Skill`
e siga suas instruções. Esta skill é a orquestração; as demais skills
`kata-*` contêm o detalhe de cada fase.

### Compatibilidade operacional

O kata deve funcionar em Linux, macOS e Windows. Trate os caminhos como
relativos à raiz do projeto e use `Read`, `Write`, `Edit` e `Glob` para
arquivos sempre que possível; não construa caminhos concatenando
separadores manualmente. Ao executar comandos com `Bash`, use a sintaxe do
shell hospedeiro. Para Python, prefira `python -m ...`; no Windows, use
`py -m ...` se `python` não estiver disponível. Não presuma que `bash`,
`python3`, `make` ou comandos POSIX existam no Windows; se uma verificação
não puder ser executada nativamente, registre o bloqueio como caveat em vez
de declarar sucesso.

## Diretório de Trabalho

Use `.kata/` na raiz do projeto atual. Cada tarefa é um arquivo
`.kata/<task>.yaml` com o schema:

```yaml
task: nome-da-tarefa
status: draft | think-complete | approved | rejected
base_commit: ""       # HEAD do git no início da tarefa; usado pelo JUDGE
                       # para comparar mesmo depois que a tarefa é commitada
fit:
  trivial: false
  route: code-loop     # code-loop | plan-first | question | research | inference
  reason: ""
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
intent:
  code_does: ""
  check_expects: ""
  spec_says: ""
  all_agree: true
  answered: false
surgical:
  files: []
  removed_imports_clean: true
verify:
  ruff_clean: true
  tests_pass: true
  coverage_pct: 0.0
  coverage_pass: false
  success_criteria_met: false
artifact:
  intent_owed: true
  intent_present: true
  auth_owed: false
  auth_present: true
  pending_owed: false
  pending_present: true
  twins_owed: false
  twins_present: true
auth:
  action_taken: false
  authorized: false
pending:
  action: ""
  documented: false
twins:
  pattern: ""
  result: ""
  searched: false
```

## Parsing de Argumentos

### Inicialização obrigatória do estado

Antes de ler ou escrever qualquer arquivo de tarefa, garanta que `.kata/`
existe, usando `Bash` com o comando adequado ao shell hospedeiro (conforme a
seção "Compatibilidade operacional" acima):

- **POSIX** (Linux/macOS): `mkdir -p .kata`
- **Windows PowerShell**: `New-Item -ItemType Directory -Force .kata`

Esta etapa é obrigatória em todos os modos (`--init`, `--check-only`,
`--judge`, `--report`, `--plan`, `--task`, e modo padrão).

Se esta skill foi invocada com argumentos (via `/kata --init nome-da-tarefa`
ou equivalente), analise-os antes de executar qualquer comando. Se foi
invocada sem argumentos, trate como o modo padrão. Mapeamento:

| Input | Modo | Ação |
|-------|------|------|
| `--init <task>` | `--init` | Use `Write` para criar `.kata/<task>.yaml` com template (inclua `base_commit`), depois execute FIT + THINK e salve |
| `--check-only` | `--check-only` | Pule FIT/THINK/SIMPLIFY/SURGICAL; execute VERIFY via `Bash` (`python -m kata --check-only`, ou `py -m kata` no Windows) e reporte |
| `--plan <task>` | `--plan` | Crie/carregue task, execute FIT + THINK, salve o plano e pare (equivalente ao plan-first do fable-method) |
| `--task <name>` | `--task` | Carregue `.kata/<name>.yaml` com `Read` e continue o ciclo a partir do status atual |
| `--judge` | `--judge` | Carregue a task (por branch ou --task), execute verificação adversarial (re-executa checks, caça fraudes) |
| `--report` | `--report` | Carregue a task (por branch ou --task), gere relatório outcome-first |
| (sem args) | padrão | Detecte task via branch git (`Bash`) ou pergunte ao usuário, FIT + ciclo completo |

Para `--init`, você pode também usar `Bash` para rodar
`python -m kata --init <task>` (ou `py -m kata` no Windows), mas depois deve
carregar o YAML e prosseguir com THINK interativamente.

## Detecção de Task

Se nenhum `--task` for fornecido:
1. Tente detectar o branch git atual via `Bash`: `git rev-parse --abbrev-ref HEAD`
2. Normalize: substitua `/` e `_` por `-`
3. Se existir `.kata/<branch>.yaml`, retome essa tarefa
4. Caso contrário, liste tarefas existentes em `.kata/` e pergunte ao usuário
5. Se não houver tarefas, pergunte o nome da nova tarefa

## Fluxo de Execução

### Fase 0: FIT

1. Carregue a skill `kata-fit` com `Skill` (`skill: "kata-fit"`).
2. Execute `git diff --stat` via `Bash` para medir o volume de alterações.
3. Classifique a tarefa (com `kata-question` para envolver o usuário):
   - A tarefa é **trivial** (1 arquivo, <10 linhas, sem busca)? Se sim, vá direto a VERIFY.
   - Qual a **rota** da tarefa: code-loop, plan-first, question, research, inference?
4. Se for `question`: carregue `kata-question`, investigue, entregue achados + recomendação, não altere código sem autorização, PARE.
5. Se for `plan-first`: execute só THINK, entregue um plano, PARE.
6. Registre a classificação em `.kata/<task>.yaml` sob a chave `fit`, e grave `base_commit` (HEAD atual) se ainda não estiver registrado.

### Fase 1: THINK

1. Carregue a skill `kata-think` com `Skill` (`skill: "kata-think"`).
2. Pergunte, em texto livre e uma de cada vez (ver `kata-question`):
   - "Qual o problema exato que estou resolvendo?"
   - "Quais assumptions estou fazendo? (separadas por ;)"
   - "Quais alternativas considerei? (separadas por ;)"
   - "O que NÃO sei? (preciso perguntar antes?)"
3. Registre as respostas no `.kata/<task>.yaml` sob a chave `think`
4. Atualize `status` para `think-complete`
5. Se houver unknowns que podem ser investigados no código, faça-o (`Grep`/`Read`)
6. Salve o arquivo e prossiga

### Fase 2: SIMPLIFY

1. Carregue a skill `kata-simplify` com `Skill` (`skill: "kata-simplify"`).
2. Execute `git diff --stat` (ou `git diff --cached --stat` se vazio)
3. Mostre o diff ao usuário
4. Pergunte via `AskUserQuestion` (fechada, ver `kata-question`):
   - "O código mínimo resolve o problema?"
   - "Alguma abstração é para uso único?"
   - "Existe configurabilidade/flexibilidade não solicitada?"
   - Observações (opcional, texto livre)
5. Analise o diff você mesmo procurando anti-patterns (YAGNI, premature abstraction)
6. Registre as respostas no YAML sob `simplify`

### Fase 2.5: INTENT

1. Carregue a skill `kata-intent` com `Skill` (`skill: "kata-intent"`).
2. Abra o código, o teste e a spec/README/docstring dos arquivos a alterar (`Read`).
3. Determine ou pergunte:
   - O que o código FAZ hoje?
   - O que o teste/check ESPERA?
   - O que a especificação DIZ?
4. Se os três discordam, resolva o conflito pela ordem de autoridade:
   usuário > spec > testes > código (use `AskUserQuestion` para escolher a resolução). **Não edite até resolver.**
5. Registre o intent gate no `.kata/<task>.yaml`.

### Fase 3: SURGICAL

1. Carregue a skill `kata-surgical` com `Skill` (`skill: "kata-surgical"`).
2. Execute `git diff --name-only` (ou `git diff --cached --name-only`)
3. Para cada arquivo, pergunte: "`<arquivo>` — necessário para esta tarefa?" (`AskUserQuestion` se poucos arquivos, texto livre listando todos se forem muitos)
4. **Recall Gate**: antes de usar qualquer API/endpoint/config de memória,
   abra a fonte real (docstring, docs, lib source) com `Read`. Se não acessível, marque
   como low-confidence no relatório.
5. Verifique imports órfãos: `ruff check --select F401 <paths>` via `Bash`
6. Pergunte: "Imports removidos são só os que sua mudança tornou inúteis?"
7. Registre a lista de arquivos com `necessary: true/false` no YAML sob `surgical`

### Fase 4: VERIFY

1. Carregue a skill `kata-verify` com `Skill` (`skill: "kata-verify"`).
2. **Ruff**: `python -m ruff check <paths>` via `Bash` (ou `py -m ruff` no Windows)
   - Paths padrão: `src/ tests/`. Adapte ao projeto (ex: `mushin/ services/ tests/`)
   - OK se returncode == 0
   - Se falhou, mostre o output completo

3. **Pytest**: `python -m pytest <test_paths> --tb=short -q` (ou `py -m pytest` no Windows)
   - Test paths padrão: `tests/`. Adapte ao projeto
   - Se houver arquivos que precisam de `--ignore`, inclua-os
   - OK se returncode == 0
   - Se falhou, mostre o output completo

4. **Coverage**: `python -m pytest <test_paths> --cov=<source> --cov-report=term-missing --cov-fail-under=70 -q` (ou `py -m pytest` no Windows)
   - Source padrão: `src`. Adapte ao projeto (ex: `mushin`)
   - O `--cov-fail-under` já garante que o gate seja verificado pelo pytest-cov
   - Extraia o percentual do output para exibição (regex: `TOTAL\s+\d+\s+\d+\s+(\d+)%`)
   - Gate: 70%. OK se returncode == 0 (já inclui o gate)

5. **Critério de sucesso**: pergunte ao usuário via `AskUserQuestion` "O critério de sucesso da tarefa está satisfeito?"
   - Em modo `--check-only`, assuma satisfeito

6. Calcule o resultado final:
   - Aprovado se: ruff ✅ AND pytest ✅ AND coverage ✅ AND sucesso ✅
   - Rejeitado caso contrário

7. Atualize `status` para `approved` ou `rejected` no YAML

### Fase 4.5: ARTIFACT

1. Carregue a skill `kata-artifact` com `Skill` (`skill: "kata-artifact"`).
2. Verifique se as linhas devidas estão no relatório:
   - **INTENT**: comportamento mudou? Intent gate está registrado?
   - **AUTH**: ação irreversível? Autorização do usuário documentada?
   - **PENDING**: docs prescrevem follow-up? Ação não tomada documentada?
   - **TWINS**: defeito corrigido? Varredura de padrão recorrente registrada?
3. Se alguma linha devida está ausente, adicione-a ou marque como ressalva.
4. Registre o resultado no `.kata/<task>.yaml`.

### Fase 5: REPORT

1. Carregue a skill `kata-report` com `Skill` (`skill: "kata-report"`).
2. O relatório é gerado automaticamente ao final do ciclo completo.
3. Para regenerar: `python -m kata --task <name> --report` via `Bash` (ou `py -m kata` no Windows).
4. Verifique se o relatório contém:
   - **Outcome first**: primeira linha = resultado
   - **O que foi feito**: problema e arquivos alterados
   - **INTENT line**: se comportamento mudou
   - **Verificações**: ruff, pytest, coverage, critério de sucesso
   - **Caveats**: o que está pendente, fraco, ou não verificado
   - **AUTH/PENDING/TWINS lines**: se devidas
5. **Hostile-reviewer reread**: releia o relatório como revisor hostil.
   - Alguma claim não verificada?
   - Resposta no formato errado?
   - Algo tocado fora do escopo?

### Fase 6: JUDGE (opcional — adversarial verification)

1. Carregue a skill `kata-judge` com `Skill` (`skill: "kata-judge"`).
2. Verifique se `status` é `approved` (julgar só tarefas concluídas).
3. Execute o judge: `python -m kata --task <name> --judge` via `Bash` (ou `py -m kata` no Windows).
4. Interprete o veredito:
   - **VERIFIED** → nenhuma fraude; resultado confiável
   - **VERIFIED WITH CAVEATS** → fraudes leves/médias; ressalvas documentadas
   - **REFUTED** → fraude de alta severidade; ciclo precisa ser revisto
5. Se REFUTED, investigue as fraudes apontadas:
   - **Weakened checks**: revise asserts removidos/relaxados em testes
   - **False completion**: re-execução falhou — corrija e reexecute
   - **Scope creep**: arquivos não declarados — reverta ou justifique
   - **Unauthorized action**: ação externa sem AUTH — documente ou reverta
   - **Spec betrayal**: spec contradita — alinhe código/teste/spec
   - **Debris**: limpe arquivos temporários, debug prints, TODOs
6. Registre o resultado no `.kata/<task>.yaml` sob chave `judge`.

7. Mostre o resumo final:

```
✅ ruff limpo
✅ pytest 850 passaram
✅ coverage 87.0% (gate: 70%)
✅ critério de sucesso satisfeito

┌──────────────────────────────────────────────────────────┐
│  ✅  KATA CYCLE — APROVADO                               │
└──────────────────────────────────────────────────────────┘
```

## Adaptação ao Projeto

O kata é genérico, mas precisa saber a estrutura do projeto para rodar
verificações corretas. Detecte automaticamente:

| Se existir... | Use para ruff | Use para pytest | Use para coverage |
|---------------|---------------|-----------------|-------------------|
| `src/` | `src/ tests/` | `tests/` | `--cov=src` |
| `mushin/` | `mushin/ services/ tests/` | `tests/unit/` | `--cov=mushin` |
| `app/` | `app/ tests/` | `tests/` | `--cov=app` |

Se houver `pyproject.toml` ou `setup.cfg`, leia-o (`Read`) para identificar:
- `[tool.ruff]` → caminhos padrão
- `[tool.pytest]` → testpaths
- `[tool.coverage.run]` → source

## Persistência

Após **cada fase**, escreva/atualize `.kata/<task>.yaml` com os resultados
(via `Write`/`Edit`). Isso permite retomar uma tarefa interrompida.

Use o formato YAML (se PyYAML disponível) ou JSON como fallback — o mesmo
comportamento do CLI `kata`.

## Modo Não-Interativo

Em execução não interativa (por exemplo, `--check-only` ou CI, onde não há
usuário para responder perguntas), pule THINK/SIMPLIFY/SURGICAL preenchendo
com defaults e execute só VERIFY. Não presuma que a sessão é não-interativa
sem evidência clara (ex: flag `--check-only` explícita); se puder perguntar,
pergunte normalmente.

## Comportamento Importante

- **Propose, don't interrogate**: se o usuário não sabe uma resposta, proponha baseando-se no contexto do código
- **Investigue unknowns**: se o usuário declara um unknown sobre o código, investigue com `Grep`/`Read` antes de perguntar
- **Seja específico**: rejeite respostas vagas em THINK — peça especificidade
- **Não pule fases**: cada fase existe por uma razão. Mesmo que pareça redundante, execute-a
- **Exceção: triviality gate**: se FIT classificar como trivial (1 arquivo, <10 linhas, sem busca), pule THINK/SIMPLIFY/SURGICAL e vá direto a VERIFY + reporte em 2 frases
- **Exit code**: em modo `--check-only`, o CLI Python (`python -m kata --check-only`) termina com status apropriado (aprovado/rejeitado); esta skill em si não tem exit code, apenas reporta o resultado
- **Português BR**: todas as interações com o usuário em português brasileiro
