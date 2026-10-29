"""Verificações do domínio data-analysis (lint, test, coverage) para o kata."""
import csv
import re
import subprocess
import sys
from pathlib import Path


def linhas():
    with open("dados.csv", newline="") as f:
        return list(csv.DictReader(f))


modo = sys.argv[1]
if modo == "lint":
    l = linhas()
    ids = [x["aluno"] for x in l]
    ok = list(l[0].keys()) == ["aluno", "nota"] and len(ids) == len(set(ids))
    print("esquema e ids:", "ok" if ok else "inválidos")
    sys.exit(0 if ok else 1)
if modo == "test":
    subprocess.run([sys.executable, "analise.py"], check=True)
    ausentes = sum(1 for x in linhas() if x["nota"] == "")
    texto = Path("resultado.txt").read_text()
    registrou = re.search(rf"linhas removidas: {ausentes} \(critério: .+\)", texto)
    if ausentes and not registrou:
        print(f"linhas removidas sem registro: {ausentes} de {len(linhas())}")
        sys.exit(1)
    print("remoções registradas" if ausentes else "nenhuma remoção")
if modo == "cobertura":
    usadas = sum(1 for x in linhas() if x["nota"] != "")
    print(f"USO {100 * usadas / len(linhas()):.1f}% ({usadas} de {len(linhas())} linhas usadas)")
