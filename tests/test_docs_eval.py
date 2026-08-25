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
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCENARIOS = REPO / "eval" / "scenarios"
README = REPO / "eval" / "README.md"
DOCS = REPO / "DOCUMENTATION.md"


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
