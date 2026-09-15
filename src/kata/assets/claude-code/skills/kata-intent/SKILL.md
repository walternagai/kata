---
name: kata-intent
description: Fase INTENT do ciclo Karpathy (kata). Use quando o kata estiver na fase 2.5 — verificar intenção entre código, teste e especificação antes de mudar comportamento. Triggers: INTENT, intent gate, intenção, código vs teste, spec, conflito, fable-method.
---
<!-- Gerado por scripts/build_skills.py a partir de phases/kata-intent.md. Não edite aqui. -->

# Skill: kata-intent

Fase 2.5 do Karpathy Development Cycle — **INTENT**.

Inspirado no **intent gate** do [The Fable Method](https://github.com/Sahir619/fable-method).

## Objetivo

Antes de qualquer mudança de comportamento, verificar que código, teste e
especificação estão alinhados. Se discordam, o conflito deve ser resolvido
antes de editar — nunca faça o código concordar com o teste silenciosamente.

## Ferramentas

- **`Read`**: abra o código, o teste e a spec/README/docstring.
- **`AskUserQuestion`** (via `kata-question`): pergunte ao usuário em caso de conflito.
- **`Write` / `Edit`**: registre o intent gate em `.kata/<task>.yaml`.

## Procedimento

### 1. Abrir as três fontes

Antes de editar qualquer arquivo:

1. **Leia o código atual** (a função/classe que será alterada)
2. **Leia o teste** (o que ele espera)
3. **Leia a spec** (README, docstring, comentário, PRD)

Se qualquer uma das três não existir, registre como "ausente".

### 2. Registrar o intent gate

Escreva três linhas no YAML:

```yaml
intent:
  code_does: "parse_date retorna datetime sem timezone"
  check_expects: "test espera datetime com timezone UTC"
  spec_says: "README: datas devem preservar timezone"
  answered: false
  skipped: false       # true só se a fase foi preenchida com default sem
                       # ninguém responder (modo não-interativo)
```

### 3. Verificar concordância

Se `code_does`, `check_expects` e `spec_says` não concordam:

1. **NÃO edite ainda.** O conflito é a descoberta mais importante.
2. Determine a ordem de autoridade:
   - Declaração explícita do usuário > spec/README > teste > código atual
3. Pergunte ao usuário (via `AskUserQuestion`, com as opções sendo as
   fontes possíveis a seguir) ou resolva pela ordem de autoridade.
4. Registre a resolução no YAML.

### 4. Referência: ordem de autoridade

Extraída do fable-method (Step 4.1):

| Fonte | Autoridade |
|-------|------------|
| Declaração do usuário | Mais alta |
| Spec / README / docstring | Segunda |
| Testes | Terceira |
| Código atual | Mais baixa |

Um pedido "corrija o código" ou "faça os testes passarem" **não** é uma
declaração de comportamento esperado — não promove os testes acima da spec.

### Exemplo

```
INTENT: code does: parse_date retorna datetime naive (sem timezone)
        check expects: datetime com timezone UTC
        spec says: README §2: "datas preservam fuso horário da entrada"

Código e spec concordam; teste está desatualizado.
Resolução: corrigir o teste, não o código.
```
