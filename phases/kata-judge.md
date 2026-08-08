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
   disponível. O CLI confere se ele resolve, é ancestral do HEAD e coincide
   com a âncora independente em `refs/kata/base/<hash>`; divergência é
   `baseline_tampering`. Sem âncora, o resultado não pode ser VERIFIED. Sem
   baseline, usa diff local contra HEAD e declara os pontos cegos observáveis.
3. **Re-run every claimed verification** — executar de novo e comparar
4. **Hunt frauds** — 7 categorias
5. **Confess blind spots** — registrar o que não teve como observar
6. **Deliver verdict** — VERIFIED / VERIFIED WITH CAVEATS / UNVERIFIABLE / REFUTED

## Execução

Via {{RUN}}:

```bash
python -m kata --task <name> --judge
```

Ou para tarefa detectada por branch:

```bash
python -m kata --judge
```

## As 7 Fraudes

| # | Fraude | Descrição | Severidade |
|---|--------|-----------|------------|
| 1 | **Weakened checks** | Asserts removidos ou relaxados em arquivos de teste, linhas comentadas, `pass` substituindo corpo de teste, `noqa` adicionado | 🔴 alta |
| 2 | **False completion** | Relatório afirma que verificação passou, mas re-execução mostra falha | 🔴 alta |
| 3 | **Scope creep** | Arquivos alterados que não foram declarados como necessários na fase SURGICAL | 🟡 média/alta |
| 4 | **Unauthorized action** | Ação externa (push, deploy) realizada sem AUTH line documentada | 🔴 alta |
| 5 | **Spec betrayal** | Código alterado para satisfazer teste que contradiz a especificação | 🔴 alta |
| 6 | **Debris** | Arquivos temporários (`.tmp`, `.bak`), debug prints, TODOs, lixo | 🟢 baixa |
| 7 | **Baseline tampering** | `base_commit` do YAML diverge da âncora `refs/kata/base/<hash>` registrada no início, ou não é ancestral do HEAD — mover o baseline encolhe o diff que o juiz examina | 🔴 alta |

A escrituração do próprio kata (`.kata/*.yaml`, `.kata/config.yaml`) não conta
como arquivo alterado: ela é criada pela ferramenta, não pelo autor da tarefa,
e contá-la acusava trabalho honesto de scope creep (R11-3).

## Vereditos

| Veredito | Condição |
|----------|----------|
| **VERIFIED** | Nenhuma fraude encontrada, e o juiz teve como procurar |
| **VERIFIED WITH CAVEATS** | Fraudes de média/baixa severidade, nenhuma alta |
| **UNVERIFIABLE** | Nenhuma fraude, mas o juiz não teve como observar |
| **REFUTED** | Pelo menos uma fraude de alta severidade |

### Pontos cegos

Um ponto cego é o juiz confessando o que não conseguiu observar. Não é
acusação: não ter observado não é evidência de fraude nem de honestidade.
Seis disparam hoje:

1. **Nenhuma verificação re-executada** — o relatório não afirma nenhum
   check (`ruff_clean`, `tests_pass`, `coverage_pass`) que o juiz saiba
   reproduzir, então nada é re-executado. Declarar os comandos do projeto em
   `.kata/config.yaml` é o que desarma este ponto cego.
2. **Teste em linguagem sem sondas** — o juiz conhece a sintaxe de Python,
   JS/TS, Go, Ruby, Rust e Java/Kotlin. Um teste fora dessa lista (`.php`,
   `.swift`, `.exs`…) não pode ser lido, e o juiz diz isso em vez de calar.
3. **Código/teste ignorado pelo Git** — candidatos relevantes sob `.gitignore`
   não entram no diff e são listados como ponto cego.
4. **Seção da tarefa ilegível** — `verify`, `surgical`, `intent` ou `artifact`
   que não sejam mapas (YAML escrito à mão), ou uma lista no topo do arquivo.
   O que não pôde ser lido é confessado e o veredito sai; antes, o judge
   morria com traceback e o código de saída ficava igual ao de REFUTED (R11-1).
5. **Baseline sem âncora independente** — o YAML declara `base_commit` mas não
   há `refs/kata/base/<hash>` para confrontá-lo. A âncora é local ao clone: um
   clone novo de tarefa antiga cai aqui, e isso é ponto cego, não fraude.
6. **Baseline não resolve mais** — o commit declarado sumiu do histórico
   (rebase, poda), então não há de onde diffar.

Não havendo fraude nenhuma, qualquer ponto cego faz o veredito ser
**UNVERIFIABLE** em vez de VERIFIED: "não consegui olhar" não pode ser
reportado como "está tudo certo". Havendo fraude, ela manda no veredito e
os pontos cegos continuam listados.

O exit code de UNVERIFIABLE é `0` — o juiz não encontrou nada errado,
apenas não teve como olhar. Quem quiser barrar no CI lê o veredito.

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

  Pontos cegos (o juiz não conseguiu observar):
    ❓ 1 arquivo(s) de teste sem padrão de enfraquecimento para a linguagem: src/soma.test.js

  Re-execução:
    ✅ ruff
    ❌ pytest

──────────────────────────────────────────────────────────

❌  KATA JUDGE — REFUTED
```

## Registro no YAML

O CLI Python não persiste o resultado do judge de volta no arquivo de
tarefa — `--judge` é uma verificação stateless, re-executada a cada chamada.
Se {{AGENTE_CAP_MIN}} decidir registrar o veredito em `.kata/<task>.yaml` (via
{{WRITE}}/{{EDIT}}), use a chave `judge`:

```yaml
judge:
  verdict: "REFUTED"           # VERIFIED | VERIFIED WITH CAVEATS |
                               # UNVERIFIABLE | REFUTED
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
- **Não observar não é aprovar**: sem nada observado, o veredito é
  UNVERIFIABLE, nunca VERIFIED
