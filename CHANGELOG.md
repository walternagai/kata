# Changelog — `kata-dev`

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
O pacote no PyPI é `kata-dev`; o comando e o repositório são `kata`.

Cada seção lista o que mudou **no ferramental**. A trilha completa de commits
está no `git log`; aqui ficam os marcos que afetam quem usa o CLI, o agente
`@kata` ou as skills instaladas. O histórico anterior à 0.6.0 (mushin e o
`scripts/karpathy_cycle.py` original) não pertence a este pacote.

## 0.8.1 — 2026-10-30

### Adicionado

- `CHANGELOG.md` — marcos de uso de cada versão, a partir da 0.6.0. O pacote
  está no PyPI desde a 0.7.1 e não havia de onde ler o que mudou; agora
  `test_changelog_menciona_a_versao_atual` reprova quando a versão publicada
  não tem seção.
- Documentação da distribuição: badges de versão e Python, seção
  "Distribuição (PyPI)" no README (nome do pacote vs comando, conteúdo do
  wheel, install/upgrade/uninstall), seção "Distribution and versions" em
  `DOCUMENTATION.md` e a URL `Changelog` nos project links do PyPI.
- O sdist passa a levar `CHANGELOG.md`.

### Alterado

- O lint e o teste padrão rodam com o interpretador do projeto
  (`.venv/bin/python`, `.venv/Scripts/python.exe`, `venv/`) quando ele importa
  as ferramentas do papel. Num `pipx install kata-dev` sem as dependências do
  alvo, o pytest re-executado morria por `ModuleNotFoundError` num repositório
  limpo — e o JUDGE lia a falha como `false_completion`.

### Corrigido

- A fase JUDGE não manda mais buscar um modelo ou comando de fornecedor
  específico. O Estágio 2 virou procedimento: tabela de quem executa
  (revisor do host, humano ou ninguém) e checklist de quatro itens ancorado
  em `file:line`. Item não checado se escreve "não verificado" e vira caveat —
  estágio inteiro não verificado nunca produz VERIFIED.
- README, `DOCUMENTATION.md`, `CLAUDE.md` e `COMPETITIVE.md` deixaram de
  ensinar `/advisor` e `/effort` como caminho do Estágio 2.
- O comando de teste declarado em `.kata/config.yaml` deste repositório
  importava o kata de `site-packages`; `pythonpath = ["src"]` no
  `[tool.pytest.ini_options]` resolve nos três sistemas operacionais.
- O ramo do JUDGE que acusa `approved_commit` não ancestral do HEAD
  (`judge.py:1717-1725`) tinha teste de nome parecido que nunca o alcançava.
- O caminho de impressão de `--install`/`--uninstall` passou a ter teste.
- `scripts/check_package.py` confere o **sdist** e não só o wheel: exigir os
  arquivos de raiz é o que impede o changelog de ficar de fora outra vez.

## 0.8.0 — 2026-10-28

### Adicionado

- `kata --stamp`: fecha a janela de diff do JUDGE depois do commit.
- `--doctor` compara a versão das skills instaladas com a do kata em execução.
- Gate de `typecheck` declarável, com recusa de operadores de shell silenciosos
  e gravação dos comandos executados (`verify.commands`).
- `make eval` para a suíte adversária de `eval/`.

### Corrigido

- Os commits da janela são atribuídos às tasks que os carimbaram.
- Janela de diff vazia vinda da base confiável é confessada, não aprovada.
- "Comando que nunca rodou" deixou de ser lido como "check reprovado".
- O relatório mostra o papel da verificação (`lint`), não o nome da ferramenta
  Python (`ruff`).
- Chaves desconhecidas em qualquer nível de `.kata/config.yaml` são recusadas.
- A cobertura mede a superfície declarada pelo projeto, não um subconjunto.
- O arquivo de tarefa continua legível e sua evidência, portátil.

## 0.7.5 — 2026-10-23

### Corrigido

- Uma janela só para a lista de arquivos alterados: o CLI declarava numa janela
  e o JUDGE auditava em outra.
- O CLI para de inventar contexto e segue o contrato das skills.
- O CI mede a cobertura que declara e constrói o pacote.

## 0.7.4 — 2026-10-20

- O wheel passa a empacotar o subagente `kata-advisor`. Sem ele, o JUDGE caía
  no Estágio 1 sem avisar que o Estágio 2 não existia.

## 0.7.3 — 2026-09-24

### Adicionado

- `kata --install` adota o symlink criado pelo `make install`, e `--doctor`
  nomeia o modo (link, cópia ou misto).

### Corrigido

- Cenário `s23-artefatos-da-reexecucao` entra no versionamento.

## 0.7.2 — 2026-09-16

- Correção da deriva da documentação e publicação no PyPI.

## 0.7.1 — 2026-09-15

### Adicionado

- `kata-dev` publicado no PyPI com as skills empacotadas (instalação sem clone).
- JUDGE: âncora com reflog e `--trusted-base` para o gate de CI.

### Corrigido

- Discordância de INTENT com resolução registrada não é mais `spec_betrayal`.
- Janela de diff vazia quando `approved_commit == base_commit`.

## 0.7.0 — 2026-09-11

- Harness de avaliação (`eval/`), `--stats` da fração compartilhada entre
  frontends, `--audit-sessions` e as sessões arquivadas do estudo externo.

## 0.6.0 — 2026-09-10

- Primeira versão publicada: CLI do ciclo de 9 fases, agente OpenCode e skills
  do Claude Code.
