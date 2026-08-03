#!/usr/bin/env python3
"""Gera as skills de cada frontend a partir da fonte única em `phases/`.

Uma fase existia em duplicata — `opencode/skills/kata-<fase>/SKILL.md` e
`claude-code/skills/kata-<fase>/SKILL.md` — e a sincronia era disciplina
manual. Disciplina manual falha: as duas cópias acumularam 395 linhas
divergentes, e parte delas era melhoria aplicada num lado e esquecida no
outro (a fase ARTIFACT ganhou uma seção "Ferramentas" só no Claude Code; o
VERIFY ganhou o atalho de `--check-only` só lá também).

Aqui a fonte é uma só e os frontends são derivados. O que de fato difere
entre eles — nome de ferramenta e a orientação que depende do harness — é
declarado explicitamente, em vez de conviver como divergência silenciosa.

Sintaxe da fonte:

    {{VAR}}                      substituído pelo valor da variável do frontend
    <!--only:claude-code-->      bloco incluído só naquele frontend
    ...
    <!--/only-->

Uso:
    python3 scripts/build_skills.py            # gera
    python3 scripts/build_skills.py --check    # falha se o gerado divergir
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FONTE = REPO / "phases"

# O arquivo da fonte que é o orquestrador, e não uma fase. Tem destino
# próprio em cada frontend (agente no OpenCode, skill no Claude Code).
ORQUESTRADOR = "kata"

FRONTENDS: dict[str, dict] = {
    "opencode": {
        "vars": {
            "AGENTE": "o agente @kata",
            "FRONTEND_NOME": "OpenCode",
            "ESTE_ORQUESTRADOR": "O prompt do agente",
            "INVOC": "@kata ",
            "INVOC_SEM_ARGS": "`@kata` (sem args)",
            "AGENTE_CAP": "O agente",
            "AGENTE_CAP_MIN": "o agente",
            "SKILL": "`skill`",
            "ASK": "`question`",
            "BASH": "`bash`",
            "READ": "`read`",
            "WRITE": "`write`",
            "EDIT": "`edit`",
            "GREP": "`grep`",
            "GLOB": "`glob`",
        },
        "orquestrador": "opencode/agent/kata.md",
        "fase": "opencode/skills/{slug}/SKILL.md",
    },
    "claude-code": {
        "vars": {
            "AGENTE": "o kata",
            "FRONTEND_NOME": "Claude Code",
            "ESTE_ORQUESTRADOR": "Esta skill",
            "INVOC": "",
            "INVOC_SEM_ARGS": "(sem args)",
            "AGENTE_CAP": "A skill",
            "AGENTE_CAP_MIN": "a skill",
            "SKILL": "`Skill`",
            "ASK": "`AskUserQuestion`",
            "BASH": "`Bash`",
            "READ": "`Read`",
            "WRITE": "`Write`",
            "EDIT": "`Edit`",
            "GREP": "`Grep`",
            "GLOB": "`Glob`",
        },
        "orquestrador": "claude-code/skills/kata/SKILL.md",
        "fase": "claude-code/skills/{slug}/SKILL.md",
    },
}

_BLOCO = re.compile(
    r"^[ \t]*<!--only:(?P<nomes>[\w\-, ]+)-->[ \t]*\n(?P<corpo>.*?)^[ \t]*<!--/only-->[ \t]*\n",
    re.DOTALL | re.MULTILINE,
)
_VAR = re.compile(r"\{\{(\w+)\}\}")


def _resolve_blocos(texto: str, frontend: str) -> str:
    """Mantém o corpo dos blocos do frontend pedido e remove os demais."""

    def escolhe(m: re.Match[str]) -> str:
        nomes = {n.strip() for n in m.group("nomes").split(",")}
        desconhecidos = nomes - set(FRONTENDS)
        if desconhecidos:
            raise ValueError(f"frontend desconhecido em <!--only:-->: {sorted(desconhecidos)}")
        return m.group("corpo") if frontend in nomes else ""

    return _BLOCO.sub(escolhe, texto)


def _resolve_vars(texto: str, valores: dict[str, str], origem: str) -> str:
    """Substitui {{VAR}}. Variável não declarada é erro, não texto literal."""

    def troca(m: re.Match[str]) -> str:
        nome = m.group(1)
        if nome not in valores:
            raise ValueError(f"{origem}: variável não declarada {{{{{nome}}}}}")
        return valores[nome]

    return _VAR.sub(troca, texto)


def render(fonte: str, frontend: str, origem: str = "<memória>") -> str:
    """Aplica blocos condicionais e variáveis para um frontend."""
    texto = _resolve_blocos(fonte, frontend)
    return _resolve_vars(texto, FRONTENDS[frontend]["vars"], origem)


# Comentário HTML: não aparece no markdown renderizado, mas aparece para quem
# abre o arquivo — que é justamente quem está prestes a editá-lo à mão.
_AVISO = (
    "<!-- Gerado por scripts/build_skills.py a partir de phases/{slug}.md."
    " Não edite aqui. -->\n"
)

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _com_aviso(texto: str, slug: str) -> str:
    """Insere o aviso de arquivo gerado logo após o frontmatter.

    Depois, e não antes: o frontmatter tem de ser a primeira coisa do arquivo
    ou os hosts não o reconhecem, e a skill perde nome e descrição.
    """
    aviso = _AVISO.format(slug=slug)
    m = _FRONTMATTER.match(texto)
    if m is None:
        return aviso + texto
    return texto[: m.end()] + aviso + texto[m.end() :]


def _destino(slug: str, frontend: str) -> Path:
    spec = FRONTENDS[frontend]
    if slug == ORQUESTRADOR:
        return REPO / spec["orquestrador"]
    return REPO / spec["fase"].format(slug=slug)


def _fontes() -> list[Path]:
    if not FONTE.is_dir():
        raise SystemExit(f"fonte não encontrada: {FONTE}")
    return sorted(FONTE.glob("*.md"))


def build(check: bool = False) -> int:
    """Gera (ou confere) todos os arquivos. Retorna a contagem de divergências."""
    divergentes: list[str] = []

    for caminho in _fontes():
        slug = caminho.stem
        fonte = caminho.read_text(encoding="utf-8")
        for frontend in FRONTENDS:
            saida = _com_aviso(
                render(fonte, frontend, origem=str(caminho.relative_to(REPO))), slug
            )
            destino = _destino(slug, frontend)
            atual = destino.read_text(encoding="utf-8") if destino.exists() else None

            if atual == saida:
                continue
            if check:
                divergentes.append(str(destino.relative_to(REPO)))
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(saida, encoding="utf-8")
            print(f"  ✅ {destino.relative_to(REPO)}")

    if check and divergentes:
        print("Arquivos gerados divergem da fonte em phases/:")
        for d in divergentes:
            print(f"  ❌ {d}")
        print("\nRode `make build-skills` e commite o resultado.")
    return len(divergentes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Não escreve; falha se algum arquivo gerado estiver desatualizado",
    )
    args = parser.parse_args()

    if not args.check:
        print("Gerando skills a partir de phases/...")
    divergentes = build(check=args.check)
    if divergentes:
        sys.exit(1)
    if not args.check:
        print("Pronto.")


if __name__ == "__main__":
    main()
