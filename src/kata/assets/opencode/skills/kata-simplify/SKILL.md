---
name: kata-simplify
description: Fase SIMPLIFY do ciclo Karpathy (kata). Use quando o agente @kata estiver na fase 2 — verificar se o código é mínimo, sem abstrações especulativas ou configurabilidade não solicitada. Triggers: SIMPLIFY, código mínimo, abstração, diff, overengineering, YAGNI.
---
<!-- Gerado por scripts/build_skills.py a partir de phases/kata-simplify.md. Não edite aqui. -->

# Skill: kata-simplify

Fase 2 do Karpathy Development Cycle — **SIMPLIFY**.

## Objetivo

Verificar se o código escrito é o **mínimo necessário** para resolver o problema
declarado na fase THINK. Detectar:
- Abstrações criadas para uso único (YAGNI)
- Configurabilidade/flexibilidade não solicitada
- Complexidade desnecessária

## Ferramentas

Para esta fase, use:

- **`bash`**: `git diff --stat` (ou `git diff --cached --stat` se vazio) para medir volume.
- **`question`** (via `kata-question`): checklist de minimalismo — pergunte ao usuário, não valide sozinho.
- **`read`**: inspecione partes do diff que parecerem suspeitas.
- **`write` / `edit`**: registre as respostas em `.kata/<task>.yaml`.

## Procedimento

### 1. Visualizar o diff

Execute (via `bash`):
```bash
git diff --stat
```

Se vazio (tudo staged):
```bash
git diff --cached --stat
```

Mostre o output ao usuário para ter noção do volume de mudanças.

### 2. Checklist de Minimalismo

Para cada item, use `question` e pergunte ao usuário:

| Pergunta | Resposta desejada | Ação se for "Sim" |
|----------|-------------------|-------------------|
| O código mínimo resolve o problema? | Sim | Sugira remoções concretas |
| Alguma abstração é para uso único? | Não | Converta em função/classe concreta |
| Existe configurabilidade/flexibilidade não solicitada? | Não | Remova parâmetros opcionais |

Se a resposta for "Sim" na coluna indesejada, **pare e proponha uma simplificação
concreta** antes de prosseguir. Não registre "Sim" sem ação.

### 3. Anti-patterns para detectar

Analise o diff procurando por:

#### Abstrações de uso único (YAGNI)
```python
# ❌ Bad: factory para criar 1 objeto
class ResponseFactory:
    def create(self, type: str) -> Response: ...

# ✅ Good: função simples
def make_response(data: dict) -> Response: ...
```

#### Configurabilidade não solicitada
```python
# ❌ Bad: 3 parâmetros opcionais que ninguém pediu
def process(data, batch_size=100, timeout=30, retries=3): ...

# ✅ Good: só o que foi pedido
def process(data): ...
```

#### Premature abstraction
```python
# ❌ Bad: interface base para 1 implementação
class BaseStorage(ABC):
    @abstractmethod
    def save(self, key, value): ...

class SQLiteStorage(BaseStorage):
    def save(self, key, value): ...

# ✅ Good: classe concreta
class SQLiteStorage:
    def save(self, key, value): ...
```

#### Speculative generality
```python
# ❌ Bad: genérico para "futuros tipos"
def handle(data: dict[str, Any]) -> Any: ...

# ✅ Good: específico
def handle(data: UserInput) -> Result: ...
```

### 4. Observações

Peça ao usuário, em texto livre (opcional):
> "Observações sobre simplificação (opcional):"

Registre no YAML.

## Output no YAML

```yaml
simplify:
  minimum_code: true
  no_single_use_abstractions: true
  no_speculative_config: true
  answered: true        # false se a fase foi preenchida com default sem
                        # ninguém responder (modo não-interativo)
  skipped: false        # true só nesse caso — ver orquestrador
  notes: |
    Plano revisado — 3 FRs, sem abstrações especulativas.
    Não criar sistema de permissions — user_id já vem do UserStore.
```

## Princípios

- **Menos é mais**: se funciona sem a abstração, remova-a
- **YAGNI**: "You Aren't Gonna Need It" — não construa para o futuro hipotético
- **KISS**: Keep It Simple, Stupid — a solução mais simples que resolve o problema
- **3 regras**: se uma abstração tem 1 implementação, é provável que seja prematura
- **Configurabilidade é custo**: cada parâmetro é um caminho de teste que você não vai cobrir
