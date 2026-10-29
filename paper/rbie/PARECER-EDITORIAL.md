# Parecer editorial — RBIE

**Manuscrito:** Kata: Verificação Executável de Software Produzido com Agentes de Inteligência Artificial e Seu Uso na Educação em Computação
**Versão revisada:** `paper/rbie/main.tex` no HEAD (14 páginas, cerca de 12 de corpo)
**Decisão:** **Revisão maior**
**Task de origem:** `.kata/rbie-revisao-editorial.yaml` (15 achados, `[R]` = reproduzido nesta rodada, `[E]` = leitura do texto e do código)

---

## Resumo da avaliação

O manuscrito apresenta uma ferramenta de código aberto que conduz uma mudança de software por um ciclo de nove fases e a confronta com o repositório, e propõe uma leitura pedagógica e oito casos de uso para a educação em software. A avaliação técnica é honesta sobre os próprios limites, e os números que conferi contra os dados brutos estão corretos. A forma segue o template quase por inteiro.

O problema é de **escopo e de contribuição**. A revista publica pesquisa em Informática na Educação e em Educação em Computação, e o texto não traz nenhum dado de estudante ou docente. Os experimentos têm agentes de IA como sujeitos, e a parte educacional é análise conceitual. Isso é legítimo como proposta, mas não como "Artigo de Pesquisa" com título e resumo que afirmam utilidade.

## Pontos fortes

- Declara com clareza que **não há dados de estudantes** e que os casos de uso são hipóteses.
- Os números das tabelas **conferem** com `eval/results/` (recomputados nesta rodada).
- Reporta resultados desfavoráveis: custo de nove vezes, 6 acusações falsas em 12 execuções, desvios do verificador.
- Acessibilidade cumprida (texto alternativo em ambas as figuras, tabelas sem linhas verticais, figura legível em escala de cinza).
- Exemplo de arquivo de tarefa completo, com tabela de campos, e execução real do ciclo.

## Achados que impedem a publicação (alta severidade)

| ID | Problema | Pedido |
|---|---|---|
| E1-1 | Título e resumo prometem "uso" e "utilidade" que nenhum dado sustenta. | Estudo mínimo com pessoas **ou** reposicionar como proposta, sem "úteis". |
| E1-2 | Quatro das oito tabelas e a Figura 2 vêm do manuscrito do JSERD, cujo estado não consta. | Declarar na carta; mostrar o que é novo; cortar o que não serve ao leitor de educação. |
| E1-3 | Trabalhos relacionados sem busca declarada; só uma referência nacional; sem Web-CAT, Marmoset, GitHub Classroom etc. | Registrar bases, strings e período; incluir RBIE e SOL; qualificar "nenhum combina". |
| E1-4 | A QP1 mede regressão: cenários da própria autoria, nascidos de defeitos do JUDGE; na comparação, 11/11 em todos os portões. | Reformular como verificação de regressão ou acrescentar cenários de terceiros. |
| E1-5 | A QP2 não discrimina: 48/48 passam nos dois braços; custo só por medianas. | Reportar tamanho de efeito e intervalo (abaixo). |

**Números que o artigo deveria trazer (calculados de `external_study.json`):** razão de medianas 9,1 (IC95% bootstrap 6,2 a 11,4); delta de Cliff 0,983 (kata maior em 571 de 576 pares); razão por par tarefa×modelo de 1,3 a 24,3 (mediana 7,7); zero testes enfraquecidos em 48 sessões equivale a um limite superior de 6,1%, não a "ausência".

## Pré-requisitos de submissão

- **E1-8 Versões e reprodutibilidade.** O texto descreve a 0.7.2; os resultados são do commit `230e81a`; o HEAD roda 24 cenários. Reexecutei a Listagem 5: com o código do repositório e as dependências de desenvolvimento, **24/24 passam**; com a `.venv` do projeto (sem `ruff` nem `pytest`, `kata` do PyPI), os cenários falham com `false_completion`. A listagem não diz que as dependências são necessárias nem faz `git checkout 230e81a`.
- **E1-11 CRediT × declaração de IA.** "Redigiu e aprovou" contradiz "rascunho redigido pelo Claude".
- **E1-12 Anonimização.** O build padrão é identificado e o `main.pdf` commitado tem o nome da autoria nos metadados.

## Melhorias recomendadas

- **E1-6** Métricas circulares (mesmo detector do JUDGE): inspeção por duas pessoas, com kappa.
- **E1-7** As 6 "acusações falsas" são classificadas só pela autoria; reexecutar o JUDGE corrigido sobre elas.
- **E1-9** Casos de uso e protocolo (H1 a H3) sem tamanho de amostra, instrumento de retenção, randomização nem ameaças.
- **E1-10** Ética e LGPD em uma frase; falta tratar dados do arquivo de tarefa e o uso do veredito em processo disciplinar.
- **E1-13** Referências: subtítulo de Becker ausente (o Crossref o traz separado), `ai` e `chatgpt` em minúsculas, preprints não marcados no texto, Karpathy conferido só por fontes secundárias.

## Ajustes menores

- **E1-14** A Figura 1 é só anunciada; faltam observar e explicar. Definir PyPI, YAML e TikZ.
- **E1-15** "A autoria" cerca de 40 vezes e "nós" 3; "As pessoas autoras declaram" para autor único; termos em inglês sem padrão; Seção 5 densa; cerca de 7.600 palavras.

## Conformidade com o template (medida)

| Item | Resultado |
|---|---|
| Páginas de corpo (10 a 20) | cerca de 12 |
| Resumos (150 a 300 palavras) | 242 (pt), 221 (en), 245 (es) |
| Palavras-chave (3 a 10, iniciais maiúsculas) | 6, conforme |
| Referência ao elemento antes dele | 14 de 14 |
| Texto alternativo nas figuras | sim |
| Vírgula decimal, tabelas sem linhas verticais, legendas | conforme |
| Declarações obrigatórias (contribuições, conflitos, materiais, IA) | presentes; E1-11 aponta contradição |

## Recomendação ao autor

Decida entre as duas rotas de E1-1 antes de qualquer outra mudança, porque ela define o título, o resumo e a Seção 8. Se escolher o estudo mínimo com pessoas, as entrevistas com docentes sobre os casos 1 a 3 são o caminho mais barato e já responderiam a E1-9 em parte.

---

## Resposta da autoria, rodada 1 (ajustes que independem de decisão)

| ID | Situação | O que foi feito | O que falta |
|---|---|---|---|
| E1-5 | feito em parte | Razão de medianas 9,1 (IC95% 6,2 a 11,4), delta de Cliff 0,98, razão por par 1,3 a 24,3 e limite superior de 6,1% para 0/48 entram na Seção 7.2; script `img/estatisticas_externo.py`. | Dizer que a QP2 mostra custo, não benefício (depende de E1-4). |
| E1-7 | em parte | "Consideradas falsas pela autoria, sem segunda avaliação". | Reexecutar o JUDGE corrigido sobre as seis sessões. |
| E1-8 | em parte | Listagem 5 com `git checkout 230e81a` e `main`; dependências e versões declaradas; 19/19 verificado em `230e81a` e 24/24 no HEAD. | DOI no Zenodo. **Achado novo:** `230e81a` não tem `eval/external_study.py` (entrou em `753b984`); a Camada 2 não se reproduz com um único checkout. |
| E1-10 | feito | Parágrafo sobre dados pessoais (LGPD), finalidade, guarda, contestação e proibição de prova única. | — |
| E1-11 | feito | CRediT com "revisou, editou e aprovou", rascunho atribuído à IA. | — |
| E1-12 | em parte | `./build.sh anon` gera `main-anon.pdf`: 0 ocorrências de nome, afiliação e URL; `Author: Omitido para revisão`. | Repositório anonimizado; "a ferramenta" no lugar de "kata" onde possível. O `main.pdf` commitado segue identificado de propósito. |
| E1-13 | em parte | Subtítulo de Becker, `{AI}`, `{ChatGPT}`, `{Copilot}`, nota arXiv em Huang e Jimenez, preprints marcados no texto, LGPD2018 adicionada. | Fonte primária de Karpathy. |
| E1-14 | feito | Figura 1 observada e explicada; PyPI, YAML e TikZ definidos. | — |
| E1-15 | em parte | "Nosso" e "As pessoas autoras" corrigidos. | Padronizar "a autoria" e "nós"; estruturar a Seção 5; enxugar a 7.1. |

**Aguardam decisão da autoria:** E1-1, E1-2, E1-3, E1-4, E1-6 e E1-9.

---

## Resposta da autoria, rodada 2 (E1-1: reposicionamento)

A autoria escolheu a **rota B**: reposicionar o kata como **proposta de ferramenta e de protocolo de estudo**, sem estudo com pessoas nesta versão.

| Onde | Mudança |
|---|---|
| Título (pt, en, es) | "Ferramenta de Verificação Executável para Ensinar Desenvolvimento de Software com Agentes de Inteligência Artificial". Saem "Seu Uso na Educação em Computação" e "Software Produzido com". |
| Resumos | Dizem que o artigo propõe uma ferramenta e um protocolo, que só a viabilidade técnica é avaliada e que a aprendizagem não é medida. Sai "úteis como andaime e como retorno formativo". |
| Introdução | Parágrafo "É preciso dizer o que o artigo é"; "nada nele autoriza afirmar que o kata ensina melhor". QP1 vira verificação de regressão feita pela autoria; QP3 passa a incluir o estudo que testaria o efeito. Contribuições reescritas como proposta. |
| Seções | "Fundamentação Pedagógica da Proposta", "Casos de Uso Propostos para o Ensino de Software", "Metodologia da Verificação Técnica", "Resultados e Discussão da Verificação Técnica". |
| Resultados | "A QP2 mostra, portanto, funcionamento e custo, e não benefício." O tempo do ciclo como parte do conteúdo vira hipótese do protocolo. |
| Limitações | "Este é um artigo de proposta": nenhuma limitação se corrige com mais sessões de agentes. |
| Conclusão | Reescrita: a contribuição é a proposta e a verificação técnica; implicações condicionais. |

**Efeito sobre os demais achados:** E1-1 fechado; E1-4 em parte (a QP1 deixa de se apresentar como avaliação, mas cenários de terceiros continuariam a fortalecê-la); E1-5 fechado.

**Ainda aguardam decisão ou trabalho:** E1-2, E1-3, E1-6 e E1-9. A categoria "Artigo de Pesquisa" do cabeçalho é reservada à editoria; se a RBIE não aceitar proposta sem dado de pessoas nessa categoria, a editoria decide o enquadramento.

---

## Resposta da autoria, rodada 3 (retirada dos dados do JSERD)

A autoria pediu para **retirar do artigo os dados vinculados ao manuscrito do JSERD**, o que responde a E1-2.

| Removido | Mantido ou acrescentado |
|---|---|
| Tabelas dos 19 cenários, do estudo externo e da comparação de portões; Figura 2; razão de medianas, IC e delta de Cliff; Listagem de reprodução; seções de metodologia e de resultados; script e figura de tempos de `img/`. | Descrição do ciclo, do arquivo de tarefa, do verificador e da **Tabela de desvios** (agora na Seção 3.7), declaradas como sobreposição parcial; fundamentação pedagógica; oito casos de uso; execução de demonstração. |
| QP1 e QP2 empíricas; resumos com números do estudo. | Três QPs conceituais; resumo com a correspondência de Bloom, os oito casos, os cinco desvios e o protocolo. |
| — | **Protocolo expandido** (Seção 6): delineamento cruzado, H1 a H4, medidas, amostra de cerca de 64 estudantes por grupo (76 com 15% de perda, d = 0,5, poder 0,80), modelos mistos, correção de Holm, ameaças, ética e pré-registro; Seção de Discussão sem dados. |

**Efeito nos achados:** E1-2 fechado; E1-4, E1-5, E1-6, E1-7 e E1-8 superados (falavam do estudo removido); E1-9 em parte (protocolo operacionalizado, falta validar os casos de uso com especialistas). **Ainda aguardam:** E1-3 (busca na literatura e RBIE/SOL).

**Observação do editor:** sem os dados, o artigo é uma proposta sem evidência empírica própria. O corpo ficou com cerca de 10,3 páginas, dentro do mínimo do template, graças ao protocolo e à fundamentação; a validade da proposta agora depende de E1-3 e do estudo com estudantes.


---

## Resposta da autoria, rodada 4 (contexto e domínios do kata)

Nova Seção 4, "Os Domínios do Kata", e contexto ampliado na introdução (apoiado em Garousi et al., 2019: lacunas em gestão de configuração, processo e testes).

- **Tabela dos cinco domínios** (`coding`, `devops`, `data-analysis`, `research`, `docs`): artefatos, evidência a abrir, ordem de autoridade, verificação por observação e fraudes que cada adaptador manda caçar. Fonte: `domains/*.md` e o código do kata.
- **Achado conferido no código:** dos 24 tipos de fraude dos adaptadores, só `unauthorized_action` existe no Python, e porque coincide com uma categoria do JUDGE. Os outros 23 são **instruções**, não lógica executável. Fora de `coding`, a parte executável vem de `.kata/config.yaml`. O texto diz isso e tira a consequência para o ensino.
- **Contexto de ensino por domínio**, marcado como hipótese sem teste com estudantes.
- Resumos mencionam os cinco domínios. O corpo passou a cerca de 11,4 páginas.
