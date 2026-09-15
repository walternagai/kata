---
name: kata-report
description: Fase REPORT do ciclo Karpathy (kata). Gera relatório outcome-first com INTENT/AUTH/PENDING/TWINS lines, caveats honestos, e sem scaffolding do ciclo. Triggers: REPORT, outcome-first, relatório, fable-method step 6, resultado final, INTENT line, AUTH line, PENDING line, TWINS line.
---
<!-- Gerado por scripts/build_skills.py a partir de phases/kata-report.md. Não edite aqui. -->

# Skill: kata-report

Fase 5 do Karpathy Development Cycle — **REPORT**.

Inspirado no **Step 6** do [The Fable Method](https://github.com/Sahir619/fable-method):
a primeira frase responde "o que aconteceu", detalhes depois, sem números de passo.

## Objetivo

Produzir um relatório legível por humanos que:

1. **Outcome first**: primeira frase = resultado aprovado/rejeitado
2. **O que foi feito**: problema declarado, arquivos alterados
3. **INTENT line**: se comportamento mudou, documentar code/check/spec
4. **Verificações**: ruff, pytest, coverage, critério de sucesso
5. **Caveats honestos**: o que foi pulado, fraco, ou não verificável
6. **Forced artifact lines**: AUTH/PENDING/TWINS se devidas
7. **Zero scaffolding**: sem nomes de passo, sem números de fase

## Execução

Via `Bash`:
```bash
python -m kata --task <name>     # relatório automático ao final do ciclo
python -m kata --task <name> --report   # regenerar relatório de tarefa existente
```

## Formato do relatório

```
✅  KATA CYCLE — APROVADO: critério de sucesso satisfeito

  Problema: validação de data não preserva fuso horário
  Critério declarado: parse_date retorna datetime com timezone UTC (teste novo passa)
  Arquivos alterados: src/parser.py, tests/test_parser.py
  INTENT: code does parse_date retorna datetime naive; check expects datetime
    com timezone UTC; spec says README: preservar fuso

  Verificações:
    ✅ ruff check limpo
    ✅ pytest 142 passou
    ✅ coverage 87.0% ≥ gate
    ✅ critério de sucesso satisfeito

  Caveats:
    ⚠ Testes de integração não executados (sem docker)

  AUTH: user said "pode fazer o deploy para staging"
  PENDING: fazer rollout para produção - aguardando sua autorização
```

A linha "Critério declarado" é a chave `done` preenchida no THINK (Fable
Step 1): o leitor vê o que era "pronto" antes da evidência e pode confrontar
com o resultado.

## Linhas devidas (forced artifacts)

| Linha | Quando aparece | Fonte |
|-------|---------------|-------|
| `INTENT: code does X; check expects Y; spec says Z` | Comportamento foi alterado e intent gate foi preenchido | `data.intent` |
| `AUTH: user said "..."` | Ação irreversível (push/deploy) foi tomada | `data.auth.authorized` |
| `PENDING: action - awaiting your authorization` | Docs prescrevem follow-up não executado | `data.pending.documented` |
| `TWINS: searched pattern - found N other sites` | Defeito corrigido com busca de padrão recorrente | `data.twins.searched` |

## Caveats comuns

- Testes de integração não executados
- Arquivos temporários detectados (`.tmp`, `.bak`, `scratch/`)
- INTENT não documentada (comportamento alterado sem registro)
- AUTH ausente (ação externa sem autorização)
- Cobertura abaixo do gate
- Lint com alertas
- **Hand back (Fable Step 5)**: `verify.hand_back: true` → o relatório deve
  dizer que N tentativas de verificação falharam e a tarefa foi devolvida ao
  usuário com o que foi tentado, o output real e a hipótese atual — não um
  "rejeitado" genérico que convida a mais um ciclo fix-verify.

## Modo --report

Regenera o relatório de uma tarefa já concluída sem reexecutar o ciclo:

```bash
python -m kata --task minha-tarefa --report
```

Útil para compartilhar resultados em CI ou revisão.

## Modo --audit (fable-method audit)

Gradua as fases de uma tarefa como **followed** / **skipped** / **faked**
(afirmado sem observação), com o risco concreto de cada skip/fake:

```bash
python -m kata --task minha-tarefa --audit
```

Exit codes: `0` = audit limpo; `1` = há fakes/skips (ou tarefa não
encontrada); `2` = argumentos inválidos. Use quando quiser saber se uma
tarefa foi de fato seguida ou só preenchida.

## Princípios

- **Outcome first**: a primeira linha é o resultado, não o processo
- **Sem scaffolding**: o leitor não precisa saber o que é FIT/THINK/SURGICAL
- **Caveats honestos**: falhas são reportadas como falhas, sem suavizar
- **Linhas devidas**: INTENT/AUTH/PENDING/TWINS aparecem só quando relevantes
