---
name: kata-fit
description: Fase FIT do ciclo Karpathy (kata). Use quando o agente @kata estiver na fase 0 — classificar a tarefa, aplicar triviality gate e definir a rota antes do THINK. Triggers: FIT, triviality gate, fit gate, classificar tarefa, rotear, plan-first, question, research, inference.
---

# Skill: kata-fit

Fase 0 do Karpathy Development Cycle — **FIT**.

Inspirado no **fit gate** do [The Fable Method](https://github.com/Sahir619/fable-method)
(think → act → prove → grow) e no **Karpathy Development Cycle**.

## Objetivo

Antes de iniciar o ciclo THINK → SIMPLIFY → SURGICAL → VERIFY, classificar
a tarefa para evitar desperdício de rigor em tarefas triviais ou mal-classificadas:

1. **Triviality gate**: a tarefa é trivial? (1 arquivo, <10 linhas, sem busca)
2. **Fit gate**: onde vive a resposta? — code-loop, plan-first, question, research, inference

## Ferramentas

Para esta fase, use:

- **shell do sistema** (a ferramenta `bash` do OpenCode, quando disponível):
  `git diff --stat` e `git diff --name-only` para medir volume do diff.
- **`question`**: classifique a tarefa com o usuário, uma pergunta por vez.
- **`grep`**: investigue se a tarefa exige pesquisa no código.
- **`write` / `edit`**: registre a classificação em `.kata/<task>.yaml`.

## Procedimento

### 1. Triviality gate

Execute:
```bash
git diff --stat          # unstaged
git diff --name-only
```

Se ambos vazios:
```bash
git diff --cached --stat # staged
git diff --cached --name-only
```

**Critério de trivialidade** (todos precisam ser verdade):
- Apenas **1 arquivo** alterado
- Menos de **10 linhas** totais de alteração
- **Nenhum novo comportamento** (só correção de typo, rename local, ajuste de comentário)
- Você já sabe exatamente o que mudar **sem precisar pesquisar**

Se trivial:
> Faça a mudança, confirme com a verificação óbvia
> (re-leia o span alterado, ou rode o comando/lint que a mudança afeta),
> e reporte em **uma ou duas frases**.
> Pule THINK/SIMPLIFY/SURGICAL — vá direto ao VERIFY.

### 2. Fit gate — Classificar a rota

Pergunte ao usuário (ou classifique baseado no contexto):

| Rota | Quando usar | O que fazer |
|------|-------------|-------------|
| **code-loop** | Tarefa de código padrão com fontes acessíveis | Ciclo completo: THINK → SIMPLIFY → SURGICAL → VERIFY |
| **plan-first** | Escopo ambíguo, ação irreversível, ou usuário pediu plano | Rode THINK, entregue um plano, PARE e aguarde aprovação |
| **question** | "Por que X está lento?", "O que você acha de Y?" | Diagnostique, não mude nada. Entregue achados + recomendação |
| **research** | Técnica/API que você não conhece | Pesquise primeiro (documentação, código fonte), depois rode code-loop |
| **inference** | Resposta vive só na sua inferência | Admita baixa confiança. Não finja rigor. Pergunte ao usuário ou marque como low-confidence |

**Critérios de "plan-first":**
- Escopo ambíguo: você pode imaginar dois entregáveis diferentes que o usuário pode querer
- Ação irreversível: push, publish, send, deploy, delete dados compartilhados
- Usuário explicitamente pediu um plano

### 3. Registrar no YAML

Se `base_commit` ainda não estiver gravado na tarefa, registre o HEAD atual
do git (`git rev-parse HEAD`) nessa chave. É o ponto de comparação que o
JUDGE usa depois — sem ele, o JUDGE só enxerga diff não commitado.

```yaml
status: draft
base_commit: "a1b2c3d..."
fit:
  trivial: false
  route: code-loop     # code-loop | plan-first | question | research | inference
  reason: "Feature request com escopo bem definido"
  answered: false
  skipped: false       # true só se a fase foi preenchida com default sem
                       # ninguém responder (modo não-interativo)
```

## Complementaridade com fable-method

O FIT gate do kata é equivalente à combinação de **triviality gate** + **fit gate**
do fable-method (Steps 0-3). A diferença principal:

- **fable-method**: o fit gate é implícito no fluxo do agente, sem CLI
- **kata**: o fit gate é explícito tanto no CLI (`--plan`, `--check-only`)
  quanto no agente OpenCode

Para tarefas que o kata não cobre (marketing, research, data analysis, devops),
consulte os domain adapters do [The Fable Method](https://github.com/Sahir619/fable-method).

## Princípios

- **Proporcionalidade**: tarefas triviais não merecem o ciclo completo
- **Honestidade**: se a resposta é só inferência, diga — não finja rigor
- **Roteamento explícito**: toda tarefa tem uma rota; rota default é code-loop
- **Não-binário**: question não vira code-loop, research não vira inference
