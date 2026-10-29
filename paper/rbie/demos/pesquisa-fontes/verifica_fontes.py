"""Verificações do domínio research para o kata: toda afirmação tem DOI que resolve e título que confere."""
import json
import re
import sys
import urllib.error
import urllib.request

LINHA = re.compile(r'^- (?P<texto>.+?)\.? \[(?P<doi>10\.[^\]]+)\] "(?P<titulo>.+)"$')


def afirmacoes():
    return [l for l in open("relatorio.md").read().splitlines() if l.startswith("- ")]


def titulo_crossref(doi):
    try:
        with urllib.request.urlopen(f"https://api.crossref.org/works/{doi}", timeout=20) as r:
            return json.load(r)["message"]["title"][0]
    except (urllib.error.URLError, KeyError, ValueError):
        return None


modo = sys.argv[1]
if modo == "lint":
    ok = open("relatorio.md").read().startswith("# ")
    print("título presente" if ok else "sem título"); sys.exit(0 if ok else 1)
if modo == "test":
    problemas = []
    for l in afirmacoes():
        m = LINHA.match(l)
        if not m:
            problemas.append(f"afirmação sem fonte: {l[2:60]}…"); continue
        real = titulo_crossref(m["doi"])
        if real is None:
            problemas.append(f"DOI não resolve: {m['doi']}")
        elif real.casefold().strip() != m["titulo"].casefold().strip():
            problemas.append(f"título não confere em {m['doi']}")
    print("; ".join(problemas) if problemas else "todas as fontes resolvem e conferem")
    sys.exit(1 if problemas else 0)
if modo == "cobertura":
    todas = afirmacoes(); com = [l for l in todas if LINHA.match(l)]
    print(f"FONTES {100 * len(com) / len(todas):.1f}% ({len(com)} de {len(todas)} afirmações com fonte)")
