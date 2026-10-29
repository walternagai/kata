# Proposta de reescrita das frases longas (item 4A)

**Status: aprovadas e aplicadas ao `main.tex` pela autoria.** (Texto original da proposta: nada havia sido aplicado.) São 45 frases com mais de 40 palavras (de 49 detectadas; as demais são frases curtas coladas a cabeçalhos pelo separador de frases). Para cada uma, o texto original, a proposta e o tamanho da maior frase resultante. Marque as que aprova (por exemplo, "aprovo todas" ou "aprovo todas menos 20, 22 e 26").

Cada proposta preserva as citações e os comandos \LaTeX{}. A principal técnica é dividir a frase em duas ou usar lista inline; nenhuma proposta acrescenta afirmação nova.

---

## [1] 43 palavras → maior frase com 29

**Antes**

```latex
A evidência inicial indica que o efeito da IA generativa sobre iniciantes é desigual: em um estudo de laboratório, alguns estudantes que não tinham dificuldade aceleraram o trabalho, enquanto nos que tinham, as dificuldades metacognitivas persistiram e a ferramenta pôde agravá-las \citep{Prather2024}.
```

**Depois**

```latex
A evidência inicial indica que o efeito da IA generativa sobre iniciantes é desigual. Em um estudo de laboratório, alguns estudantes que não tinham dificuldade aceleraram o trabalho, e nos que tinham, as dificuldades metacognitivas persistiram e a ferramenta pôde agravá-las \citep{Prather2024}.
```

## [2] 49 palavras → maior frase com 38

**Antes**

```latex
Os agentes de código atuam sobre todos esses artefatos: editam um \textit{Dockerfile}, um \textit{notebook}, um relatório ou uma especificação com a mesma facilidade com que editam um programa, e cada um desses artefatos tem a sua forma de ser verificada e a sua forma de ser fraudada.
```

**Depois**

```latex
Os agentes de código atuam sobre todos esses artefatos. Editam um \textit{Dockerfile}, um \textit{notebook}, um relatório ou uma especificação com a mesma facilidade com que editam um programa, e cada artefato tem a sua forma de ser verificado e a sua forma de ser fraudado.
```

## [3] 47 palavras → maior frase com 29

**Antes**

```latex
O \textit{SpecBench}, um \textit{preprint} ainda sem revisão por pares, mede esse fenômeno, conhecido como \textit{reward hacking}, e relata que a distância entre os testes visíveis e os testes ocultos cresce 28 pontos percentuais a cada aumento de dez vezes no tamanho do código \citep{SpecBench2026}.
```

**Depois**

```latex
O \textit{SpecBench}, um \textit{preprint} ainda sem revisão por pares, mede esse fenômeno, conhecido como \textit{reward hacking}. Ele relata que a distância entre os testes visíveis e os testes ocultos cresce 28 pontos percentuais a cada aumento de dez vezes no tamanho do código \citep{SpecBench2026}.
```

## [4] 56 palavras → maior frase com 37

**Antes**

```latex
As quatro diretrizes que um repositório de terceiros extraiu de observações de Karpathy sobre erros comuns de modelos ao programar (pensar antes de codificar, simplicidade primeiro, mudanças cirúrgicas e execução guiada por objetivos) \citep{KarpathySkills2026}, e o Método Fable (classificar a tarefa antes de agir, exigir evidências e verificar de forma adversarial) \citep{Fable2026} respondem com disciplina.
```

**Depois**

```latex
Duas propostas respondem com disciplina. Uma são as quatro diretrizes que um repositório de terceiros extraiu de observações de Karpathy sobre erros comuns de modelos ao programar: pensar antes de codificar, simplicidade primeiro, mudanças cirúrgicas e execução guiada por objetivos \citep{KarpathySkills2026}. A outra é o Método Fable, que manda classificar a tarefa antes de agir, exigir evidências e verificar de forma adversarial \citep{Fable2026}.
```

## [5] 45 palavras → maior frase com 33

**Antes**

```latex
Este artigo propõe o \textbf{kata}, uma ferramenta de código aberto que transforma essa disciplina em um ciclo de nove fases cuja parte objetiva é código Python testado, e não instrução ao modelo, como apoio ao ensino de desenvolvimento de software com agentes de IA.
```

**Depois**

```latex
Este artigo propõe o \textbf{kata}, uma ferramenta de código aberto que transforma essa disciplina em um ciclo de nove fases, como apoio ao ensino de desenvolvimento de software com agentes de IA. A parte objetiva do ciclo é código Python testado, e não instrução ao modelo.
```

## [6] 75 palavras → maior frase com 67

**Antes**

```latex
As contribuições são: (i) o kata e a descrição de seus algoritmos objetivos; (ii) uma fundamentação pedagógica do ciclo, apresentada como hipótese de projeto; (iii) dois casos de uso para um primeiro teste em sala e seis extensões, cada um com fluxo, evidência produzida e ressalva; (iv) os limites conhecidos do verificador, reproduzidos e documentados; e (v) um protocolo de estudo com estudantes, ainda não executado, que testaria o efeito da ferramenta sobre a aprendizagem.
```

**Depois**

```latex
As contribuições são cinco: (i) o kata e a descrição de seus algoritmos objetivos; (ii) uma fundamentação pedagógica do ciclo, apresentada como hipótese de projeto; (iii) dois casos de uso para um primeiro teste em sala e seis extensões, cada um com fluxo, evidência produzida e ressalva; (iv) os limites conhecidos do verificador, reproduzidos e documentados; e (v) um protocolo de estudo com estudantes, ainda não executado.
```

## [8] 42 palavras → maior frase com 43

**Antes**

```latex
Aplicamos oito \textit{strings} em português (IA generativa e programação; ChatGPT e programação; juiz online; correção automática e programação; ensino de teste; criação de testes; integridade acadêmica e programação; engenharia de software com IA generativa e ensino) ao período de 2022 a 2026.
```

**Depois**

```latex
Aplicamos oito \textit{strings} em português ao período de 2022 a 2026: IA generativa e programação; ChatGPT e programação; juiz online; correção automática e programação; ensino de teste; criação de testes; integridade acadêmica e programação; e engenharia de software com IA generativa e ensino.
```

## [9] 44 palavras → maior frase com 39

**Antes**

```latex
Incluímos os que tratam de (a) IA generativa no ensino de programação ou de engenharia de software, (b) correção automática, retorno e juízes online, (c) ensino de teste de software ou (d) integridade e uso aceitável de IA, e excluímos os de outro tema.
```

**Depois**

```latex
Incluímos os trabalhos que tratam de (a) IA generativa no ensino de programação ou de engenharia de software, (b) correção automática, retorno e juízes online, (c) ensino de teste de software ou (d) integridade e uso aceitável de IA. Excluímos os de outro tema.
```

## [10] 50 palavras → maior frase com 30

**Antes**

```latex
Um relatório de grupo de trabalho internacional combinou revisão de 71 artigos, um levantamento com estudantes e docentes de 20 países, entrevistas com 22 docentes e orientações éticas \citep{Prather2023}, e uma síntese posterior discute os desafios e as oportunidades que esses modelos trazem a docentes e estudantes \citep{Denny2024}.
```

**Depois**

```latex
Um relatório de grupo de trabalho internacional combinou revisão de 71 artigos, um levantamento com estudantes e docentes de 20 países, entrevistas com 22 docentes e orientações éticas \citep{Prather2023}. Uma síntese posterior discute os desafios e as oportunidades que esses modelos trazem a docentes e estudantes \citep{Denny2024}.
```

## [11] 42 palavras → maior frase com 30

**Antes**

```latex
Do lado dos estudantes, um experimento controlado com 69 iniciantes (10 a 17 anos) encontrou que o acesso a um gerador de código aumentou o desempenho em tarefas de autoria, sem reduzir o desempenho em tarefas posteriores de modificação manual \citep{Kazemitabaar2023}.
```

**Depois**

```latex
Do lado dos estudantes, um experimento controlado com 69 iniciantes (10 a 17 anos) encontrou que o acesso a um gerador de código aumentou o desempenho em tarefas de autoria. O desempenho em tarefas posteriores de modificação manual não diminuiu \citep{Kazemitabaar2023}.
```

## [12] 50 palavras → maior frase com 31

**Antes**

```latex
As respostas dos modelos a pedidos de ajuda de iniciantes são em parte úteis e em parte imprecisas \citep{Hellas2023}, o que torna necessário que a pessoa saiba verificar o que recebe, e há propostas de atividades que treinam a compreensão de código e a formulação de \textit{prompts} \citep{Denny2024b}.
```

**Depois**

```latex
As respostas dos modelos a pedidos de ajuda de iniciantes são em parte úteis e em parte imprecisas \citep{Hellas2023}, o que exige que a pessoa saiba verificar o que recebe. Há também propostas de atividades que treinam a compreensão de código e a formulação de \textit{prompts} \citep{Denny2024b}.
```

## [13] 41 palavras → maior frase com 39

**Antes**

```latex
\textbf{Produção nacional.} Dos 27 trabalhos incluídos, 18 tratam de IA generativa no ensino de programação ou de engenharia de software, 4 de correção automática e juízes online, 3 de ensino de teste e 2 de integridade e uso aceitável de IA.
```

**Depois**

```latex
Dos 27 trabalhos incluídos, 18 tratam de IA generativa no ensino de programação ou de engenharia de software, 4 de correção automática e juízes online, 3 de ensino de teste e 2 de integridade e uso aceitável de IA.
```

## [14] 47 palavras → maior frase com 25

**Antes**

```latex
Um mapeamento de 52 estudos descreve três papéis da IA generativa no ensino de programação (participante colaborativo, ferramenta de apoio e mediador pedagógico) \citep{Bedin2025}, outro, de 18 estudos, trata da programação orientada a objetos \citep{Camilo2026}, e uma revisão examina as estratégias pedagógicas empregadas \citep{Silva2024}.
```

**Depois**

```latex
Um mapeamento de 52 estudos descreve três papéis da IA generativa no ensino de programação: participante colaborativo, ferramenta de apoio e mediador pedagógico \citep{Bedin2025}. Outro mapeamento, de 18 estudos, trata da programação orientada a objetos \citep{Camilo2026}, e uma revisão examina as estratégias pedagógicas empregadas \citep{Silva2024}.
```

## [15] 56 palavras → maior frase com 22

**Antes**

```latex
Sobre correção, um estudo mostra que códigos corretos para um corretor automático podem apresentar comportamentos que indicam falhas de aprendizagem \citep{SilvaCaceffo2023}, outro propõe retorno gerado por modelos de linguagem em lugar de mensagens de erro e resultados de teste \citep{Pimentel2025}, e uma mesa temática propõe discutir como tornar juízes online instrumentos pedagógicos \citep{Delgado2026}.
```

**Depois**

```latex
Sobre correção, um estudo mostra que códigos corretos para um corretor automático podem apresentar comportamentos que indicam falhas de aprendizagem \citep{SilvaCaceffo2023}. Outro propõe retorno gerado por modelos de linguagem em lugar de mensagens de erro e resultados de teste \citep{Pimentel2025}. Uma mesa temática propõe discutir como tornar juízes online instrumentos pedagógicos \citep{Delgado2026}.
```

## [16] 42 palavras → maior frase com 20

**Antes**

```latex
Examinamos o resumo, ou o seu início, de 26 dos 27 (o outro não tem resumo, e foi triado pelo título), e nenhum descreve um portão que reexecute as verificações declaradas e confronte as afirmações do arquivo de tarefa com o repositório.
```

**Depois**

```latex
Examinamos o resumo, ou o seu início, de 26 dos 27 trabalhos. O outro não tem resumo e foi triado pelo título. Nenhum descreve um portão que reexecute as verificações declaradas e confronte as afirmações do arquivo de tarefa com o repositório.
```

## [17] 56 palavras → maior frase com 30

**Antes**

```latex
Avaliar os testes escritos pelos próprios estudantes, e não só o código, é uma estratégia clássica para levá-los da tentativa e erro à reflexão \citep{Edwards2004}, e há relatos de experiência sobre ensinar a escrever testes, avaliar as suítes dos estudantes, dar incentivo para escrevê-los cedo e sobre os limites da cobertura como critério \citep{Spacco2006}.
```

**Depois**

```latex
Avaliar os testes escritos pelos próprios estudantes, e não só o código, é uma estratégia clássica para levá-los da tentativa e erro à reflexão \citep{Edwards2004}. Há também relatos de experiência sobre ensinar a escrever testes, avaliar as suítes dos estudantes, dar incentivo para escrevê-los cedo e sobre os limites da cobertura como critério \citep{Spacco2006}.
```

## [18] 43 palavras → maior frase com 31

**Antes**

```latex
O andaime (\textit{scaffolding}) é o apoio que permite realizar uma tarefa além da capacidade inicial de quem aprende, ao assumir os elementos que ela ainda não domina \citep{Wood1976}, e a literatura posterior destaca que ele deve ser retirado aos poucos.
```

**Depois**

```latex
O andaime (\textit{scaffolding}) é o apoio que permite realizar uma tarefa além da capacidade inicial de quem aprende, ao assumir os elementos que ela ainda não domina \citep{Wood1976}. A literatura posterior destaca que ele deve ser retirado aos poucos.
```

## [20] 80 palavras → maior frase com 82

**Antes**

```latex
Uma mudança passa por FIT (classificar a tarefa e rotear), THINK (declarar problema, premissas, alternativas e incógnitas antes de codificar), SIMPLIFY (verificar que o código é mínimo), INTENT (comparar o que o código faz, o que o teste espera e o que a especificação diz), SURGICAL (justificar cada arquivo alterado), VERIFY (executar lint, testes e cobertura), TWIN CHECK (procurar o mesmo defeito em outros pontos do projeto), ARTIFACT (conferir as linhas de evidência devidas) e REPORT (relatar o resultado primeiro).
```

**Depois**

```latex
Uma mudança passa por nove fases: FIT (classificar a tarefa e rotear), THINK (declarar problema, premissas, alternativas e incógnitas antes de codificar), SIMPLIFY (verificar que o código é mínimo), INTENT (comparar o que o código faz, o que o teste espera e o que a especificação diz), SURGICAL (justificar cada arquivo alterado), VERIFY (executar lint, testes e cobertura), TWIN CHECK (procurar o mesmo defeito em outros pontos do projeto), ARTIFACT (conferir as linhas de evidência devidas) e REPORT (relatar o resultado primeiro).
```

## [21] 41 palavras → maior frase com 24

**Antes**

```latex
Uma tarefa de no máximo um arquivo e menos de dez linhas alteradas é candidata a trivial, e só vai direto à verificação, sem o cerimonial de planejamento, se a pessoa confirmar que a mudança não altera comportamento nem exige pesquisa.
```

**Depois**

```latex
Uma tarefa de no máximo um arquivo e menos de dez linhas alteradas é candidata a trivial. Ela só vai direto à verificação, sem o cerimonial de planejamento, se a pessoa confirmar que a mudança não altera comportamento nem exige pesquisa.
```

## [22] 72 palavras → maior frase com 27

**Antes**

```latex
Ele procura sete categorias de fraude: testes enfraquecidos (por exemplo, o corpo trocado por \texttt{pass}); falsa conclusão (o relatório diz que os testes passam e a reexecução falha); escopo excedente (o relatório declara um arquivo e a árvore tem quatro); ação não autorizada; traição da especificação (um desacordo de intenção aprovado mesmo assim); resíduos; e adulteração da linha de base (o \texttt{base\_\allowbreak{}commit} do arquivo diverge da âncora gravada no Git).
```

**Depois**

```latex
Ele procura sete categorias de fraude. Há testes enfraquecidos (por exemplo, o corpo trocado por \texttt{pass}) e falsa conclusão (o relatório diz que os testes passam e a reexecução falha). Há escopo excedente (o relatório declara um arquivo e a árvore tem quatro), ação não autorizada e traição da especificação (um desacordo de intenção aprovado mesmo assim). Há ainda resíduos e adulteração da linha de base (o \texttt{base\_\allowbreak{}commit} do arquivo diverge da âncora gravada no Git).
```

## [23] 53 palavras → maior frase com 57

**Antes**

```latex
O \texttt{kata -{}-audit} gradua cada fase como \textit{seguida} (respondida com conteúdo real), \textit{pulada} (preenchida com o padrão de uma execução não interativa, sem que ninguém respondesse), \textit{falsificada} (marcada como respondida com conteúdo vazio ou padrão, ou uma afirmação de verificação sem evidência) ou \textit{degradada} (executada sem a habilidade da própria fase carregada).
```

**Depois**

```latex
O \texttt{kata -{}-audit} gradua cada fase em uma de quatro notas. A fase é \textit{seguida} se foi respondida com conteúdo real, \textit{pulada} se foi preenchida com o padrão de uma execução não interativa, sem que ninguém respondesse, \textit{falsificada} se foi marcada como respondida com conteúdo vazio ou padrão (ou se há afirmação de verificação sem evidência) e \textit{degradada} se foi executada sem a habilidade da própria fase carregada.
```

## [24] 43 palavras → maior frase com 28

**Antes**

```latex
Na primeira tentativa, o kata rodou com um interpretador Python sem \texttt{ruff} nem \texttt{pytest}, e rejeitou o ciclo com a mensagem de que os módulos não existiam: o portão não aprova o que não conseguiu executar (saída reproduzível em \texttt{demos/saidas/01c-sem-\allowbreak{}ferramentas.txt}).
```

**Depois**

```latex
Na primeira tentativa, o kata rodou com um interpretador Python sem \texttt{ruff} nem \texttt{pytest}. Rejeitou o ciclo com a mensagem de que os módulos não existiam, porque o portão não aprova o que não conseguiu executar (saída reproduzível em \texttt{demos/saidas/01c-sem-\allowbreak{}ferramentas.txt}).
```

## [25] 46 palavras → maior frase com 22

**Antes**

```latex
Na execução da listagem, porém, o campo de resolução do conflito do INTENT ficou vazio e, mesmo assim, o ciclo foi aprovado e a auditoria graduou todas as fases como seguidas, porque ela verifica que a fase foi respondida, e não que a resposta é boa.
```

**Depois**

```latex
Na execução da listagem, porém, o campo de resolução do conflito do INTENT ficou vazio e, mesmo assim, o ciclo foi aprovado. A auditoria graduou todas as fases como seguidas, porque verifica que a fase foi respondida, e não que a resposta é boa.
```

## [26] 103 palavras → maior frase com 43

**Antes**

```latex
Nelas, o JUDGE refuta a tarefa acima por traição da especificação e passa a \texttt{VERIFIED} quando o conflito recebe uma frase qualquer (Execução 2); um teste esvaziado passa em testes e cobertura e só o JUDGE o acusa (Execução 3); a auditoria acusa as sete fases vazias de um arquivo escrito à mão (Execução 4); o domínio \texttt{docs} é verificado por comandos que o projeto declara (Execução 5); e o domínio \texttt{data-analysis} reprova uma análise que descarta linhas sem registro (Execução 6); e os domínios \texttt{devops} e \texttt{research} reprovam uma configuração sem \textit{healthcheck} e um relatório com fonte inexistente (Execuções 7 e 8).
```

**Depois**

```latex
Sete execuções adicionais estão no Apêndice~A. Nelas, o JUDGE refuta a tarefa acima por traição da especificação e passa a \texttt{VERIFIED} quando o conflito recebe uma frase qualquer (Execução 2). Um teste esvaziado passa em testes e cobertura e só o JUDGE o acusa (Execução 3), e a auditoria acusa as sete fases vazias de um arquivo escrito à mão (Execução 4). Os domínios \texttt{docs}, \texttt{data-analysis}, \texttt{devops} e \texttt{research} são verificados por comandos que o projeto declara, e reprovam, respectivamente, uma flag inexistente, uma remoção de linhas sem registro, uma configuração sem \textit{healthcheck} e um relatório com fonte inexistente (Execuções 5 a 8).
```

## [27] 43 palavras → maior frase com 22

**Antes**

```latex
Em uma leitura rápida: os blocos de \texttt{fit} a \texttt{surgical} são declarações da pessoa (ou o padrão de uma execução não interativa), o bloco \texttt{verify} é preenchido pelo kata a partir de códigos de saída, e os blocos \texttt{twins} e \texttt{artifact} são calculados.
```

**Depois**

```latex
Em uma leitura rápida, os blocos de \texttt{fit} a \texttt{surgical} são declarações da pessoa (ou o padrão de uma execução não interativa). O bloco \texttt{verify} é preenchido pelo kata a partir de códigos de saída, e os blocos \texttt{twins} e \texttt{artifact} são calculados.
```

## [28] 61 palavras → maior frase com 18

**Antes**

```latex
Em uma disciplina, os fluxos de integração contínua e de revisão são as formas naturais de conferir entregas, e os de ciclo e auditoria, as de acompanhar o processo.

|SEÇÃO| O ciclo da Seção~\ref{sec:kata} é o mesmo em todo o kata, mas o que significa abrir a evidência, observar o resultado e desconfiar de uma afirmação muda conforme o artefato.
```

**Depois**

```latex
Em uma disciplina, os fluxos de integração contínua e de revisão são as formas naturais de conferir entregas. Os de ciclo e auditoria servem para acompanhar o processo.
```

## [29] 57 palavras → maior frase com 29

**Antes**

```latex
\textbf{O que é executável e o que é instrução.} Os tipos de fraude da última coluna da Tabela~\ref{tab:dominios-b} são instruções escritas nos adaptadores, e não lógica do JUDGE: dos 24 tipos listados, só \texttt{unauthorized\_\allowbreak{}action} aparece no pacote Python, e porque coincide com uma das sete categorias do JUDGE; os outros 23 não existem no código.
```

**Depois**

```latex
\textbf{O que é executável e o que é instrução.} Os tipos de fraude da última coluna da Tabela~\ref{tab:dominios-b} são instruções escritas nos adaptadores, e não lógica do JUDGE. Dos 24 tipos listados, só \texttt{unauthorized\_\allowbreak{}action} aparece no pacote Python, porque coincide com uma das sete categorias do JUDGE, e os outros 23 não existem no código.
```

## [30] 49 palavras → maior frase com 37

**Antes**

```latex
O terceiro são as linhas vermelhas, ações que exigem uma intervenção humana documentada, como publicar dados pessoais, executar \textit{deploy} ou \textit{push} sem a linha AUTH com a citação do usuário, pôr segredos no \textit{diff} ou no arquivo de tarefa, ou afirmar um fato de API sem abrir a fonte.
```

**Depois**

```latex
O terceiro são as linhas vermelhas, ações que exigem uma intervenção humana documentada. São exemplos publicar dados pessoais, executar \textit{deploy} ou \textit{push} sem a linha AUTH com a citação do usuário, pôr segredos no \textit{diff} ou no arquivo de tarefa e afirmar um fato de API sem abrir a fonte.
```

## [31] 50 palavras → maior frase com 42

**Antes**

```latex
\textbf{Fases e dificuldades de iniciantes.} Em um estudo de laboratório com iniciantes que programavam com IA generativa, \cite{Prather2024} descrevem dificuldades metacognitivas conhecidas, como formar um modelo conceitual incorreto do problema e ter uma falsa sensação de progresso depois de testar a solução, e propõem andaimar a experiência com a ferramenta.
```

**Depois**

```latex
\textbf{Fases e dificuldades de iniciantes.} Em um estudo de laboratório com iniciantes que programavam com IA generativa, \cite{Prather2024} descrevem dificuldades metacognitivas conhecidas, como formar um modelo conceitual incorreto do problema e ter uma falsa sensação de progresso depois de testar a solução. Os autores propõem andaimar a experiência com a ferramenta.
```

## [32] 42 palavras → maior frase com 26

**Antes**

```latex
\textbf{Reflexão na ação e testes.} \cite{Edwards2004} argumenta que o teste de software promove a formação de hipóteses e a validação experimental, que são centrais à reflexão na ação, e que avaliar a capacidade de demonstrar a correção por testes reforça essas habilidades.
```

**Depois**

```latex
\textbf{Reflexão na ação e testes.} \cite{Edwards2004} argumenta que o teste de software promove a formação de hipóteses e a validação experimental, centrais à reflexão na ação. Segundo ele, avaliar a capacidade de demonstrar a correção por testes reforça essas habilidades.
```

## [33] 54 palavras → maior frase com 33

**Antes**

```latex
\textbf{O arquivo e a auditoria como retorno formativo.} O retorno é formativo quando informa a pessoa sobre a distância entre o desempenho atual e o desejado, a tempo de ela agir \citep{Black1998}, e um retorno eficaz responde a três perguntas: aonde vou, como estou indo e o que vem a seguir \citep{Hattie2007}.
```

**Depois**

```latex
\textbf{O arquivo e a auditoria como retorno formativo.} O retorno é formativo quando informa a pessoa sobre a distância entre o desempenho atual e o desejado, a tempo de ela agir \citep{Black1998}. Um retorno eficaz responde a três perguntas: aonde vou, como estou indo e o que vem a seguir \citep{Hattie2007}.
```

## [34] 42 palavras → maior frase com 28

**Antes**

```latex
Aqui, a Tabela~\ref{tab:bloom} permite fazer o caminho inverso a partir de uma fase: se o resultado desejado é que a pessoa saiba justificar o escopo de uma mudança, a fase SURGICAL é a atividade e o arquivo de tarefa, a evidência.
```

**Depois**

```latex
Aqui, a Tabela~\ref{tab:bloom} permite fazer o caminho inverso a partir de uma fase. Se o resultado desejado é que a pessoa saiba justificar o escopo de uma mudança, a fase SURGICAL é a atividade e o arquivo de tarefa, a evidência.
```

## [35] 41 palavras → maior frase com 26

**Antes**

```latex
\textit{Fluxo.} Na integração contínua do repositório da turma, \texttt{kata -{}-check-only} roda lint, testes e cobertura, e \texttt{kata -{}-judge -{}-trusted-base <ref>} confronta as afirmações do arquivo de tarefa com o \textit{diff} desde uma referência que a pessoa não controla.
```

**Depois**

```latex
\textit{Fluxo.} Na integração contínua do repositório da turma, \texttt{kata -{}-check-only} roda lint, testes e cobertura. O comando \texttt{kata -{}-judge -{}-trusted-base <ref>} confronta as afirmações do arquivo de tarefa com o \textit{diff} desde uma referência que a pessoa não controla.
```

## [36] 45 palavras → maior frase com 26

**Antes**

```latex
Um banco de exercícios pode ser montado assim: cada tarefa é o estado anterior à correção mais os testes que a correção alterou, com o histórico reinicializado para que a solução não seja lida, e verificada para falhar no estado inicial e passar na correção.
```

**Depois**

```latex
Um banco de exercícios pode ser montado assim. Cada tarefa é o estado anterior à correção mais os testes que a correção alterou, com o histórico reinicializado para que a solução não seja lida. Verifica-se que ela falha no estado inicial e passa na correção.
```

## [37] 42 palavras → maior frase com 29

**Antes**

```latex
\textbf{Caso 6: especificação, testes e intenção.} \textit{Fluxo.} A fase INTENT pede três respostas (o que o código faz, o que o teste espera, o que a especificação diz) e, havendo discordância, apresenta a ordem de autoridade: declaração do usuário, especificação, testes, código.
```

**Depois**

```latex
\textbf{Caso 6: especificação, testes e intenção.} \textit{Fluxo.} A fase INTENT pede três respostas: o que o código faz, o que o teste espera e o que a especificação diz. Havendo discordância, apresenta a ordem de autoridade: declaração do usuário, especificação, testes, código.
```

## [38] 52 palavras → maior frase com 25

**Antes**

```latex
Nas seguintes, a política da disciplina dispensa fases, e as rotas do FIT dão o apoio possível: o portão de tarefa trivial leva uma mudança de um arquivo e menos de dez linhas, confirmada como sem efeito de comportamento, direto à verificação, e as rotas \texttt{plan-first} e \texttt{question} param antes do código.
```

**Depois**

```latex
Nas seguintes, a política da disciplina dispensa fases, e as rotas do FIT dão o apoio possível. O portão de tarefa trivial leva direto à verificação uma mudança de um arquivo e menos de dez linhas, confirmada como sem efeito de comportamento. As rotas \texttt{plan-first} e \texttt{question} param antes do código.
```

## [39] 46 palavras → maior frase com 28

**Antes**

```latex
Duas pessoas avaliadoras, sem saber a condição, aplicam uma rubrica de cinco dimensões, pontuadas de 0 a 2 com âncoras escritas: premissa explícita, premissa verificável (que um comando, um arquivo ou um teste pode conferir), alternativa considerada, critério de pronto observável e justificativa de cada arquivo.
```

**Depois**

```latex
Duas pessoas avaliadoras, sem saber a condição, aplicam uma rubrica de cinco dimensões, pontuadas de 0 a 2 com âncoras escritas. As dimensões são premissa explícita, premissa verificável (que um comando, um arquivo ou um teste pode conferir), alternativa considerada, critério de pronto observável e justificativa de cada arquivo.
```

## [40] 54 palavras → maior frase com 21

**Antes**

```latex
A deriva do agente é outra ameaça, porque o desfecho depende do agente hospedeiro e do modelo, que mudam entre semestres: mitiga-se usando o mesmo agente, o mesmo modelo e a mesma versão nas duas condições, registrando-os a cada entrega e tratando uma troca de versão no meio do estudo como desvio de protocolo.
```

**Depois**

```latex
A deriva do agente é outra ameaça, porque o desfecho depende do agente hospedeiro e do modelo, que mudam entre semestres. Mitiga-se usando o mesmo agente, o mesmo modelo e a mesma versão nas duas condições, registrando-os a cada entrega. Uma troca de versão no meio do estudo conta como desvio de protocolo.
```

## [41] 42 palavras → maior frase com 22

**Antes**

```latex
Por envolver seres humanos, o estudo exigiria aprovação ética conforme a legislação vigente \citep{brasil2024lei14874,cns2016resolucao510}, consentimento específico para o uso dos registros e tratamento dos dados conforme a LGPD \citep{LGPD2018}, com pseudonimização dos arquivos de tarefa e do histórico do Git.
```

**Depois**

```latex
Por envolver seres humanos, o estudo exigiria aprovação ética conforme a legislação vigente \citep{brasil2024lei14874,cns2016resolucao510} e consentimento específico para o uso dos registros. Os dados seriam tratados conforme a LGPD \citep{LGPD2018}, com pseudonimização dos arquivos de tarefa e do histórico do Git.
```

## [42] 50 palavras → maior frase com 32

**Antes**

```latex
Por causa da relação de poder entre docente e estudante, o recrutamento e o consentimento são conduzidos por quem não avalia a turma, a recusa e a desistência não trazem prejuízo, as avaliadoras da H1 recebem registros pseudonimizados e o docente só vê resultados agregados depois de fechadas as notas.
```

**Depois**

```latex
Por causa da relação de poder entre docente e estudante, o recrutamento e o consentimento são conduzidos por quem não avalia a turma, e a recusa e a desistência não trazem prejuízo. As avaliadoras da H1 recebem registros pseudonimizados, e o docente só vê resultados agregados depois de fechadas as notas.
```

## [43] 76 palavras → maior frase com 70

**Antes**

```latex
\textbf{Docentes.} (i) O revisor independente do kata poderia ser uma etapa automática de entrega, ao lado do corretor de exercícios, desde que o veredito seja lido como indício (Seção~\ref{sec:limites}). (ii) O ciclo completo deve ser planejado como atividade de aprendizagem, com tempo previsto, e não como ferramenta de produtividade. (iii) A auditoria e a Tabela~\ref{tab:rubrica} oferecem um ponto de partida para o retorno sobre o processo, que ainda precisa ser testado com turmas.
```

**Depois**

```latex
\textbf{Docentes.} (i) O revisor independente do kata poderia ser uma etapa automática de entrega, ao lado do corretor de exercícios, desde que o veredito seja lido como indício (Seção~\ref{sec:limites}). (ii) O ciclo completo deve ser planejado como atividade de aprendizagem, com tempo previsto. (iii) A auditoria e a Tabela~\ref{tab:rubrica} oferecem um ponto de partida para o retorno sobre o processo, que ainda precisa ser testado com turmas.
```

## [44] 67 palavras → maior frase com 65

**Antes**

```latex
\textbf{Equipes de desenvolvimento.} (i) O \texttt{kata -{}-check-only} e o \texttt{kata -{}-judge} podem rodar em integração contínua, e \texttt{-{}-trusted-base} fecha, no servidor, parte dos desvios da Tabela~\ref{tab:desvios}. (ii) Em repositórios com falhas preexistentes, a auditoria cega ao contexto pode acusar falsamente, e declarar a base conhecida evitaria isso. (iii) Este artigo não oferece evidência de que o ciclo melhore o resultado do trabalho.
```

**Depois**

```latex
\textbf{Equipes de desenvolvimento.} (i) O \texttt{kata -{}-check-only} e o \texttt{kata -{}-judge} podem rodar em integração contínua, e \texttt{-{}-trusted-base} fecha, no servidor, parte dos desvios da Tabela~\ref{tab:desvios}. (ii) Em repositórios com falhas preexistentes, a auditoria cega ao contexto pode acusar falsamente, e declarar a base conhecida evitaria isso. (iii) O artigo não oferece evidência de que o ciclo melhore o resultado.
```

## [45] 43 palavras → maior frase com 29

**Antes**

```latex
\textbf{O que o artigo não responde.} Não sabemos se o kata melhora a aprendizagem, se a retenção sem agente é preservada, quanto tempo o ciclo custa a estudantes, se docentes leem os registros ou se a rubrica da Tabela~\ref{tab:rubrica} funciona em sala.
```

**Depois**

```latex
\textbf{O que o artigo não responde.} Não sabemos se o kata melhora a aprendizagem, se a retenção sem agente é preservada e quanto tempo o ciclo custa a estudantes. Também não sabemos se docentes leem os registros nem se a rubrica da Tabela~\ref{tab:rubrica} funciona em sala.
```

## [46] 52 palavras → maior frase com 37

**Antes**

```latex
\textbf{Condições para uma primeira adoção.} Para quem quiser experimentar a proposta antes de qualquer estudo, sugerimos um piloto pequeno: uma turma, os casos 1 e 2, tarefas curtas, o ciclo reduzido (planejamento e verificação), um docente que leia os registros e uma conversa com a turma sobre o que a ferramenta mede.
```

**Depois**

```latex
\textbf{Condições para uma primeira adoção.} Para quem quiser experimentar a proposta antes de qualquer estudo, sugerimos um piloto pequeno. Ele usaria uma turma, os casos 1 e 2, tarefas curtas e o ciclo reduzido (planejamento e verificação), com um docente que leia os registros e uma conversa com a turma sobre o que a ferramenta mede.
```

## [49] 47 palavras → maior frase com 48

**Antes**

```latex
Os trabalhos futuros são: executar o protocolo da Seção~\ref{sec:protocolo} com estudantes, começando pelos casos 1 e 2; fechar os desvios do verificador, com uma opção de falha fechada para \texttt{UNVERIFIABLE}; e declarar as falhas preexistentes da base para que a auditoria não puna dívida herdada.
```

**Depois**

```latex
Os trabalhos futuros são três: executar o protocolo da Seção~\ref{sec:protocolo} com estudantes, começando pelos casos 1 e 2; fechar os desvios do verificador, com uma opção de falha fechada para \texttt{UNVERIFIABLE}; e declarar as falhas preexistentes da base para que a auditoria não puna dívida herdada.
```

---

## Observações

- As propostas **6, 20, 23, 43 e 44** continuam com uma frase acima de 40 palavras porque são enumerações (contribuições, as nove fases, as quatro notas da auditoria, as recomendações por público). Dividir esses casos em sentenças soltas piora a leitura. Uma alternativa é transformar 6, 20 e 23 em lista `itemize`; diga se prefere.
- A proposta **26** também corrige um defeito de pontuação que **já foi aplicado** ao `main.tex` (havia dois "; e" seguidos).
- As propostas **8**, **31** e **49** ficam com 43, 42 e 48 palavras: são frases com lista de itens ou citação, e reduzi o que dava sem perder conteúdo.
