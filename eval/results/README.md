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
