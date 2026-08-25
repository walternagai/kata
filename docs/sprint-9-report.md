# Sprint 9 — Evolução — Relatório

> Executado em 2026-08-24, base `e5f3e2e` (pós-S7). Tasks: s9-sondas-linguagens,
> s9-domain-adapters, s9-publish-pypi.

## O que foi feito

1. **s9-sondas-linguagens (FECHADO — verificação)**: as sondas C#/PHP/Swift já
   existiam desde o Sprint 5 (commit 53a1879) — `_CS_PROBES` (judge.py:254),
   `_PHP_PROBES` (:276), `_SWIFT_PROBES` (:300), `_LANGUAGES` com 15 extensões /
   10 linguagens (:323-339), cobertas por `TestProbesPorLinguagem`
   (test_judge.py:2019-2030) e pelo cenário s18-sondas-js (19/19 traps).
   Nada a implementar; fechamento documentado na task.

2. **s9-domain-adapters (IMPLEMENTADO)**: 3 adapters novos criados em `domains/`
   seguindo o TEMPLATE.md:
   - `kata-data-analysis.md` — pandas/SQL/notebooks/dashboards; fraudes:
     unverified_analysis, cherry_picking, data_leak, fabricated_number...
   - `kata-research.md` — fontes primárias/literatura/experimentos; fraudes:
     fabricated_source, hallucinated_behavior, stale_source...
   - `kata-docs.md` — README/docstrings/specs; fraudes: drift_numerico,
     fabricated_command, stale_procedure, orphan_section
   - `DOMAIN_SKILLS` atualizado (skills.py:46), testes `test_domains.py`
     parametrizados para os 4 adapters (53 testes), `make build-skills` gerou
     os SKILL.md nos 2 frontends, symlinks instalados via `make install` /
     `make install-claude-code`, doctor limpo, "quando existir" removido de
     phases/kata.md + frontends gerados.

3. **s9-publish-pypi (PLANO — PARADO, ação irreversível)**: plano completo
   gravado (verificação de nome, bump 0.7.0, build + twine check, ensaio
   TestPyPI, upload real com token, verificação `pipx run kata --version`,
   doc de rota). **Nenhuma ação externa executada** — `auth.authorized: false`,
   aguardando autorização explícita do usuário com quote (token PyPI + nome).

## Verificações

| Check | Resultado |
|---|---|
| ruff check | ✅ |
| ruff format --check | ✅ (24 arquivos) |
| pytest | ✅ 873 (era 839 — +34: parametrização de domínios) |
| check-skills | ✅ (build regenerou frontends) |
| traps adversarial | ✅ 19/19 |
| coverage | 98.9% (gate 70%) |

## Caveats

- `s9-publish-pypi` permanece **approved com ação pendente**: publish é
  irreversível e exige token/nome decididos pelo usuário.
- Os 3 novos adapters têm conteúdo proposto pelo modelo (autoridade/fraudes/
  red lines por domínio) — revisão humana recomendada antes de uso real.
- Tasks em `.kata/` são git-ignored (design do repo); os entregáveis
  versionáveis deste sprint são: `domains/*.md` (3 novos), `skills.py`,
  `tests/test_domains.py`, `phases/kata.md` + frontends gerados.
