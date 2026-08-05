"""Invariants dos domain adapters do kata.

Domain adapters vivem em `domains/` e são gerados para os frontends assim
como as fases. Eles não são skills instaláveis no sentido de fases — são
opcionais —, mas a fonte única e a geração compartilham a mesma disciplina.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from build_skills import (  # noqa: E402 - depende do sys.path acima
    REQUIRED_ROLES,
    _fontes,
    render,
)

DOMAINS = REPO / "domains"
TEMPLATE = DOMAINS / "TEMPLATE.md"

SECOES_OBRIGATORIAS = (
    "## Domínio",
    "## Evidência",
    "## Autoridade",
    "## Verify by observation",
    "## Fraud table",
    "## Minimum evidence set",
    "## Red lines",
)


@pytest.fixture
def domain_fontes() -> list[Path]:
    return sorted(p for p in DOMAINS.glob("*.md") if p.stem != "TEMPLATE")


class TestTemplateSchema:
    def test_template_existe_e_tem_secoes_obrigatorias(self) -> None:
        assert TEMPLATE.exists(), f"{TEMPLATE} não encontrado"
        texto = TEMPLATE.read_text(encoding="utf-8")
        for secao in SECOES_OBRIGATORIAS:
            assert secao in texto, f"TEMPLATE.md não tem a seção {secao!r}"


class TestDomainAdapters:
    def test_adapter_devops_existe(self) -> None:
        assert (DOMAINS / "kata-devops.md").exists()

    @pytest.mark.parametrize("secao", SECOES_OBRIGATORIAS)
    def test_adapter_devops_tem_todas_as_secoes(self, secao: str) -> None:
        texto = (DOMAINS / "kata-devops.md").read_text(encoding="utf-8")
        assert secao in texto, f"kata-devops.md não tem a seção {secao!r}"

    def test_adapter_devops_tem_frontmatter(self) -> None:
        texto = (DOMAINS / "kata-devops.md").read_text(encoding="utf-8")
        assert texto.startswith("---\n"), "frontmatter não começa com ---"
        assert "name: kata-devops" in texto
        assert "description:" in texto

    def test_load_domain_esta_no_contrato(self) -> None:
        assert "LOAD_DOMAIN" in REQUIRED_ROLES

    def test_load_domain_e_usado_pelo_orquestrador(self) -> None:
        texto = "".join(c.read_text(encoding="utf-8") for c in _fontes() if c.stem == "kata")
        assert "{{LOAD_DOMAIN}}" in texto, "orquestrador não usa {{LOAD_DOMAIN}}"

    @pytest.mark.parametrize("frontend", ["opencode", "claude-code"])
    def test_adapter_renderizado_sem_vazamento_de_marcadores(self, frontend: str) -> None:
        fonte = DOMAINS / "kata-devops.md"
        saida = render(fonte.read_text(encoding="utf-8"), frontend, str(fonte))
        for marcador in ("<!--only", "<!--if", "<!--ifnot", "<!--/", "{{{", "{{"):
            assert marcador not in saida, f"{frontend}: marcador/variável vazado: {marcador}"

    def test_fontes_de_domain_nao_incluem_template(self) -> None:
        assert not any(p.stem == "TEMPLATE" for p in _fontes())
