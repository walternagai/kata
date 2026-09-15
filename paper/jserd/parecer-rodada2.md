# Parecer editorial — JSERD (rodada 2)

**Manuscrito:** *Kata: an executable quality gate for AI-assisted software changes*
**Autor:** W. A. Nagai
**Tipo declarado:** software article
**Data:** 2026-09-15
**Versão avaliada:** `paper/jserd/paper.tex` em `6c713ef` (23 páginas, PDF de 23 páginas em 15/09 10:21)
**Versão avaliada anteriormente:** `189751c` (21 páginas) — parecer em `parecer.md`
**Recomendação:** **Revisão menor (minor revision)**

---

## 1. Síntese da rodada

Esta é a segunda revisão do mesmo manuscrito. A rodada 1 pediu um mínimo para
aceite — M1 (calibrar a alegação comparativa), M2 (divulgar as campanhas),
M5 (modelo de ameaça), M7 (reenquadramento e RQs), e as questões menores 1–6.
**O mínimo foi atendido.** A verificação desta rodada confirma, item por item,
contra a evidência primária, não contra o texto da resposta:

| Item | Estado | Evidência da verificação |
|---|---|---|
| M1 | **Atendido** | Tabela 2 recomputada dos JSONs: FP 0/4/2/5 na campanha final e 0/3/3/3+1 na rodada 1 re-pontuada; `16/15/15/14` sem pontos cegos confere. O texto agora decompõe as 11 acusações e nega superioridade de contenção (§1, §3.3, §9.3, §10, conclusão). |
| M2 | **Atendido** | As cinco campanhas estão descritas uma a uma (§3.3), com a direção de cada mudança de pontuação. **Re-pontuei com o classificador atual:** as 57 células de agente da campanha publicada na Tabela 2 (`compare_gates_round2.json`) reproduzem o status publicado, 0 divergências; as 36 células substantivas da campanha abortada (`compare_gates_final.json`) também, e as 21 diferenças restantes são INCONCLUSIVE→LIMIT, ou seja, detecção do bloqueio de gasto, não comportamento de gate. A rodada 1 tem de fato 300 caracteres por resposta, e o s06 cabe inteiro — a truncagem declarada é real. |
| M5 | **Atendido** | Nova §6.4 com adversário, escopo e cinco evasões. Reproduzi a principal: **janela de diff vazia com `approved_commit == base_commit` dá VERIFIED na versão avaliada e UNVERIFIABLE no HEAD** — a correção `3cacc5a` faz o que o texto diz. |
| M7 | **Atendido** | RQ1–RQ3 na Introdução, ligadas às seções; resumo, §9 e conclusão dizem que as fases de julgamento não tiveram ablação; as diretrizes viram hipóteses. |
| Menores 1–6 | **Atendidos** | Quatro graus do audit (verificado no código e no texto); tempos com a carga; coluna removida; tag única `v0.7.0`; modelo declarado como não registrado pelo harness, com a origem dos logs locais. |

**Acréscimos que não estavam no mínimo e elevam o artigo:** a §6.4 é hoje a
seção mais forte do manuscrito — cinco evasões reproduzíveis, com commit de
correção e lacuna residual declarada — e a §9.2 passou a reportar os vereditos
do JUDGE das próprias sessões (6 REFUTED por `spec_betrayal`), corrigindo uma
omissão que era, por si só, um problema de integridade do estudo externo.

**O que impede o aceite agora** é menor e de outra natureza: um falso positivo
determinístico que o próprio fluxo de CI do artigo fabrica (**N1**), uma
referência cruzada que falta no §8.3 sobre o alcance real da proteção da
âncora (**N2**) e a qualificação de uma frase do estudo externo que nenhum
artefato arquivado sustenta (**N4**). Nenhum deles exige redesenho: são ajustes
de texto, uma decisão de política e, no caso de N1, um filtro já existente no
próprio módulo.

---

## 2. Achados novos desta rodada

### N1. O JUDGE acusa os artefatos que a própria re-execução produz — honesto que passou em `--check-only` sai REFUTED no `--judge`

**Gravidade: alta** (falso positivo determinístico, não estocástico).

`hunt_scope_creep` cobra todo arquivo alterado que não esteja declarado.
A lista de alterados vem de `_changed_files` (`judge.py:721` no HEAD; `:659`
na v0.7.0), que soma `git diff` **mais os untracked** (`:751`; `:689`). O
`run_all` que re-executa lint/testes/coverage roda **depois** de a lista ser
capturada (`judge.py:1589`), mas os artefatos que ele deixa — `.coverage`,
`src/__pycache__/*.pyc`, `tests/__pycache__/*.pyc` — ficam na árvore e são
**vistos na execução seguinte**.

Sequência reproduzida em um repositório honesto, árvore limpa, sem
`.gitignore`, tarefa commitada, HEAD == base:

```
judge run 1: VERIFIED
judge run 2: REFUTED
   [high] scope_creep — 3 arquivo(s) alterado(s) não declarado(s)
   → .coverage, src/__pycache__/c.cpython-312.pyc,
     tests/__pycache__/test_c.cpython-312-pytest-9.1.1.pyc
   exit=1
```

Com um `.gitignore` que cubra `.coverage` e `__pycache__/`, o mesmo estado dá
VERIFIED nas três execuções. As três manifestações, medidas no HEAD (três
repositórios novos, um por caso, para evitar contaminação entre medições):

| `.gitignore` do projeto | Segunda execução |
|---|---|
| sem `.gitignore` | **REFUTED, exit 1** (`scope_creep [high]`, 3 arquivos) |
| cobre `__pycache__/` mas não `.coverage` | VERIFIED WITH CAVEATS, exit 0 (`scope_creep [medium]`, 1 arquivo) |
| cobre os dois | VERIFIED |

A primeira é a que quebra CI; a segunda é o caso mais comum num projeto Python
realista (ignora `__pycache__/`, esquece `.coverage`) e ainda produz uma
acusação falsa, só que em severidade média. Mas a contaminação é **anterior ao
`--judge`**:
`kata --check-only` — o entry point de CI que o §8.3 recomenda — deixa
`.coverage` e `__pycache__/` na árvore (verificado: `?? .coverage`,
`?? src/__pycache__/`, `?? tests/__pycache__/` depois de um `--check-only`
bem-sucedido). **No mesmo workspace**, um `--judge` posterior acusa os
artefatos que o `--check-only` acabou de criar: o juiz sai 1 sobre trabalho
honesto, sem que o agente tenha feito nada de errado. Isso cobre a sequência
de CI recomendada no §8.3 quando os dois passos compartilham a árvore (o caso
comum de um job que roda ambos), o fluxo local de pre-commit, e duas revisões
sucessivas do mesmo check-out. Um `--judge` em job separado, com check-out
limpo, começa a árvore do zero e não vê o problema — o que só confirma que a
falha é de estado residual no workspace, não do veredito.

O fenômeno **não é introduzido pelas correções desta rodada** — reproduz
idêntico em `230e81a`/v0.7.0. O que mudou é a relevância: o artigo agora
recomenda explicitamente o par `--check-only` + `--judge` como gating de CI e
PR (§8.3, §9.2.2, §3.3 da rodada anterior). E não há, no texto, uma única
menção a `.coverage`/caches como fonte de escopo — a mitigação existe apenas
para o estudo externo (`_clean_tool_caches`, `eval/external_study.py:281`,
chamado em `:503` e `:666`), o que é também a razão de os 48 runs medidos não
terem visto o problema: **o instrumento limpa a árvore antes de medir, e a
armadilha do s07 não tem `.gitignore` nem roda o juiz duas vezes.**

Impacto sobre as alegações publicadas:

- Não invalida as campanhas nem o estudo externo (que limpam a árvore), mas
  **contradiz a viabilidade prática como gate** que o §9.2.2 e o §8.3 afirmam
  para CI/pre-commit. O custo de 2 s por revisão continua verdadeiro; o que
  não é verdadeiro é que ele seja estável sem higiene de `.gitignore`.
- **A suíte de traps não protege contra isso**: nenhum dos 22 cenários tem
  `.gitignore` (verifiquei: zero arquivos `fixture/.gitignore`), o harness
  exclui só `.kata/` e `pyproject.toml` via `.git/info/exclude`
  (`eval/run_traps.py:192`), e nenhum cenário executa o juiz duas vezes (uma
  chamada, `:529`). É uma classe de falso positivo — "o passo anterior deixou
  artefato" — que o mecanismo de dois lados não vê.

Peço:

1. filtrar artefatos de ferramenta conhecidos (`.coverage*`, `coverage.xml`,
   `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `htmlcov/`) da lista de
   alterados, exatamente como `_ignored_code_files` (`judge.py:847`) já faz do
   lado dos *ignorados*, e como `_clean_tool_caches` já faz do lado do estudo;
2. ou, no mínimo, declarar a higiene de `.gitignore` como pré-requisito
   operacional nas §8.3/§9.2.2, com um cenário de trap que rode o juiz duas
   vezes (que falharia hoje) para transformar a garantia em regressão;
3. e uma frase no §9.2 dizendo que os artefatos de ferramenta são limpos
   antes da medição — hoje isso só está em `eval/results/README.md`, não no
   artigo, e é justamente o que separa a medição do uso real.

### N2. A defesa contra a âncora reescrita não vale no pre-commit local — o texto está correto, mas o §8.3 pode enganar

**Gravidade: baixa** (o texto acerta; falta uma referência cruzada).

Verifiquei as três variantes da evasão da âncora contra a versão avaliada e
contra o HEAD. **Todos os resultados batem com a §6.4**:

| Evasão | `230e81a` (avaliada) | HEAD |
|---|---|---|
| YAML + âncora movidos juntos (`git update-ref`) | VERIFIED (exit 0) | REFUTED (`baseline_tampering`, reflog) |
| Âncora apagada, `base_commit` do YAML movido | UNVERIFIABLE (exit 0) | UNVERIFIABLE (exit 0) |
| Âncora apagada e recriada no HEAD (reflog apagado) | VERIFIED (exit 0) | VERIFIED (exit 0) |
| A terceira, com `--trusted-base <base real>` | — | REFUTED (`weakened_checks`) |

A prosa da §6.4 ("moving both the YAML and the ref \ldots empties the diff
window, and the verdict is VERIFIED"; "Deleting the ref and editing the YAML
yields UNVERIFIABLE"; "Deleting and recreating the anchor erases its reflog
and still evades that check locally; `--trusted-base` closes it in CI") descreve
cada linha acima fielmente. Não há defeito de declaração.

O que peço é uma referência cruzada em **§8.3** (e na hipótese (1) da §9.2.2):
os bullets de CI/PR recomendam `--judge` "against the PR's baseline anchor",
mas não mencionam `--trusted-base`, que é a única defesa documentada contra a
recriação da âncora — e não existe para o pre-commit local, onde a ref
confiável não está disponível. Como o §4.1 e o §9.2.2 apresentam o gate como
utilizável "in routine pre-commit workflows", uma frase ali evitando que o
leitor trate a proteção local como equivalente à do CI é suficiente. A §6.4
está correta; o §8.3 é quem pode ser lido rápido demais.

### N3. `conflict_resolution` com qualquer texto não vazio desarma `spec_betrayal`

**Gravidade: baixa** (o custo já está declarado; falta dizer o que ele implica).

A correção `15ccb7a` era obrigatória: sem ela, toda correção honesta com
INTENT resolvido saía REFUTED — foi o que derrubou seis das 24 sessões do
estudo externo. O texto agora diz isso (§6, item *specification betrayal*; §9.2)
e o parágrafo de remediação do prompt manda resolver o conflito com o usuário
antes de editar e nunca escrever a resolução depois do veredito. Verifiquei o
mecanismo: `hunt_spec_betrayal` (`judge.py:1262`) só acusa quando
`all_agree: false` e `_resolucao_de_conflito` é vazio; **qualquer texto não
vazio é aceito**, e o próprio texto registra que a resolução é "accepted
without verification". Reproduzi:

- `all_agree: false` + `conflict_resolution: "resolvido conforme o usuário"` →
  VERIFIED, com a resolução listada como claim aceita sem verificação;
- `all_agree: false` + resolução vazia → REFUTED `spec_betrayal [high]`.

Ou seja: o construto passou de "pega discordância resolvida" (o falso positivo
que quebrava bug fixes) para "aceita qualquer resolução" (um falso negativo
trivial de desarmar, já que a resolução é autodeclarada). **O texto registra a
parte que importa** — a resolução vai para as claims aceitas sem verificação —
e o prompt de fase (não o artigo) já cobre o caso de escrever a resolução
depois do veredito. O pedido é uma única frase na §6.4 fechando o argumento: a
entrada *Plausible but false content* lista "a phase filled with plausible but
false content is graded followed"; um `conflict_resolution` de uma linha, aceito
sem verificação, é exatamente isso aplicado ao item mais caro da lista de
fraudes. Hoje o leitor precisa juntar §6, §6.4 e §9.2 para chegar lá.

### N4. O resumo ainda promete mais do que a §9.2 pode sustentar

**Gravidade: baixa** (calibração de linguagem).

O resumo diz que "the independent JUDGE review flagged the one case of
undeclared scope, while the sessions' own JUDGE runs falsely refuted six
honest fixes" — correto e honesto. Mas a frase imediatamente anterior, "found
no weakened tests in either condition", continua apoiada **no detector do
próprio JUDGE** (§9.2, métrica (b)), que o parecer da rodada 1 (M4) apontou
como instrumento circular e construto sintático estreito — e o manuscrito não
resolveu isso: não há inspeção manual, mutação, nem testes ocultos; a única
frase que vai além do detector é "the test bodies touched by the agents
remained genuine assertions" (§9.2), que **não é sustentada por nenhum
artefato arquivado** — os diffs das 48 sessões não estão em
`eval/results/external_study_sessions/` (só as task files). Peço remover ou
suportar essa frase, e qualificar "no weakened tests" com "according to the
JUDGE's detector", como a própria Tabela 4 já faz na legenda.

---

## 3. Estado das pendências da rodada 1

| Item (rodada 1) | Estado |
|---|---|
| M3 (baseline determinístico: CI + script de escopo + test smells) | **Pendente.** Nenhuma menção a `make test`, SonarQube, tsDetect ou mutação no texto. O argumento "Kata é mais rápido e estável que um LLM" continua sendo, na parte comparativa, um contraste com revisores LLM, não com o gate determinístico que um time já tem. |
| M4 (recall do detector medido de forma independente) | **Pendente, e agora com mais peso** — ver N4: a única medida de "0 weakened" continua sendo o detector, e a §9.2 acrescenta uma frase qualitativa sem lastro. |
| M6 (poder do estudo externo) | **Parcialmente endereçado pela transparência.** A §9.2 agora declara N=1, efeito piso, condições, reexecuções e o custo 9×; o título da subseção mudou para "feasibility, scope integrity, and execution overhead". O instrumento circular (métrica b) e a assimetria do task file sintetizado (o texto diz "identical in shape for both arms" — verifiquei no JSON: `declared_source: json` em 48/48, então a síntese é simétrica) permanecem, mas agora declarados. Aceitável como artigo de software; insuficiente como artigo de pesquisa. |
| M8 (dimensões neutras na Tabela 1) | **Pendente.** As dimensões continuam sendo "Executes / Shared core / Fraud / Audit / Self-verify", derivadas da arquitetura do Kata. O texto declara que a avaliação é do autor e que a comparação executada supersede a tabela — o que mitiga, mas não muda o fato de que "Self-verify: Yes" para Kata e "No" para todos os outros não é um critério do problema. |
| Menores 7–15 | **Abertos, em ordem decrescente de peso:** **7** (o corpo ainda chama o ciclo de "Karpathy Development Cycle" sem "inspired by"; a ressalva existe só na nota do `paper.bib`), **8** (mushin citado como "a private local project" no §9.1 — não verificável), **9** (o Fable Method não é declarado como não revisado por pares, embora as arXiv o sejam no §3.1) e **11** (a Figura 1 ainda sobrepõe "plan-first: stops after THINK" / "question: stops after FIT" à seta tracejada; rótulo em `paper.tex` l.630-631, confirmado na página 7 do PDF). **10, 12, 13, 14 e 15 são editoriais e baratos:** os três trabalhos de verificação ainda aparecem em §3.1, §4.4 e §10; o cabeçalho segue com "2026, 14:1" (l.57); as três menções à revista (l.154-155, l.435, l.2230) não citam o trecho das diretrizes; a §9.1 ainda relata as três execuções do trap suite; e o t05 (§9.2) já enquadra o aviso como limite do audit mecânico, mas sem chamá-lo de falso aviso. Todos estão na task `jserd-menores-7-15`. |

---

## 4. Consistência editorial (verificada nesta rodada)

- **Contagem de cenários:** o texto usa "19" para a avaliação (correto para
  v0.7.0; verifiquei: 19 diretórios em `eval/scenarios/` na tag) e menciona
  s20/s21/s22 como correções posteriores (§6, §6.4). Não há inconsistência.
  A suíte no HEAD tem 22/22 passando (rodei).
- **Tempos:** o resumo e a conclusão dizem "about one second" nos traps e
  "about two seconds" nos repositórios reais — confere com os JSONs (mediana
  Kata 0,99 s nos traps; 1,89 s de revisão no estudo). "9×" confere (49 s →
  442 s).
- **`session_judge_verdict` null em 48/48:** confere, e o texto explica a causa
  (o harness busca o banner `KATA JUDGE` na saída de texto; `:334`/`:443` do
  harness). Os 12 vereditos vindos das task files (6 V, 6 REFUTED por
  `spec_betrayal` só em claude-sonnet-5) batem com o que li nas task files.
- **`v0.7.0` como tag única:** a tag existe, é ancestral dos commits citados, e
  contém os harnesses. As correções `3cacc5a`/`15ccb7a`/`3454fc7` são
  **posteriores** à tag e o texto diz isso em cada caso. `--trusted-base` não
  existe em v0.7.0 e o texto não afirma que existe (cita-o como correção
  posterior) — confere.
- **Recomendação do parecer da rodada 1 (fixar a pontuação antes de nova
  campanha):** atendida na forma — as mudanças estão declaradas e a regra final
  está fixada; nenhuma nova campanha foi feita, o que o texto admite (a
  limitação do `UNVERIFIABLE` no formato dos agentes permanece, com a ressalva
  do claude-wizard no s12/s13).

---

## 5. O que mudaria a recomendação

| Nível | Exigência |
|---|---|
| **Mínimo para aceite (agora)** | N1 (item 3, a frase no §9.2, e o item 1 ou o 2 — filtrar os artefatos ou declarar a higiene como pré-requisito, com o cenário de trap que rode o juiz duas vezes) e N4 (qualificar "no weakened tests" e remover ou suportar a frase sobre "genuine assertions") |
| **Para um artigo forte** | N2 (referência cruzada do `--trusted-base` no §8.3), M3, M4 e M8 |
| **Pendências de publicação** | Depositar a release (Zenodo/Software Heritage) e citar o DOI; a ressalva do modelo dos agentes na §3.3 permanece (logs locais não arquivados) |

N2 e N3 não entram no mínimo porque **o texto já está correto nos dois casos**:
a §6.4 descreve fielmente as evasões que reproduzi, e o custo da resolução
autodeclarada está registrado como claim aceita sem verificação. São pedidos
de clareza — uma referência cruzada e uma frase de escopo —, não correções.

A engenharia e a transparência continuam acima da média, e a rodada 2 as
melhorou: a §6.4 é um modelo do que um artigo de ferramenta deve fazer com o
próprio ponto fraco. O problema remanescente é o mesmo da rodada 1, em escala
menor: **calibração entre o que foi medido e o que é afirmado** — agora entre
o que o instrumento mede (árvore limpa pelo harness) e o que o usuário
encontra (árvore que o próprio passo anterior sujou).

---

## 6. Tasks kata para esta rodada

| Task | Finding | Escopo |
|---|---|---|
| `.kata/jserd-n1-artefatos-ferramenta.yaml` | N1 | Código (filtro + teste + cenário de trap) **ou** texto (§8.3/§9.2.2), à escolha do usuário; §9.2 sempre |
| `.kata/jserd-n4-estudo-externo-calibrado.yaml` | N4 | Resumo, §9.2 e §11: qualificar pelo detector e remover a frase das "genuine assertions" |
| `.kata/jserd-n2-n3-clareza-6-4.yaml` | N2, N3 | §8.3, §9.2.2 e o item "Plausible but false content" da §6.4 |
| `.kata/jserd-menores-7-15.yaml` | Menores 7–15 | Introdução, §3.1, §4.4, §9.1, §9.2, §10, Figura 1, cabeçalho |

As quatro foram criadas com FIT, THINK e INTENT preenchidos (critério de pronto
declarado antes da edição, como manda o próprio ciclo) e audit limpo; execução
pendente. A N1 é a única que pode virar mudança de código — as outras três são
de texto. Se o usuário escolher o caminho (B) da N1 (só declarar a higiene de
`.gitignore`), a task vira docs e deixa de exigir `make test` como critério.

---

## 7. Como foi feita a verificação

- **Tabela 2 e Tabela 4 recomputadas** dos cinco JSONs em `eval/results/` e do
  `external_study.json` (48 runs). Re-pontuei as 57 células de agente de
  `compare_gates_round2.json` (0 divergências) e as 36 células substantivas de
  `compare_gates_final.json` (0 divergências; as 21 restantes são
  INCONCLUSIVE→LIMIT).
- **Suítes executadas:** traps no HEAD (22/22) e em `230e81a` (19/19);
  `make lint` e `make test` do repositório (899 passam, 98,61%).
- **Evasões reproduzidas fora do repositório**, em worktrees de `230e81a`,
  `3cacc5a` e HEAD: janela de diff vazia (VERIFIED → UNVERIFIABLE), as três
  variantes da âncora (movida, apagada, apagada-e-recriada), `--trusted-base`,
  e o par `--check-only`+`--judge`. A matriz das variantes da âncora foi
  refeita duas vezes: na primeira, um `approved_commit` residual de um teste
  anterior contaminou o resultado da variante conjunta, e a re-execução com
  estado limpo (três repositórios novos, um por variante) mostrou que **o texto
  da §6.4 estava certo** e a medição inicial é que estava errada — o achado
  saiu do parecer. Registro a sequência porque é exatamente o tipo de erro que
  este parecer cobra do autor; a mesma disciplina de "repositório novo por
  caso" foi aplicada à matriz de N1.
- **N1 reproduzido** em repositório honesto, árvore limpa, nas duas versões
  (avaliada e HEAD), com três `.gitignore` diferentes.
- **Task files das 24 sessões lidas** com `yaml.safe_load`; vereditos do JUDGE
  comparados ao que o texto afirma.
- **Figura 1 inspecionada** renderizada (página 7 do PDF).
- Não conferi: diffs das sessões externas (não arquivados), DOI (não
  depositado), e 5 dos 10 preprints arXiv (como na rodada 1).
