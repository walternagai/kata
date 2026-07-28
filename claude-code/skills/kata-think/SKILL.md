---
name: kata-think
description: Fase THINK do ciclo Karpathy (kata). Use quando o kata estiver na fase 1 — declarar problema, assumptions, alternativas e unknowns antes de codar. Triggers: THINK, assumptions, problema, unknowns, antes de codificar, declarar contexto.
---

# Skill: kata-think

Fase 1 do Karpathy Development Cycle — **THINK**.

## Objetivo

Antes de escrever qualquer linha de código, declarar explicitamente:
1. O problema exato que está sendo resolvido
2. As assumptions que estão sendo feitas (e que podem estar erradas)
3. As alternativas que foram consideradas (e por que foram descartadas)
4. O que NÃO se sabe (unknowns que precisam de investigação ou pergunta)

## Ferramentas

Para esta fase, use:

- **Texto livre** (ver `kata-question`): faça as 4 perguntas ao usuário, **uma a uma**,
  em texto normal, com uma proposta baseada em contexto quando possível. Não jogue
  todas de uma vez, e não force isso em `AskUserQuestion` — são respostas narrativas,
  não escolhas fechadas.
- **`Read` / `Grep`**: investigue unknowns sobre código existente (ex: "Como X funciona hoje?").
- **`Write` / `Edit`**: registre as respostas em `.kata/<task>.yaml` e atualize `status: think-complete`.

## Roteiro de Perguntas

### 1. Problema
> "Qual o problema exato que estou resolvendo?"

- Seja específico: não aceite "implementar feature X" — pergunte "qual dor X resolve?"
- Framing em uma frase: sujeito + verbo + objeto + contexto

### 2. Assumptions
> "Quais assumptions estou fazendo? (separadas por `;`)"

Uma assumption é uma crença não-verificada que, se errada, invalida a solução.

**Exemplos de boas assumptions:**
- "O usuário sempre autentica antes de acessar /run"
- "SQLite WAL mode é suficiente para a carga esperada"
- "O provider LLM retorna JSON válido na primeira tentativa"
- "Dados existentes com user_id=NULL podem ser tratados como globais"

**Exemplos de assumptions ruins (vagas):**
- "Deve funcionar"
- "Performance é ok"
- "Usuários vão usar direito"

### 3. Alternativas
> "Quais alternativas considerei? (separadas por `;`)"

Para cada alternativa, registrar:
- O que era
- Por que foi descartada

**Exemplo:**
```
- alt A: fail-fast com RuntimeError — descartado: quebra dev local intencional
- alt B: só warn sem health degraded — descartado: operador pode não ver logs
- alt C: warn + health degraded — escolhido: preserva dev sem silenciar em prod
```

### 4. Unknowns
> "O que NÃO sei? (preciso perguntar antes?)"

Unknowns são coisas que você precisa investigar no código, perguntar ao usuário,
ou testar antes de prosseguir.

**Tipos de unknown:**
- **Código**: "Como X funciona hoje?" → investigar com `Grep`/`Read`
- **Decisão**: "Devo usar A ou B?" → perguntar ao usuário (bom caso para `AskUserQuestion`, se A/B forem as únicas opções)
- **Comportamento**: "O que acontece quando Y?" → testar ou perguntar

Se um unknown bloqueia a implementação, **PARE e pergunte** antes de prosseguir.
Se é investigável, resolva-o e registre a resposta.

## Quando o usuário não sabe

Se o usuário responder "não sei" ou "você decide", proponha uma resposta baseada
no contexto do diff/repositório e peça confirmação:

> "Com base no diff, o problema parece ser X. Concorda? Se sim, vou registrar
> como: 'X'."

Não aceite respostas vagas. Exija especificidade: "Deve funcionar" não é uma
assumption válida.

## Output no YAML

Após coletar as respostas, escreva/atualize `.kata/<task>.yaml`:

```yaml
status: think-complete
think:
  problem: "O Mushin v2.2 acumula três problemas P0 que impedem confiança em produção..."
  assumptions:
    - "FR-01: warn no startup + /health degraded (não fail-fast)"
    - "FR-02: migration SQLite adiciona coluna user_id com default NULL"
  alternatives:
    - "alt A: fail-fast — descartado: quebra dev local"
    - "alt B: só warn — descartado: operador pode não ver"
  unknowns: |
    RESOLVIDO:
    1. Como extrair user_id? → dependencies.py:177 retorna user dict
    2. Migration SQLite? → seguir pattern ADD_*_COLUMN existente
  answered: true
```

## Princípios

- **Propose, don't interrogate**: se o usuário não sabe, proponha uma resposta baseada no contexto
- **Show reasoning**: registre por que cada alternativa foi descartada
- **Investigue unknowns**: não deixe unknowns em aberto — resolva-os ou escale
- **Seja específico**: assumptions vagas não protegem contra nada
