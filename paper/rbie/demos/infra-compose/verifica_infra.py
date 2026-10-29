"""Verificações do domínio devops para o kata (lint, test, coverage) sobre docker-compose.yml."""
import subprocess
import sys

import yaml

compose = yaml.safe_load(open("docker-compose.yml"))
servicos = compose["services"]
modo = sys.argv[1]
if modo == "lint":
    r = subprocess.run(["docker", "compose", "config", "-q"], capture_output=True, text=True)
    print(r.stderr.strip() or "docker compose config: sintaxe ok")
    sys.exit(r.returncode)
if modo == "test":
    problemas = []
    for nome, s in servicos.items():
        if s.get("image", "").endswith(":latest") or ":" not in s.get("image", ":"):
            problemas.append(f"{nome}: imagem sem versão fixa ({s.get('image')})")
        hc = s.get("healthcheck", {})
        if not hc or hc.get("disable"):
            problemas.append(f"{nome}: healthcheck ausente ou desativado")
    print("; ".join(problemas) if problemas else "imagens fixadas e healthchecks ativos")
    sys.exit(1 if problemas else 0)
if modo == "cobertura":
    com = sum(1 for s in servicos.values() if s.get("healthcheck") and not s["healthcheck"].get("disable"))
    print(f"HEALTH {100 * com / len(servicos):.1f}% ({com} de {len(servicos)} serviços com healthcheck)")
