"""Média das notas. Versão 2: registra quantas linhas removeu e por qual critério."""
import csv

with open("dados.csv", newline="") as f:
    linhas = list(csv.DictReader(f))
notas = [float(l["nota"]) for l in linhas if l["nota"] != ""]
removidas = len(linhas) - len(notas)
with open("resultado.txt", "w") as f:
    f.write(f"media: {sum(notas) / len(notas):.2f}\n")
    if removidas:
        f.write(f"linhas removidas: {removidas} (critério: nota ausente)\n")
