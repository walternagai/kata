---
name: kata-docs
description: Domain adapter do kata para documentação. Use quando a tarefa declarar `domain: docs`. Adapta o ciclo Karpathy para README, guides, changelogs, docstrings, especificações e documentos técnicos.
---
<!-- Gerado por scripts/build_skills.py a partir de domains/kata-docs.md. Não edite aqui. -->

# Skill: kata-docs

Domain adapter para o ciclo Kata no domínio **docs**.

Este adapter especializa o ciclo FIT → THINK → SIMPLIFY → INTENT → SURGICAL
→ VERIFY → ARTIFACT → REPORT para tarefas de documentação: README, guides,
changelogs, docstrings, especificações e documentos técnicos.

## Domínio

Cobre:

- README, guides, tutoriais e exemplos de uso
- Docstrings e comentários de código (quando a task é de docs)
- Changelog/notas de release
- Especificações (PRD, spec de feature, ADR, architecture docs)
- Referência de CLI/API (como as seções de DOCUMENTATION.md deste repo)

Não cobre:

- Código (use `coding`); alteração de código que acompanha doc é task de coding
- Conteúdo analítico (use `research`) — docs é forma, research é conteúdo

## Evidência

Antes de agir, abra e inspecione (`Read` / `Grep`):

1. **Documentos existentes**: o(s) arquivo(s) a alterar e seus vizinhos
2. **Fonte da verdade técnica**: código/CLI/docs gerados que o documento descreve
   (ex.: doc de flag → abrir o argparse/entry point; doc de API → abrir a função)
3. **Convenções do repo**: README/AGENTS/CLAUDE que definem estilo e estrutura
4. **Estado** (`Bash`): `git log` do arquivo (o que mudou), `git status`

Regra: todo comando/flag/assinatura citado em doc tem fonte no código; toda
contagem citada (fases, fraudes, cenários) é derivada da implementação, não de
memória — a classe de drift que o R12-01..04 fechou.

## Autoridade

1. **Declaração explícita do usuário**
2. **Fonte técnica real** (código, CLI, doc gerada — a doc descreve o que existe)
3. **Convenções do repo** (AGENTS.md/CLAUDE.md/README padrão)
4. **Inferência do modelo** — low-confidence

Se a doc antiga discorda do código atual, a doc está desatualizada — corrigir a
doc (não o código) e registrar o drift.

## Verify by observation

- **Comando citado**: rodar o comando e conferir que a saída bate (`Bash`)
- **Flag/assinatura**: grep na fonte (`Grep`)
- **Contagem**: derivar da implementação (teste que conta; ver test_docs_eval.py)
- **Build de docs**: `make build-skills` / `make check-skills` quando a doc é fonte de skills
- **Formatação**: `ruff format --check` para docstring; lint de markdown quando houver

Não declare "doc atualizada" sem conferir que o comando/flag citado existe.

## Fraud table

| Tipo | Descrição | Severidade |
|------|-----------|------------|
| **drift_numerico** | Contagem/estado desatualizado em doc (fases, cenários, versões) | medium |
| **fabricated_command** | Comando/flag/assinatura que não existe na implementação | high |
| **stale_procedure** | Passo que descreve comportamento que o código mudou | medium |
| **orphan_section** | Seção de doc que ninguém linka/nenhuma fonte sustenta | low |

## Minimum evidence set (binding)

1. Abrir o documento-alvo e os vizinhos (`Read`)
2. Conferir cada comando/flag/número citado na fonte (`Grep`/`Bash`)
3. Se a doc é fonte de skills geradas, rodar `make check-skills` (build verde)
4. Registrar o que foi verificado vs. inferido no relatório

## Rotas FIT por shape

| Rota | Quando usar | O que fazer |
|------|-------------|-------------|
| **code-loop** | Atualizar/criar doc com fonte acessível | Ciclo completo |
| **research** | Descobrir o comportamento para documentar | Investigar primeiro, depois escrever |
| **question** | "Como X funciona?" (doc de diagnóstico) | Explicar sem editar doc |

As rotas possíveis no domínio docs seguem o mesmo schema do ciclo base:
`code-loop | plan-first | question | research | inference`.

## Verify commands sugeridos

```yaml
verify:
  lint: ruff check src/ tests/   # docstrings de código
  test: pytest tests/ -q
  coverage: echo "n/a (docs)"
```

## Red lines

- Não citar comando/flag sem abrir a fonte (`Read`/`Grep`)
- Não deixar drift de contagem/estado (derivar da implementação)
- Não editar doc de código gerado (opencode/ claude-code/ SKILL.md) à mão —
  editar a fonte em phases/ e rodar `make build-skills`
- Não reescrever a voz/estilo do projeto (conferir AGENTS.md/CLAUDE.md antes)

## Registro no YAML

```yaml
domain: docs
fit:
  route: code-loop   # ajustar conforme o caso
```

## Docstring final

Para tasks de docs, o relatório deve listar: arquivos tocados, fonte de cada
comando/flag citado (arquivo:linha ou sha), e o que não pôde ser verificado.
