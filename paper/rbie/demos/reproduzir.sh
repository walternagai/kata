#!/usr/bin/env bash
# Reproduz as execuções reais do kata descritas no artigo (Seção 3.5 e Apêndice A) em projetos temporários.
# Requisitos: python3 com ruff, pytest, pytest-cov e pyyaml; git; docker (Execução 7); rede (Execução 8). Não faz nenhum `git commit`.
#   KATA_SRC   caminho do src/ do kata (padrão: ../../../src deste repositório)
#   PYTHON     interpretador (padrão: python3)
#   PYTHON_SEM_FERRAMENTAS  interpretador sem ruff e pytest, para a primeira tentativa da Execução 1 (opcional)
# Saídas em saidas/*.txt
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${KATA_SRC:-$AQUI/../../../src}"
export NO_COLOR=1
PY="${PYTHON:-python3}"
OUT="$AQUI/saidas"; mkdir -p "$OUT"
limpa() { sed 's/\x1b\[[0-9;]*m//g'; }
kata() { "$PY" -m kata "$@" 2>&1 | limpa; }
codigo() { "$PY" -m kata "$@" >/dev/null 2>&1; echo "exit=$?"; }
TMP="$(mktemp -d)"; echo "projetos em $TMP"

# ---------- projeto 1: calculadora (domínio coding) ----------
mkdir -p "$TMP/calc/src" "$TMP/calc/tests"; cd "$TMP/calc" && git init -q
cat > src/calculadora.py <<'PY'
def dividir(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("divisão por zero")
    return a / b
PY
cat > tests/test_calculadora.py <<'PY'
import pytest

from src.calculadora import dividir


def test_dividir_basico():
    assert dividir(6, 3) == 2


def test_dividir_por_zero():
    with pytest.raises(ValueError):
        dividir(1, 0)
PY
touch src/__init__.py; echo ".kata/" >> .git/info/exclude; git add -A

# Execução 1: ciclo completo (interativo, respostas de conduzir.py)
"$PY" "$AQUI/conduzir.py" --init dividir-por-zero >  "$OUT/01-ciclo.txt"
"$PY" "$AQUI/conduzir.py" --task dividir-por-zero >> "$OUT/01-ciclo.txt"
kata --audit --task dividir-por-zero > "$OUT/01b-audit-limpo.txt"

# Execução 2: JUDGE com conflito sem resolução, depois com resolução
kata --judge --task dividir-por-zero > "$OUT/02a-judge-refuted.txt"; codigo --judge --task dividir-por-zero >> "$OUT/02a-judge-refuted.txt"
"$PY" - <<'PY'
import yaml
p = ".kata/dividir-por-zero.yaml"; d = yaml.safe_load(open(p))
d["intent"]["conflict_resolution"] = "o teste prevalece sobre o código atual (ordem: usuário > spec > testes > código); o código passa a levantar ValueError"
open(p, "w").write(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
PY
kata --judge --task dividir-por-zero > "$OUT/02b-judge-verified.txt"; codigo --judge --task dividir-por-zero >> "$OUT/02b-judge-verified.txt"

# Execução 3: teste enfraquecido (corpo vira pass)
cat > tests/test_calculadora.py <<'PY'
import pytest

from src.calculadora import dividir


def test_dividir_basico():
    assert dividir(6, 3) == 2


def test_dividir_por_zero():
    pass
PY
git add -A
kata --judge --task dividir-por-zero > "$OUT/03a-judge-weakened.txt"; codigo --judge --task dividir-por-zero >> "$OUT/03a-judge-weakened.txt"
kata --check-only > "$OUT/03b-check-only.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/03b-check-only.txt"

# Execução 4: auditoria de um arquivo de tarefa escrito à mão, com fases vazias
mkdir -p "$TMP/aluno/.kata"; cd "$TMP/aluno" && git init -q
cat > .kata/entrega-aluno.yaml <<'Y'
task: entrega-aluno
status: approved
domain: coding
fit: {trivial: false, route: code-loop, reason: '', answered: true}
think: {problem: '', answered: true}
simplify: {answered: true}
intent: {code_does: '', answered: true}
surgical: {answered: true}
verify: {success_criteria_met: true, ruff_clean: false, tests_pass: false, coverage_pass: false}
twins: {defect_fixed: true, searched: false}
Y
kata --audit --task entrega-aluno > "$OUT/04-audit-faked.txt"; "$PY" -m kata --audit --task entrega-aluno >/dev/null 2>&1; echo "exit=$?" >> "$OUT/04-audit-faked.txt"

# Execução 5: domínio docs, verificação declarada pelo projeto (config.yaml)
mkdir -p "$TMP/docs/.kata"; cd "$TMP/docs" && git init -q
cp "$AQUI/docs-readme/verifica_doc.py" "$AQUI/docs-readme/README.md" .
cp "$AQUI/docs-readme/config.yaml" .kata/config.yaml
git add -A
kata --check-only > "$OUT/05a-docs-reprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/05a-docs-reprovado.txt"
sed -i 's/--auditar/--audit/' README.md
kata --check-only > "$OUT/05b-docs-aprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/05b-docs-aprovado.txt"

# Execução 6: domínio data-analysis, remoção silenciosa de linhas (verificação declarada pelo projeto)
mkdir -p "$TMP/dados/.kata"; cd "$TMP/dados" && git init -q
cp "$AQUI/dados-csv/dados.csv" "$AQUI/dados-csv/verifica_dados.py" .
cp "$AQUI/dados-csv/analise_v1.py" analise.py
cp "$AQUI/dados-csv/config.yaml" .kata/config.yaml
git add -A
kata --check-only > "$OUT/06a-dados-reprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/06a-dados-reprovado.txt"
cp "$AQUI/dados-csv/analise_v2.py" analise.py; git add -A
kata --check-only > "$OUT/06b-dados-aprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/06b-dados-aprovado.txt"

# Execução 7: domínio devops, verificação com `docker compose config` e regras do adaptador executáveis
mkdir -p "$TMP/infra/.kata"; cd "$TMP/infra" && git init -q
cp "$AQUI/infra-compose/verifica_infra.py" .; cp "$AQUI/infra-compose/docker-compose_v1.yml" docker-compose.yml
cp "$AQUI/infra-compose/config.yaml" .kata/config.yaml; git add -A
kata --check-only > "$OUT/07a-infra-reprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/07a-infra-reprovado.txt"
cp "$AQUI/infra-compose/docker-compose_v2.yml" docker-compose.yml; git add -A
kata --check-only > "$OUT/07b-infra-aprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/07b-infra-aprovado.txt"

# Execução 8: domínio research, fontes que precisam resolver no Crossref (exige rede)
mkdir -p "$TMP/pesquisa/.kata"; cd "$TMP/pesquisa" && git init -q
cp "$AQUI/pesquisa-fontes/verifica_fontes.py" .; cp "$AQUI/pesquisa-fontes/relatorio_v1.md" relatorio.md
cp "$AQUI/pesquisa-fontes/config.yaml" .kata/config.yaml; git add -A
kata --check-only > "$OUT/08a-pesquisa-reprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/08a-pesquisa-reprovado.txt"
cp "$AQUI/pesquisa-fontes/relatorio_v2.md" relatorio.md; git add -A
kata --check-only > "$OUT/08b-pesquisa-aprovado.txt"; "$PY" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/08b-pesquisa-aprovado.txt"

# Variante da Execução 3: teste esvaziado SEM a importação que sobra (só o enfraquecimento é acusado)
mkdir -p "$TMP/calc3/src" "$TMP/calc3/tests" "$TMP/calc3/.kata"; cd "$TMP/calc3" && git init -q; echo ".kata/" >> .git/info/exclude
cp "$TMP/calc/src/calculadora.py" src/; touch src/__init__.py
cat > tests/test_calculadora.py <<'PY'
from src.calculadora import dividir


def test_dividir_basico():
    assert dividir(6, 3) == 2


def test_dividir_por_zero():
    pass
PY
cat > .kata/t.yaml <<'Y'
task: t
status: approved
domain: coding
fit: {trivial: false, route: code-loop, reason: x, answered: true}
think: {problem: x, answered: true}
simplify: {minimum_code: true, answered: true}
intent: {code_does: a, check_expects: a, spec_says: a, all_agree: true, answered: true}
surgical: {files: [{path: src/__init__.py, necessary: true}, {path: src/calculadora.py, necessary: true}, {path: tests/test_calculadora.py, necessary: true}], answered: true}
verify: {ruff_clean: true, tests_pass: true, coverage_pass: true, coverage_pct: 75.0, success_criteria_met: true}
twins: {searched: true, defect_fixed: false}
Y
git add -A
kata --judge --task t > "$OUT/03c-judge-weakened-sem-import.txt"; codigo --judge --task t >> "$OUT/03c-judge-weakened-sem-import.txt"

# Primeira tentativa da Execução 1: interpretador sem ruff e pytest (defina PYTHON_SEM_FERRAMENTAS)
if [ -n "${PYTHON_SEM_FERRAMENTAS:-}" ]; then
  cd "$TMP/calc" && "$PYTHON_SEM_FERRAMENTAS" -m kata --check-only 2>&1 | limpa > "$OUT/01c-sem-ferramentas.txt"; "$PYTHON_SEM_FERRAMENTAS" -m kata --check-only >/dev/null 2>&1; echo "exit=$?" >> "$OUT/01c-sem-ferramentas.txt"
else
  echo "(defina PYTHON_SEM_FERRAMENTAS para reproduzir a primeira tentativa da Execução 1)"
fi
echo "saídas em $OUT"
