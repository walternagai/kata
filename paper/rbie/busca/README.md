# Busca sistemática curta para os Trabalhos Relacionados

Executada em 3 de outubro de 2026. O artigo resume o protocolo na Seção 2 ("Critérios de seleção").

- `busca_sol.py`: roda as oito *strings* em português nos veículos do SOL (SBIE, WEI, EDUCOMP e EDUCOMP estendido) e na RBIE (pelo Crossref, ISSN 2317-6121, porque a busca do site da RBIE devolveu "Nenhum resultado encontrado" até para "programação"). Grava `resultados_busca.csv` e `contagens.txt`.
- `triagem.csv`: a decisão sobre cada um dos 52 artigos distintos no período (2022 a 2026), com o tema ou o motivo da exclusão.
- `bib_citados.json`, `abstracts_triagem.json`: metadados e resumos usados na triagem e nas citações.

**Funil:** 126 registros brutos, 75 distintos, 52 no período, 27 incluídos, 25 excluídos.

**Critérios de inclusão:** (a) IA generativa no ensino de programação ou de engenharia de software; (b) correção automática, retorno e juízes online; (c) ensino de teste de software; (d) integridade e uso aceitável de IA. **Exclusão:** outro tema.

**Limites:** triagem por uma única pessoa, com apoio de um assistente de IA, sem concordância entre avaliadores; strings só em português; cinco veículos; a RBIE foi consultada por um meio diferente (Crossref, 25 registros por string, filtro por palavra no título); resumos de 7 artigos foram lidos só no início, e um artigo não tem resumo.
