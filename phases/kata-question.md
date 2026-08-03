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

<!--only:opencode-->
Guia para o uso da ferramenta {{ASK}} e da rota `question` no Karpathy Development Cycle.
<!--/only-->
<!--only:claude-code-->
Guia para perguntar ao usuário e para a rota `question` no Karpathy
Development Cycle, adaptado ao conjunto de ferramentas do Claude Code.
<!--/only-->

## Objetivo

1. Fazer perguntas ao usuário de forma disciplinada, uma por vez, sem interrogar.
2. Diagnosticar e entregar achados quando a tarefa for classificada como rota `question` no FIT.
3. Evitar decisões unilaterais quando a resposta depende de preferência, contexto de negócio ou intenção do usuário.

<!--only:opencode-->
## Ferramentas

Para esta skill, use:

- **{{ASK}}**: faça uma pergunta por chamada. Não agrupe múltiplas perguntas em uma única chamada.
- **{{BASH}}**: `git diff`, `grep`, `pytest` etc., para coletar evidências antes de perguntar.
- **{{READ}} / {{GREP}}**: investigue o código para embasar a pergunta.
- **{{WRITE}} / {{EDIT}}**: registre a resposta ou os achados em `.kata/<task>.yaml`.
<!--/only-->
<!--only:claude-code-->
## Diferença em relação ao OpenCode

O OpenCode tem uma ferramenta dedicada `question` para perguntas de texto
livre. O Claude Code não tem — existem duas formas de perguntar, e a escolha
entre elas importa:

| Tipo de pergunta | Ferramenta | Exemplos no kata |
|-------------------|-----------|-------------------|
| **Aberta / texto livre** | Responda em texto normal, com uma proposta baseada em contexto, e espere a próxima mensagem do usuário. **Não** use {{ASK}} aqui — ela é para decisões fechadas, não para narrativa livre. | THINK (problem/assumptions/alternatives/unknowns), INTENT (code_does/check_expects/spec_says), observações opcionais |
| **Fechada / poucas opções nomeadas** | {{ASK}} — até 4 opções por pergunta, sempre com "Other" disponível para texto livre. Coloque a opção que você recomenda em primeiro lugar. | FIT (rota, se reduzida a até 4 alternativas nomeadas), SIMPLIFY (checklist sim/não), SURGICAL (arquivo necessário?), VERIFY (critério de sucesso satisfeito?), INTENT (como resolver um conflito) |

Regra prática: se a resposta certa é "escreva um parágrafo", pergunte em
texto. Se a resposta certa é "escolha entre A, B ou C" (ou "sim/não"), use
{{ASK}}.
<!--/only-->

## Rota `question` no FIT

A rota `question` é escolhida quando o usuário quer entender algo antes de decidir.

| Quando usar | Exemplo | O que fazer |
|-------------|---------|-------------|
| Diagnóstico | "Por que X está lento?" | Investigue, meça, mostre achados. Não mude código. |
| Opinião / recomendação | "O que você acha de usar Y?" | Liste prós e contras, recomende, aguarde decisão. |
| Esclarecimento | "Como Z funciona hoje?" | Explique baseado no código/doc, confirme se é isso. |
<!--only:opencode-->
| Conflito de intenção | Código/teste/spec discordam | Pergunte qual autoridade prevalece. |
<!--/only-->
<!--only:claude-code-->
| Conflito de intenção | Código/teste/spec discordam | Pergunte qual autoridade prevalece (bom caso para {{ASK}}). |
<!--/only-->

### Procedimento da rota `question`

1. **Entenda a pergunta** — reformule para o usuário confirmar.
2. **Colete evidências** — use {{BASH}}, {{READ}} e {{GREP}} para obter dados.
3. **Não altere código** — a menos que o usuário autorize explicitamente.
4. **Entregue achados** — organize em: contexto, evidências, recomendação.
5. **Registre** em `.kata/<task>.yaml` (via {{WRITE}}/{{EDIT}}) sob `question` e finalize o ciclo.

```yaml
status: approved
fit:
  trivial: false
  route: question
  reason: "Usuário perguntou por que cobertura caiu no módulo X"
question:
  question: "Por que a cobertura caiu no módulo X?"
  findings: |
    - Arquivo X.py adicionou 120 linhas sem testes
    - Função Y não é chamada por nenhum teste
  recommendation: "Adicionar testes para Y e extrair lógica testável"
  action_taken: false
  user_approved: false
```

## Uso geral de perguntas

### Regras

<!--only:opencode-->
- **Uma pergunta por chamada** — nunca jogue 4 perguntas de uma vez.
- **Contexto primeiro** — mostre ao usuário o que você já sabe antes de perguntar.
- **Proponha, não interrogue** — ofereça uma resposta padrão; pergunte se confirma.
<!--/only-->
<!--only:claude-code-->
- **Uma pergunta por vez** — nunca jogue 4 perguntas abertas de uma vez em texto; se forem fechadas, {{ASK}} já limita a 4 por chamada.
- **Contexto primeiro** — mostre ao usuário o que você já sabe (diff, achados) antes de perguntar.
- **Proponha, não interrogue** — ofereça uma resposta padrão (a primeira opção em {{ASK}}, ou a proposta inicial em texto); pergunte se confirma.
<!--/only-->
- **Seja específico** — perguntas vagas geram respostas vagas.
- **Não use pergunta para substituir investigação** — primeiro pesquise com {{BASH}}/{{READ}}/{{GREP}}, depois pergunte.

### Exemplos

<!--only:opencode-->
❌ Bad:
> "Qual o problema? Quais assumptions? Quais alternativas? O que você não sabe?"

✅ Good:
> "Qual o problema exato que estou resolvendo? (ex: 'parse_date falha quando a entrada tem timezone')"
<!--/only-->
<!--only:claude-code-->
❌ Bad (texto livre tratado como se fosse escolha fechada):
> {{ASK}} com opções ["Sim", "Não"] para "Qual o problema exato que estou resolvendo?"

✅ Good (pergunta aberta, em texto, com proposta):
> "Pelo diff, parece que `parse_date` falha quando a entrada tem timezone.
> Esse é o problema exato que estamos resolvendo? Se não, descreva em uma frase."
> *(aguarda a próxima mensagem do usuário)*

✅ Good (pergunta fechada, via {{ASK}}):
> Pergunta: "O arquivo `app/dashboard/pages/Overview.py` é necessário para esta tarefa?"
> Opções: ["Sim, necessário (recomendado)", "Não, é refactoring fora do escopo"]
<!--/only-->

### Quando perguntar

<!--only:opencode-->
- FIT: para classificar rota e trivialidade.
- THINK: para preencher problem/assumptions/alternatives/unknowns.
- SIMPLIFY: para validar se código é mínimo.
- INTENT: para resolver conflitos entre código/teste/spec.
- SURGICAL: para confirmar se arquivo/import é necessário.
- VERIFY: para confirmar se critério de sucesso foi satisfeito.
<!--/only-->
<!--only:claude-code-->
- FIT: para classificar rota e trivialidade (rota com {{ASK}} se couber em 4 opções nomeadas; senão, liste em texto e peça a escolha).
- THINK: para preencher problem/assumptions/alternatives/unknowns (texto livre).
- SIMPLIFY: para validar se código é mínimo ({{ASK}} sim/não).
- INTENT: para resolver conflitos entre código/teste/spec ({{ASK}} com a ordem de autoridade como opções).
- SURGICAL: para confirmar se arquivo/import é necessário ({{ASK}} por arquivo, ou lista em texto se houver muitos arquivos).
- VERIFY: para confirmar se critério de sucesso foi satisfeito ({{ASK}} sim/não).
<!--/only-->

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
<!--only:claude-code-->
- **Ferramenta certa para o tipo certo de pergunta**: texto livre para narrativa, {{ASK}} para decisões fechadas.
<!--/only-->
- **Diagnóstico não é ação**: na rota `question`, o output é conhecimento, não diff.
- **Documente a resposta**: registre no YAML para rastreabilidade.
