# Verificação de citações e tabelas — paper/rbie/main.tex

> **Nota (rodada 3):** as tabelas do estudo externo, dos cenários e da comparação de portões, e a Figura 2, foram retiradas do artigo. A conferência dessas tabelas abaixo vale para a versão anterior e fica como registro; as referências e as demais tabelas continuam válidas.

Método: Chain of Verification, variante *factored* (afirmação extraída → pergunta atômica → resposta contra a fonte
primária, sem reler o texto do artigo). O `/fact-check` não existe entre as skills desta sessão; o equivalente foi feito
à mão com resumos oficiais (Crossref, Semantic Scholar, arXiv), páginas dos repositórios, buscas na web e o próprio
repositório do kata. **Limite:** só resumos foram lidos para os artigos pagos; o que depende do corpo do artigo está marcado.

## Referências (42 afirmações citadas)

| Chave | Afirmação no artigo | Fonte conferida | Veredito | Ação |
|---|---|---|---|---|
| Finnie2022 | modelo supera a maioria dos estudantes em provas introdutórias | resumo: "Codex outscores most students" | Correto; "duas provas" não constava no resumo | Removido "duas" |
| Prather2023 | relatório de grupo de trabalho | resumo: 71 artigos, levantamento em 20 países, 22 entrevistas, ética | Impreciso ("riscos e recomendações") | Reescrito com o conteúdo do resumo |
| Denny2024 | "currículo precisa mudar sem abandonar leitura e verificação" | resumo de uma linha: desafios e oportunidades | **Não sustentado** | Reescrito para o que o resumo diz |
| Prather2024 | quem tem menos metacognição se beneficia menos | resumo: dificuldades persistem e a IA pode agravá-las; 21 sessões | Subestimava o achado | Reescrito |
| Becker2023 | oportunidades e desafios da geração de código | resumo: position paper, CS1 | Correto | — |
| Lau2023 | curto prazo restringir, longo prazo incorporar | resumo: curto prazo coibir fraude; longo prazo **dividido** entre proibir e integrar; 20 docentes | **Incorreto** | Corrigido |
| Daun2023 | discussões análogas em eng. de software | resumo: position paper de ChatGPT em ES | Correto | — |
| Kazemitabaar2023 | sem prejuízo imediato | resumo: 69 iniciantes; maior desempenho em autoria; modificação manual sem queda | Correto, vago | Precisado |
| Prather2023b | dificuldades de interação com Copilot | resumo: dificuldades cognitivas e metacognitivas | Correto, vago | Precisado |
| Hellas2023 | respostas em parte úteis, em parte imprecisas | resumo: ~90% acham ao menos um problema real; 40% de falsos positivos | Correto | — |
| Denny2024b | atividades de compreensão de código e prompts | resumo: EiPE + LLM | Correto | — |
| Keuning2018 | maioria aponta erros, poucas orientam o passo seguinte | resumo: 101 ferramentas; idem | Correto | — |
| Edwards2004 | avaliar testes dos estudantes → reflexão | resumo: idem | Correto | — |
| Spacco2006 | ensinar TDD "com servidor de entregas" | resumo: experiência com testes dos alunos, incentivos, limites da cobertura | Parcial (servidor não consta) | Reescrito |
| Kratzke2019 | estudantes enganam corretores | resumo: 190 estudantes, 3300 submissões, 4 truques | Correto | — |
| Black1998 | efeitos substanciais; definição de retorno pela lacuna | busca: efeitos 0,4–0,7; "comparação de níveis real e de referência" | Correto | — |
| Hattie2007 | três perguntas (aonde vou / como estou / o que vem) | busca: confirma o modelo; o resumo oficial não o traz | Correto (corpo do artigo, via fontes secundárias) | — |
| Wood1976 | andaime "retirado conforme avança" | busca: definição = assumir elementos além da capacidade; *fading* é literatura posterior | **Atribuição indevida** | Fading separado, sem atribuir a Wood |
| Biggs1996 | alinhamento construtivo | não conferido nesta sessão (conhecimento prévio) | Plausível | Conferir antes de submeter |
| Anderson2001 | seis processos da taxonomia revisada | conhecimento prévio; a **Tabela 1 usava "Transferir" e "Comunicar"**, que não são categorias | Tabela errada | Trocado por Aplicar/Avaliar/Criar |
| Garousi2019 | lacunas entre cursos e indústria | resumo: SLR de 35 estudos; testes entre lacunas e entre habilidades mais importantes | Correto | — |
| Barr2015 | "teste que passa vale o oráculo" | resumo: survey do problema do oráculo | Inferência nossa, não da fonte | Marcada como dedução |
| SpecBench2026 | 28 p.p. por 10x em código | arXiv: confirma literalmente | Correto | — |
| Huang2024 | LLMs não se autocorrigem sem retorno externo | arXiv: confirma | Correto | — |
| Manheim2019 | lei de Goodhart | arXiv: variantes de Goodhart | Correto ("aplicada ao código" é extensão nossa) | — |
| Jimenez2024 | SWE-bench, issues reais | arXiv: 2.294 problemas, 12 repositórios | Correto | — |
| Kapoor2024 | custo, não só acurácia | arXiv: confirma | Correto | — |
| Fable2026 | portões de ajuste/intenção/verificação, como texto de prompt | README: skills em Markdown, não código | Correto | — |
| Karpathy2026 | "Ciclo de Desenvolvimento de Karpathy" (4 princípios) | buscas: a palestra trata de engenharia agêntica (spec, revisão de diff, evals); os 4 princípios são o nome que o README do kata adota | **Atribuição excessiva** | Reescrito: nome é do kata |
| Wohlin2012 | quase-experimento; 4 validades | busca: ambos presentes | Correto | — |
| Bispo2020, SBC2024, Lei 14.874, CNS 510 | contexto e conformidade | copiados do template oficial | Não reconferidos | — |

## Tabelas

| Tabela | Conferência | Resultado |
|---|---|---|
| Cenários (19) | `ground_truth.yaml` s01–s19 | 11/1/4/3 — confere |
| Estudo externo | recomputado do `external_study.json` | Todas as células conferem (contagens, medianas, faixas) |
| Veredito das 24 sessões kata | `judge:` nos `.kata/*.yaml` | 12 com veredito: 6 VERIFIED, 6 REFUTED (todas claude, `spec_betrayal`) — confere |
| Auditoria (151/13/1) | `external_study_audit.json` | Confere |
| Comparação de portões | `compare_gates_round2.json` | Detecção, corretos, falsos positivos e medianas conferem; **tempo do determinístico não consta no JSON** → "N/A" |
| Desvios do JUDGE | `git log` dos commits 3cacc5a, 3454fc7, 15ccb7a; código de `judge.py` | Confere |
| Rubrica (riscos) | `_AUDIT_RISKS` em `report.py` | Confere (tradução; "spec" por extenso) |
| Bloom (Tabela 1) | — | **Corrigida** (ver acima); a atribuição segue sendo interpretação |
| Casos de uso | flags de `--help` e código | Comandos existem. **Corrigido:** `skipped` só é marcado em execuções não interativas; não há comando para dispensar fases. FIT "trivial" exige confirmação da pessoa |

## Achados sobre o próprio kata (fora do escopo do artigo)
- FIT conta `.kata/*.yaml` não ignorado como arquivo alterado (ver memória do projeto).
- A auditoria grada como `seguida` um INTENT com `all_agree: false` e `conflict_resolution` vazio.

---

## Atualização (rodada 4)

**Saíram do artigo:** a palestra de Karpathy (`Karpathy2026`) e o mapeamento de Sousa e Silveira (`Sousa2026`, fora dos veículos da busca sistemática). As conferências deles acima ficam como registro histórico.

**Entraram e foram conferidas** (resumo oficial no SOL ou no Crossref; só o início do resumo foi lido para alguns):

| Chave | Afirmação no artigo | Fonte conferida | Veredito |
|---|---|---|---|
| KarpathySkills2026 | Repositório de terceiros que extrai quatro diretrizes de observações de Karpathy | README no GitHub (licença MIT; liga ao post original no X; quatro princípios com os nomes citados) | Correto; o autor aparece como o nome de usuário e o repositório mudou de dono |
| Silva2024 | Revisão sobre estratégias pedagógicas com IA generativa | Resumo (SBIE 2024) | Correto |
| Bedin2025 | Mapeamento de 52 estudos, três papéis da IA generativa | Resumo (SBIE 2025) | Correto |
| Camilo2026 | Mapeamento de 18 estudos sobre POO | Resumo (WEI 2026) | Correto |
| SilvaCaceffo2023 | Códigos corretos para um corretor podem indicar falhas de aprendizagem | Resumo (EDUCOMP 2023) | Correto |
| Pimentel2025 | Retorno gerado por LLM em lugar de mensagens de erro e resultados de teste | Resumo (SBIE 2025) | Correto |
| Delgado2026 | Mesa temática sobre juízes online como instrumentos pedagógicos | Resumo (EDUCOMP 2026, anais estendidos) | Correto; é resumo de mesa, não estudo |
| Almeida2025 | Estimular a criação de testes melhorou o desempenho | Resumo (SBIE 2025) | Correto |
| Deus2024 | 1.258 linhas de código do ChatGPT; padrões incomuns em iniciantes | Resumo (SBIE 2024) | Correto |
| Oliveira2026 | Gradua o uso de IA em cinco níveis | Resumo (EDUCOMP 2026) | Correto |

**Formatação das referências:** siglas protegidas nos títulos e partículas de nomes (`da Silva`, `Galvão de Carvalho`) passaram para o sobrenome; a lista agrupa esses autores pela partícula (`da Silva` sob D), o que o estilo `apalike-sol` não permite ajustar.
