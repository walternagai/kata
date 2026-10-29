"""Conduz o kata interativo por um pseudo-terminal, respondendo aos prompts conhecidos.

Uso: python3 conduzir.py <args do kata>   (as respostas abaixo são as da demonstração do artigo)
"""

from __future__ import annotations

import os
import pty
import re
import select
import sys
import time

RESPOSTAS = [
    (r"Justificativa", "corrigir divisão por zero sem guarda"),
    (r"problema exato", "a função dividir levanta ZeroDivisionError sem guarda"),
    (r"assumptions estou", "a API pública de dividir é estável"),
    (r"alternativas", "guarda com ValueError; devolver None"),
    (r"O que NÃO sei", "nada"),
    (r"'pronto'", "o teste test_dividir_por_zero passa e a cobertura fica em pelo menos 70%"),
    (r"código FAZ", "dividir levanta ZeroDivisionError"),
    (r"teste/check ESPERA", "o teste espera ValueError"),
    (r"README DIZ", "o README não menciona o caso"),
    (r"concordam", "n"),
    (r"Padrão (a )?busca", "a / b"),
]


def resposta(linha: str) -> str:
    for padrao, texto in RESPOSTAS:
        if re.search(padrao, linha):
            return texto
    return ""  # Enter: aceita o padrão


def main() -> None:
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(sys.executable, [sys.executable, "-m", "kata", *sys.argv[1:]])
    saida, buf, ultimo = "", "", time.time()
    fim = time.time() + 120
    while time.time() < fim:
        pronto, _, _ = select.select([fd], [], [], 0.5)
        if fd in pronto:
            try:
                dado = os.read(fd, 4096).decode("utf-8", "replace")
            except OSError:
                break
            if not dado:
                break
            saida += dado
            buf += dado
            ultimo = time.time()
        elif buf and not buf.endswith("\n") and time.time() - ultimo > 0.4:
            os.write(fd, (resposta(buf.split("\n")[-1]) + "\n").encode())
            buf = ""
    print(re.sub(r"\x1b\[[0-9;]*m", "", saida).replace("\r", ""))


if __name__ == "__main__":
    main()
