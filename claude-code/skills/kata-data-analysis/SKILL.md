---
name: kata-data-analysis
description: Domain adapter do kata para análise de dados. Use quando a tarefa declarar `domain: data-analysis`. Adapta o ciclo Karpathy para pandas, notebooks, SQL, dashboards, pipelines de dados e relatórios analíticos.
---
<!-- Gerado por scripts/build_skills.py a partir de domains/kata-data-analysis.md. Não edite aqui. -->

# Skill: kata-data-analysis

Domain adapter para o ciclo Kata no domínio **data-analysis**.

Este adapter especializa o ciclo FIT → THINK → SIMPLIFY → INTENT → SURGICAL
→ VERIFY → ARTIFACT → REPORT para tarefas que tocam análise de dados:
manipulação de datasets, notebooks, SQL, dashboards, pipelines de dados e
relatórios analíticos.

## Domínio

Cobre:

- Transformação e limpeza de dados (pandas, Polars, dplyr, SQL)
- Análise exploratória (EDA) e estatística descritiva
- Notebooks (Jupyter, `.ipynb`) e scripts de análise
- Consultas SQL e modelagem de dados para análise
- Dashboards, gráficos e visualização de dados
- Pipelines de dados (ETL/ELT) e agregações

Não cobre:

- Desenvolvimento de aplicações genéricas (use o ciclo `coding` padrão)
- Modelagem/treino de ML em produção (exige revisão especializada de ML)
- Acesso a dados pessoais/sensíveis sem autorização explícita e red line
- Ciência de resultados (p-hacking, seleção conveniente de amostra)

## Evidência

Antes de agir, abra e inspecione (`Read` / `Grep`):

1. **Dados e código de análise**:
   - `*.ipynb`, `*.py` (scripts de análise), `*.sql`
   - `requirements.txt`/`pyproject.toml` (dependências de dados)
   - arquivos de dados (CSV/Parquet/JSON) e seu schema

2. **Documentação analítica**:
   - `README.md`, seção de análise/metodologia
   - Comentários de células/notebooks e docstrings das funções de análise
   - Descrição de origem dos dados (provenance) e dicionário de dados

3. **Estado dos dados** (`Bash`):
   - `pandas`/`polars` — `df.shape`, `df.dtypes`, `df.isna().sum()`
   - SQL — `EXPLAIN`/`SELECT count(*)` para confirmar schema e volumes
   - `git status`, `git diff` (o que muda nos scripts de análise)

Regra: nunca altere uma análise sem abrir primeiro os dados e o código que os
produz, e sem saber o schema/volumetria atual.

## Autoridade

Ordem de autoridade para decisões no domínio data-analysis:

1. **Declaração explícita do usuário** (maior autoridade)
2. **Documentação de dados** (dicionário de dados, README, metadados)
3. **Código de análise versionado** (scripts, notebooks, SQL)
4. **Dados observados** (schema real, distribuições, amostra)
5. **Inferência do modelo** — sempre declarar como low-confidence e perguntar ao usuário

Se houver conflito entre o dicionário de dados e o schema real, resolva
perguntando ao usuário — nunca assuma que o código está certo quando os
dados dizem outra coisa.

## Verify by observation

Uma claim de data-analysis só vale se for observável. Após cada mudança, rode
pelo menos uma verificação real:

| Ação | Verificação mínima |
|------|--------------------|
| Alterar script/notebook | Rodar o script (`python`/`jupyter nbconvert --execute`) com exit 0 |
| Alterar SQL | Rodar `EXPLAIN`/`SELECT` em amostra e conferir schema do resultado |
| Limpeza/transformação | Validar shape/nulos esperados (`assert` ou soma de `isna`) |
| Novo dashboard/visual | Renderizar e conferir eixos/legendas (não só gerar HTML) |
| Pipeline de dados | Rodar o pipeline ponta a ponta com amostra e comparar saída |

Não declare "análise funcionou" sem observar o resultado. "Processei os dados"
sem mostrar o shape/valores é claim não verificada — trate como caveat.

## Fraud table

Fraudes específicas de data-analysis que o JUDGE e o agente devem caçar:

| Tipo | Descrição | Severidade |
|------|-----------|------------|
| **unverified_analysis** | "Análise pronta" sem a execução do script/notebook rodado | high |
| **cherry_picking** | Seleção conveniente de amostra/resultado que favorece a conclusão | high |
| **data_leak** | Dado sensível/pessoal no diff ou no YAML da tarefa | high |
| **unpinned_dependency** | Dependência de dados sem versão/pin (reprodutibilidade) | medium |
| **silent_drop** | Linhas/colunas removidas sem registro do critério de remoção | medium |
| **fabricated_number** | Número/estatística no relatório sem fonte nos dados ou no código | high |
| **unauthorized_access** | Acesso/consulta a dados restritos sem autorização | high |

## Minimum evidence set (binding)

Antes de qualquer ação no domínio **data-analysis**:

1. Abrir o código de análise e os dados relevantes (`Read`)
2. Abrir o dicionário de dados/metadados, se existir
3. Rodar a verificação de schema/amostra do domínio (`Bash`):
   - `head` do dataframe / `SELECT ... LIMIT 10`
   - conferir types e nulos
4. Se a ação envolver dados sensíveis/restritos, obter AUTH com citação exata
   do usuário via `AskUserQuestion` e registrar em `auth.action_taken: true`,
   `auth.authorized: true`, `auth.action` e `auth.quote`
5. Verificar o resultado real depois da ação (`Bash`)

Se qualquer item for impossível, pare e explique o bloqueio.

## Rotas FIT por shape

| Rota | Quando usar | O que fazer |
|------|-------------|-------------|
| **plan-first** | Análise exploratória de grande escala, acesso a dados sensíveis, publicação de relatório | Planeje, documente riscos, pare e aguarde aprovação. |
| **question** | "Por que essa métrica subiu?", "O que está errado no resultado?" | Diagnosticar. Não altere script sem autorização. |
| **research** | API/biblioteca de dados desconhecida (ex.: nova função pandas, ferramenta de viz) | Pesquisar documentação oficial antes de tocar. |
| **code-loop** | Mudança reversível em script/notebook de análise com dados conhecidos | Ciclo completo com verify por observação. |
| **inference** | Só dá para inferir (dados insuficientes, amostra viesada) | Declarar baixa confiança; perguntar ao usuário. |

As rotas possíveis no domínio data-analysis seguem o mesmo schema do ciclo
base: `code-loop | plan-first | question | research | inference`.

## Verify commands sugeridos

O projeto pode declarar seus próprios comandos em `.kata/config.yaml`:

```yaml
verify:
  lint: ruff check notebooks/ scripts/
  test: pytest tests/ -q
  coverage: echo "coverage not applicable"
```

Se o projeto não declarar, o agente deve propor os defaults do domínio e
registrar o bloqueio como caveat — nunca inventar verificação que não rodou.

Defaults comuns:

- **validação de dados**: `python -c "import pandas; df=pd.read_csv('data/x.csv'); print(df.shape, df.dtypes)"`
- **execução de notebook**: `jupyter nbconvert --execute --to notebook --inplace notebook.ipynb`
- **validação SQL**: `psql -c 'EXPLAIN <query>;'`
- **pipeline ponta a ponta**: `python pipeline.py --sample`

## Red lines

Ações que este adapter **nunca** permite sem intervenção humana documentada:

- Publicar/anexar dados sensíveis ou pessoais sem `auth.action_taken` e `auth.quote`
- Rodar análise sobre dados de produção de escrita sem validação em cópia
- Declarar "análise validada" sem a execução rodada de verdade
- Oculta linhas/colunas (silent drop) sem registrar o critério
- Usar resultado de amostra como universal sem declarar a limitação

## Registro no YAML

Durante o FIT, registre o domínio no `.kata/<task>.yaml`:

```yaml
domain: data-analysis
status: draft
base_commit: "..."
fit:
  trivial: false
  route: code-loop     # ajustar: plan-first para dados sensíveis/publicação
  reason: "..."
```

Se o domínio não for `coding`, carregue este adapter com `Skill` e
siga as regras acima.

## AUTH/PENDING

- **AUTH**: acesso a dados sensíveis ou publicação de análise exige autorização
  com citação (mesma estrutura do kata-devops).
- **PENDING**: se a análise deixar follow-up obrigatório (ex.: "revisar com o
  time de dados antes de publicar"), documente `pending.action` e
  `pending.documented: true`.
