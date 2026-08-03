# Kata (型)

[![CI](https://github.com/walternagai/kata/actions/workflows/ci.yml/badge.svg)](https://github.com/walternagai/kata/actions/workflows/ci.yml)

> Python 3.11+ | CLI + OpenCode Agent + Claude Code Skills | Karpathy Development Cycle + Fable Method

Kata (型, "forma/padrão") é um agente OpenCode, um conjunto de skills para
Claude Code e um CLI Python que implementam o ciclo
FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT,
com AUDIT e JUDGE adversarial, inspirado em:

1. **Karpathy Development Cycle** (Andrej Karpathy): pensar antes de codar,
   manter o código mínimo, mudanças cirúrgicas e verificação objetiva.
2. **The Fable Method** (Sahir619/fable-method): classificar a tarefa antes de
   agir (fit gate), triviality gate, evidência antes de ação, verificação
   adversarial e relatório outcome-first.

Para a referência técnica completa, consulte [`DOCUMENTATION.md`](DOCUMENTATION.md).

O ciclo completo:
```
FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT
                                                                           ↓ (opcional)
                                                                         JUDGE
```

Modos adicionais do CLI: `--audit` (gradua as fases da tarefa como
followed / skipped / faked) e `--check-only` (só verificação, para CI).

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
| `@kata --task nome --audit` | Gradua as fases: followed / skipped / faked / degraded |

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
| `/kata --task nome --audit` | Gradua as fases: followed / skipped / faked / degraded |

### CLI Python

```bash
kata --init minha-tarefa       # Cria .kata/minha-tarefa.yaml
kata                            # Ciclo interativo completo
kata --check-only               # Só VERIFY (lint + test + coverage)
kata --plan                     # Modo planejamento: FIT + THINK, para
kata --plan --task minha-tarefa # Planeja tarefa específica
kata --task minha-tarefa        # Retoma tarefa específica
kata --task minha-tarefa --report  # Relatório outcome-first
kata --doctor                      # As skills de fase estão instaladas?
kata --task minha-tarefa --audit   # Gradua fases (followed/skipped/faked)
kata --task minha-tarefa --judge   # Verificação adversarial (caça fraudes)
```

### Argumentos do CLI

| Flag | Default | Descrição |
|------|---------|-----------|
| `--plan` | `False` | Modo planejamento: FIT + THINK, não modifica código |
| `--judge` | `False` | Verificação adversarial (re-executa checks, caça fraudes) |
| `--report` | `False` | Gera relatório outcome-first de tarefa concluída |
| `--audit` | `False` | Gradua as fases da tarefa: followed / skipped / faked / degraded |
| `--doctor` | `False` | Confere se as skills de fase estão instaladas em cada frontend |
| `--ruff-paths` | `src/ tests/` | Caminhos para ruff check |
| `--test-paths` | `tests/` | Caminhos para pytest |
| `--ignore` | (nenhum) | Caminhos para ignorar no pytest |
| `--cov-source` | auto-detectado | Pacote fonte para coverage: lê `[tool.coverage.run] source` do `pyproject.toml`, com fallback `src` |
| `--gate` | `verify.gate`, senão `70` | Gate mínimo de coverage (%) |

Essas flags configuram os **defaults Python**. Um papel declarado em
`.kata/config.yaml` roda verbatim, e as flags de caminho daquele papel
deixam de valer.

## Projetos que não são Python

Quem sabe verificar um projeto é o projeto. Declare os comandos em
`.kata/config.yaml`, ao lado dos arquivos de tarefa:

```yaml
verify:
  lint: npx eslint src tests
  test: npx vitest run
  coverage: npx vitest run --coverage
  coverage_pattern: 'All files\\s+\\|\\s+([\\d.]+)'
  gate: 80
```

Cada papel aceita string ou lista, e todo papel é opcional: o que for
omitido cai no default Python (ruff/pytest/pytest-cov), então dá para
trocar só o linter e manter o pytest. Sem o arquivo, nada muda.

O JUDGE segue a mesma linha: ele conhece a sintaxe de teste de Python,
JS/TS, Go, Ruby, Rust e Java/Kotlin. Linguagem fora dessa lista vira
ponto cego declarado, não silêncio.

## Fases do Ciclo

### 0. FIT (classificação da tarefa)

Inspirado no fit gate do [The Fable Method](https://github.com/Sahir619/fable-method).
Classifica a tarefa antes de investir esforço:
- **Triviality gate**: 1 arquivo, <10 linhas, sem busca → vá direto a VERIFY
- **Rotas**: code-loop, plan-first, question, research, inference

### 1. THINK
Declarar problema, assumptions, alternativas e unknowns antes de codar — e o
**critério de sucesso** (`done`), declarado antes da evidência (Fable Step 1).
Budget de investigação: 2 buscas sem resultado → pare e pergunte ao usuário.

### 2. SIMPLIFY
Verificar se o código é mínimo — sem abstrações especulativas (YAGNI) ou
configurabilidade não solicitada.

### 2.5 INTENT
Verificar que código, teste e spec concordam antes de mudar comportamento.
Ordem de autoridade em conflito: usuário > spec > testes > código. Não edite
até resolver o conflito.

### 3. SURGICAL
Validar arquivo-por-arquivo que cada mudança rastreia direto ao pedido,
sem efeitos colaterais.

### 4. VERIFY
Rodar lint + teste + coverage (gate >= 70%) e confrontar o critério `done`
declarado no THINK com o resultado final. Os comandos vêm de
`.kata/config.yaml` quando o projeto os declara; senão, são os defaults
Python (ruff, pytest, pytest-cov com `--cov-fail-under`).
**Hard bound** (Fable Step 5): após 3 tentativas falhas, a tarefa é devolvida
ao usuário (`hand back`) com o que foi tentado, o output real e a hipótese
atual — em vez de repetir o fix-verify indefinidamente.

### 4.2 TWIN CHECK
Defeito corrigido? O mesmo padrão costuma existir em outros lugares — busque
no projeto inteiro e registre o resultado. "Sem defeito" ≠ "não chequei".

### 4.5 ARTIFACT
Verificar que as linhas devidas estão no relatório: INTENT (comportamento
mudou), AUTH (ação irreversível), PENDING (follow-up prescrito e não tomado),
TWINS (defeito corrigido e varredura registrada).

### 5. REPORT
Relatório outcome-first documentando o que foi feito, com caveats honestos.

### AUDIT (modo CLI)
`kata --audit` gradua as fases da tarefa como **followed** / **skipped** /
**faked** (afirmado sem observação — o padrão R7-1), nomeando o risco concreto
de cada skip/fake. Equivalente ao `/fable-method audit`.

### JUDGE (opcional)
Verificação adversarial — re-executa as verificações afirmadas, confronta o
diff com o relatório e caça fraudes em 6 categorias (weakened checks, false
completion, scope creep, unauthorized action, spec betrayal, debris).
É a última fase, aplicada apenas quando solicitada após o REPORT.

Se o juiz não encontrar fraude mas também não tiver tido como observar — nada
re-executado (o caso de todo toolchain que não é Python), ou teste numa
linguagem cujos padrões ele não lê — o veredito é **UNVERIFIABLE**, não
VERIFIED, e os pontos cegos vêm listados. "Não consegui olhar" não é
reportado como "está tudo certo".

## Diretório de Trabalho

O kata usa `.kata/` na raiz do projeto. Cada tarefa é um arquivo YAML:

```
.kata/
  minha-tarefa.yaml
  bug-fix-123.yaml
```

## Desenvolvimento

```bash
make build-skills          # gera opencode/ e claude-code/ a partir de phases/
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
├── phases/                            ← FONTE ÚNICA dos prompts (11 arquivos:
│                                         kata.md + as 10 fases). É aqui que se
│                                         edita; o resto é gerado.
├── opencode/                          ← GERADO (make build-skills)
│   ├── agent/kata.md                  ← Agente @kata (OpenCode)
│   └── skills/kata-*/SKILL.md         ← 10 skills (fit, think, simplify, intent,
│                                         surgical, verify, artifact, report,
│                                         question, judge; TWIN CHECK vive no
│                                         orquestrador)
├── claude-code/                       ← GERADO (make build-skills)
│   └── skills/kata-*/SKILL.md         ← 11 skills (orquestrador kata + as 10 acima)
├── src/kata/
│   ├── cli.py                  ← CLI (orquestra as 9 fases + audit + judge)
│   ├── fit.py                  ← Lógica do fit gate (diff_stats, is_trivial)
│   ├── config.py               ← .kata/config.yaml (comandos do projeto alvo)
│   ├── skills.py               ← Preflight: as skills de fase estão instaladas?
│   ├── verify.py               ← Lógica de verificação (lint/teste/coverage)
│   ├── judge.py                ← Lógica adversarial (caça fraudes)
│   ├── __init__.py             ← Versão do pacote
│   └── __main__.py             ← Entry point para `python -m kata`
├── eval/                       ← Cenários de trap adversarial (python3 eval/run_traps.py)
├── scripts/
│   ├── build_skills.py                                 ← Gera os frontends a partir de phases/
│   ├── install.sh / install.ps1                        ← Instalação no OpenCode
│   └── install-claude-code.sh / install-claude-code.ps1 ← Instalação no Claude Code
└── tests/                      ← Testes pytest (ver `make test` para cobertura)
```

## Licença

MIT
