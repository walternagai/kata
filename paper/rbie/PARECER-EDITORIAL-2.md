# Parecer editorial, rodada 2 — RBIE

**Manuscrito:** Kata: Ferramenta de Verificação Executável para Ensinar Desenvolvimento de Software com Agentes de Inteligência Artificial
**Versão avaliada:** commit `705f99d` (14 páginas, cerca de 11,4 de corpo; resumos de 265, 240 e 273 palavras)
**Decisão:** **Revisão maior, mais estreita que a da rodada 1**
**Task de origem:** `.kata/rbie-revisao-editorial-rodada2.yaml` (13 achados `E2-m`; `[R]` = medido nesta rodada, `[E]` = leitura crítica)

---

## O que melhorou desde a rodada 1

- O artigo diz o que é (proposta de ferramenta e de protocolo) e não afirma efeito sobre a aprendizagem.
- Os números dos resumos conferem com o corpo: cinco desvios, oito casos de uso, cinco domínios.
- O protocolo ganhou hipóteses, medidas, margem de não inferioridade, ameaças, ética e pré-registro.
- Todas as 36 referências são citadas, e a verificação de citações (rodada anterior) corrigiu as atribuições erradas.
- Sobreposição com o JSERD reduzida: os dados saíram.

## O que ainda bloqueia

| ID | Problema | Pedido |
|---|---|---|
| E2-1 | **Cruzado × H3.** No cruzado todas as equipes usam o kata, então a retenção não se compara entre grupos; e a intervenção pedagógica deixa efeito residual. | Grupos paralelos para H2 e H3; cruzado só para H1, com a ordem como fator. |
| E2-2 | **Potência.** 76 por grupo ignora a correção de Holm. Recalculado: 62,8 sem correção, **89,2** com Holm no pior caso (alfa 0,0125), cerca de **105** com 15% de perda. H2 é proporção, H3 é de não inferioridade (49,5 por grupo) e a atribuição por turma pede efeito de agrupamento. | Calcular por hipótese; corrigir o número nos três resumos e na conclusão. |
| E2-3 | **Validade da ferramenta inacessível.** Sem os dados, nenhuma afirmação de que o verificador funciona tem evidência no artigo, e o "manuscrito separado" não é citado nem acessível. | Citar como preprint, anexar versão anonimizada ou resumir o que foi verificado; rotular a Seção 3 como descrição do projeto. |
| E2-4 | **Literatura** (pendência da rodada 1). Sem busca declarada; uma referência da área no Brasil. | Registrar a busca, incluir RBIE/SBIE e qualificar "nenhum combina". |
| E2-5 | **Citação errada que sobrou.** O Caso 1 diz que quem tem dificuldades metacognitivas "se beneficia menos" (Prather et al., 2024); a fonte diz que as dificuldades persistem e podem ser agravadas. | Corrigir já. |
| E2-6 | **Registro de adaptador ausente** descrito como automático. No código, o Python só audita `preflight.skills_missing`; quem escreve é o agente, por instrução. A graduação é uma entrada `preflight`, não uma por fase. | Reescrever. |

## Recomendados

- **E2-7** Os cinco desvios não se reproduzem a partir do artigo; indicar os cenários (s12, s19, s20, s22) e arquivar o projeto de demonstração.
- **E2-8** Os resumos destacam cinco domínios, mas 23 dos 24 tipos de fraude dos adaptadores não existem no Python e quatro domínios não foram avaliados; dizer isso no resumo ou restringir o destaque a programação.
- **E2-9** Casos de uso e rubrica sem consulta a docentes; validar com especialistas ou limitar a proposta aos casos 1, 2 e 7.

## Ajustes menores

- **E2-10** 29 frases com mais de 40 palavras (máximo de 80); "ressalva" 17 vezes.
- **E2-11** Tabela 3 em `\footnotesize` (template: `\small`); falta termo de domínio nas palavras-chave; "Ensinar" no título promete mais do que o artigo mostra.
- **E2-12** Inferência da autoria colada à frase de Garousi et al. (2019) na introdução.
- **E2-13** Pendências herdadas: literatura, fonte primária de Karpathy, DOI do commit, repositório anonimizado, "a autoria" contra "nós".

## Observação do editor

Sem os dados, a Seção 3 descreve intenção e não comportamento verificado, e o único resultado do verificador no artigo é a lista de desvios, que é a parte desfavorável. Isso é honesto, mas deixa o revisor sem como julgar a ferramenta. E2-3 é o ponto de maior impacto na aceitação, e E2-1 e E2-2 são erros de desenho que se corrigem sem nenhum dado novo.

---

## Resposta da autoria à rodada 2 (E2-1, E2-2 e E2-5)

| ID | Situação | O que foi feito |
|---|---|---|
| E2-5 | feito | Caso 1: "as dificuldades metacognitivas persistem e a ferramenta pode agravá-las" (Prather et al., 2024). |
| E2-1 | feito | Grupos paralelos como desenho principal; atribuição individual ou por equipe dentro de cada turma, com o mesmo docente nas duas condições. O cruzado foi descartado como desenho principal (a H3 exige um grupo sem o kata, e a intervenção deixa efeito residual) e só cabe como análise secundária da H1. Risco novo declarado: contaminação entre colegas. |
| E2-2 | feito | Amostra por hipótese (tabela de amostra): H2 é a principal, com nível de 0,05 e 30% contra 15% de falha oculta supostos, o que dá **121 por grupo (142 com 15% de perda)**; H1, H3 e H4 são secundárias, com Holm entre três (84, 71 e 33). Com equipes de três e correlação intraclasse suposta de 0,2, o plano sobe a 199. Resumos e conclusão passam de 76 para 142. |

O número da rodada 3 (76 por grupo) era inválido: ignorava a correção de Holm. Os efeitos da Tabela 7 são suposições de planejamento e pedem um estudo-piloto antes da coleta.

**Ainda abertos:** E2-3, E2-4, E2-6, E2-7, E2-8, E2-9 e os menores.

---

## Resposta da autoria: execuções reais com o kata

Quatro execuções reais novas (Apêndice A), além do ciclo completo da Seção 3.3: JUDGE com conflito sem resolução e depois com uma frase (`REFUTED` e depois `VERIFIED`), teste esvaziado (`REFUTED` por `weakened_checks`, com `pytest` e cobertura passando), auditoria de arquivo à mão (7 fases `faked`) e domínio `docs` com verificação declarada em `config.yaml` (rejeitado e depois aprovado).

- Novo diretório `paper/rbie/demos/` com `reproduzir.sh`, `conduzir.py`, o projeto de documentação e as saídas completas; o script não faz nenhum `git commit`.
- **E2-7** fica em parte atendido (projeto de demonstração arquivado); falta apontar na tabela de desvios o cenário de cada desvio.
- As execuções confirmam por execução dois pontos antes só lidos no código: o JUDGE refuta o conflito sem resolução, e uma frase qualquer basta para o veredito virar `VERIFIED`.
