---
name: kata-question
description: Uso da ferramenta `question` e da rota `question` no ciclo Karpathy (kata). Use quando o agente @kata precisar perguntar algo ao usuário, diagnosticar sem alterar código, ou conduzir questionários no FIT, THINK, SIMPLIFY, INTENT, SURGICAL ou VERIFY. Triggers: question, perguntar, questionário, diagnosticar, rota question.
---

# Skill: kata-question

Guia para o uso da ferramenta `question` e da rota `question` no Karpathy Development Cycle.

## Objetivo

1. Fazer perguntas ao usuário de forma disciplinada, uma por vez, sem interrogar.
2. Diagnosticar e entregar achados quando a tarefa for classificada como rota `question` no FIT.
3. Evitar decisões unilaterais quando a resposta depende de preferência, contexto de negócio ou intenção do usuário.

## Ferramentas

Para esta skill, use:

- **`question`**: faça uma pergunta por chamada. Não agrupe múltiplas perguntas em uma única chamada.
- **`bash`**: `git diff`, `grep`, `pytest` etc., para coletar evidências antes de perguntar.
- **`read` / `grep`**: investigue o código para embasar a pergunta.
- **`write` / `edit`**: registre a resposta ou os achados em `.kata/<task>.yaml`.

## Rota `question` no FIT

A rota `question` é escolhida quando o usuário quer entender algo antes de decidir.

| Quando usar | Exemplo | O que fazer |
|-------------|---------|-------------|
| Diagnóstico | "Por que X está lento?" | Investigue, meça, mostre achados. Não mude código. |
| Opinião / recomendação | "O que você acha de usar Y?" | Liste prós e contras, recomende, aguarde decisão. |
| Esclarecimento | "Como Z funciona hoje?" | Explique baseado no código/doc, confirme se é isso. |
| Conflito de intenção | Código/teste/spec discordam | Pergunte qual autoridade prevalece. |

### Procedimento da rota `question`

1. **Entenda a pergunta** — reformule para o usuário confirmar.
2. **Colete evidências** — use `bash`, `read`, `grep` para obter dados.
3. **Não altere código** — a menos que o usuário autorize explicitamente.
4. **Entregue achados** — organize em: contexto, evidências, recomendação.
5. **Registre** em `.kata/<task>.yaml` sob `question` e finalize o ciclo.

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

## Uso geral da ferramenta `question`

### Regras

- **Uma pergunta por chamada** — nunca jogue 4 perguntas de uma vez.
- **Contexto primeiro** — mostre ao usuário o que você já sabe antes de perguntar.
- **Proponha, não interrogue** — ofereça uma resposta padrão; pergunte se confirma.
- **Seja específico** — perguntas vagas geram respostas vagas.
- **Não use `question` para substituir investigação** — primeiro pesquise, depois pergunte.

### Exemplos

❌ Bad:
> "Qual o problema? Quais assumptions? Quais alternativas? O que você não sabe?"

✅ Good:
> "Qual o problema exato que estou resolvendo? (ex: 'parse_date falha quando a entrada tem timezone')"

### Quando perguntar

- FIT: para classificar rota e trivialidade.
- THINK: para preencher problem/assumptions/alternatives/unknowns.
- SIMPLIFY: para validar se código é mínimo.
- INTENT: para resolver conflitos entre código/teste/spec.
- SURGICAL: para confirmar se arquivo/import é necessário.
- VERIFY: para confirmar se critério de sucesso foi satisfeito.

## Output no YAML

Para uso geral, registre quando a resposta influencia o ciclo:

```yaml
question:
  asked: "O critério de sucesso da tarefa está satisfeito?"
  answer: "Sim"
  context: "Testes passam e cobertura está acima de 70%"
```

Para rota `question`, use o formato acima com `findings` e `recommendation`.

## Princípios

- **Uma pergunta por vez**: respeite o tempo de resposta do usuário.
- **Contexto antes de pergunta**: mostre dados, não peça para adivinhar.
- **Propose, don't interrogate**: ofereça uma resposta, não uma inquisição.
- **Diagnóstico não é ação**: na rota `question`, o output é conhecimento, não diff.
- **Documente a resposta**: registre no YAML para rastreabilidade.
