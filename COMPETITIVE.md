# Diferenciais Competitivos do Kata

> Última pesquisa: GitHub Search, agosto de 2026.

O Kata compete no espaço de **qualidade para código gerado por/agentes de IA** — ciclos de desenvolvimento disciplinados, skills para Claude Code/OpenCode, *quality gates* e verificação adversarial. Esta página consolida os projetos open-source similares encontrados e destaca o que torna o Kata distinto.

---

## 1. Projetos mais diretamente similares

| Projeto | Linguagem | Stars* | Foco principal | Similaridade com Kata |
|---|---:|---:|---|---|
| [Sahir619/fable-method](https://github.com/Sahir619/fable-method) | Python | 2.1k | Workflow “Think / Act / Verify” com eval que mantém o modelo honesto | **Inspiração direta do Kata** — fit gate, triviality gate, verificação adversarial, relatório outcome-first |
| [UnpaidAttention/fable5-methodology](https://github.com/UnpaidAttention/fable5-methodology) | Shell | 89 | Metodologia transferível de engenharia de software para agentes de IA | Muito próxima: playbook, skills contratados, ciclo de vida |
| [ardhaecosystem/fable-method](https://github.com/ardhaecosystem/fable-method) | Python | 10 | Fable Method com 4 skills Hermes (think/act/prove/…) | Replicação do Fable, portanto alinhada com Kata |
| [oliwoodman/fable-skills](https://github.com/oliwoodman/fable-skills) | — | 32 | 5 skills deixadas pelo Fable (security sweep, setup, build planner, honest advisor, bug hunter) | Conjunto de skills especializadas, como as `kata-*` |
| [vlad-ko/claude-wizard](https://github.com/vlad-ko/claude-wizard) | Shell | 64 | 8 fases de desenvolvimento com TDD, revisão adversarial e quality gates | **Muito similar**: ciclo nomeado, TDD, adversarial review, gates |
| [LerianStudio/ring](https://github.com/LerianStudio/ring) | HTML | 205 | 89 skills e 38 agentes especializados que impõem boas práticas de engenharia | Grande ecossistema de skills; cobre TDD, debugging, code review |
| [junit/pre-commit-review](https://github.com/junit/pre-commit-review) | Rust | 6 | AI Agent skill para code review pré-commit e quality gating local | Foco no gate local, como VERIFY/JUDGE do Kata |
| [TeamSPWK/nova](https://github.com/TeamSPWK/nova) | Shell | 2 | AI Agent Ops para Claude Code — avaliador independente, revisão adversarial e pre-commit quality gate | Combina adversarial review + gate pré-commit, bem próximo de Kata |
| [jeremylongshore/intent-audit-harness](https://github.com/jeremylongshore/intent-audit-harness) | Shell | 1 | Test-policy enforcement determinístico e contenção à prova de IA para quality gates | Toca no ponto “proteger config de teste contra mutações da IA”, complementar ao Kata |
| [aiagentflow/aiagentflow](https://github.com/aiagentflow/aiagentflow) | TypeScript | 41 | Orquestrador local-first, CLI-driven, multi-agent, com specs/PRDs/guidelines | CLI + workflow + specs, próximo da proposta do Kata |
| [cauethenorio/hym](https://github.com/cauethenorio/hym) | — | 2 | Skills composáveis para Claude Code que guiam o ciclo de desenvolvimento | Similar em formato (skills para Claude Code) |
| [thedavidmurray/claude-test-driven-development](https://github.com/thedavidmurray/claude-test-driven-development) | — | 0 | Skill Claude Code para disciplina TDD RED-GREEN-REFACTOR | Equivalente a uma fase VERIFY/TDD especializada |

\* Stars coletados em agosto de 2026; podem mudar.

---

## 2. Projetos relacionados (mesmo espaço, menor sobreposição)

| Projeto | Linguagem | Stars | Foco | Por que aparece na mesma busca |
|---|---:|---:|---|---|
| [langtalks/swe-agent](https://github.com/langtalks/swe-agent) | Python | 638 | Multi-agent system de software engineering (researcher + developer) | Orquestração de agentes para código, mas sem o ciclo qualidade do Kata |
| [PacificStudio/openase](https://github.com/PacificStudio/openase) | Go | 263 | Ticket-driven automated software engineering | Automação de código a partir de tickets |
| [app-builders-club/mvp-builder](https://github.com/app-builders-club/mvp-builder) | Shell | 13 | Document-Driven Development com TDD e skills para Claude Code | Document-first + TDD, tangente ao THINK/INTENT do Kata |
| [SalesforceAIResearch/agentforce-adlc](https://github.com/SalesforceAIResearch/agentforce-adlc) | Python | 95 | Agent Development Life Cycle para Agentforce | Ciclo de vida de agente, mas voltado a Salesforce/Agentforce |
| [vokako/AIDLC-skills](https://github.com/vokako/AIDLC-skills) | — | 4 | AI-Driven Development Life Cycle como plugin Claude Code | Outro ciclo de vida em formato de skills |

---

## 3. Tabela de diferenciais competitivos do Kata

| Diferencial | O que o Kata faz | Por que isso é vantagem | Quem não tem (ou tem menos) |
|---|---|---|---|
| **Ciclo com fases nomeadas e orquestradas** | FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT + AUDIT + JUDGE | Pipeline executável com ordem, dependências e saídas esperadas — não é só um prompt ou um conjunto de skills | Fable-method é teoria/playbook; claude-wizard tem 8 fases, mas sem backend unificado; muitos são apenas skills isoladas |
| **Backend Python real + dois frontends** | `src/kata/` implementa `fit.py`, `verify.py`, `judge.py`, `cli.py`; skills para OpenCode e Claude Code geradas da mesma fonte | Comportamento objetivo testável, versionável e consistente entre OpenCode e Claude Code | Projetos como claude-wizard, nova, pre-commit-review vivem quase só em prompts/skills, sem lógica central testada |
| **Fonte única das fases (`phases/*.md`)** | `phases/kata-<fase>.md` gera tanto `opencode/` quanto `claude-code/` via `make build-skills` | Elimina divergência entre frontends; 93% do conteúdo é compartilhado; `tests/test_skills_build.py` garante sincronia | Fable-skills, claude-skills-vault, ring são coleções manuais de skills — alto risco de drift entre versões/plataformas |
| **JUDGE adversarial executável** | `judge.py` caça fraudes com git real (committed/untracked), integrado ao CLI como `--judge` | Verificação adversarial não fica só no prompt: roda e dá veredito | Fable Method fala de adversarial, mas o Kata materializa em código com testes reais de git |
| **Schema `.kata/<task>.yaml` + compatibilidade mushin** | Configuração declarativa por tarefa; compatível com `.karpathy/` do mushin via `ln -s .karpathy .kata` | Rastreia intent, auth, pending, twins por tarefa; migração fácil de usuários do ciclo Karpathy anterior | Nenhum concorrente menciona schema declarativo de tarefa ou compatibilidade com outro ecossistema |
| **Domain adapters gerados de fonte única** | `domains/kata-<domínio>.md` gera skills para OpenCode e Claude Code; `kata-devops` já disponível | Estende o ciclo a devops/infra sem duplicar textos entre frontends; domain skills são opcionais | Fable Method tem domain adapters manuais; outros competidores não têm mecanismo de geração compartilhada por domínio |
| **VERIFY com cobertura gate** | `verify.py` roda lint/teste/coverage com fallback padrão (ruff/pytest/pytest-cov) e respeita `.kata/config.yaml`; suporta `--cov-fail-under` | Gate objetivo e mensurável de qualidade, adaptável por projeto alvo | Projetos de skills geralmente instruem o agente a “rodar testes”, sem gate numérico nem integração com config |
| **Preflight de skills + `--doctor`** | `skills.py` lista skills canônicas e verifica instalação por frontend; fase sem skill vira `degraded` no audit | Garante que o ciclo só rode com o toolbox completo; diagnóstico claro | Nenhum concorrente oferece checagem de instalação de skills como feature de preflight |
| **Testes reais para JUDGE (git de verdade)** | `TestJudgeTaskDetectsCommittedFraud` e `TestJudgeSeesUntrackedFiles` criam repositório git real em `tmp_path` | A parte mais difícil de mockar é testada de verdade, não com mocks que esconderiam bugs | Rara entre projetos de agentes de IA; a maioria não testa interação com git |
| **CLI Python independente** | `kata.cli:main` funciona fora dos agentes; `__main__.py` permite `python -m kata` | Usável headless, em CI, ou por humanos sem depender de Claude Code/OpenCode | Projetos como claude-wizard, ring, fable-skills são exclusivamente skills/plugins |
| **Relatório outcome-first estruturado** | REPORT com `INTENT`, `AUTH`, `PENDING`, `TWINS` lines; ARTIFACT verifica linhas devidas | Saída padronizada conectando decisão, permissão, débitos e clones — útil para revisão humana e audit | Outros focam no “o que foi feito”; Kata foca no “o que ficou devendo, autorizado e por quê” |
| **Lint + coverage medidos no próprio código do ciclo** | `make lint && make test` medem `cli.py`; gate de cobertura 70%; CI roda Makefile | A ferramenta se aplica a si mesma: come-come próprio cachorro | Poucos projetos de workflow/metodologia impõem cobertura sobre seu próprio código |

---

## 4. Resumo competitivo

> O Kata não é só um **prompt**, **skill** ou **metodologia**: é uma **ferramenta Python testável** que empacota o ciclo Karpathy + Fable em um pipeline executável, com frontends gerados de fonte única, verificação adversarial real e um schema de tarefa que rastreia intenção, autorização e débitos técnicos.

Se um usuário precisa apenas de um conjunto de skills para Claude Code, alternativas como **claude-wizard**, **ring** ou **fable-skills** podem ser suficientes. Se ele precisa de **qualidade mensurável, reprodutível e auditável** — com backend compartilhado entre OpenCode e Claude Code — o Kata é a opção mais completa.
