#!/usr/bin/env bash
# Compila o artigo JSERD: paper.tex -> paper.pdf, nesta mesma pasta.
#
# Uso (funciona de qualquer diretório, e também daqui de dentro):
#   bash paper/jserd/compile-paper.sh
#   cd paper/jserd && ./compile-paper.sh
#
# O script mora ao lado do paper.tex e resolve tudo a partir da própria
# localização, então não depende do diretório de onde foi chamado.
#
# Sequência: xelatex, bibtex, e então xelatex repetido até o LaTeX parar de
# pedir nova passada ("Rerun to get cross-references right"). O laço existe
# porque a convergência é uma propriedade do documento, não uma constante:
# este gasta 4 passadas de xelatex (a 1ª, mais 3 depois do bibtex) e a última
# ainda pede Rerun na saída da 3ª, porque a bibliografia desloca as
# referências cruzadas quando o .bbl entra. Aqui as 3 e as 4 passadas
# renderizam idênticas (conferido a 100 dpi, 0 pixel de diferença), então
# rodar uma a menos não corromperia este PDF — mas o número certo depende de
# quantas referências cruzadas a última edição mexeu, e não há como saber sem
# olhar o log. O laço decide pelo log em vez de chutar, com teto de segurança.
#
# O veredito NÃO é o exit code do xelatex. Neste documento o xelatex sai com
# código 1 por um erro do microtype em XeTeX (o recurso de tracking só existe
# no pdftex); o próprio microtype o desliga e segue, e o PDF sai completo.
# `-halt-on-error` abortaria exatamente nesse ponto, antes de gerar saída.
# A verificação aqui é sobre o log e o PDF: um erro que não seja o do
# microtype reprova, referência indefinida reprova, e um log que continue
# pedindo Rerun depois do teto também.
#
# Os auxiliares (aux, bbl, blg, log, out) são regerados a cada execução e
# estão no .gitignore; só o PDF é versionado.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# O script mora em paper/jserd/, ao lado do paper.tex: a pasta do paper é a
# dele mesmo, e todo caminho abaixo sai daqui — por isso tanto faz chamar da
# raiz do repositório, de dentro da pasta ou de qualquer outro diretório.
PAPER_DIR="$SCRIPT_DIR"
JOB="paper"
LOG="$PAPER_DIR/$JOB.log"
PDF="$PAPER_DIR/$JOB.pdf"

# Único erro conhecido e aceito: qualquer outro "!" no log reprova.
KNOWN_ERROR="tracking feature only works with pdftex"

# Teto de passadas: este documento converge em 4; 8 é margem folgada e ainda
# corta um laço que não converge (referência cruzada recém-introduzida).
MAX_RUNS=8

if ! command -v xelatex >/dev/null 2>&1; then
    echo "Erro: xelatex não encontrado. Instale o TeX Live (texlive-xetex)." >&2
    exit 1
fi
if ! command -v bibtex >/dev/null 2>&1; then
    echo "Erro: bibtex não encontrado. Instale o TeX Live (texlive-bibtex-extra)." >&2
    exit 1
fi
if [[ ! -f "$PAPER_DIR/$JOB.tex" ]]; then
    echo "Erro: $PAPER_DIR/$JOB.tex não existe." >&2
    exit 1
fi

cd "$PAPER_DIR"

# O PDF é o artefato de submissão: se a compilação falhar, o anterior volta.
# Sem isto, um erro no meio deixaria um PDF parcial no lugar do bom.
BACKUP=""
if [[ -f "$PDF" ]]; then
    BACKUP="$(mktemp)"
    cp "$PDF" "$BACKUP"
fi

fail() {
    echo "" >&2
    echo "❌  $1" >&2
    if [[ -n "$BACKUP" ]]; then
        cp "$BACKUP" "$PDF"
        rm -f "$BACKUP"
        echo "    paper.pdf anterior restaurado (nada parcial fica no lugar)." >&2
    else
        echo "    Nenhum paper.pdf anterior para restaurar." >&2
    fi
    exit 1
}

# Build determinístico: auxiliares de uma compilação anterior não podem vazar
# para esta (um .bbl velho esconderia uma falha do bibtex).
rm -f "$JOB.aux" "$JOB.bbl" "$JOB.blg" "$JOB.log" "$JOB.out" "$JOB.xdv"

echo "▶ xelatex (passada 1)"
xelatex -interaction=nonstopmode "$JOB.tex" >/dev/null 2>&1 || true

if [[ ! -f "$JOB.aux" ]]; then
    fail "xelatex não produziu $JOB.aux — a primeira passada não completou"
fi

echo "▶ bibtex"
bibtex_out="$(bibtex "$JOB" 2>&1)" || {
    printf '%s\n' "$bibtex_out" >&2
    fail "bibtex falhou"
}
if [[ ! -f "$JOB.bbl" ]]; then
    fail "bibtex não produziu $JOB.bbl"
fi
if grep -qE "I couldn't open|error message" <<<"$bibtex_out"; then
    printf '%s\n' "$bibtex_out" >&2
    fail "bibtex relatou erro (acima)"
fi

# Laço de convergência: repete enquanto o LaTeX pedir nova passada.
runs=1
while (( runs < MAX_RUNS )); do
    runs=$((runs + 1))
    echo "▶ xelatex (passada $runs)"
    xelatex -interaction=nonstopmode "$JOB.tex" >/dev/null 2>&1 || true
    if ! grep -q "Rerun to get cross-references right" "$LOG"; then
        break
    fi
done

# ── verificação ──────────────────────────────────────────────────────────
# 1. a última passada fechou as referências cruzadas
if grep -q "Rerun to get cross-references right" "$LOG"; then
    fail "o log continua pedindo nova passada após $runs passadas (teto: $MAX_RUNS)"
fi

# 2. erros: tudo que começa com "!" no log, menos o do microtype
real_errors="$(grep '^!' "$LOG" | grep -vF "$KNOWN_ERROR" || true)"
if [[ -n "$real_errors" ]]; then
    printf '%s\n' "$real_errors" >&2
    fail "erro novo no log (acima)"
fi

# 3. o PDF foi escrito, e com quantas páginas
pages="$(sed -n 's/.*Output written on .* (\([0-9][0-9]*\) page.*/\1/p' "$LOG" | tail -1)"
if [[ -z "$pages" ]]; then
    fail "o log não registra 'Output written' — o PDF não foi gerado"
fi

# 4. referências e citações resolvidas
if grep -qi 'undefined' "$LOG"; then
    grep -i 'undefined' "$LOG" >&2
    fail "referência ou citação indefinida"
fi

# ── resumo ───────────────────────────────────────────────────────────────
[[ -n "$BACKUP" ]] && rm -f "$BACKUP"

size="$(du -h "$PDF" | cut -f1)"
echo ""
echo "✅  $JOB.pdf — $pages página(s), $size, $runs passada(s) de xelatex"
echo "    erros: 0 novos (1 conhecido: microtype tracking em XeTeX)"
echo "    referências indefinidas: 0"
