# Parecer editorial, rodada 4 — RBIE

**Versão avaliada:** commit `4470b19` (19 páginas, cerca de 13,4 de corpo, cerca de 9.000 palavras)
**Decisão:** **revisão menor**, condicionada a E4-1, E4-2, E4-5 e E4-8
**Task:** `.kata/rbie-revisao-editorial-rodada4.yaml` (14 achados: 5 médios e 9 baixos; 7 `[R]` e 7 `[E]`)

Nenhum achado bloqueia a publicação. A fragilidade principal continua sendo a falta de acesso ao material da verificação técnica, que a autoria decidiu não conceder e que o artigo declara.

## O que foi conferido sem divergência
O funil da busca (126, 75, 52, 27 e 25; 18, 4, 3 e 2) bate com os arquivos de `busca/`; todos os elementos são referenciados antes de aparecer; não há referência sem rótulo; "a autoria" não aparece fora das declarações; a versão anônima não vaza nome.

## Correções (regressões e erros de forma)
| ID | Problema |
|---|---|
| E4-1 | "Sete execuções adicionais estão no Apêndice A." aparece duas vezes seguidas (efeito da reescrita automática). |
| E4-2 | O parágrafo "Produção nacional" perdeu o título em itálico. |
| E4-3 | "Uma são as quatro diretrizes…" (concordância). |
| E4-4 | "O que o artigo não responde" repete "Também não sabemos" e perdeu o referente de "duas primeiras perguntas". |
| E4-5 | Referências: títulos com siglas em minúsculas (`ai`, `llms`, `ias`, `chatgpt`) e partículas de nomes viradas iniciais (`S. d.`, `G. d.`); "Anderson Da Silva" como nome próprio. |
| E4-6 | Listagens 3 a 7 só citadas por faixa. |
| E4-7 | `VERIFICACAO-CITACOES.md` desatualizado. |

## Metodologia do protocolo
- **E4-8** A condição kata é `--plan` mais `--check-only`, mas a H1 mede "justifica mais arquivos" (fase SURGICAL, ausente) e o Caso 2 usa `--judge` (também ausente).
- **E4-9** A H2, a principal, não tem mecanismo declarado, e as proporções de 30% contra 15% não têm base.
- **E4-10** A perda de 15% é igual nos dois grupos, mas a condição kata dá mais trabalho e pode perder mais gente.

## Redação e estrutura
- **E4-11** A última frase do resumo resume mal as Execuções 5 a 8.
- **E4-12** "Problema conhecido dos modelos de linguagem, a invenção de fontes" sem citação.
- **E4-13** O protocolo da busca ocupa cerca de 330 palavras do corpo; mover para um Apêndice B.
- **E4-14** O apêndice tem oito listagens (cerca de quatro páginas); reduzir.

---

## Resposta da autoria: correções diretas (E4-1 a E4-7)

| ID | O que foi feito |
|---|---|
| E4-1 | Frase duplicada removida. |
| E4-2 | Título "Produção nacional." restaurado. |
| E4-3 | "A primeira é o conjunto das quatro diretrizes…" e "A segunda é o Método Fable". |
| E4-4 | Uma só lista de incógnitas; o protocolo cobre aprendizagem, retenção e tempo. |
| E4-5 | Siglas protegidas nos títulos e partículas passadas ao sobrenome. A lista agrupa "da Silva" sob D, o que o estilo `apalike-sol` não permite ajustar. |
| E4-6 | Cada execução do Apêndice A cita a sua listagem. |
| E4-7 | `VERIFICACAO-CITACOES.md` atualizado. |

**Resolvidos por decisão da autoria:** E4-8 e E4-9. A condição kata passa a incluir SURGICAL e JUDGE; a H1 ganha o campo "arquivos alterados e justificativa" no formulário do controle; a H2 declara o mecanismo (critério de pronto antes do código mais o aviso do JUDGE), com o veredito fora da medida; a ameaça dos desvios do JUDGE foi acrescentada. As proporções de 30% contra 15% seguem como suposição a calibrar no piloto.

**Resolvidos por decisão da autoria (alternativas 10A a 14A):** E4-10 (perda por condição, análise de sensibilidade e ameaça), E4-11 (frase dos resumos), E4-12 (frase sem fonte trocada, sem citação nova), E4-13 (protocolo da busca no Apêndice B) e E4-14 (Execuções 5 a 8 numa só listagem; a Execução 4 foi mantida, por ser curta).

**Ainda abertos:** nenhum.
