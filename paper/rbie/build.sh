#!/usr/bin/env bash
# Compila o artigo da RBIE 2026. Requer xelatex, bibtex e pygmentize no PATH (minted exige -shell-escape).
#   ./build.sh        gera main.pdf (versão identificada)
#   ./build.sh anon   gera main-anon.pdf (submissão anônima: sem autoria, afiliação, URL nem metadados)
set -euo pipefail
cd "$(dirname "$0")"
alvo=main
if [ "${1:-}" = "anon" ]; then
  alvo=main-anon
  sed 's/\\anonfalse/\\anontrue/' main.tex > "$alvo.tex"
fi
xelatex -shell-escape -interaction=nonstopmode "$alvo.tex" >/dev/null || true
bibtex "$alvo" >/dev/null || true
xelatex -shell-escape -interaction=nonstopmode "$alvo.tex" >/dev/null || true
xelatex -shell-escape -interaction=nonstopmode "$alvo.tex" | grep -E "^!|Warning: Citation|undefined" || true
pdfinfo "$alvo.pdf" | grep -E "Pages|Author"
if [ "$alvo" = "main-anon" ]; then
  rm -f "$alvo.tex" "$alvo".{aux,bbl,blg,log,out,toc}; rm -rf "_minted-$alvo"
  echo "Conferir vazamento: pdftotext $alvo.pdf - | grep -i -E 'nagai|unifei|walternagai'"
fi
