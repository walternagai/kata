"""As contagens da árvore de diretórios do README têm de bater com o disco.

O `README.md` é o texto publicado no PyPI, e a árvore que ele desenha cita
números: quantos arquivos há em `phases/`, quantas skills em `opencode/skills/`
e em `claude-code/skills/`. Na 0.9.0 esses três números foram publicados
defasados (11 em vez de 12, 14 em vez de 15, 15 em vez de 16) porque nada os
conferia: `test_docs_eval.py` guarda as contagens do `eval/README.md`, não as
do README principal.

Contagem em prosa não apodrece sozinha — ela apodrece em silêncio, e só é
notada quando alguém relê o documento. Este módulo troca a releitura por uma
verificação, e cobre também o `AGENTS.md`, que descreve a mesma árvore.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from kata.skills import DOMAIN_SKILLS, PHASE_SKILLS

REPO = Path(__file__).resolve().parent.parent


def _skills(raiz: Path) -> int:
    """Quantas skills existem em `raiz` — um diretório por skill."""
    return len([p for p in raiz.iterdir() if p.is_dir()])


# Cada entrada é: (marcador da linha, padrão que extrai o número, chave da
# contagem real). O marcador é o que ancora a busca: procurar "12" solto no
# documento casaria com qualquer número, e o guarda passaria a depender de não
# existir outra frase com o mesmo formato.
_CONTAGENS: dict[str, Callable[[], int]] = {
    "phases": lambda: len(list((REPO / "phases").glob("*.md"))),
    "fase_skills": lambda: len(PHASE_SKILLS),
    "skills": lambda: _skills(REPO / "opencode" / "skills"),
    "skills_claude": lambda: _skills(REPO / "claude-code" / "skills"),
}

_CASOS: dict[str, list[tuple[str, str, str]]] = {
    "README.md": [
        ("FONTE ÚNICA dos prompts", r"\((\d+) arquivos", "phases"),
        ("kata.md + as", r"(\d+) skills", "fase_skills"),
        ("10 de fase", r"(\d+) skills", "skills"),
        ("orquestrador kata", r"(\d+) skills", "skills_claude"),
    ],
    "AGENTS.md": [
        ("10 de fase", r"(\d+) skills", "skills"),
        # No claude-code a linha diz "as mesmas N skills": o orquestrador tem
        # linha própria acima, então o N é o do OpenCode, não o do total.
        ("as mesmas", r"(\d+) skills", "skills"),
    ],
}


def _citado(texto: str, marcador: str, padrao: str) -> int:
    """O número que a linha de `marcador` cita, extraído por `padrao`."""
    for linha in texto.splitlines():
        if marcador not in linha:
            continue
        achado = re.search(padrao, linha)
        if achado:
            return int(achado.group(1))
    raise AssertionError(
        f"nenhuma linha com {marcador!r} cita o padrão {padrao!r} — "
        "a árvore mudou de forma e o guarda perdeu a âncora"
    )


def _divergencias(texto: str, arquivo: str) -> list[str]:
    """Contagens citadas no texto que não batem com o filesystem.

    Devolve a lista em vez de afirmar direto para que o invariante possa ser
    exercitado com uma entrada falsa: um guarda que só sabe dizer "passou" é
    indistinguível do vácuo.
    """
    problemas: list[str] = []
    for marcador, padrao, chave in _CASOS[arquivo]:
        citado = _citado(texto, marcador, padrao)
        real = _CONTAGENS[chave]()
        if citado != real:
            problemas.append(f"{marcador!r} cita {citado}, e existem {real}")
    return problemas


@pytest.mark.parametrize("arquivo", sorted(_CASOS))
def test_arvore_cita_o_que_existe_no_disco(arquivo: str) -> None:
    texto = (REPO / arquivo).read_text(encoding="utf-8")
    problemas = _divergencias(texto, arquivo)
    assert not problemas, f"{arquivo} cita contagem que não confere: " + "; ".join(problemas)


def test_breakdown_bate_com_as_listas_canonicas() -> None:
    """`10 de fase + 4 domain adapters` é a decomposição do total do OpenCode.

    Se `PHASE_SKILLS` ou `DOMAIN_SKILLS` mudar e o texto não, o total pode
    continuar certo com a decomposição errada — que é exatamente o estado em
    que a 0.9.0 foi publicada ("14 skills" com "10 + 4" logo ao lado).
    """
    linha = next(
        (
            linha
            for linha in (REPO / "README.md").read_text(encoding="utf-8").splitlines()
            if "10 de fase" in linha
        ),
        None,
    )
    assert linha is not None, "README.md não cita mais '10 de fase' — atualize o guarda"

    de_fase = re.search(r"(\d+) de fase", linha)
    adapters = re.search(r"(\d+) domain", linha)
    assert de_fase and adapters, f"a linha perdeu a decomposição: {linha!r}"
    assert int(de_fase.group(1)) == len(PHASE_SKILLS)
    assert int(adapters.group(1)) == len(DOMAIN_SKILLS)


def test_o_guarda_reprova_o_texto_que_foi_publicado() -> None:
    """Prova de não-vacuidade, com o texto que a 0.9.0 publicou no PyPI.

    Sem isto, o guarda poderia estar lendo uma linha que nunca existe e
    passando por omissão. Aqui ele recebe texto sintético com os números
    antigos e tem de acusar as três divergências.
    """
    antigo = (
        "├── phases/            ← FONTE ÚNICA dos prompts (11 arquivos:\n"
        "│                      kata.md + as 10 skills de fase +\n"
        "│   └── skills/kata-*/SKILL.md  ← 14 skills (10 de fase + 4 domain\n"
        "│   └── skills/kata-*/SKILL.md  ← 15 skills (orquestrador kata + as 14 acima)\n"
    )
    assert _divergencias(antigo, "README.md") == [
        "'FONTE ÚNICA dos prompts' cita 11, e existem 12",
        "'10 de fase' cita 14, e existem 15",
        "'orquestrador kata' cita 15, e existem 16",
    ]
