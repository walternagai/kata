---
name: kata-agile
description: "Orquestrador alternativo de ciclo curto — FIT → THINK → DECLARE → VERIFY → REPORT (5 fases, 4 interações). Selecione APENAS quando o usuário pedir `kata-agile` pelo nome. Para 'tarefa pequena', 'antes de commitar' ou qualquer pedido genérico de qualidade, use o @kata: a escolha entre ciclo curto e completo é dele, medida no FIT, não desta descrição. Triggers: kata-agile (somente por nome explícito)."
---
<!-- Gerado por scripts/build_skills.py a partir de phases/kata-agile.md. Não edite aqui. -->

# Skill: kata-agile — o ciclo curto

Este é um **orquestrador alternativo** ao `kata`. Ele percorre cinco fases e
quatro interações com o usuário. O `@kata` completo continua existindo, e a
tarefa escala para ele quando um dos gatilhos da seção **Quando não usar**
dispara.

**Ele não se escolhe sozinho.** A descrição acima não anuncia "tarefa
pequena": quem decide abrir uma tarefa em ciclo curto é o usuário, pedindo
`kata-agile` pelo nome. A alternativa — deixar a descrição disputar o gatilho
do `@kata` ("antes de commitar", "garantir qualidade") — fazia o modelo
desviar tarefa grande para o ciclo curto sem ninguém escolher, e o gatilho de
escalonamento só roda **depois** de a skill já ter sido escolhida.

O que encurta é a **conversa**, não a verificação. Lint, teste e coverage
rodam de verdade, pelo CLI, e o resultado é gravado na tarefa. Um ciclo curto
que não verifica nada não é o kata-agile — é o `--check-only`.

## As cinco fases

```
FIT → THINK → DECLARE → VERIFY → REPORT
```

| Fase | Interação | O que grava em `.kata/<task>.yaml` |
|------|-----------|-----------------------------------|
| FIT | 1 pergunta: rota, trivialidade e gatilho de escalonamento | `fit.*`, `base_commit` |
| THINK | 2 perguntas: problema e critério `done` | `think.problem`, `done` |
| DECLARE | 1 declaração: arquivos, alinhamento código/teste/spec, minimalidade | `surgical.files[]`, `intent.*`, `simplify.*` |
| VERIFY | 1 confirmação: o critério `done` está satisfeito? | `verify.*`, `status` |
| REPORT | 0 ou 1: houve defeito corrigido? | `artifact.*`, `twins.*` |

As fases **SIMPLIFY**, **INTENT** e **SURGICAL** não desapareceram: elas
viraram uma declaração única na fase DECLARE, e continuam gravando as mesmas
chaves — que são as que o `--judge` lê. O **TWIN CHECK** virou uma pergunta
dentro do REPORT. O **ARTIFACT** também: o cálculo das linhas devidas tem de
continuar rodando (ver §"REPORT"), porque é ele que arma a checagem de AUTH
do juiz.

## Preflight

Antes de começar, confirme a instalação com `Bash`:

```bash
python -m kata --doctor
```

Exit 1 é instalação **parcial** de skill obrigatória — pare e peça ao usuário
`kata --install all`. O `kata-agile` em si é **opcional** no doctor: se a
mensagem for só `ℹ️ skill de fase opcional faltando`, a instalação está sadia
e você está lendo esta skill, então ela existe.

Se a skill de uma fase não carregar com `Skill`, **não improvise** o
conteúdo dela: aplique o piso descrito em `phases/kata.md` §"Contrato mínimo de
cada fase", acrescente o nome a `preflight.skills_missing` e diga no relatório.

## Quando não usar — gatilho de escalonamento

Avalie no FIT e **reavalie no DECLARE** (o diff só existe depois do código).
Qualquer item abaixo manda a tarefa para o `@kata` completo:

1. diff acima de **5 arquivos** ou **200 linhas** adicionadas;
2. `domain != coding` (devops, research, data-analysis, docs);
3. **ação irreversível** — push, deploy, publish, migração de dados: AUTH
   vive no ciclo completo;
4. **VERIFY reprovou uma vez** — a segunda tentativa roda no `@kata`;
5. `fit.trivial: true` com diff acima do limite do juiz: escalar evita um
   `REFUTED` previsível.

O gatilho é **medido**, nunca "o agente achou melhor". Escalar não é falha do
ciclo curto — é o ciclo curto funcionando.

## Fase 1: FIT

Carregue `kata-fit` com `Skill` e siga-o. Diferença em relação ao ciclo
completo: você faz **uma** pergunta, e ela cobre rota, trivialidade e
escalonamento.

Grave `base_commit` (HEAD atual, via `Bash`: `git rev-parse HEAD`) se a
tarefa ainda não tiver. Sem ele, o `--judge` não tem piso de comparação.

Se a rota for `question`, `plan-first` ou `research`: **saia do kata-agile**.
As rotas são `code-loop | plan-first | question | research | inference` — só
`code-loop` segue para as cinco fases. As outras têm contrato próprio
(`kata-question`, `--plan`, pesquisa antes de agir) e não ganham nada com o
ciclo curto. `inference` é baixa confiança: diga isso ao usuário e não finja
rigor.

## Fase 2: THINK

Carregue `kata-think` com `Skill` e pergunte **duas** coisas, uma por
vez:

1. "Qual o problema exato, em uma frase?"
2. "O que é 'pronto'? (critério verificável + como confirmo)"

Assumptions, alternativas e unknowns são **opcionais** aqui: registre-os se o
usuário os der, mas não bloqueie a fase para obtê-los. O audit cobra
`think.problem`; o `done` é o que o VERIFY confronta depois.

Grave `think.problem`, `think.assumptions` (se houver), `done` e
`think.answered: true`. Atualize `status: think-complete`.

O `done` é declarado **antes** da evidência — é isso que impede o critério de
ser escrito depois do resultado para caber nele.

## Fase 3: DECLARE

Executada **depois** do código pronto. Rode `git diff --name-only` (e
`git diff --cached --name-only` se houver staged) com `Bash` e faça **uma**
declaração ao usuário, cobrindo os três pontos:

```
Vou declarar o que mudou. Para cada arquivo: por que ele é necessário?
Código, teste e spec concordam? Alguma abstração ou configuração não
rastreia ao pedido?
```

Grave as três seções de uma vez:

```yaml
surgical:
  files:
    - path: src/kata/cli.py
      necessary: true      # + uma frase do porquê, no relatório
  removed_imports_clean: true
  answered: true
intent:
  code_does: "..."          # o que o código FAZ hoje
  check_expects: "..."      # o que o teste/check ESPERA
  spec_says: "..."          # o que a especificação DIZ
  all_agree: true
  answered: true
simplify:
  minimum_code: true
  no_single_use_abstractions: true
  no_speculative_config: true
  answered: true
```

Regras que não mudam:

- **`surgical.files` não é opcional.** O `--judge` acusa `scope_creep` para
  todo arquivo alterado que não esteja declarado como `necessary: true`.
  Declarar é o que substitui a pergunta arquivo-por-arquivo.
- **Conflito entre código, teste e spec**: pare e resolva com o usuário pela
  ordem de autoridade — usuário > spec > testes > código. `all_agree: false`
  sem `intent.conflict_resolution` é `spec_betrayal` no juiz.
- Se o diff estourou o gatilho de escalonamento, **pare aqui** e entregue ao
  `@kata` com o que já está gravado.

## Fase 4: VERIFY

O gate é do CLI, não seu:

```bash
python -m kata --verify-task <task> --criterion-met
```

(no Windows, `py -m kata ...`)

- `--verify-task` roda lint, typecheck (se declarado em `.kata/config.yaml`),
  teste e coverage, grava `verify.commands`, `verify.gate_used`,
  `verify.ran_at`, os booleanos e o `status`. **Não transcreva resultado à
  mão** — evidência digitada é afirmação, e é isso que o `--judge` chama de
  `false_completion`.
- `--criterion-met` afirma que o `done` do THINK foi satisfeito. **Pergunte ao
  usuário antes** (esta é a interação desta fase). Se ele disser que não,
  use `--no-criterion-met` e a tarefa sai `rejected`.
- Sem a flag e sem terminal, o comando recusa: ninguém afirmou o critério.
- Exit 1 = não aprovado. Leia o output, corrija e repita. Ao chegar a **3
  falhas** (`verify.hand_back: true`), devolva a tarefa ao usuário com o que
  foi tentado, o output real e a hipótese atual — e escale para o `@kata`.

## Fase 5: REPORT

Duas coisas: o **cálculo das linhas devidas** (era o ARTIFACT) e o relatório.

1. Calcule as linhas devidas pelo CLI:

   ```bash
   python -m kata --artifact-task <task>
   ```

   Ele preenche `artifact.*` a partir do que já está no YAML: `intent_owed` se
   algum arquivo alterado não é documentação, `auth_owed` por
   `auth.action_taken`, `twins_owed` por conflito no INTENT ou defeito
   declarado. **Exit 1 significa linha devida ausente**, e a mensagem diz
   qual. Não transcreva `artifact` à mão: era o último ponto do ciclo curto em
   que o agente escrevia uma conta que o CLI sabe fazer.

   **`auth_owed` não é opcional.** Se você fez `push`, `deploy` ou `publish`,
   `auth.action_taken` é `true` e, sem `auth.authorized` **e** `auth.quote`, o
   juiz acusa `unauthorized_action` — ele lê o ato, não o cálculo, desde a
   0.10.0. Não existe caminho em que a linha AUTH seja devida e você a omita.

2. Se um **defeito foi corrigido** (ou se o INTENT registrou conflito),
   pergunte qual padrão buscar (``Grep`` no projeto inteiro) e grave
   `twins.pattern`, `twins.result`, `twins.searched: true`, contagens. Sem
   defeito corrigido, grave `twins.defect_fixed: false` — a resposta também é
   evidência de que a pergunta foi feita.

3. Salve o YAML e gere o relatório pelo CLI, que é quem sabe o formato:

   ```bash
   python -m kata --task <task> --report
   ```

   O `--report` recusa tarefa que não está `approved` — ou seja, não há
   relatório sem gate. Isso é intencional.

## Compatibilidade com `--audit`, `--judge` e `--report`

O ciclo curto **não muda o schema**. Ele grava as mesmas chaves, e por isso:

- `--audit` gradua `fit`, `think`, `intent`, `simplify`, `surgical`, `verify` e
  `twins` do mesmo jeito que no ciclo completo. Fase que você não tocar é
  **omitida**, não acusada; fase que você marcar `answered: true` com conteúdo
  vazio é `faked`.
- `--judge` continua válido: `scope_creep` lê `surgical.files`,
  `spec_betrayal` lê `intent`, `unauthorized_action` lê `artifact`,
  `false_completion` re-executa o gate. Nada nele pressupõe as 9 fases.
- `--report` só emite relatório de tarefa `approved`.

## O que este ciclo não faz

- **Não roda o `--judge` por padrão.** Verificação adversarial é para ação
  irreversível, tarefa de risco ou pedido explícito — nesses casos, escale
  para o `@kata` completo.
- **Não carrega domain adapter.** `domain != coding` é gatilho de
  escalonamento.
- **Não substitui o `@kata`.** Ele é o caminho para o que não é pequeno.

## Persistência

Grave o YAML **depois de cada fase** (`Write`/`Edit`). É o mesmo arquivo do
ciclo completo: uma tarefa pode começar em `kata-agile` e terminar no `@kata`
sem perder `base_commit`, `done` nem o que já foi declarado.

## Princípios

- **Encurte a conversa, nunca a verificação.**
- **Uma pergunta por fase**, com a resposta padrão proposta.
- **Declare, não interrogue**: no DECLARE você afirma e o usuário corrige.
- **Escalone cedo**: tarefa que estourou o gatilho no meio é do `@kata`.
- **Português BR** em todas as interações com o usuário.
