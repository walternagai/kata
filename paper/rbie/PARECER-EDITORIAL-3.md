# Parecer editorial, rodada 3 — RBIE

**Versão avaliada:** commit `a2f82fb` (16 páginas, cerca de 13 de corpo, 7.914 palavras)
**Decisão:** revisão maior, condicionada a E3-21 e E3-23; o restante é menor
**Task:** `.kata/rbie-revisao-editorial-rodada3.yaml` (23 achados: 10 médios e 13 baixos; 9 `[R]` e 14 `[E]`)

Nenhum achado novo bloqueia a publicação. Os dois de maior impacto vêm das rodadas anteriores (literatura nacional e acesso à verificação técnica da ferramenta).

## Correções (erros que as últimas mudanças introduziram)

| ID | Problema |
|---|---|
| E3-1 | A Seção 5 diz que responde à QP3; depois da renumeração é a QP1 (e a Seção 6 responde à QP2). |
| E3-2 | Seção 4: o registro e a graduação do adaptador ausente seguem descritos como automáticos; quem registra e carrega é o agente (pendência de E2-6). |
| E3-3 | O caso 7 é indicado para o primeiro teste, mas o artigo diz que o kata não dispensa fases e o protocolo só usa os casos 1 e 2. |
| E3-4 | Introdução: "estudantes que não tinham dificuldade aceleraram" — a fonte diz "alguns". |
| E3-5 | Caso 5 remete à seção errada. |
| E3-6 | Frase sem fonte na primeira linha; "o nome é da autoria do kata" é ambíguo. |
| E3-7 | A informação "o kata não tem comando para dispensar fases" se repete três vezes. |

## Estrutura e leitura

- **E3-8** O corpo é 33,8% ferramenta (O Kata 24,1% mais Domínios 9,7%), contra 7,4% de fundamentação pedagógica e 2,6% de discussão. Mover as Execuções 2 a 5 para o Apêndice A e ampliar a parte pedagógica.
- **E3-9** As Execuções 2 a 4 usam JUDGE e auditoria antes de as Seções 3.6 a 3.8 os definirem.
- **E3-10** O arquivo de tarefa é explicado antes da execução que o gera.

## Protocolo

- **E3-11** Retenção medida "ao fim"; a fonte citada (Kazemitabaar et al., 2023) mediu após uma semana. Propor pós-teste adiado.
- **E3-12** A rubrica da H1 não existe (dimensões, escala, treino, kappa-alvo).
- **E3-13** Agente, modelo e versão não constam entre as ameaças.
- **E3-14** Ética: quem recruta e colhe o consentimento deveria ser quem não avalia.
- **E3-15** A H2 depende da qualidade dos testes ocultos e de proporções supostas.

## Execuções e demonstrações

- **E3-16** Verificado nesta rodada: sem a importação sobrando, o JUDGE acusa só `weakened_checks` e o lint passa, então a frase da Execução 3 é verdadeira, mas não reproduzível a partir de `demos/`. A "primeira tentativa" sem `ruff` e `pytest` também não está lá.
- **E3-17** As execuções cobrem 2 dos 5 domínios.

## Forma e template

- **E3-18** 11 caixas estouram a largura (9 em tabelas, de 6 a 30 pt).
- **E3-19** Resumos com 281, 251 e 288 palavras (limite de 300); faltam palavras-chave de domínio.
- **E3-20** Tabelas renumeradas; documentos de revisão antigos citavam os números anteriores (resolvido: agora citam pelo nome da tabela).

## Referências e pendências

- **E3-21** Literatura nacional e busca declarada (E1-3 e E2-4).
- **E3-22** Fable e Karpathy sem commit, data de acesso e transcrição; dedução sobre Garousi et al. ainda no texto.
- **E3-23** A validade da ferramenta depende de um manuscrito inacessível (E2-3).

**Pendências das rodadas anteriores ainda abertas:** E2-8 (resumos destacam cinco domínios, quatro sem avaliação), E2-9 (casos de uso sem consulta a docentes).

---

## Resposta da autoria: correções diretas (E3-1 a E3-7)

| ID | O que foi feito |
|---|---|
| E3-1 | A Seção 5 responde à QP1; a Seção 6 abre dizendo que responde à QP2. |
| E3-2 | Seção 4: a instrução manda o agente carregar o adaptador e registrar a falta; a auditoria marca `preflight` como degradado ao ler o registro; o agente pode omiti-lo; domínio desconhecido gera aviso do pacote. |
| E3-3 | Conclusão e Caso 7 alinhados ao protocolo: primeiro teste nos casos 1 e 2. |
| E3-4 | "Alguns estudantes que não tinham dificuldade aceleraram o trabalho". |
| E3-5 | Caso 5 remete às Execuções 1 e 4. |
| E3-6 | Primeira frase com apoio em Finnie et al.; "o nome foi dado pelo projeto kata". |
| E3-7 | A afirmação sobre dispensar fases fica na tabela e no Caso 7; frase do Caso 1 dividida. |

**Ainda abertos:** E3-8 a E3-23 (estrutura, protocolo, execuções, forma e referências). E3-8 e E3-9 pedem decisão da autoria (mover as execuções para o apêndice e reordenar a Seção 3).

---

## Resposta da autoria: decisões E3-8 e E3-9 (confirmadas)

| ID | O que foi feito |
|---|---|
| E3-8 | Execuções 2 a 5 (Listagens 4 a 7 e a tabela de execuções) movidas para o **Apêndice A**; o corpo tem um parágrafo-resumo. A fundamentação pedagógica ganhou três parágrafos (fases e dificuldades de iniciantes, com Prather et al., 2024; reflexão na ação, com Edwards, 2004; riscos pedagógicos da própria ferramenta) e a discussão, dois (o que o artigo não responde; condições para uma primeira adoção). |
| E3-9 | Nova ordem da Seção 3: ciclo, verificador, auditoria, limites conhecidos, Execução 1, arquivo de tarefa, fluxos de uso. |
| E3-10 | Resolvido pela reordenação: a Execução 1 antecede o arquivo de tarefa que ela gera. |

O corpo continua com cerca de 12 páginas (mínimo do template: 10), e o apêndice não entra na contagem.

**Ainda abertos:** E3-11 a E3-23 (protocolo, demonstrações, forma e referências).

---

## Resposta da autoria: E3-11 a E3-23

| ID | Situação | O que foi feito |
|---|---|---|
| E3-11 | feito | H3 mede a retenção depois de um intervalo fixado antes da coleta (por exemplo, uma semana, como em Kazemitabaar et al., 2023). |
| E3-12 | feito | Rubrica da H1 com cinco dimensões, notas de 0 a 2 com âncoras, treino em 10 registros do piloto e kappa-alvo fixado antes. |
| E3-13 | feito | Deriva do agente nas ameaças: mesmo agente, modelo e versão nas duas condições, registrados a cada entrega. |
| E3-14 | feito | Recrutamento por quem não avalia; recusa sem prejuízo; registros pseudonimizados; docente só vê agregados depois das notas. |
| E3-15 | feito | Testes ocultos validados por uma segunda pessoa; proporções calibradas no piloto. |
| E3-16 | feito | `reproduzir.sh` com a variante sem importação (só `weakened_checks`, lint limpo) e a primeira tentativa sem `ruff` e `pytest`. |
| E3-17 | em parte | Execução 6 (`data-analysis`) no Apêndice A, reproduzível; infraestrutura e pesquisa seguem sem execução. |
| E3-18 | feito | De 11 avisos de largura para 2 (1,5 pt numa tabela e os 66 pt do template). |
| E3-19 | feito | Resumos com 272, 243 e 277 palavras; palavra-chave "Ensino de Software". |
| E3-20 | feito | Documentos de revisão citam as tabelas pelo nome. |
| E3-21 | em parte | Busca exploratória declarada e quatro trabalhos nacionais conferidos no Crossref; lacuna qualificada. Sem busca sistemática. |
| E3-22 | em parte | Fable com commit e data de acesso; Karpathy com nota sobre a fonte; inferência de Garousi marcada. Falta a transcrição. |
| E3-23 | decidido pela autoria | Sem acesso ao manuscrito, aos cenários nem ao `run_traps.py`; ponteiros removidos. A Seção 3 passa a se declarar descrição da autoria, sem evidência independente, e a validade interna registra o limite. |

**Ainda abertos:** o que depende da autoria (acesso ao outro manuscrito, E3-23), de trabalho sistemático (busca, E3-21), de transcrição (E3-22) e de novas execuções (infraestrutura e pesquisa, E3-17), mais E2-8 e E2-9.

---

## Decisão da autoria sobre E3-23

A autoria **não dará acesso** ao manuscrito do JSERD, aos cenários adversariais nem ao `run_traps.py`. O artigo foi ajustado: saíram o ponteiro para os cenários e o comando, os identificadores de cenário da tabela de desvios, a frase sobre os cenários no Caso 2 e o manifesto de 12 tarefas no Caso 4. Em troca, a Seção 3 diz que é declaração da autoria, a introdução diz que o manuscrito não é disponibilizado nesta submissão e a validade interna registra que o leitor só pode reexecutar as seis execuções de demonstração.

**Efeito editorial:** a validade da ferramenta continua sem evidência acessível ao revisor (E2-3 e E3-23). É a principal fragilidade do artigo e fica declarada, não resolvida. Ao julgar a proposta, a editoria deve tratar a descrição do verificador como intenção de projeto e as execuções de `demos/` como ilustração.


---

## Resposta da autoria: decisões sobre os itens abertos e parciais

| Item | Escolha | O que foi feito |
|---|---|---|
| Literatura (E1-3, E2-4, E3-21) | 1A | Busca sistemática curta no SOL (SBIE, WEI, EDUCOMP, EDUCOMP estendido) e na RBIE (pelo Crossref, porque o site da RBIE devolve "Nenhum resultado encontrado" até para "programação"): 8 *strings*, 2022 a 2026, 126 registros, 75 distintos, 52 no período, 27 incluídos. Protocolo, triagem e código em `busca/`. Limites declarados. |
| Domínios (E2-8) | 2A | Os resumos dizem que as regras específicas dos quatro adaptadores são instruções ao agente e não foram avaliadas. |
| Casos de uso (E1-9, E2-9) | 3A | Corpo limitado aos casos 1 e 2 (os do protocolo); casos 3 a 8 em "Extensões". |
| Densidade (E2-10) | 4A | 45 reescritas em `PROPOSTA-FRASES.md`, **aprovadas e aplicadas**; as frases acima de 40 palavras caíram de 29 para 10, quase todas enumerações. |
| Template e título (E2-11) | 5A | Título "para Apoiar o Ensino de"; Tabela dos domínios dividida em duas, em `\small`. |
| Voz (E1-15, E2-13) | 6B | Primeira pessoa do plural no texto; "a autoria" só nas declarações. |
| Karpathy (E1-13, E3-22) | 7B | A palestra saiu; a fonte passou a ser o repositório MIT no GitHub que extraiu as quatro diretrizes e liga ao post original no X. |
| Anonimização (E1-12, E2-13) | 8C | Na submissão, "serão disponibilizados após o aceite", sem URL. Sem DOI do commit. |
| Domínios sem execução (E3-17) | 9A | Execução 7 (`devops`, com `docker compose config`) e Execução 8 (`research`, DOIs conferidos no Crossref): os cinco domínios têm execução real. |

**Ainda aberto:** nada que dependa de decisão. Decididos pela autoria, sem ação: E2-3 e E3-23 (sem acesso ao manuscrito e ao material da verificação), E2-7 (só o arquivamento da demonstração).
