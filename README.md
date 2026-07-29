# Kata (型)

[![CI](https://github.com/walternagai/kata/actions/workflows/ci.yml/badge.svg)](https://github.com/walternagai/kata/actions/workflows/ci.yml)

> Python 3.11+ | CLI + OpenCode Agent + Claude Code Skills | Karpathy Development Cycle + Fable Method

Kata (型, "forma/padrão") é um agente OpenCode, um conjunto de skills para
Claude Code e um CLI Python que implementam o ciclo
FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → ARTIFACT → REPORT,
com JUDGE adversarial opcional, inspirado em:

1. **Karpathy Development Cycle** (Andrej Karpathy): pensar antes de codar,
   manter o código mínimo, mudanças cirúrgicas e verificação objetiva.
2. **The Fable Method** (Sahir619/fable-method): classificar a tarefa antes de
   agir (fit gate), triviality gate, evidência antes de ação, verificação
   adversarial e relatório outcome-first.

Para a referência técnica completa, consulte [`DOCUMENTATION.md`](DOCUMENTATION.md).

O ciclo completo:
```
FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → ARTIFACT → REPORT
                                                                  ↓ (opcional)
                                                                JUDGE
```

Como um kata marcial, é uma sequência disciplinada e repetível de movimentos:
classificar a tarefa, pensar antes de codar, manter o código mínimo, verificar
intenção, mudanças cirúrgicas e verificar com critérios objetivos.

## Instalação

### Agente OpenCode (recomendado)

```bash
git clone <repo> ~/dev/ninja-apps/kata
cd ~/dev/ninja-apps/kata
make install
# Reinicie o OpenCode
```

Após reiniciar, use `@kata` no OpenCode para iniciar o ciclo.

No Windows PowerShell, use o instalador nativo:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
# Para evitar links simbólicos/junctions, use cópias:
# .\scripts\install.ps1 -Copy
# Desinstalar: .\scripts\install.ps1 -Uninstall
```

O instalador usa `OPENCODE_CONFIG_DIR` quando definido; caso contrário, usa
`~/.config/opencode`, o caminho global do OpenCode em todas as plataformas.

### Skills Claude Code

```bash
git clone <repo> ~/dev/ninja-apps/kata
cd ~/dev/ninja-apps/kata
make install-claude-code
```

Depois de instalado, use a skill `kata` no Claude Code (ex: `/kata`, ou
descreva a tarefa e deixe o Claude Code acioná-la pela descrição).

No Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-claude-code.ps1
# Para evitar links simbólicos/junctions, use cópias:
# .\scripts\install-claude-code.ps1 -Copy
# Desinstalar: .\scripts\install-claude-code.ps1 -Uninstall
```

O instalador usa `CLAUDE_CONFIG_DIR` quando definido; caso contrário, usa
`~/.claude`, o caminho global do Claude Code em todas as plataformas.

Diferente do agente `@kata` do OpenCode, a versão Claude Code é só skills
(sem subagente): o ciclo do kata é muito interativo — pergunta a cada
fase — e isso se encaixa melhor rodando na conversa principal do que em um
subagente isolado que só reporta um resumo ao final.

### CLI Python (opcional, para CI/headless)

```bash
pip install -e .
```

## Uso

### No OpenCode

| Comando | Ação |
|---------|------|
| `@kata` | Ciclo interativo completo |
| `@kata --init nome-da-tarefa` | Cria tarefa e executa FIT + THINK |
| `@kata --check-only` | Só verificação (CI/snapshot) |
| `@kata --plan nome-da-tarefa` | Modo planejamento: FIT + THINK, para sem modificar código |
| `@kata --task nome` | Retoma tarefa existente |
| `@kata --task nome --judge` | Verificação adversarial (caça fraudes) |
| `@kata --task nome --report` | Relatório outcome-first |

### No Claude Code

A skill `kata` recebe os mesmos argumentos que o agente OpenCode, passados
como texto após o nome (ex: `/kata --init nome-da-tarefa`):

| Comando | Ação |
|---------|------|
| `/kata` | Ciclo interativo completo |
| `/kata --init nome-da-tarefa` | Cria tarefa e executa FIT + THINK |
| `/kata --check-only` | Só verificação (CI/snapshot) |
| `/kata --plan nome-da-tarefa` | Modo planejamento: FIT + THINK, para sem modificar código |
| `/kata --task nome` | Retoma tarefa existente |
| `/kata --task nome --judge` | Verificação adversarial (caça fraudes) |
| `/kata --task nome --report` | Relatório outcome-first |

### CLI Python

```bash
kata --init minha-tarefa       # Cria .kata/minha-tarefa.yaml
kata                            # Ciclo interativo completo
kata --check-only               # Só VERIFY (lint + test + coverage)
kata --plan                     # Modo planejamento: FIT + THINK, para
kata --plan --task minha-tarefa # Planeja tarefa específica
kata --task minha-tarefa        # Retoma tarefa específica
```

### Argumentos do CLI

| Flag | Default | Descrição |
|------|---------|-----------|
| `--plan` | `False` | Modo planejamento: FIT + THINK, não modifica código |
| `--ruff-paths` | `src/ tests/` | Caminhos para ruff check |
| `--test-paths` | `tests/` | Caminhos para pytest |
| `--ignore` | (nenhum) | Caminhos para ignorar no pytest |
| `--cov-source` | auto-detectado | Pacote fonte para coverage: lê `[tool.coverage.run] source` do `pyproject.toml`, com fallback `src` |
| `--gate` | `70` | Gate mínimo de coverage (%) |

## Fases do Ciclo

### 0. FIT (classificação da tarefa)

Inspirado no fit gate do [The Fable Method](https://github.com/Sahir619/fable-method).
Classifica a tarefa antes de investir esforço:
- **Triviality gate**: 1 arquivo, <10 linhas, sem busca → vá direto a VERIFY
- **Rotas**: code-loop, plan-first, question, research, inference

### 1. THINK
Declarar problema, assumptions, alternativas e unknowns antes de codar.

### 2. SIMPLIFY
Verificar se o código é mínimo — sem abstrações especulativas (YAGNI) ou
configurabilidade não solicitada.

### 3. INTENT
Verificar se a intenção do código está clara — nomes, imports, estrutura
refletem o que o código faz.

### 4. SURGICAL
Validar arquivo-por-arquivo que cada mudança rastreia direto ao pedido,
sem efeitos colaterais.

### 5. VERIFY
Rodar ruff + pytest + coverage (gate >= 70%) usando `--cov-fail-under` e
checar critério de sucesso.

### 6. ARTIFACT
Gerar artefatos da tarefa (provas, verificações, etc).

### 7. REPORT
Relatório outcome-first documentando o que foi feito.

### JUDGE (opcional)
Verificação adversarial — tenta caçar fraudes e inconsistências no
código produzido. É a nona e última fase, aplicada apenas quando
solicitada após o REPORT.

## Diretório de Trabalho

O kata usa `.kata/` na raiz do projeto. Cada tarefa é um arquivo YAML:

```
.kata/
  minha-tarefa.yaml
  bug-fix-123.yaml
```

## Desenvolvimento

```bash
make test                  # pytest + coverage
make lint                  # ruff check
make format                # ruff format
make install                # instala agente + skills no OpenCode
make uninstall               # remove symlinks do OpenCode
make install-claude-code     # instala skills no Claude Code
make uninstall-claude-code   # remove symlinks do Claude Code
```

## Compatibilidade

O schema `.kata/<task>.yaml` é compatível com o `.karpathy/` do mushin. Para
migrar tarefas existentes:

```bash
ln -s .karpathy .kata   # symlink preserva acesso ao legado
```

## Estrutura

```
kata/
├── opencode/
│   ├── agent/kata.md                  ← Agente @kata (OpenCode)
│   └── skills/kata-*/SKILL.md         ← 10 skills (8 fases + question + JUDGE)
├── claude-code/
│   └── skills/kata-*/SKILL.md         ← 11 skills (kata orquestrador + 8 fases + question + JUDGE)
├── src/kata/
│   ├── cli.py                  ← CLI headless (orquestra as 8 fases + judge)
│   ├── fit.py                  ← Lógica do fit gate (diff_stats, is_trivial)
│   ├── verify.py               ← Lógica de verificação (ruff/pytest/coverage)
│   ├── judge.py                ← Lógica adversarial (caça fraudes)
│   ├── __init__.py             ← Versão do pacote
│   └── __main__.py             ← Entry point para `python -m kata`
├── scripts/
│   ├── install.sh / install.ps1                        ← Instalação no OpenCode
│   └── install-claude-code.sh / install-claude-code.ps1 ← Instalação no Claude Code
└── tests/                      ← Testes pytest (ver `make test` para cobertura)
```

## Licença

MIT
