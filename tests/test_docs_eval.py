"""Guarda de contagem de cenários de eval (R12-04).

O drift numérico em docs já aconteceu 3 vezes: R11-2 (phases/kata-judge.md),
CR-001/CR-003 (kata.md e __init__.py) e R12-01/R12-03 (eval/README.md e
DOCUMENTATION.md). Todas as vezes o guarda só foi adicionado depois da
descoberta. Este teste deriva a verdade de `eval/scenarios/` (o número de
diretórios e os vereditos esperados) e exige que as duas docs citem a
contagem e os nomes corretos — sem ele, a próxima rodada de cenários repete
o drift em silêncio.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCENARIOS = REPO / "eval" / "scenarios"
README = REPO / "eval" / "README.md"
DOCS = REPO / "DOCUMENTATION.md"
ROADMAP = REPO / "docs" / "features-roadmap.md"
ARTIGO = REPO / "docs" / "artigo-kata.md"
AGENTS = REPO / "AGENTS.md"
COMPETITIVE = REPO / "COMPETITIVE.md"


def _cenarios() -> list[str]:
    return sorted(p.name for p in SCENARIOS.iterdir() if p.is_dir())


def _cenarios_com_fraude() -> list[str]:
    """Cenários cujo ground_truth espera fraude (expected_frauds não vazio)."""
    plantam: list[str] = []
    for nome in _cenarios():
        texto = (SCENARIOS / nome / "ground_truth.yaml").read_text(encoding="utf-8")
        if "expected_frauds:" in texto and not re.search(r"expected_frauds:\s*\[\s*\]", texto):
            plantam.append(nome)
    return plantam


def _cenarios_com_reexecucao() -> list[str]:
    """Cenários cujo fixture afirma checks verificáveis (verify.ruff_clean
    etc. não-null) — o judge re-executa e precisa de ruff+pytest instalados."""
    reexecutam: list[str] = []
    for nome in _cenarios():
        for yaml_path in sorted((SCENARIOS / nome / "fixture" / ".kata").glob("*.yaml")):
            texto = yaml_path.read_text(encoding="utf-8")
            if re.search(r"(?:ruff_clean|tests_pass|coverage_pct):\s*(?:true|false|\d)", texto):
                reexecutam.append(nome)
                break
    return reexecutam


def _ids(nomes: list[str]) -> str:
    """s01-weakened-checks → s01 (o sufixo é descritivo; só o id é estável)."""
    return ", ".join(n.split("-")[0] for n in nomes)


def _expande_faixas(texto: str) -> str:
    """Expande faixas de cenários do tipo 's01–s06' em 's01 s02 … s06'."""

    def _sub(m: re.Match[str]) -> str:
        ini, fim = int(m.group(1)), int(m.group(2))
        return " ".join(f"s{i:02d}" for i in range(ini, fim + 1))

    return re.sub(r"\bs(\d{2})[–-]s(\d{2})\b", _sub, texto)


class TestEvalDocsRefletemCenarios:
    """As contagens de cenários das docs têm de bater com eval/scenarios/.

    Sem este guarda, o drift numérico em docs não derruba a suíte — a
    contagem envelhece em silêncio até alguém reler a doc.
    """

    def test_contagem_no_readme_bate_com_os_diretorios(self) -> None:
        n = len(_cenarios())
        texto = README.read_text(encoding="utf-8")
        assert f"{n} cenários" in texto, (
            f"eval/README.md não cita '{n} cenários' — a contagem está "
            f"desatualizada (existem {n} diretórios em eval/scenarios/)"
        )

    def test_tabela_do_readme_lista_todos_os_cenarios(self) -> None:
        texto = README.read_text(encoding="utf-8")
        for nome in _cenarios():
            assert f"`{nome}`" in texto, (
                f"eval/README.md não documenta o cenário {nome} na tabela — "
                "adicione a linha com categoria e o que ele exercita"
            )

    def test_docs_contam_corretamente_os_que_plantam_fraude(self) -> None:
        plantam = _cenarios_com_fraude()
        docs = DOCS.read_text(encoding="utf-8")
        n = len(plantam)
        # "Twelve scenarios (s01–s06, s08–s11, s14, s18) plant a fraud"
        m = re.search(r"(\w+)\s+scenarios\s+\(([^)]*)\)\s+plant a fraud", docs)
        assert m is not None, "DOCUMENTATION.md perdeu a frase 'N scenarios (...) plant a fraud'"
        declarado = m.group(1).lower()
        por_extenso = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20,
        }
        assert por_extenso.get(declarado) == n, (
            f"DOCUMENTATION.md declara '{declarado} scenarios' e "
            f"{n} ground_truth plantam fraude: {_ids(plantam)}"
        )
        # A lista entre parênteses tem de bater item a item com os ids reais
        # (expande faixas do tipo "s01–s06").
        listados = sorted(re.findall(r"\b(s\d{2})\b", _expande_faixas(m.group(2))))
        esperados = sorted(n.split("-")[0] for n in plantam)
        assert listados == esperados, (
            f"DOCUMENTATION.md lista {listados} e os plantadores reais são {esperados}"
        )

    def test_readme_cita_reexecucao_correta(self) -> None:
        """Os cenários que re-executam dependem de ruff+pytest instalados: a
        lista do README tem que bater com os fixtures que afirmam checks."""
        texto = README.read_text(encoding="utf-8")
        m = re.search(r"cenários com re-execução \(([^)]+)\)", texto)
        assert m is not None, "eval/README.md perdeu a lista de re-execução"
        citados = re.findall(r"s\d{2}", m.group(1))
        assertados = [n.split("-")[0] for n in _cenarios_com_reexecucao()]
        assert citados == assertados, (
            f"eval/README.md lista re-execução {citados} e os fixtures reais são {assertados}"
        )


class TestRoadmapNaoEnvelhece:
    """`docs/features-roadmap.md` também afirma números — e ninguém conferia.

    Ele dizia "19 cenários (s01–s19)" com 23 no disco e "10 linguagens" com 9
    famílias de sondas, e o guarda de eval/README + DOCUMENTATION não olhava
    para lá (revisão completa 2026-10, B1).
    """

    def test_conta_os_cenarios(self) -> None:
        texto = ROADMAP.read_text(encoding="utf-8")
        n = len(_cenarios())
        assert f"{n} cenários de trap" in texto, (
            f"docs/features-roadmap.md não cita '{n} cenários de trap' — "
            f"existem {n} diretórios em eval/scenarios/"
        )
        ultimo = _cenarios()[-1].split("-")[0]
        assert f"s01–{ultimo}" in texto or f"s01-{ultimo}" in texto, (
            f"a faixa citada no roadmap não termina em {ultimo}"
        )

    def test_conta_as_extensoes_de_linguagem(self) -> None:
        """O número de extensões é o que o judge conhece, não o que a doc lembra."""
        from kata.judge import _LANGUAGES

        texto = ROADMAP.read_text(encoding="utf-8")
        assert f"{len(_LANGUAGES)} extensões" in texto, (
            f"docs/features-roadmap.md não cita '{len(_LANGUAGES)} extensões' — "
            f"_LANGUAGES cobre {len(_LANGUAGES)}"
        )


class TestMarkdownNaoTemLixo:
    def test_nenhum_markdown_tem_caractere_cirilico(self) -> None:
        """Texto corrompido por encoding já passou: "JUическое" no roadmap.

        Cirílico não tem uso legítimo nas docs deste repo (PT-BR e inglês),
        então a presença é sempre corrupção. Fixtures de eval ficam de fora:
        são projetos deliberadamente quebrados.
        """
        import re as _re

        cirilico = _re.compile(r"[\u0400-\u04FF]")
        sujos: list[str] = []
        for md in REPO.rglob("*.md"):
            if "scenarios" in md.parts or ".git" in md.parts:
                continue
            texto = md.read_text(encoding="utf-8", errors="replace")
            m = cirilico.search(texto)
            if m:
                linha = texto[: m.start()].count("\n") + 1
                sujos.append(f"{md.relative_to(REPO)}:{linha}")
        assert not sujos, f"caractere cirílico (corrupção?) em: {', '.join(sujos)}"


class TestArtigoNaoEnvelhece:
    """O artigo em docs/ também afirma números que precisam ser medidos."""

    def test_conta_os_cenarios(self) -> None:
        texto = ARTIGO.read_text(encoding="utf-8")
        n = len(_cenarios())
        assert f"{n} cenários de trap" in texto, (
            f"docs/artigo-kata.md não cita '{n} cenários de trap' — "
            f"existem {n} diretórios em eval/scenarios/"
        )

    @staticmethod
    def _medido() -> float:
        saida = subprocess.run(
            [sys.executable, "scripts/build_skills.py", "--stats"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        casamento = re.search(r"compartilhado:\s*([\d.]+)%", saida)
        assert casamento is not None, f"build_skills --stats mudou de formato: {saida!r}"
        return float(casamento.group(1))

    @staticmethod
    def _dentro_da_tolerancia(texto: str, medido: float) -> bool:
        """Algum percentual citado está a ≤ 0,5 p.p. do medido.

        A tolerância existe porque exigir o literal exato transformava
        qualquer linha nova numa fase em quatro edições de documentação —
        medido três vezes em 2026-10 (92,5 → 92,7 → 92,8). O guarda continua
        pegando drift real (release que move o número em 1 p.p. reprova) e não
        vira vácuo: `test_tolerancia_nao_e_vacua` prova.
        """
        numeros = [float(n.replace(",", ".")) for n in re.findall(r"(\d{2}[.,]\d)%", texto)]
        return any(abs(n - medido) <= 0.5 for n in numeros)

    def test_percentual_compartilhado(self) -> None:
        """O número vem de build_skills, não da memória — dentro da tolerância."""
        medido = self._medido()
        for caminho in (DOCS, AGENTS, COMPETITIVE, ARTIGO):
            texto = caminho.read_text(encoding="utf-8")
            assert self._dentro_da_tolerancia(texto, medido), (
                f"{caminho.name} não cita o percentual compartilhado ~{medido}% "
                "(tolerância de 0,5 p.p.)"
            )

    def test_tolerancia_nao_e_vacua(self) -> None:
        """Um número fora da faixa reprova: a tolerância é 0,5, não infinita."""
        assert self._dentro_da_tolerancia("compartilhado: 92,8%", 92.8) is True
        assert self._dentro_da_tolerancia("compartilhado: 92,4%", 92.8) is True
        # 0,5 é a borda e conta como dentro; 0,6 reprova.
        assert self._dentro_da_tolerancia("compartilhado: 93,3%", 92.8) is True
        assert self._dentro_da_tolerancia("compartilhado: 93,4%", 92.8) is False
        assert self._dentro_da_tolerancia("nada de percentual aqui", 92.8) is False
