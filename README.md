# Kata (型)

> Python 3.11+ | CLI + OpenCode Agent | Karpathy Development Cycle + Fable Method

Kata (型, "forma/padrão") é um agente OpenCode e CLI Python que implementa o
ciclo FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → ARTIFACT → REPORT,
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
| `--cov-source` | `src` | Pacote fonte para coverage |
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

### 8. JUDGE (opcional)
Verificação adversarial — tenta caçar fraudes e inconsistências no
código produzido.

## Diretório de Trabalho

O kata usa `.kata/` na raiz do projeto. Cada tarefa é um arquivo YAML:

```
.kata/
  minha-tarefa.yaml
  bug-fix-123.yaml
```

## Desenvolvimento

```bash
make test      # pytest + coverage
make lint       # ruff check
make format     # ruff format
make install    # instala agente + skills
make uninstall  # remove symlinks
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
│   ├── agent/kata.md           ← Agente @kata
│   └── skills/kata-*/SKILL.md  ← 9 skills (8 fases + JUDGE)
├── src/kata/
│   ├── cli.py                  ← CLI headless (orquestra as 8 fases + judge)
│   ├── fit.py                  ← Lógica do fit gate (diff_stats, is_trivial)
│   ├── verify.py               ← Lógica de verificação (ruff/pytest/coverage)
│   ├── judge.py                ← Lógica adversarial (caça fraudes)
│   ├── __init__.py             ← Versão do pacote
│   └── __main__.py             ← Entry point para `python -m kata`
├── scripts/install.sh          ← Instalação via symlinks
└── tests/                      ← Testes pytest (ver `make test` para cobertura)
```

## Licença

MIT
