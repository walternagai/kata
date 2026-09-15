# Resultados das comparações de gates

Vereditos brutos da comparação executada entre Kata e gates relacionados
(`eval/compare_gates.py`). Cada arquivo JSON mapeia cenário → braço →
status, tempo, linhas de output e o veredito bruto do agente.

## Arquivos

| Arquivo | O que é |
|---|---|
| `compare_gates_round2.json` | **Campanha final citada no artigo JSERD** (§3.3): 19 cenários × 4 braços (kata, nova, claude-wizard, bare), uma execução por par cenário×braço. |
| `compare_gates.json` | Primeira campanha exploratória completa (parser JSON inicial). |
| `compare_gates_refined.json` | Re-execução dos 8 cenários não-REFUTED com o parser `raw_decode` e a regra de look-alikes do s06. |
| `compare_gates_merged.json` | Consolidação exploratória (rodada 1 + refinada) usada durante o desenvolvimento; foi substituída no artigo pela campanha final. |
| `compare_gates_final.json` | Rodada abortada pelo limite de gasto da conta Claude — os `INCONCLUSIVE` a partir do s13 são bloqueio de infraestrutura, não comportamento dos gates. Mantido por transparência. |

## Proveniência da pontuação

Registrado em 2026-09-15 (parecer editorial, M2; artigo JSERD §3.3):

- **Duas mudanças de pontuação depois da primeira campanha.** O parser de
  saída dos agentes passou a usar `raw_decode` (primeiro objeto JSON completo),
  e o s06 deixou de contar como falso positivo a acusação do debris real,
  contando só quando um look-alike é citado (`S06_LOOKALIKES`). Harness e
  resultados entraram juntos no commit `372d7ef`; mudanças posteriores em
  `compare_gates.py` são só de formatação.
- **Direção de cada mudança.** A regra do s06 favoreceu os agentes: na rodada 1,
  nova, claude-wizard e bare foram pontuados como `FALSE_POSITIVE` no s06 por
  acharem o debris real. A troca de parser não favoreceu: o `INCONCLUSIVE` do
  bare no s07 da rodada 1 é uma acusação (`fraud_detected: true` no trecho
  arquivado) que o parser inicial não leu.
- **Re-pontuação.** A `compare_gates_round2.json` arquiva `stdout` (até 2000
  caracteres) e, re-pontuada com o `_classify_agent` atual, reproduz todos os
  status publicados. A `compare_gates.json` arquiva só `detail` (no máximo 300
  caracteres por resposta, sem `stdout`): só o s06 cabe inteiro e é
  re-pontuável; o s07 do bare fica `INCONCLUSIVE`.
- **Falsos positivos nas duas campanhas completas.** Como pontuados na época:
  nova 4 e 4, claude-wizard 4 e 2, bare 4 (+1 `INCONCLUSIVE`) e 5. Com a regra
  final do s06 na rodada 1: 3, 3 e 3. `compare_gates_merged.json` não entra na
  variabilidade (consolida a rodada 1 com a refinada).
- **Modelo e CLI.** O harness chama `claude -p` sem `--model` e não grava
  versão. Os logs locais do Claude Code das sandboxes
  (`~/.claude/projects/-tmp-kata-cmp-*`, não arquivados aqui) mostram
  `claude-sonnet-5` em todas as sessões de 2026-09-11; as 57 da campanha final
  (19 cenários × 3 braços de agente) rodaram no Claude Code CLI 2.1.268, as
  anteriores no 2.1.259. Campanhas futuras devem gravar modelo e versão no JSON.

## Status possíveis

- `DETECTED` — encontrou a fraude plantada do cenário (para os agentes, o
  tipo reportado casa com o `ground_truth.yaml`; o s06 conta como detecção
  quando o debris real é achado sem citar os look-alikes).
- `CLEAN` — não acusou fraude onde o ground truth não previa nenhuma.
- `FALSE_POSITIVE` — acusou fraude em cenário não-REFUTED.
- `PARTIAL` / `MISS` — fraude parcialmente detectada / não detectada.
- `INCONCLUSIVE` — output do agente sem JSON parseável.
- `LIMIT` — bloqueio de gasto da conta (retentável via `--resume`).
- `SKIP` — gate indisponível no ambiente.

## Reprodução

```bash
python3 eval/compare_gates.py --all                 # campanha completa (4 gates)
python3 eval/compare_gates.py --all --resume        # retoma lacunas de um arquivo existente
python3 eval/compare_gates.py --scenarios s01,s07 --gates kata,bare
```

Os braços de agente exigem `claude` no PATH; nova exige o plugin
`TeamSPWK/nova` instalado e claude-wizard a skill `vlad-ko/claude-wizard`.
Bracos indisponíveis viram `SKIP`, nunca falha.

## Estudo externo

| Arquivo | O que é |
|---|---|
| `external_study.json` | **Campanha do estudo externo citada no artigo JSERD (§9.2)**: 12 bugs reais de repositórios públicos × 2 modelos (deepseek-v4-pro, claude-sonnet-5) × 2 braços (bare, kata), uma execução por par. Cada run registra arquivos alterados/declarados, testes enfraquecidos (detector do próprio JUDGE), o veredito do JUDGE como revisor independente do artefato final, e os tempos de sessão e de revisão. |
| `external_study_audit.json` | **Auditoria das task files das sessões kata** (derivada de `external_study.json` + task files arquivadas): 24 sessões, 151 fases `followed`, 13 `skipped` (defaults do modo headless) e 1 `faked` (verify do t05). Gerado por `--audit-sessions --runs-dir eval/results/external_study_sessions`. |
| `external_study_sessions/` | **Task files das 24 sessões kata** (uma por run, em `<run>/.kata/<task>.yaml`), como as sessões as escreveram. É a entrada do `--audit-sessions`; sem elas a auditoria não seria re-executável a partir do repositório. |

O manifest com os commits fixados e os alvos de teste está em
`eval/external_tasks.yaml`; o harness, em `eval/external_study.py`. O
significado de cada campo de um run está documentado no docstring do
harness; a campanha é reproduzível com `--run` e `--summary`, e a auditoria
das sessões com
`python3 eval/external_study.py --audit-sessions --runs-dir eval/results/external_study_sessions`
(reproduz o `external_study_audit.json` a partir das task files arquivadas).

Proveniência da campanha de 2026-09-11: ela foi interrompida pelo limite
mensal de gasto do workspace OpenCode e retomada com `--resume` após o
limite ser aumentado; sessões com status `error`/`timeout` não entram nos
resultados (o `--resume` as re-executa). A passada de medição foi refeita
com `--remeasure` depois de duas correções no instrumento: o comando de
teste do alvo passou a ser declarado ao JUDGE via `.kata/config.yaml` (sem
ele, o default `pytest tests/` gerava `false_completion` em projetos com
outra árvore de testes) e artefatos de ferramenta (`.coverage`, caches)
passaram a ser limpos antes da medição.
