# Sprint 8 — Robustez e DX — Relatório

> Executado em 2026-08-24, HEAD `fa1a0a2`. Tasks: s8-juiz-batch-tasks, s8-fechar-fix-m3-m4, s8-features-roadmap.

## O que foi feito

1. **Auditoria JUDGE batch** (s8-juiz-batch-tasks): 35 tasks julgadas com `--judge` →
   7 VERIFIED, 26 REFUTED, 2 UNVERIFIABLE. **Nenhuma regressão real** — os REFUTED
   são falsos positivos estruturais: (a) tasks pré-R14 sem `approved_commit` diffam
   até HEAD (com commits posteriores: fixtures de trap, testes, docs); (b)
   `surgical.files` com paths de diretório (s4-testes-divida, s5-docs-build) não é
   expandido pelo judge. Detalhes em `docs/audit-judge-2026.md` e
   `.kata/judge-batch-2026.md`.
2. **Corrigido `.kata/code-review-round-9.yaml`** (ilegível — indentação quebrada;
   impossível de julgar; agora parseia).
3. **Âncoras `refs/kata/base/*`** gravadas para as tasks desta sessão
   (code-review-round-12, npx-install, round-9, s8-juiz-batch-tasks).
4. **fix-m3-m4 arquivada**: M3/M4 já implementados pelo commit `e9f4b35`
   (collect_unverifiable_claims judge.py:439, _detect_intent_owed cli.py:1103,
   _detect_twins_owed cli.py:1149) — status `archived`, `approved_commit: 21fcb7d`.
5. **Features roadmap**: `docs/features-roadmap.md` — inventário das features
   existentes (derivado do código) + roadmap de pendências + não-objetivos.

## Verificações

| Check | Resultado |
|---|---|
| ruff check | ✅ |
| ruff format --check | ✅ |
| pytest | ✅ 839 |
| check-skills | ✅ |
| coverage | 98.9% (gate 70%) |

## Achados que viram fix-round-13

- **Falso positivo estrutural**: judge não expande paths de diretório em
  `surgical.files` (2 tasks com approved_commit ainda REFUTED).
- **Backfill `approved_commit`** nas tasks pré-R14 (26 tasks REFUTED por diff até HEAD).

## Caveats

- Tasks em `.kata/` são git-ignored (design do repo) — os entregáveis versionáveis
  são `docs/audit-judge-2026.md`, `docs/features-roadmap.md`, este relatório e o
  conserto do YAML round-9 (que também é git-ignored; registrado aqui).
- `npx-install` e `code-review-round-12` ficaram UNVERIFIABLE no batch (sem âncora
  no momento da execução); âncoras gravadas depois — re-julgamento fix-round-12 → VERIFIED.
