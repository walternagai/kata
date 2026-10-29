"""Média das notas. Versão 1: descarta em silêncio as linhas sem nota."""
import csv

with open("dados.csv", newline="") as f:
    linhas = list(csv.DictReader(f))
notas = [float(l["nota"]) for l in linhas if l["nota"] != ""]
with open("resultado.txt", "w") as f:
    f.write(f"media: {sum(notas) / len(notas):.2f}\n")
