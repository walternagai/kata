# Kata (型)

> Karpathy Development Cycle — CLI Python + Agente OpenCode

Kata (型, "forma/padrão") é um agente OpenCode e CLI Python que implementa o
ciclo de desenvolvimento de 4 passos inspirado em Andrej Karpathy:

```
THINK → SIMPLIFY → SURGICAL → VERIFY
```

Como um kata marcial, é uma sequência disciplinada e repetível de movimentos:
pensar antes de codar, manter o código mínimo, fazer mudanças cirúrgicas e
verificar com critérios objetivos.

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
| `@kata --init nome-da-tarefa` | Cria tarefa e executa THINK |
| `@kata --check-only` | Só verificação (CI/snapshot) |
| `@kata --task nome` | Retoma tarefa existente |

### CLI Python

```bash
kata --init minha-tarefa       # Cria .kata/minha-tarefa.yaml
kata                            # Ciclo interativo completo
kata --check-only               # Só VERIFY (lint + test + coverage)
kata --task minha-tarefa        # Retoma tarefa específica
```

### Argumentos do CLI

| Flag | Default | Descrição |
|------|---------|-----------|
| `--ruff-paths` | `src/ tests/` | Caminhos para ruff check |
| `--test-paths` | `tests/` | Caminhos para pytest |
| `--ignore` | (nenhum) | Caminhos para ignorar no pytest |
| `--cov-source` | `src` | Pacote fonte para coverage |
| `--gate` | `70` | Gate mínimo de coverage (%) |

## As 4 Fases

### 1. THINK
Declarar problema, assumptions, alternativas e unknowns antes de codar.

### 2. SIMPLIFY
Verificar se o código é mínimo — sem abstrações especulativas (YAGNI) ou
configurabilidade não solicitada.

### 3. SURGICAL
Validar arquivo-por-arquivo que cada mudança rastreia direto ao pedido,
sem efeitos colaterais.

### 4. VERIFY
Rodar ruff + pytest + coverage (gate >= 70%) e checar critério de sucesso.

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
│   └── skills/kata-*/SKILL.md  ← 4 skills (uma por fase)
├── src/kata/
│   ├── cli.py                  ← CLI headless (orquestra as 4 fases)
│   ├── verify.py               ← Lógica de verificação (ruff/pytest/coverage)
│   ├── __init__.py             ← Versão do pacote
│   └── __main__.py             ← Entry point para `python -m kata`
├── scripts/install.sh          ← Instalação via symlinks
└── tests/                      ← 78 testes, 99% coverage
```

## Licença

MIT
