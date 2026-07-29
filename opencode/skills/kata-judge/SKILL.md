---
name: kata-judge
description: Fase JUDGE do ciclo Karpathy (kata). Verificação adversarial de tarefas concluídas — re-executa verificações, caça fraudes, entrega veredito. Triggers: JUDGE, adversarial verification, fable-judge, caça fraudes, veredito, REFUTED, VERIFIED WITH CAVEATS.
---

# Skill: kata-judge

Fase 5 do Karpathy Development Cycle — **JUDGE** (adversarial verification).

Inspirado no **fable-judge** do [The Fable Method](https://github.com/Sahir619/fable-method),
que trata um relatório como um conjunto de claims e não acredita em nada
que não observou.

## Objetivo

Verificar adversarialmente uma tarefa concluída:

1. **Collect claims** — extrair do YAML o que o relatório diz que foi feito
2. **Establish ground truth** — diff contra o estado real do código, desde
   `base_commit` (o HEAD registrado no início da tarefa, na fase FIT) se
   disponível; senão, diff local (unstaged/staged). `base_commit` é o que
   permite ao JUDGE continuar enxergando a mudança depois que ela é
   commitada — o estado normal de uma tarefa "concluída"
3. **Re-run every claimed verification** — executar de novo e comparar
4. **Hunt frauds** — 6 categorias
5. **Deliver verdict** — VERIFIED / VERIFIED WITH CAVEATS / REFUTED

## Execução

Use o CLI do kata:

```bash
python -m kata --task <name> --judge
```

Ou para tarefa detectada por branch:

```bash
python -m kata --judge
```

## As 6 Fraudes

| # | Fraude | Descrição | Severidade |
|---|--------|-----------|------------|
| 1 | **Weakened checks** | Asserts removidos ou relaxados em arquivos de teste, linhas comentadas, `pass` substituindo corpo de teste, `noqa` adicionado | 🔴 alta |
| 2 | **False completion** | Relatório afirma que verificação passou, mas re-execução mostra falha | 🔴 alta |
| 3 | **Scope creep** | Arquivos alterados que não foram declarados como necessários na fase SURGICAL | 🟡 média/alta |
| 4 | **Unauthorized action** | Ação externa (push, deploy) realizada sem AUTH line documentada | 🔴 alta |
| 5 | **Spec betrayal** | Código alterado para satisfazer teste que contradiz a especificação | 🔴 alta |
| 6 | **Debris** | Arquivos temporários (`.tmp`, `.bak`), debug prints, TODOs, lixo | 🟢 baixa |

## Vereditos

| Veredito | Condição |
|----------|----------|
| **VERIFIED** | Nenhuma fraude encontrada |
| **VERIFIED WITH CAVEATS** | Fraudes de média/baixa severidade, nenhuma alta |
| **REFUTED** | Pelo menos uma fraude de alta severidade |

## Resultado no CLI

```
  Claims verificadas:
    • ruff check limpo (sem erros de lint)
    • todos os testes passam
    • coverage ≥ gate (95.0%)

  Claims aceitas sem verificação (não re-executáveis):
    • critério de sucesso satisfeito

  Fraudes encontradas:
    🔴 [high] false_completion
       ruff re-executado falhou, mas relatório afirma que passou
       → relatório: ruff_clean=True → reality: ruff falhou
    🟡 [medium] scope_creep
       2 arquivo(s) alterado(s) não declarado(s) como necessários
       → extra_a.py, extra_b.py

  Re-execução:
    ✅ ruff
    ❌ pytest

──────────────────────────────────────────────────────────

❌  KATA JUDGE — REFUTED
```

## Registro no YAML

O CLI Python não persiste o resultado do judge de volta no arquivo de
tarefa — `--judge` é uma verificação stateless, re-executada a cada chamada.
Se o agente decidir registrar o veredito em `.kata/<task>.yaml` (via
`write`/`edit`), use a chave `judge`:

```yaml
judge:
  verdict: "REFUTED"           # VERIFIED | VERIFIED WITH CAVEATS | REFUTED
  frauds:
    - type: false_completion
      severity: high
      description: "ruff re-executado falhou, mas relatório afirma que passou"
  caveats:
    - "1 fraude(s) de alta severidade"
  judged_at: "2026-07-28"      # data (ou commit) em que o judge rodou
```

## Modo Automático

O judge executa automaticamente como fase extra ao final do ciclo se
desejado, mas por padrão é um modo separado (`--judge`) que o usuário
invoca explicitamente para verificar uma tarefa já concluída.

## Princípios

- **O diff é a verdade; o relatório não é**: acredite no que o git mostra, não no que o YAML diz
- **Re-execute sempre**: toda claim de verificação deve ser re-executada, nunca assumida
- **Fraude de alta severidade = REFUTED**: uma só já invalida o ciclo
- **Caveats honestos**: se algo não pôde ser verificado, diga exatamente isso
