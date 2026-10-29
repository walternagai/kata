"""Busca sistemática curta no SOL (Biblioteca Digital da SBC) para os Trabalhos Relacionados.

Roda cada string em cada veículo, pagina todos os resultados, remove duplicatas e filtra o
período. Grava resultados_busca.csv (um registro por artigo) e contagens.txt. A triagem por
título e resumo é feita depois, à mão, e fica em triagem.csv.
"""

from __future__ import annotations

import csv
import html
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).parent
DATA_MINIMA = "2022-01-01"
# A busca do site da RBIE devolve "Nenhum resultado encontrado" até para "programação" (testado em
# 3 out. 2026), então a RBIE é consultada pelo Crossref (ISSN 2317-6121, período e string).
RBIE_ISSN = "2317-6121"
VEICULOS = {
    "SBIE": "https://sol.sbc.org.br/index.php/sbie",
    "WEI": "https://sol.sbc.org.br/index.php/wei",
    "EDUCOMP": "https://sol.sbc.org.br/index.php/educomp",
    "EDUCOMP-estendido": "https://sol.sbc.org.br/index.php/educomp_estendido",
}
STRINGS = [
    '"inteligência artificial generativa" programação',
    "ChatGPT programação",
    '"juiz online"',
    '"correção automática" programação',
    '"ensino de teste"',
    '"criação de testes"',
    '"integridade acadêmica" programação',
    '"engenharia de software" "IA generativa" ensino',
]
BLOCO = re.compile(r'<div class="obj_article_summary">(.*?)\n</div>', re.S)


def baixa(url: str) -> str:
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "busca-sistematica"}), timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except OSError:
            time.sleep(2)
    return ""


def registros(pagina: str):
    for b in BLOCO.findall(pagina):
        t = re.search(r'<a href="([^"]+)">\s*(.*?)\s*</a>', b, re.S)
        if not t:
            continue
        data = re.search(r'<div class="published">\s*([\d-]+)', b)
        autores = re.search(r'<div class="authors">\s*(.*?)\s*</div>', b, re.S)
        yield {
            "url": t.group(1),
            "titulo": html.unescape(re.sub(r"\s+", " ", t.group(2))),
            "autores": html.unescape(re.sub(r"\s+", " ", autores.group(1))) if autores else "",
            "data": data.group(1) if data else "",
        }


PALAVRAS = ("program", "teste", "juiz", "juízes", "chatgpt", "generativa", "correção automática",
            "integridade", "engenharia de software", "plágio")


def busca_rbie(string: str):
    """RBIE via Crossref: relevância do Crossref, 25 registros por string, filtro por palavra no título."""
    q = urllib.parse.quote(string.replace('"', ""))
    url = (f"https://api.crossref.org/works?query.bibliographic={q}&filter=issn:{RBIE_ISSN},"
           f"from-pub-date:{DATA_MINIMA}&rows=25&select=DOI,title,author,issued")
    import json
    try:
        itens = json.loads(baixa(url))["message"]["items"]
    except (ValueError, KeyError):
        return
    for m in itens:
        titulo = html.unescape((m.get("title") or [""])[0])
        if not any(w in titulo.lower() for w in PALAVRAS):
            continue
        d = m.get("issued", {}).get("date-parts", [[0]])[0]
        data = "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(d + [1] * (3 - len(d))))
        autores = ", ".join(f"{a.get('given', '')} {a.get('family', '')}".strip() for a in m.get("author", []))
        yield {"url": f"https://doi.org/{m['DOI']}", "titulo": titulo, "autores": autores, "data": data}


def main() -> None:
    brutos, vistos = [], {}
    por_busca = Counter()
    for s in STRINGS:
        for r in busca_rbie(s):
            brutos.append({**r, "veiculo": "RBIE (Crossref)", "string": s})
            por_busca[("RBIE (Crossref)", s)] += 1
        time.sleep(0.5)
    for vnome, base in VEICULOS.items():
        for s in STRINGS:
            pagina_n, total = 1, None
            while True:
                url = f"{base}/search/search?query={urllib.parse.quote(s)}&searchPage={pagina_n}"
                h = baixa(url)
                recs = list(registros(h))
                if total is None:
                    m = re.search(r"de\s+(\d+)\s+itens", h)
                    total = int(m.group(1)) if m else len(recs)
                for r in recs:
                    brutos.append({**r, "veiculo": vnome, "string": s})
                    por_busca[(vnome, s)] += 1
                if not recs or sum(1 for b in brutos if b["veiculo"] == vnome and b["string"] == s) >= total:
                    break
                pagina_n += 1
                time.sleep(0.5)
            time.sleep(0.5)
    for b in brutos:
        vistos.setdefault(b["url"], {**b, "strings": set()})["strings"].add(b["string"])
    unicos = list(vistos.values())
    no_periodo = [u for u in unicos if u["data"] >= DATA_MINIMA]
    with open(AQUI / "resultados_busca.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["veiculo", "data", "titulo", "autores", "url", "strings"])
        for u in sorted(no_periodo, key=lambda x: (x["veiculo"], x["data"], x["titulo"])):
            w.writerow([u["veiculo"], u["data"], u["titulo"], u["autores"], u["url"], " | ".join(sorted(u["strings"]))])
    linhas = [f"registros brutos (soma das buscas): {len(brutos)}", f"artigos distintos: {len(unicos)}",
              f"no período (>= {DATA_MINIMA}): {len(no_periodo)}", "", "brutos por veículo e string:"]
    for (v, s), n in sorted(por_busca.items()):
        linhas.append(f"  {v:18} {s:55} {n}")
    (AQUI / "contagens.txt").write_text("\n".join(linhas) + "\n")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
