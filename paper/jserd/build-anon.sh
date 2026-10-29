#!/usr/bin/env bash
# Gera paper-anon.pdf (submissão anônima do JSERD): paper.tex com \anontrue.
set -euo pipefail
cd "$(dirname "$0")"
sed 's/\\anonfalse/\\anontrue/' paper.tex > paper-anon.tex
cp paper.bib paper-anon.bib 2>/dev/null || true
sed -i 's/\\bibliography{paper}/\\bibliography{paper}/' paper-anon.tex
xelatex -interaction=nonstopmode paper-anon.tex >/dev/null || true
bibtex paper-anon >/dev/null || true
xelatex -interaction=nonstopmode paper-anon.tex >/dev/null || true
xelatex -interaction=nonstopmode paper-anon.tex >/dev/null || true
xelatex -interaction=nonstopmode paper-anon.tex | grep -E "^!|undefined" || true
pdfinfo paper-anon.pdf | grep -E "Pages|Author"
rm -f paper-anon.tex paper-anon.bib paper-anon.{aux,bbl,blg,log,out,toc}
echo "Conferir vazamento: pdftotext paper-anon.pdf - | grep -i -E 'nagai|unifei|orcid'"
