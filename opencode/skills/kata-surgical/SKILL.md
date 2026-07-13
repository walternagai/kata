---
name: kata-surgical
description: Fase SURGICAL do ciclo Karpathy (kata). Use quando o agente @kata estiver na fase 3 — validar arquivo por arquivo que cada mudança rastreia direto ao pedido, sem efeitos colaterais. Triggers: SURGICAL, cada linha, arquivo, import, diff, rastrear, efeito colateral.
---

# Skill: kata-surgical

Fase 3 do Karpathy Development Cycle — **SURGICAL**.

## Objetivo

Validar que **cada arquivo alterado** rastreia direto ao pedido/PRD.
Nenhuma mudança deve ser "de passagem" ou "enquanto estou aqui".

> O código cirúrgico toca só o necessário — como um bisturi, não um machado.

## Procedimento

### 1. Listar arquivos alterados

Execute:
```bash
git diff --name-only
```

Se vazio (tudo staged):
```bash
git diff --cached --name-only
```

Você terá uma lista de arquivos. Exemplo:
```
mushin/api/app.py
mushin/api/dependencies.py
mushin/api/routers/run.py
tests/unit/test_orchestrator.py
```

### 2. Validar cada arquivo

Para **cada arquivo** da lista, pergunte:

> "`<arquivo>` — necessário para esta tarefa?"

Registre `true` ou `false` no YAML.

**Critérios de "necessário":**
- O arquivo contém mudança que resolve um FR/bug do escopo
- O arquivo é um teste da mudança feita
- O arquivo é um ajuste de configuração obrigatório (ex: pyproject.toml)

**Sinais de "desnecessário" (questionar):**
- Refactoring não pedido ("enquanto estou aqui, vou limpar isso")
- Reformatação de código fora do escopo (ruff format acidental)
- Remoção de comentários/imports não relacionados
- Adição de type hints em funções não tocadas

### 3. Verificar imports órfãos

Pergunte:
> "Imports removidos são só os que sua mudança tornou inúteis?"

**Detecção automática** (opcional):
```bash
# Encontra imports não utilizados com ruff
ruff check --select F401 mushin/ services/ tests/
```

Se houver imports F401 que **não** são resultado da sua mudança, são efeito
colateral desnecessário — questione.

### 4. Verificar efeitos colaterais

Para cada arquivo, mentalmente verifique:
- **Mudança de assinatura**: se uma função mudou assinatura, todos os callers foram atualizados?
- **Mudança de schema**: se um modelo mudou, as migrations estão incluídas no diff?
- **Mudança de comportamento**: se a lógica mudou, os testes foram atualizados?
- **Imports novos**: cada import novo é realmente necessário para a mudança?

## Output no YAML

```yaml
surgical:
  files:
    - path: mushin/api/app.py
      necessary: true
    - path: mushin/api/dependencies.py
      necessary: true
    - path: tests/unit/test_orchestrator.py
      necessary: true
    - path: mushin/dashboard/pages/Overview.py
      necessary: false  # refactoring não pedido
  removed_imports_clean: true
  notes: |
    Cada arquivo rastreia direto a um FR do PRD.
    Overview.py removido do diff — refactoring não pertence a esta tarefa.
```

## Princípios

- **Um diff, uma tarefa**: se a mudança não rastreia ao pedido, remova-a
- **Bisturi, não machado**: altera o mínimo de linhas possível
- **Efeito colateral zero**: se sua mudança toca arquivo que não deveria, divida em duas tarefas
- **Atomicidade**: o diff deve ser reviewable em uma sentada
- **Rastreabilidade**: cada arquivo deve poder ser justificado em uma frase: "este arquivo faz X porque Y do PRD"
