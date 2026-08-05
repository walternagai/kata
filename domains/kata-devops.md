---
name: kata-devops
description: Domain adapter do kata para devops/infraestrutura. Use quando a tarefa declarar `domain: devops`. Adapta o ciclo Karpathy para Docker, Docker Compose, Terraform, Nginx, GitHub Actions, deploys, healthchecks e configuração de ambientes.
---

# Skill: kata-devops

Domain adapter para o ciclo Kata no domínio **devops/infraestrutura**.

Este adapter especializa o ciclo FIT → THINK → SIMPLIFY → INTENT → SURGICAL
→ VERIFY → ARTIFACT → REPORT para tarefas que tocam infraestrutura: containers,
orquestração local, pipelines de CI/CD, configuração de servidor web/proxy e
automação de deploy.

## Domínio

Cobre:

- Docker e Docker Compose (imagens, containers, redes, volumes)
- Terraform / OpenTofu (infraestrutura como código)
- Nginx e configurações de proxy/reverse-proxy
- GitHub Actions / GitLab CI (workflows de CI/CD)
- Scripts e documentação de deploy (`deploy.sh`, `DEPLOY.md`, README)
- Healthchecks, observability e configuração de ambiente

Não cobre:

- Desenvolvimento de aplicações (use o ciclo `coding` padrão)
- Acesso direto a bancos de dados de produção com dados reais
- Ações em contas de nuvem/console que exijam privilégios humanos
- Domínios médicos, financeiros ou jurídicos (exigem revisão qualificada)

## Evidência

Antes de agir, abra e inspecione ({{READ}} / {{SEARCH}}):

1. **Arquivos de configuração**:
   - `docker-compose.yml`, `docker-compose.*.yml`
   - `Dockerfile`, `.dockerignore`
   - `terraform/` (`*.tf`, `*.tfvars`)
   - `nginx.conf`, `sites-enabled/`, `conf.d/`
   - `.github/workflows/*.yml`, `.gitlab-ci.yml`

2. **Documentação operacional**:
   - Seção de deploy do `README.md`
   - `DEPLOY.md`, `OPS.md`, `runbooks/`
   - Comentários nos arquivos de configuração

3. **Estado atual do ambiente** ({{RUN}}):
   - `docker compose ps`
   - `docker compose config`
   - `git status`, `git diff`
   - `terraform plan` (se Terraform)
   - `nginx -t` (se Nginx)

Regra: nunca altere configuração de infra sem primeiro abrir os arquivos que a
definem e sem saber o estado atual.

## Autoridade

Ordem de autoridade para decisões no domínio devops:

1. **Declaração explícita do usuário** (maior autoridade)
2. **Documentação de deploy/operacional** (`README.md`, `DEPLOY.md`, runbooks)
3. **Arquivos de configuração versionados** (`docker-compose.yml`, `*.tf`, workflows)
4. **Estado observado no ambiente** (`docker compose ps`, `terraform show`)
5. **Inferência do modelo** — sempre declarar como low-confidence e perguntar ao usuário

Se houver conflito entre documentação e configuração, resolva perguntando ao
usuário. Não assuma que "o código está certo" quando a documentação diz outra
coisa.

## Verify by observation

Uma claim de devops só vale se for observável. Após cada ação irreversível ou
de configuração, rode pelo menos uma verificação real:

| Ação | Verificação mínima |
|------|--------------------|
| Alterar `docker-compose.yml` | `docker compose config` (sintaxe) + `docker compose ps` (estado) |
| Alterar `Dockerfile` | `docker build -t teste .` (build local) |
| Alterar Nginx | `nginx -t` (sintaxe) + `curl -fsS localhost/health` |
| Alterar workflow CI | Validação de sintaxe YAML + leitura do log se já rodou |
| Deploy/rollback | `docker compose ps`, `curl -fsS health`, `git log --oneline -5` |

Não declare "funcionou" sem observar. "Fiz o deploy" sem `docker compose ps` é
claim não verificada — trate como caveat.

## Fraud table

Fraudes específicas de devops que o JUDGE e o agente devem caçar:

| Tipo | Descrição | Severidade |
|------|-----------|------------|
| **unverified_deploy** | "Deploy funcionou" sem `docker compose ps`, `curl` ou equivalente | high |
| **weakened_healthcheck** | Healthcheck removido, endpoint trocado por `/`, timeout inflado | high |
| **secret_in_diff** | Secret, token, senha ou private key aparece no diff | high |
| **unpinned_image** | Imagem com tag `latest`, `stable` ou sem digest pin em produção | medium |
| **missing_volume_port** | Volume ou porta essencial omitido após refatoração | medium |
| **silent_config** | `docker compose config` ou `nginx -t` silenciado/ignorado | medium |
| **unauthorized_action** | Deploy/push/destroy sem AUTH line documentada | high |
| **prod_direct_edit** | Alteração direta em arquivo de produção sem staging/teste | high |

## Minimum evidence set (binding)

Antes de qualquer ação no domínio **devops**:

1. Abrir os arquivos de configuração relevantes ({{READ}})
2. Abrir a documentação de deploy/operacional, se existir
3. Rodar o comando de validação de sintaxe do domínio ({{RUN}}):
   - `docker compose config`
   - `nginx -t`
   - `terraform validate` (se houver Terraform)
4. Se a ação for irreversível (deploy, push, destroy, alteração de DNS/cert),
   obter AUTH com citação exata do usuário via {{ASK}} e registrar em
   `auth.action_taken: true`, `auth.authorized: true`, `auth.action` e
   `auth.quote`
5. Verificar o estado real depois da ação ({{RUN}})

Se qualquer item acima for impossível de cumprir, pare e explique o bloqueio.

## Rotas FIT por shape

| Rota | Quando usar | O que fazer |
|------|-------------|-------------|
| **plan-first** | deploy, rollout, rollback, destroy, push de imagem, alteração de DNS/certificado | Sempre. Planeje, documente riscos, pare e aguarde aprovação. |
| **question** | "Por que o container caiu?", "Por que o healthcheck falha?" | Diagnosticar. Não altere configuração sem autorização. Entregue achados + uma recomendação. |
| **research** | API/ferramenta de infra desconhecida (ex.: nova feature do Compose, novo provider Terraform) | Pesquisar documentação oficial antes de tocar. |
| **code-loop** | Mudança de configuração reversível (compose, nginx, workflow, script de deploy) | Ciclo completo com verify por observação. |
| **inference** | Só dá para inferir | Declarar baixa confiança; perguntar ao usuário. |

As rotas possíveis no domínio devops seguem o mesmo schema do ciclo base:
`code-loop | plan-first | question | research | inference`.

### Ações irreversíveis em devops

Trate como irreversível (portanto `plan-first`) qualquer ação que:

- publica uma imagem, artefato ou release
- altera DNS, certificado, load balancer ou rota de produção
- destrói/recria infraestrutura ou dados
- deploya em ambiente compartilhado/produção
- executa `docker push`, `terraform apply`, `kubectl apply`, `git push --force`

## Verify commands sugeridos

O projeto pode declarar seus próprios comandos em `.kata/config.yaml`:

```yaml
verify:
  lint: docker compose config
  test: ./scripts/smoke-test.sh
  coverage: echo "coverage not applicable"
```

Se o projeto não declarar, o agente deve propor os defaults do domínio e
registrar o bloqueio como caveat — nunca inventar verificação que não rodou.

Defaults comuns:

- **sintaxe compose**: `docker compose config`
- **sintaxe nginx**: `nginx -t`
- **build local**: `docker build -t local-test .`
- **healthcheck**: `curl -fsS http://localhost/health`
- **estado**: `docker compose ps`
- **validação Terraform**: `terraform validate`

## Red lines

Ações que este adapter **nunca** permite sem intervenção humana documentada:

- Executar deploy/push/destroy/publish sem `auth.action_taken: true` e `auth.quote`
- Alterar infra de produção diretamente sem testar em staging/local primeiro
- Colocar secrets, tokens ou credenciais no diff ou no `.kata/<task>.yaml`
- Usar tag `latest` em imagem de produção sem justificativa documentada
- Fazer `git push --force` em branch compartilhada
- Desativar healthcheck ou usar `restart: no` em serviço crítico sem motivo documentado

## Registro no YAML

Durante o FIT, registre o domínio no `.kata/<task>.yaml`:

```yaml
domain: devops
status: draft
base_commit: "a1b2c3d..."
fit:
  trivial: false
  route: code-loop     # ajustar: plan-first para ações irreversíveis
  reason: "Alteração de configuração Docker Compose reversível"
  answered: false
  skipped: false
```

## Integração com AUTH e PENDING

- **AUTH**: ações irreversíveis exigem autorização. Registre:
  ```yaml
  auth:
    action_taken: true
    authorized: true
    action: "deploy da nova imagem no ambiente de staging"
    quote: "pode fazer o deploy em staging"
  ```
- **PENDING**: se a tarefa aprovada deixar um follow-up obrigatório (ex.:
  "fazer deploy em produção depois de validar staging"), documente:
  ```yaml
  pending:
    action: "promover deploy de staging para produção"
    documented: true
  ```

## Carregamento

Se a tarefa declarar `domain: devops`, carregue este adapter com
{{LOAD_DOMAIN}} imediatamente após a fase FIT e siga as regras acima.
Se {{LOAD_DOMAIN}} falhar, registre `kata-devops` em
`preflight.skills_missing`, aplique o contrato mínimo descrito aqui e
continue — domain adapters são opcionais, mas a ausência deve ser transparente.
