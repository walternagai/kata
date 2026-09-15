---
name: kata-artifact
description: Fase ARTIFACT do ciclo Karpathy (kata). Use quando o kata estiver na fase 4.5 — verificar que linhas devidas (INTENT, AUTH, PENDING, TWINS) estão no relatório antes de finalizar. Triggers: ARTIFACT, artifact gate, relatório, linhas devidas, fable-method.
---
<!-- Gerado por scripts/build_skills.py a partir de phases/kata-artifact.md. Não edite aqui. -->

# Skill: kata-artifact

Fase 4.5 do Karpathy Development Cycle — **ARTIFACT**.

Inspirado no **artifact gate** do [The Fable Method](https://github.com/Sahir619/fable-method).

## Objetivo

Antes de finalizar o ciclo, varrer o relatório e verificar que todas as
linhas devidas estão presentes. Se algo está ausente e é devido, adicione.

## Ferramentas

- **`Read`**: verifique o `.kata/<task>.yaml` atual.
- **`AskUserQuestion`** (via `kata-question`) ou texto livre: preencha linhas devidas ausentes.
- **`Write` / `Edit`**: registre o resultado em `.kata/<task>.yaml`.

## Linhas devidas

| Linha | Quando é devida | Onde aparece |
|-------|-----------------|--------------|
| `INTENT: code does <X>; check expects <Y>; spec says <Z>` | Comportamento foi alterado | Seção `intent` do YAML |
| `AUTH: user said "<exact words>"` | Ação irreversível (push, deploy, publish) | Seção `auth` do YAML |
| `PENDING: <action> - awaiting your authorization` | Ação prescrita pelas docs mas não executada | Seção `pending` do YAML |
| `TWINS: searched <pattern> - found <N> other sites: <files>` | `twins.defect_fixed: true` | Seção `twins` do YAML |

## Procedimento

### 1. Verificar INTENT

Se comportamento foi alterado (VERIFY foi executado):
- A seção `intent` do YAML deve ter `answered: true` e `code_does` preenchido
  — ou, em ciclo não-interativo, `skipped: true` (ninguém respondeu; a fase
  foi preenchida com default, e isso é documentado, não omitido).
- Se ausente: registre que a intenção não foi documentada.

### 2. Verificar AUTH

Se uma ação irreversível foi tomada:
- O YAML deve ter a seção `auth` com a citação exata do usuário.
- Se ausente: registre que a ação não foi autorizada.

### 3. Verificar PENDING

Se as docs do projeto prescrevem uma ação pós-tarefa (deploy, restart):
- O YAML deve ter a seção `pending` documentando a ação não tomada.
- Se ausente: registre o follow-up pendente.

### 4. Verificar TWINS

O sinal é `twins.defect_fixed`, gravado pela fase TWIN CHECK — não "as
verificações passaram", que é o estado normal de qualquer tarefa concluída e
faria esta linha ser cobrada sempre. Se a fase TWIN CHECK não rodou, a
resposta não foi registrada e a linha fica em aberto.

Se um defeito foi corrigido:
- O YAML deve ter a seção `twin` com o padrão buscado e resultados.
- Se ausente: registre que a varredura de gêmeos não foi feita.

### 5. Relatório final

```yaml
artifact:
  intent_owed: true
  intent_present: true
  auth_owed: false
  auth_present: true
  pending_owed: false
  pending_present: true
  twins_owed: false
  twins_present: true
```

Se houver linhas devidas ausentes e não puder corrigir, marque como
relatório com ressalvas no status final.
