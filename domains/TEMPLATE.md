---
name: kata-<domínio>
description: Domain adapter do kata para <domínio>. Use quando a tarefa declarar `domain: <domínio>` e for necessário adaptar o ciclo Karpathy às evidências, autoridades e verificações deste domínio.
---

# Skill: kata-<domínio>

Domain adapter para o ciclo Kata no domínio **<domínio>**.

Este arquivo segue o template `domains/TEMPLATE.md`. Cada adapter define,
para o seu domínio: o que conta como evidência, quem é a autoridade, como
verificar por observação, quais fraudes o JUDGE deve caçar e o *minimum
evidence set* vinculante.

## Domínio

Descreva aqui o escopo do adapter: que tipo de tarefa ele cobre e que tipo
não cobre. Exemplo:

> Devops/infra: Docker, Docker Compose, Terraform, Nginx, GitHub Actions,
> deploys, healthchecks e configuração de ambientes.
>
> Não cobre: desenvolvimento de aplicações, banco de dados de produção com
dados reais, ações em contas de nuvem sem autorização explícita.

## Evidência

Liste o que deve ser aberto/verificado **antes de agir**. Use {{READ}} e
{{SEARCH}} para inspecionar:

- arquivos de configuração do domínio (ex.: `docker-compose.yml`)
- documentação de deploy/operacional (`README.md`, `DEPLOY.md`)
- arquivos de CI/CD (`.github/workflows/`, `.gitlab-ci.yml`)
- estado atual do ambiente (via {{RUN}}: `docker compose ps`, `terraform show`)

A regra é: nunca alterar configuração de infra sem abrir primeiro os
arquivos que a definem.

## Autoridade

Quem/qual arquivo decide o comportamento correto? Ordene de mais a menos
autoritário:

1. declaração explícita do usuário
2. documentação de deploy/operacional (`README.md`, `DEPLOY.md`)
3. arquivos de configuração versionados (`docker-compose.yml`, `*.tf`)
4. estado observado no ambiente
5. inferência do modelo (baixa confiança — sempre declarada)

## Verify by observation

Como confirmar que a ação funcionou. Deve ser observável, não uma claim no
relatório:

- `docker compose config` valida a sintaxe do compose
- `docker compose ps` mostra containers em execução
- `curl -fsS http://localhost/health` confirma que a aplicação responde
- `git diff` mostra exatamente o que foi alterado

## Fraud table

Fraudes específicas deste domínio que o JUDGE (e o agente ao se auto-revisar)
deve caçar:

| Tipo | Descrição | Severidade |
|------|-----------|------------|
| unverified_deploy | "Deploy funcionou" sem comando de verificação rodado | high |
| weakened_healthcheck | Healthcheck removido, relaxado ou sem endpoint | high |
| secret_in_diff | Secret/credencial aparece no diff | high |
| unpinned_image | Imagem Docker com tag `latest` ou sem hash pin | medium |
| missing_volume_port | Volume/porta essencial omitido da configuração | medium |
| silent_config | `docker compose config` ou equivalente silenciado/ignorado | medium |
| unauthorized_action | Deploy/push/destroy sem AUTH line documentada | high |

## Minimum evidence set (binding)

Checklist obrigatório. Antes de qualquer ação no domínio **<domínio>**:

1. Abrir os arquivos de configuração relevantes ({{READ}})
2. Abrir a documentação de deploy/operacional, se existir
3. Rodar o comando de validação/sintaxe do domínio ({{RUN}})
4. Se a ação for irreversível (deploy, push, destroy), obter AUTH com quote
   do usuário via {{ASK}} e registrar em `auth.action` + `auth.quote`
5. Verificar o estado real depois da ação ({{RUN}})

## Rotas FIT por shape

Como o FIT gate classifica tarefas deste domínio:

| Rota | Quando usar | O que fazer |
|------|-------------|-------------|
| **plan-first** | deploy, rollout, destroy, push de imagem, alteração de DNS/certificate | Planejar, parar e aguardar aprovação. Sempre. |
| **question** | "por que o container caiu?", "por que o deploy falhou?" | Diagnosticar, não alterar código sem autorização. |
| **research** | API/ferramenta de infra não conhecida | Pesquisar documentação oficial antes de tocar. |
| **code-loop** | mudança de configuração reversível (compose, nginx, workflow) | Ciclo completo com verify por observação. |
| **inference** | só dá para inferir | Declarar baixa confiança; perguntar ao usuário. |

## Verify commands sugeridos

Comandos típicos para o VERIFY neste domínio. O projeto pode declarar os
seus próprios em `.kata/config.yaml`:

```yaml
verify:
  lint: docker compose config
  test: ./scripts/smoke-test.sh
  coverage: echo "N/A"
```

Quando o projeto não declarar, o agente deve propor os defaults acima e
registrar o bloqueio como caveat — nunca inventar verificação que não rodou.

## Red lines

Ações que o adapter **nunca** permite sem intervenção humana documentada:

- Executar deploy/push/destroy/publish sem `auth.action_taken: true` e `auth.quote`
- Alterar infra de produção diretamente (sem testar em staging/primeiro)
- Colocar secrets/credenciais no diff ou no YAML da tarefa
- Usar tag `latest` em imagem de produção sem justificativa documentada

## Registro no YAML

Durante o FIT, registre o domínio no `.kata/<task>.yaml`:

```yaml
domain: <domínio>
status: draft
base_commit: "..."
fit:
  trivial: false
  route: code-loop   # ajustar conforme este adapter
  reason: "..."
```

Se o domínio não for `coding`, carregue este adapter com {{LOAD_DOMAIN}} e
siga as regras acima.
