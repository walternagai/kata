# Carta ao autor — decisão editorial

**Manuscrito:** "Kata: an executable quality gate for AI-assisted software changes" (`paper.tex`)
**Periódico:** JSERD (tipo Software)
**Decisão:** revisão maior (major revision)

Prezado Dr. Nagai,

Agradeço a submissão ao JSERD. Li o manuscrito integralmente. Minha decisão é **revisão maior (major revision)**.

O trabalho tem mérito. Os pontos fortes são o threat model franco, com evasões reproduzidas, e a decisão de projeto de confessar o que não se observou (UNVERIFIABLE). Há também o registro transparente das mudanças de regra de pontuação e a disciplina de provar que cada teste novo falha sem a correção. Os instrumentos corrigidos nos estudos (medição por delta contra falhas pré-existentes, estado-base no prompt do juiz) são reutilizáveis.

O problema é o critério do tipo Software: demonstrar "significant advance over previously published software", em geral por comparação direta. Hoje a evidência que sustenta esse avanço é circular, fraca ou medida numa versão que o próprio texto diz estar corrigida.

## 1. Pontos que precisam ser resolvidos

**1.1 Versão avaliada.** Os resultados vêm de `230e81a` (0.6.0). A tag é `v0.7.0` e o pacote é `0.7.2`. Comparação e estudo externo rodaram em `6f56b35`. Três correções posteriores (`15ccb7a`, `3cacc5a`, `3454fc7`) alteram o comportamento do JUDGE, e o suite passou de 19 para 24 cenários. O leitor não sabe a que versão cada afirmação se aplica, e o texto admite que a correção do falso positivo foi "stated, not measured" (l. 2340–2342). Peço que congele uma release, re-execute todas as avaliações nela e a arquive com DOI (Zenodo) já na revisão.

**1.2 Validade do contrato de dois lados (RQ1).** Os 19 cenários foram escritos pelo autor, cada um motivado por um defeito encontrado no JUDGE (l. 1951–1954). São fixtures de regressão, e 19/19 é verdadeiro por construção. Peço:
- um conjunto de cenários escrito por terceiros, ou por um red-team LLM sem acesso ao código;
- precision/recall com intervalo de confiança;
- um corpus real de commits que enfraquecem testes, minerado de históricos públicos, para estimar recall fora da distribuição.

**1.3 Comparação com gates relacionados (RQ2).** A paridade de detecção é o achado, e determinismo e velocidade são consequência quase tautológica de um script contra um LLM. Além disso:
- Os braços não são pontuados da mesma forma. O Kata é pontuado por veredito exato e os agentes por JSON binário sem UNVERIFIABLE. O wizard foi "correto" em s12 e s13 respondendo "sem fraude", quando o esperado era UNVERIFIABLE (l. 593). Isso contradiz o argumento de que agentes não podiam confessar.
- Há N=1 por gate, regras de pontuação alteradas após ver os resultados e modelo não registrado na execução. nova e claude-wizard foram emulados como prompts, e não rodaram em seus fluxos nativos.
- A comparação de tempo (0,1 s contra 16–40 s) usa fixtures com suítes quase vazias. Em repositórios reais o JUDGE levou até 116 s (l. 2281). Não há custo em tokens ou dólares dos agentes.
- Faltam baselines executáveis reais: CI com checks obrigatórios, pre-commit, mutation testing. O baseline "determinístico" (l. 617) é um grep de padrões.

Peço refazer a comparação com UNVERIFIABLE disponível a todos, k≥5 execuções por cenário, modelos registrados, custo reportado e ao menos um ablation (JUDGE sem as partes executáveis contra revisor prompt-only com as mesmas ferramentas).

**1.4 Falso positivo em código real.** O único dado de FP do JUDGE em código não escrito pelo autor é 6/12 refutações indevidas nas sessões do estudo externo (l. 2330–2346). O "47/48 sem falsas acusações" vem de task files sintetizados sem desacordo de intent, o que exclui por construção o caso que falhava. Esse dado deve estar no abstract e na discussão como resultado principal, e não numa subordinada.

**1.5 Estudo externo (RQ3).** Há efeito teto (48/48 passam) e N=1 por célula. A métrica de testes enfraquecidos usa o detector sintático do próprio JUDGE, o que o texto reconhece como circular (l. 2757–2763). Peço também:
- Discutir **contaminação**. tomli, idna, pyflakes e more-itertools são repositórios públicos populares, e os commits de correção provavelmente estão nos dados de treino dos modelos. Reinicializar o histórico não resolve. Use tarefas posteriores ao cutoff ou meça a memorização.
- Quantificar ou ao menos limitar o viés de seleção das re-execuções por timeout, que atinge mais o braço kata (l. 2357–2363).
- Reconhecer que os testes de aceitação já pré-aplicados facilitam a tarefa em relação ao uso real.

**1.6 Escopo da afirmação sobre o ciclo.** Só FIT, VERIFY e JUDGE são executáveis. As outras seis fases são skills e respondem a prompts `[Y/n]` ao próprio agente (l. 1270–1280). Isso é autoatestação, o problema que o artigo critica. A frase "Kata is not a skill" (l. 2846) contradiz a Figura 1. As fases de julgamento foram avaliadas só em custo. Ou realize um ablation, ou restrinja título, abstract e conclusão ao que foi medido (o JUDGE e as fases VERIFY/FIT).

**1.7 Adversário adaptativo.** O adversário do threat model é um agente que escreve o código e o task file, o mesmo cenário de reward hacking que motiva o trabalho. O artigo reproduz bypasses que dão VERIFIED sobre teste enfraquecido (l. 1612–1644), um deles atingindo a demonstração da Seção 5 (l. 1537–1542). UNVERIFIABLE sai com exit 0 e é manufaturável (l. 1645–1650). Deixar a avaliação contra um adversário adaptativo como trabalho futuro deixa a tese central sem teste. Peço ao menos um estudo piloto com um agente instruído a evadir o JUDGE, relatando a taxa de evasão.

**1.8 Estudos Gauntlet (RQ4).**
- O fork é descrito como separado da versão avaliada (l. 2410), mas a seção Declarations não dá commit nem artefato dele.
- "Pre-registered" (l. 2387, 2440) não tem registro ou timestamp verificável.
- A direção do resultado inverte. No piloto o loop vence o ciclo por 4–4–0. Na campanha o ciclo vence o loop por 1–5–4. O texto afirma que a campanha "reproduz" o piloto, e isso é ruído, não replicação.
- Com 21/30 empates, zero eventos em todas as métricas e N=1 por célula, o estudo não tem poder para "remover explicações alternativas" (l. 2587–2589). A conclusão correta é "inconclusivo", não "nulo".
- Há um único juiz LLM por par, sem modelo declarado nem teste de viés de posição ou de autopreferência. Um caso de execução fabricada foi confirmado e os outros 23 julgamentos não foram reinspecionados (l. 2617–2622).

Recomendo mover o Gauntlet para outro manuscrito, ou reduzi-lo a um apêndice marcado como exploratório e inconclusivo. Isso também encurta o artigo, que hoje mistura descrição da ferramenta, quatro avaliações e um threat model.

## 2. Pontos menores

- **Abstract.** São cerca de 430 palavras, com muitos números e contra-ressalvas. Reestruture em problema, solução, evidência e limites.
- **Tabela 1.** As dimensões definidas no texto (Executes, Shared core, Fraud, Audit, Self-verify) não coincidem com as seis colunas da tabela. A tabela mostra o Kata com "Yes" em todas, avaliado pelo próprio autor. Alinhe as definições às colunas.
- **Literatura.** Preprints de 2026 "validam" a decisão de projeto (l. 396), o que é overclaim. Falta trabalho sobre manipulação de testes por LLMs (benchmarks de "impossible tasks", por exemplo), mutation testing, assurance cases e atestação de proveniência (in-toto/SLSA).
- **Marcadores internos.** "K-13", "R14", "R7-1" e "K-01" nos listings e no texto não significam nada para o leitor. Remova ou explique.
- **Listing 6.** A numeração das linhas está quebrada ("19 4 flush", "5", "6"). As referências `arquivo.py:linha` ficam obsoletas a cada commit. Prefira nomes de função.
- **Saídas da CLI.** As saídas citadas foram traduzidas do português (l. 1231). O leitor não vê a saída real. Mostre a original ou torne o idioma configurável.
- **Redundância.** A ressalva da comparação aparece no abstract, na introdução, nos resultados, na discussão, na conclusão e nas ameaças. A Seção 7.4 repete a 3.3. Consolide em um único lugar e referencie.
- **Estrutura.** "Executed gate comparison" fica dentro de State of the Field, mas depende de definições da Seção 7.
- **Afirmações sem suporte.** "Dogfooded in production" (l. 2811) e "faster than any developer can review" (l. 85, 243) precisam de dados ou citação.

## 3. Resumo dos pedidos

| Prioridade | Pedido |
|---|---|
| Obrigatório | Release congelada, avaliações re-executadas nela, DOI |
| Obrigatório | Conjunto de cenários independente e precision/recall com IC |
| Obrigatório | Comparação refeita (UNVERIFIABLE para todos, k≥5, custo, baselines executáveis, ablation) |
| Obrigatório | FP 6/12 como resultado principal |
| Obrigatório | Discussão de contaminação no estudo externo |
| Obrigatório | Escopo da afirmação ajustado ao que foi medido (JUDGE, não o ciclo inteiro) |
| Obrigatório | Piloto com adversário adaptativo |
| Obrigatório | Gauntlet fora do corpo principal ou rebaixado a inconclusivo |
| Desejável | Abstract, redundâncias, Tabela 1, marcadores internos, Listing 6, saídas originais |
| Desejável | Literatura adicional |

Fico à disposição para esclarecer qualquer ponto. Peço que a resposta venha com uma carta ponto a ponto e uma versão marcada do manuscrito.

Atenciosamente,
Editor Associado, JSERD
