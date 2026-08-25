---
name: kata-research
description: Domain adapter do kata para pesquisa. Use quando a tarefa declarar `domain: research`. Adapta o ciclo Karpathy para investigação bibliográfica, análise de fontes, experimentos, revisão de literatura e produção de conhecimento.
---

# Skill: kata-research

Domain adapter para o ciclo Kata no domínio **research**.

Este adapter especializa o ciclo FIT → THINK → SIMPLIFY → INTENT → SURGICAL
→ VERIFY → ARTIFACT → REPORT para tarefas de pesquisa: investigação de
técnicas/APIs, revisão de literatura, análise de fontes, estudos comparativos
e entrega de conhecimento verificável.

## Domínio

Cobre:

- Investigação de API/biblioteca/técnica desconhecida (documentação oficial, fonte)
- Revisão de literatura e síntese de fontes (papers, docs, posts técnicos)
- Análise comparativa (opções A vs B com critérios explícitos)
- Experimentos de avaliação (benchmarks, testes de hipótese)
- Backlog/relatórios de achados com evidência reproduzível

Não cobre:

- Implementação de código (se a pesquisa concluir com decisão, a implementação
  é uma task nova — ver "Entrega" abaixo)
- Análise de dados em produção (use `data-analysis`)
- Ações irreversíveis em infra (use `devops`)

## Evidência

Antes de agir, abra e inspecione ({{READ}} / {{SEARCH}}):

1. **Fontes primárias**: documentação oficial, código-fonte da lib, RFC, paper
   (citar a URL/sha; não usar memória como fonte)
2. **Código do repo** que a pesquisa referencia (callers, usos, exemplos)
3. **Estado atual** ({{RUN}}): `git log`, `git status`, arquivos tocados
4. **Buscas**: `grep`/`glob` no repo; busca web via ferramenta de fetch do host
   (quando disponível — registrar a URL consultada)

Regra: toda claim de pesquisa tem fonte citável (URL, arquivo:linha, sha).
Sem fonte, é inferência — declare como low-confidence.

## Autoridade

Ordem de autoridade para decisões no domínio research:

1. **Declaração explícita do usuário** (maior autoridade)
2. **Documentação oficial / fonte primária** (docs, RFC, paper — não resumos de terceiros)
3. **Código observado** (a implementação real é fonte de verdade para comportamento)
4. **Inferência do modelo** — sempre declarar como low-confidence

Se documentação e código discordam, diga os dois e pergunte ao usuário — não
apague a divergência.

## Verify by observation

Uma claim de pesquisa só vale se for observável:

- **Citação de API**: abrir a doc/linha da lib e citar o trecho ({{READ}})
- **Comportamento**: reproduzir com um teste/script mínimo ({{RUN}})
- **Achado de revisão**: apontar arquivo:linha ({{SEARCH}})
- **Veredito**: afirmar o que foi observado vs. inferido (caveat explícito)

Não declare "a pesquisa chegou a X" sem mostrar o passo que leva a X.

## Fraud table

Fraudes específicas de research:

| Tipo | Descrição | Severidade |
|------|-----------|------------|
| **fabricated_source** | Citar doc/fonte que não existe ou inventar API/assinatura | high |
| **hallucinated_behavior** | Afirmar que "X funciona assim" sem reproduzir/abrir fonte | high |
| **cherry_picking_sources** | Selecionar só fontes que favorecem a conclusão | medium |
| **stale_source** | Usar doc de versão antiga como verdade da atual | medium |
| **unverifiable_claim** | Conclusão sem evidência reproduzível no relatório | high |

## Minimum evidence set (binding)

1. Abrir fonte primária ({{READ}}; fetch web quando o host tiver) — obrigatório para API/comportamento
2. Reproduzir comportamento em teste/script mínimo ({{RUN}}) quando aplicável
3. Registrar no relatório: fontes citadas + o que foi observado vs. inferido
4. Ação irreversível (publicar achado, aplicar mudança de comportamento):
   AUTH com quote do usuário
5. Verificar o achado (re-ler a fonte, rodar o repro)

## Rotas FIT por shape

| Rota | Quando usar | O que fazer |
|------|-------------|-------------|
| **research** | Investigar técnica/API desconhecida | Pesquisar fontes primárias primeiro, depois ciclo |
| **question** | "Por que X funciona assim?" (diagnóstico) | Diagnosticar sem alterar código |
| **plan-first** | Decisão que muda comportamento/repo inteiro | Plano, parar, aguardar aprovação |
| **code-loop** | Achado vira mudança pequena e reversível | Ciclo completo normal |

As rotas possíveis no domínio research seguem o mesmo schema do ciclo base:
`code-loop | plan-first | question | research | inference`.

## Verify commands sugeridos

```yaml
verify:
  lint: ruff check src/ tests/
  test: pytest tests/ -q
  coverage: echo "n/a (pesquisa)"
```

## Red lines

- Nunca afirmar fato de API/doc sem abrir a fonte ({{READ}})
- Nunca apresentar inferência como observação
- Nunca aplicar mudança de comportamento sem aprovação (plan-first quando reversível
  e desconhecido)
- Nunca plagar — citar a fonte

## Registro no YAML

```yaml
domain: research
fit:
  route: research   # investigar e entregar; não altera código sem autorização
```

## Entrega

Se a pesquisa conclui com "mudar X", a mudança vira **rodada nova** com
`fit.route: code-loop` — a research entrega decisão/achado, não diff.
