# Parecer editorial — JSERD

**Manuscrito:** *Kata: an executable quality gate for AI-assisted software changes*
**Autor:** W. A. Nagai
**Tipo declarado:** software article
**Data:** 2026-09-14
**Versão avaliada:** `paper/jserd/paper.pdf` (21 páginas), repositório no commit `189751c`
**Recomendação:** **Revisão maior (major revision)**

---

## 1. Síntese

O artigo apresenta o Kata, uma ferramenta em Python com dois frontends para agentes (OpenCode e
Claude Code). Ela organiza uma mudança de código num ciclo de nove fases e oferece um juiz
adversarial (JUDGE). O JUDGE re-executa lint, testes e cobertura, compara o arquivo de tarefa com
o `git diff` e procura sete categorias de "fraude". A avaliação tem três partes:

- **(a)** 19 cenários-armadilha escritos pelo próprio autor;
- **(b)** uma comparação executada contra nova, claude-wizard e um prompt simples, nos mesmos 19
  cenários;
- **(c)** um estudo externo com 12 bugs reais × 2 modelos × 2 condições (N=1 por célula).

**Pontos fortes:**

- Os artefatos são excepcionalmente abertos: harnesses, JSONs brutos e task files das sessões
  estão publicados.
- As Listings estão ancoradas em commit. As referências de linha foram conferidas e batem
  (`fit.py:23`, `verify.py:201-207`, `judge.py:728`, `judge.py:1377`, `cli.py:115`,
  `report.py:169`).
- Os commits `230e81a` e `6f56b35` existem, e `src/kata` não muda entre eles, como o texto afirma.
- A seção de ameaças é franca, e o artigo não afirma causalidade.
- As cinco referências arXiv conferidas existem e dizem o que é citado: SpecBench, Unreliable
  Progress Bar, Double Measurement Confound, Consort e TrajMark. A de SpecBench inclui o número de
  28 p.p.

**O problema central:** a evidência não sustenta a principal afirmação comparativa. E a afirmação
que ela sustenta ("um script determinístico é mais rápido e estável que um LLM revisor") é quase
trivial.

---

## 2. Questões maiores

### M1. A vantagem na comparação (§3.3) vem de convenções do próprio Kata, não de maior contenção

As 11 falsas acusações dos agentes na campanha citada (`compare_gates_round2.json`) se distribuem
assim:

| Origem | Falsas acusações |
|---|---|
| Cenários de ponto cego s12/s13/s19 (esperam `UNVERIFIABLE`, que o formato de resposta dos agentes **não permitia** declarar) | 7 |
| s17, que depende da semântica de `approved_commit`, convenção interna do Kata que os agentes não conheciam | 3 |
| bare em s07 | 1 |

Retirando os três cenários de ponto cego, o placar de acertos passa de 19 / 15 / 17 / 14 para
**16 / 15 / 15 / 14** (Kata / nova / claude-wizard / bare). Retirando também o s17, a diferença
se reduz a um único erro do baseline.

O texto reconhece as duas ressalvas: os cenários estão "dentro da distribuição" do Kata e o formato
não tinha `UNVERIFIABLE`. Mesmo assim, "zero falsas acusações" continua como achado principal no
resumo, na introdução, no §9.3 e na conclusão. O que peço:

- mover essa afirmação para o nível que a evidência permite;
- ou refazer a campanha com um formato de resposta que inclua `UNVERIFIABLE` e com a semântica de
  `approved_commit` informada no prompt.

### M2. Critério de pontuação revisado depois de ver resultados, sem declaração no texto

O diretório `eval/results/` tem **cinco** arquivos de campanha, não três:

- **`compare_gates.json`:** nova e bare acharam o debris real do s06 (`scratch/saida.tmp`) e mesmo
  assim foram pontuados como falsa acusação.
- **`compare_gates_refined.json`:** re-executa só os 8 cenários sem fraude plantada, com outro
  parser (`raw_decode`) e nova regra de pontuação para os nomes parecidos com debris do s06.
- **`compare_gates_merged.json`:** junta a rodada 1 com a refinada. Não é uma campanha
  independente, mas o intervalo "[min–max] across three campaigns" da Tabela 2 o conta como uma.
- **`compare_gates_final.json`:** rodada abortada pelo limite de gasto. O nome confunde com a
  campanha "final" que o artigo cita.

As correções parecem legítimas e até favoreceram os concorrentes. Ainda assim, uma regra mudada
depois de ver resultados precisa ser declarada. Peço:

- descrever todas as rodadas e as mudanças de parser e de regra;
- tirar a campanha "merged" do cálculo de variabilidade;
- idealmente, fixar a pontuação antes de uma nova campanha.

### M3. Falta um baseline determinístico, e a comparação escolhida é fraca demais para Kata perder

O Kata foi comparado apenas com revisores LLM. Determinismo, custo (0,1 s contra 16 s) e
estabilidade são propriedades de *qualquer* script comparado a *qualquer* LLM, não do Kata. O
baseline relevante para um *quality gate* é outro: CI comum (`make test`), mais um script que
compare arquivos declarados com o diff, mais um detector de test smells.

- Esse baseline pegaria s02, s03 e provavelmente s01, s10 e s11.
- A pergunta que o artigo precisa responder é **o que o Kata acrescenta em relação a esse
  baseline**.
- A literatura correspondente está ausente: quality gates industriais (SonarQube), detecção de
  test smells (p.ex. tsDetect, Peruma et al., ESEC/FSE 2020), testes de mutação (Jia & Harman, TSE
  2011) e benchmarks de agentes que alteram testes (p.ex. ImpossibleBench, 2025). Confirmar essas
  referências antes de citar.

### M4. O detector de testes enfraquecidos isenta justamente o padrão central de reward hacking

A *pair rule* K-01 (§4.4, Listing 6) diz que trocar `expect(x).toBe(1)` por `expect(x).toBe(2)` é
"modificação, não remoção". Mas mudar o valor esperado até o teste concordar com o código errado é
exatamente o fenômeno citado no §2 ("tests get weakened until they agree with the code"). Nenhum dos
19 cenários exercita esse caso.

O construto "weakened checks" é, portanto, **sintático e estreito**: pega `pass`, asserts
comentados e `assert True`. Não pega:

- afrouxamento de asserção (`==` virando `is not None`);
- troca de oráculo;
- asserções tautológicas não listadas.

Peço:

- declarar essa lacuna como ameaça à validade de construto;
- medir o recall do detector de forma independente, por exemplo com enfraquecimentos gerados
  automaticamente por operadores de mutação sobre suites reais.

### M5. Nenhum modelo de ameaça explícito para um juiz que se diz "adversarial"

Não se define quem é o adversário nem o que ele pode fazer. Considerando um agente com shell e
escrita no repositório:

1. **A saída 0 em `UNVERIFIABLE` é um caminho de evasão.** O próprio s19 mostra que um teste
   escondido por `.git/info/exclude` gera `UNVERIFIABLE` e passa no CI, e `cli.py:1659` confirma
   que isso é deliberado. Um agente pode fabricar pontos cegos para passar. Para um *gate*, falhar
   aberto ou fechado é decisão de política: deve ser configurável e discutida.
2. **A âncora `refs/kata/base/<sha>` fica no repositório que o agente controla.** O s14 testa só a
   edição do YAML. Um `git update-ref` também passaria?
3. **O audit só detecta `answered: true` com conteúdo *vazio* (Listing 7).** Conteúdo plausível mas
   falso é graduado como *followed*. A frase "A skill has no way to know whether a phase was faked;
   Kata does" (§7.1) promete mais do que o mecanismo entrega.
4. **O escopo depende do que o agente declara.** Basta declarar todos os arquivos alterados para
   neutralizar a detecção, e `necessary: true` é autodeclarado.

Peço um modelo de ameaça explícito e um experimento com **adversário adaptativo**: um agente
instruído a trapacear conhecendo o JUDGE. Sem isso, "adversarial" descreve a intenção, não uma
propriedade demonstrada.

### M6. O estudo externo (§9.2) não tem poder para o que o artigo quer mostrar

- **Efeito piso.** Zero testes enfraquecidos em 48 execuções, em ambas as condições. Com tarefas
  pequenas, bem isoladas e com testes de regressão visíveis, não há incentivo para trapacear, e o
  estudo não consegue distinguir as condições. SpecBench mede o fenômeno com testes *ocultos*; aqui
  todos os testes de aceitação são visíveis.
- **Instrumento circular.** A métrica (b) usa o detector do próprio JUDGE para medir
  enfraquecimento. Com o limite apontado em M4, "0 weakened" pode significar apenas "0 detectáveis
  por esse detector". É preciso uma medida independente: inspeção manual, mutação ou testes
  ocultos.
- **Condições assimétricas.** No braço bare o task file foi *sintetizado* pelo harness; no braço
  kata foi escrito pelo agente. Detectar escopo não declarado a partir de um JSON de declaração é um
  teste pouco exigente.
- **Seleção por reexecução.** Sessões com timeout ou limite de gasto foram reexecutadas, e as
  falhas foram descartadas (confirmado em `eval/results/README.md`). O braço kata é cerca de 9× mais
  longo, portanto mais exposto a timeout. Informe quantas reexecuções houve em cada braço.
- **O ciclo completo não foi observado.** O JUDGE de dentro das sessões não foi capturado
  (`session_judge_verdict` é null em todas as 48), então a condição "kata" não foi medida como é
  descrita.
- **Custo sem benefício medido.** O ciclo custa cerca de 9× na mediana, com pico de 19 min. O
  benefício "defensivo em tarefas complexas" (§9.2.2) é conjectura. As recomendações práticas
  ("Teams should deploy…") não se apoiam nos dados.

### M7. O título e o enquadramento prometem mais do que foi avaliado

O título fala de um *quality gate* e o artigo descreve um ciclo de nove fases. O que foi avaliado é
quase só o JUDGE, e só a variante determinística dele. O ciclo de autoria não tem avaliação além do
custo, e as fases de julgamento (THINK, SIMPLIFY, INTENT, SURGICAL, TWIN CHECK) não têm ablação.
Duas saídas possíveis:

- **(a)** focar o artigo no JUDGE como verificador de afirmações;
- **(b)** manter o escopo e acrescentar perguntas de pesquisa com avaliação correspondente.

Hoje o manuscrito não tem RQs explícitas. Sugestão de estrutura:

| RQ | Pergunta | Como medir |
|---|---|---|
| RQ1 | Recall | Fraudes injetadas por terceiros ou por mutação, fora dos 19 cenários |
| RQ2 | Taxa de falsas acusações | Centenas de commits reais honestos com task files sintetizados (o estudo externo já tem o harness) |
| RQ3 | Robustez | Adversário adaptativo (M5) |
| RQ4 | Custo-benefício do ciclo | Tarefas com incentivo real a trapacear |
| RQ5 | Contribuição de cada fase | Ablação |

### M8. A classificação da Tabela 1 é autoavaliada e parece construída para o Kata vencer

As dimensões "Shared core", "Audit" e "Self-verify" descrevem características do próprio Kata. Não
são critérios neutros do problema. Pontos específicos:

- **nova "Executes: No".** O plugin nova declara um *hook* que bloqueia commits sem PASS do
  Evaluator (exit 2), e o próprio §3.3 menciona o servidor MCP do nova. Pela definição do artigo
  ("runs checks and reads their exit codes") a classificação talvez se sustente, mas precisa de
  justificativa explícita.
- **Consort executa verificação** e fica fora da comparação executada por "escopo de banco de
  dados". É um argumento aceitável, mas indica que a comparação só incluiu o que dava para rodar no
  mesmo host.

Sugiro derivar as dimensões do problema (p.ex. do que SpecBench e a literatura de oráculo exigem),
não da arquitetura do Kata.

---

## 3. Questões menores

1. **Inconsistência nos graus do audit.** O resumo e a introdução falam em três (*followed,
   skipped, faked*); a Tabela 3 e o §7 têm quatro (*degraded*).
2. **Tempo de revisão com três valores.** "About one second" no resumo e no §3.3, "approximately
   two seconds" no §4, e cerca de 1,9 s com máximo de 116 s na Tabela 8. Padronizar e sempre dizer
   em qual carga foi medido.
3. **Coluna "Median output" da Tabela 2 (28 lines contra 1 line).** Não tem significado analítico:
   mede o formato JSON imposto aos agentes. Remover.
4. **"Orders of magnitude in time".** Retórica para uma diferença entre script e LLM (ver M3).
5. **Versões.** O §8 diz que as instruções refletem a tag `v0.6.0`, os harnesses estão em
   `6f56b35` e o resto em `v0.7.0`; as Declarações dizem que tudo está em `v0.7.0`. Unificar numa
   única tag, citada com DOI (Zenodo/Software Heritage).
6. **Modelo dos agentes na §3.3.** "Claude Code's default model" não é reprodutível. Informe modelo
   e versão exatos e a versão do CLI.
7. **"Karpathy Development Cycle".** Dar a um método o nome de quem não o definiu, com base numa
   palestra, é problemático. Sugiro deixar claro que o nome é do autor ("inspired by…").
8. **"mushin agent (a private project)".** Não é verificável. Remover ou justificar.
9. **O construto de fraude vem de repositório GitHub não revisado por pares** (Fable Method).
   Declarar isso como limitação.
10. **Redundância.** A revisão de trabalhos recentes aparece três vezes (§3.1, §4.3, §10); a
    comparação duas (§3.3, §9.3); "zero false positives, about one second" cerca de seis vezes. O
    §8 (manual do CLI) e boa parte das Listings 2–9 servem melhor à documentação ou a um apêndice.
    Hoje há mais descrição que avaliação.
11. **Figura 1.** Os rótulos pequenos se sobrepõem às curvas ("plan-first: stops after THINK /
    question: stops after FIT").
12. **Cabeçalho "2026, 14:1".** Placeholder de volume num manuscrito submetido.
13. **Categoria "software article".** O texto afirma duas vezes que "the journal's guidelines
    request…". Cite o trecho exato das diretrizes vigentes do JSERD. A formulação lembra
    JOSS/SoftwareX, e se a categoria não existir o artigo será avaliado como artigo de pesquisa, com
    exigência empírica maior.
14. **Execuções repetidas de código determinístico.** Rodar a suíte três vezes não é evidência
    estatística. Basta dizer que a saída é determinística.
15. **Aviso do audit no t05.** A discussão sobre dívida técnica prévia (`baseline_failures`) é boa,
    mas mostra um falso aviso prático do audit. Apresente como tal.

---

## 4. O que mudaria a recomendação

| Nível | Exigência |
|---|---|
| **Mínimo para aceite** | M1, M2, M7 (reenquadramento e honestidade nos números principais) e M5 (modelo de ameaça escrito, mesmo sem experimento), mais as questões menores 1–6 |
| **Para um artigo forte** | Baseline determinístico (M3), recall medido de forma independente com mutação (M4), taxa de falsas acusações em commits reais em escala (RQ2) e um experimento com adversário adaptativo (M5) |

A engenharia e a transparência são acima da média. O problema é de **calibração entre o que foi
medido e o que é afirmado**, e isso tem conserto.

---

## 5. Como foi feita a verificação

- Referências de linha, commits e tags conferidos no repositório.
- Tabela 2 recalculada a partir dos cinco JSONs brutos em `eval/results/` (origem de M1 e M2).
- 5 dos 10 preprints arXiv conferidos em arxiv.org; os outros cinco não foram checados.

## 6. Tasks kata para o mínimo de aceite

| Task | Finding |
|---|---|
| `.kata/jserd-m1-comparacao-calibrada.yaml` | M1 |
| `.kata/jserd-m2-campanhas-divulgadas.yaml` | M2 |
| `.kata/jserd-m5-modelo-ameaca.yaml` | M5 (texto) |
| `.kata/jserd-m7-enquadramento-rqs.yaml` | M7 |
| `.kata/jserd-menores-consistencia.yaml` | Menores 1–6 |
