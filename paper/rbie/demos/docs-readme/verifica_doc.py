"""Verificações de documentação para o kata no domínio docs (lint, test, coverage)."""
import re, subprocess, sys
from pathlib import Path

def flags_do_kata():
    out = subprocess.run([sys.executable, "-m", "kata", "--help"], capture_output=True, text=True).stdout
    return set(re.findall(r"--[a-z][a-z-]+", out))

def flags_do_doc():
    return set(re.findall(r"--[a-z][a-z-]+", Path("README.md").read_text()))

modo = sys.argv[1]
if modo == "lint":
    ruins = [i + 1 for i, l in enumerate(Path("README.md").read_text().splitlines()) if l != l.rstrip()]
    print("espaços no fim da linha:", ruins or "nenhum"); sys.exit(1 if ruins else 0)
if modo == "test":
    inexistentes = sorted(flags_do_doc() - flags_do_kata())
    print("flags citadas que não existem:", inexistentes or "nenhuma"); sys.exit(1 if inexistentes else 0)
if modo == "cobertura":
    todas = flags_do_kata() - {"--help", "--version"}
    doc = flags_do_doc() & todas
    print(f"COBERTURA {100 * len(doc) / len(todas):.1f}% ({len(doc)} de {len(todas)} flags documentadas)")
