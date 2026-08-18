<!--only:opencode-->
---
name: kata-question
description: Uso da ferramenta `question` e da rota `question` no ciclo Karpathy (kata). Use quando {{AGENTE}} precisar perguntar algo ao usuário, diagnosticar sem alterar código, ou conduzir questionários no FIT, THINK, SIMPLIFY, INTENT, SURGICAL ou VERIFY. Triggers: question, perguntar, questionário, diagnosticar, rota question.
---
<!--/only-->
<!--only:claude-code-->
---
name: kata-question
description: Como perguntar ao usuário e a rota `question` no ciclo Karpathy (kata) para Claude Code. Use quando {{AGENTE}} precisar perguntar algo ao usuário, diagnosticar sem alterar código, ou conduzir questionários no FIT, THINK, SIMPLIFY, INTENT, SURGICAL ou VERIFY. Triggers: question, perguntar, questionário, diagnosticar, rota question, AskUserQuestion.
---
<!--/only-->

# Skill: kata-question

<!--ifnot:closed_choice_ask-->
Guia para o uso da ferramenta {{ASK}} e da rota `question` no Karpathy Development Cycle.
<!--/ifnot-->
<!--if:closed_choice_ask-->
Guia para perguntar ao usuário e para a rota `question` no Karpathy
Development Cycle, adaptado a um host cuja ferramenta de perguntar é de
escolha fechada.
<!--/if-->

**A rota `question` e a ferramenta de perguntar são coisas diferentes.** A
rota é um valor de `fit.route` no YAML da tarefa e se escreve `question` em
qualquer frontend; a ferramenta muda de nome conforme o host.

## Objetivo

1. Fazer perguntas ao usuário de forma disciplinada, uma por vez, sem interrogar.
2. Diagnosticar e entregar achados quando a tarefa for classificada como rota `question` no FIT.
3. Evitar decisões unilaterais quando a resposta depende de preferência, contexto de negócio ou intenção do usuário.

<!--ifnot:closed_choice_ask-->
## Ferramentas

Para esta skill, use:

- **{{ASK}}**: faça uma pergunta por chamada. Não agrupe múltiplas perguntas em uma única chamada.
- **{{RUN}}**: `git diff`, `grep`, `pytest` etc., para coletar evidências antes de perguntar.
- **{{READ}} / {{SEARCH}}**: investigue o código para embasar a pergunta.
- **{{WRITE}} / {{EDIT}}**: registre a resposta ou os achados em `.kata/<task>.yaml`.
<!--/ifnot-->
<!--if:closed_choice_ask-->
## Qual ferramenta para qual pergunta

Neste host, {{ASK}} é de **escolha fechada**: opções nomeadas, até 4 por
pergunta, com "Other" sempre disponível para texto livre. Não há ferramenta
dedicada para pergunta aberta — ela vai em texto normal. A escolha entre as
duas formas importa:

| Tipo de pergunta | Ferramenta | Exemplos no kata |
|-------------------|-----------|-------------------|
| **Aberta / texto livre** | Responda em texto normal, com uma proposta baseada em contexto, e espere a próxima mensagem do usuário. **Não** use {{ASK}} aqui — ela é para decisões fechadas, não para narrativa livre. | THINK (problem/assumptions/alternatives/unknowns), INTENT (code_does/check_expects/spec_says), observações opcionais |
| **Fechada / poucas opções nomeadas** | {{ASK}} — até 4 opções por pergunta, sempre com "Other" disponível para texto livre. Coloque a opção que você recomenda em primeiro lugar. | FIT (rota, se reduzida a até 4 alternativas nomeadas), SIMPLIFY (checklist sim/não), SURGICAL (arquivo necessário?), VERIFY (critério de sucesso satisfeito?), INTENT (como resolver um conflito) |

Regra prática: se a resposta certa é "escreva um parágrafo", pergunte em
texto. Se a resposta certa é "escolha entre A, B ou C" (ou "sim/não"), use
{{ASK}}.
<!--/if-->

## Rota `question` no FIT

A rota `question` é escolhida quando o usuário quer entender algo antes de decidir.

| Quando usar | Exemplo | O que fazer |
|-------------|---------|-------------|
| Diagnóstico | "Por que X está lento?" | Investigue, meça, mostre achados. Não mude código. |
| Opinião / recomendação | "O que você acha de usar Y?" | Liste prós e contras, recomende, aguarde decisão. |
| Esclarecimento | "Como Z funciona hoje?" | Explique baseado no código/doc, confirme se é isso. |
<!--ifnot:closed_choice_ask-->
| Conflito de intenção | Código/teste/spec discordam | Pergunte qual autoridade prevalece. |
<!--/ifnot-->
<!--if:closed_choice_ask-->
| Conflito de intenção | Código/teste/spec discordam | Pergunte qual autoridade prevalece (bom caso para {{ASK}}). |
<!--/if-->

### Procedimento da rota `question`

1. **Entenda a pergunta** — reformule para o usuário confirmar.
2. **Colete evidências** — use {{RUN}}, {{READ}} e {{SEARCH}} para obter dados.
3. **Não altere código** — a menos que o usuário autorize explicitamente.
4. **Entregue achados** — organize em: contexto, evidências, recomendação.
5. **Registre** em `.kata/<task>.yaml` (via {{WRITE}}/{{EDIT}}) e finalize o ciclo.

> A rota `question` NÃO tem seção própria no schema: o audit, o relatório e o
> judge não leem `question:` no YAML (K-19). Registre os achados nas chaves
> existentes — `think.problem`/`think.unknowns` para contexto e `fit.reason`
> para a recomendação — e deixe `status` como `think-complete`: o CLI para
> após o THINK nesta rota e não aprova a tarefa.

```yaml
status: think-complete
fit:
  trivial: false
  route: question
  reason: "Diagnóstico: cobertura caiu no módulo X — achados: 120 linhas sem teste em X.py, função Y sem chamada; recomendação: testar Y e extrair lógica testável. Usuário não autorizou alteração."
think:
  problem: "Por que a cobertura caiu no módulo X?"
  unknowns: "RESOLVIDO: X.py ganhou 120 linhas sem testes; Y não é chamada por teste nenhum."
  answered: true
```

## Uso geral de perguntas

### Regras

<!--ifnot:closed_choice_ask-->
- **Uma pergunta por chamada** — nunca jogue 4 perguntas de uma vez.
- **Contexto primeiro** — mostre ao usuário o que você já sabe antes de perguntar.
- **Proponha, não interrogue** — ofereça uma resposta padrão; pergunte se confirma.
<!--/ifnot-->
<!--if:closed_choice_ask-->
- **Uma pergunta por vez** — nunca jogue 4 perguntas abertas de uma vez em texto; se forem fechadas, {{ASK}} já limita a 4 por chamada.
- **Contexto primeiro** — mostre ao usuário o que você já sabe (diff, achados) antes de perguntar.
- **Proponha, não interrogue** — ofereça uma resposta padrão (a primeira opção em {{ASK}}, ou a proposta inicial em texto); pergunte se confirma.
<!--/if-->
- **Seja específico** — perguntas vagas geram respostas vagas.
- **Não use pergunta para substituir investigação** — primeiro pesquise com {{RUN}}/{{READ}}/{{SEARCH}}, depois pergunte.

### Exemplos

<!--ifnot:closed_choice_ask-->
❌ Bad:
> "Qual o problema? Quais assumptions? Quais alternativas? O que você não sabe?"

✅ Good:
> "Qual o problema exato que estou resolvendo? (ex: 'parse_date falha quando a entrada tem timezone')"
<!--/ifnot-->
<!--if:closed_choice_ask-->
❌ Bad (texto livre tratado como se fosse escolha fechada):
> {{ASK}} com opções ["Sim", "Não"] para "Qual o problema exato que estou resolvendo?"

✅ Good (pergunta aberta, em texto, com proposta):
> "Pelo diff, parece que `parse_date` falha quando a entrada tem timezone.
> Esse é o problema exato que estamos resolvendo? Se não, descreva em uma frase."
> *(aguarda a próxima mensagem do usuário)*

✅ Good (pergunta fechada, via {{ASK}}):
> Pergunta: "O arquivo `app/dashboard/pages/Overview.py` é necessário para esta tarefa?"
> Opções: ["Sim, necessário (recomendado)", "Não, é refactoring fora do escopo"]
<!--/if-->

### Quando perguntar

<!--ifnot:closed_choice_ask-->
- FIT: para classificar rota e trivialidade.
- THINK: para preencher problem/assumptions/alternatives/unknowns.
- SIMPLIFY: para validar se código é mínimo.
- INTENT: para resolver conflitos entre código/teste/spec.
- SURGICAL: para confirmar se arquivo/import é necessário.
- VERIFY: para confirmar se critério de sucesso foi satisfeito.
<!--/ifnot-->
<!--if:closed_choice_ask-->
- FIT: para classificar rota e trivialidade (rota com {{ASK}} se couber em 4 opções nomeadas; senão, liste em texto e peça a escolha).
- THINK: para preencher problem/assumptions/alternatives/unknowns (texto livre).
- SIMPLIFY: para validar se código é mínimo ({{ASK}} sim/não).
- INTENT: para resolver conflitos entre código/teste/spec ({{ASK}} com a ordem de autoridade como opções).
- SURGICAL: para confirmar se arquivo/import é necessário ({{ASK}} por arquivo, ou lista em texto se houver muitos arquivos).
- VERIFY: para confirmar se critério de sucesso foi satisfeito ({{ASK}} sim/não).
<!--/if-->

## Output no YAML

Registre quando a resposta influencia o ciclo:

```yaml
question:
  asked: "O critério de sucesso da tarefa está satisfeito?"
  answer: "Sim"
  context: "Testes passam e cobertura está acima de 70%"
```

Para rota `question`, use o formato com `findings` e `recommendation` mostrado acima.

## Princípios

- **Uma pergunta por vez**: respeite o tempo de resposta do usuário.
- **Contexto antes de pergunta**: mostre dados, não peça para adivinhar.
- **Propose, don't interrogate**: ofereça uma resposta, não uma inquisição.
<!--if:closed_choice_ask-->
- **Ferramenta certa para o tipo certo de pergunta**: texto livre para narrativa, {{ASK}} para decisões fechadas.
<!--/if-->
- **Diagnóstico não é ação**: na rota `question`, o output é conhecimento, não diff.
- **Documente a resposta**: registre no YAML para rastreabilidade.
