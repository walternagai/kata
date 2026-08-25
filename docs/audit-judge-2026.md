# Auditoria JUDGE — todas as tasks de .kata/ (Sprint 8, HEAD fa1a0a2)

> Batch: 35 tasks julgadas com `kata --task <nome> --judge` (8 tasks de planejamento
> S7/S8/S9 ficaram fora — não têm ciclo). Executado em 2026-08-24.

## Vereditos

| Veredito | Qtd | Tasks |
|---|---|---|
| VERIFIED | 7 | fix-judge-delecao-teste, fix-judge-yaml-malformado, fix-scope-creep-estrutural, fix-round-12, s1-judge-falsos-positivos, s2-judge-robusto, s3-cli-endurecido |
| REFUTED | 26 | todas as code-review-round-* (3-12), complete-code-review, features-list, fix-fable-gaps, fix-m3-m4, fix-review-round-3, fix-round-10/11/4/8, s1-quick-wins, s2-tensao-judge, s3-cobertura, s4-robustez, s4-testes, s5-docs, s5-evolucao, code-review-backlog |
| UNVERIFIABLE | 2 | code-review-round-12, npx-install (sem âncora no batch; âncoras gravadas depois) |
| YAML ilegível | 1 | code-review-round-9 (indentação quebrada — corrigida nesta rodada) |

## Causa-raiz (por classe)

1. **scope_creep — falso positivo estrutural (26/26 REFUTED)**: tasks sem
   `approved_commit` (pré-R14) diffam `base..HEAD`; o HEAD inclui commits
   posteriores (fixtures de trap s01-s19, testes, docs, CI) que o juiz acusa
   como "não declarados". É a limitação documentada no R14/commit 5fb099c —
   **não é regressão real do código**.
2. **weakened_checks — fixtures de trap plantados**: fixtures de
   `eval/scenarios/*/fixture` contêm fraudes deliberadas (pass, assert True,
   it.skip). Quando o diff da task abrange esses fixtures, o judge as acusa —
   esperado, não regressão.
3. **s4-testes-divida / s5-docs-build (approved_commit ok, mesmo assim REFUTED)**:
   `surgical.files` usa **paths de diretório** (ex.: `eval/scenarios/s17-approved-commit/`)
   que não casam com os arquivos do diff → todos os arquivos internos contam
   como não declarados. **Falso positivo estrutural do judge**: ele não expande
   diretórios declarados em `surgical.files` (registrado como achado para
   fix-round 13; fora do escopo desta auditoria).

## Regressões reais

**Nenhuma.** Tasks com approved_commit correto e files declarados por arquivo
(fix-round-12, fix-scope-creep-estrutural, s1/s2/s3, fix-judge-*) verificam
sem fraude. Os REFUTED são as 2 classes de falso positivo acima.

## Ações desta rodada

- `.kata/code-review-round-9.yaml` corrigido (ilegível → parseia).
- Âncoras `refs/kata/base/*` gravadas para code-review-round-12, npx-install,
  code-review-round-9, s8-juiz-batch-tasks (UNVERIFIABLE → VERIFIED/REFUTED).

## Para o fix-round-13 (registrado, fora do escopo)

- Judge deve expandir paths de diretório em `surgical.files` (bate com git diff
  arquivo a arquivo) — senão tasks com declaração por dir sempre colhem REFUTED.
- Considerar marcar `approved_commit` em tasks antigas pós-R14 (backfill).
