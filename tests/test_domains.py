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
    ADAPTERS = ("kata-devops", "kata-data-analysis", "kata-research", "kata-docs")

    def test_adapter_devops_existe(self) -> None:
        assert (DOMAINS / "kata-devops.md").exists()

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_adapter_existe(self, adapter: str) -> None:
        assert (DOMAINS / f"{adapter}.md").exists(), f"{adapter}.md não existe em domains/"

    @pytest.mark.parametrize("secao", SECOES_OBRIGATORIAS)
    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_adapter_tem_todas_as_secoes(self, adapter: str, secao: str) -> None:
        texto = (DOMAINS / f"{adapter}.md").read_text(encoding="utf-8")
        assert secao in texto, f"{adapter}.md não tem a seção {secao!r}"

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_adapter_tem_frontmatter(self, adapter: str) -> None:
        texto = (DOMAINS / f"{adapter}.md").read_text(encoding="utf-8")
        assert texto.startswith("---\n"), "frontmatter não começa com ---"
        assert f"name: {adapter}" in texto
        assert "description:" in texto

    def test_load_domain_esta_no_contrato(self) -> None:
        assert "LOAD_DOMAIN" in REQUIRED_ROLES

    def test_load_domain_e_usado_pelo_orquestrador(self) -> None:
        texto = "".join(c.read_text(encoding="utf-8") for c in _fontes() if c.stem == "kata")
        assert "{{LOAD_DOMAIN}}" in texto, "orquestrador não usa {{LOAD_DOMAIN}}"

    @pytest.mark.parametrize("frontend", ["opencode", "claude-code"])
    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_adapter_renderizado_sem_vazamento_de_marcadores(
        self, frontend: str, adapter: str
    ) -> None:
        fonte = DOMAINS / f"{adapter}.md"
        saida = render(fonte.read_text(encoding="utf-8"), frontend, str(fonte))
        for marcador in ("<!--only", "<!--if", "<!--ifnot", "<!--/", "{{{", "{{"):
            assert marcador not in saida, f"{frontend}: marcador/variável vazado: {marcador}"

    def test_fontes_de_domain_nao_incluem_template(self) -> None:
        assert not any(p.stem == "TEMPLATE" for p in _fontes())

    def test_domain_skills_bate_com_os_adapters_em_domains(self) -> None:
        """R10-19: a lista canônica do preflight e os arquivos de domains/
        são duas visões do mesmo conjunto — o análogo de
        test_a_lista_canonica_bate_com_as_fontes_em_phases para domínios."""
        from kata.skills import DOMAIN_SKILLS

        esperado = {p.stem for p in DOMAINS.glob("*.md") if p.stem != "TEMPLATE"}
        assert set(DOMAIN_SKILLS) == esperado, (
            f"domains/ e kata.skills.DOMAIN_SKILLS divergem: "
            f"só em domains/ {sorted(esperado - set(DOMAIN_SKILLS))}, "
            f"só em DOMAIN_SKILLS {sorted(set(DOMAIN_SKILLS) - esperado)}"
        )

    def test_doctor_domain_nao_avisa_frontend_nunca_instalado(self, tmp_path, monkeypatch) -> None:
        """R10-15: frontend ausente não gera aviso de domain skill faltando —
        sem as skills de fase, avisar a falta de um adapter opcional é ruído."""
        from kata.skills import FRONTENDS, check_domain_skills

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        for frontend in FRONTENDS:
            assert check_domain_skills(frontend) == []

    def test_domain_sem_prefixo_kata_falha_no_build(self, tmp_path, monkeypatch) -> None:
        """R10-20: adapter fora da convenção kata-<domínio> não é carregado
        pelo orquestrador nem checado pelo doctor — o build tem de falhar."""
        import build_skills as bs

        (tmp_path / "phases").mkdir()
        (tmp_path / "phases" / "kata-fit.md").write_text("# fase", encoding="utf-8")
        (tmp_path / "domains").mkdir()
        (tmp_path / "domains" / "devops.md").write_text("# dominio", encoding="utf-8")
        monkeypatch.setattr(bs, "FONTE", tmp_path / "phases")
        monkeypatch.setattr(bs, "DOMINIOS", tmp_path / "domains")
        with pytest.raises(SystemExit, match="kata-"):
            _fontes()

    def test_colisao_de_stem_entre_phases_e_domains_falha(self, tmp_path, monkeypatch) -> None:
        """R10-18: um domínio com o mesmo stem de uma fase renderizaria para
        o MESMO destino e sobrescreveria a fase em silêncio — o build tem de
        falhar nomeado, não gerar a skill errada."""
        import build_skills as bs

        (tmp_path / "phases").mkdir()
        (tmp_path / "phases" / "kata-fit.md").write_text("# fase", encoding="utf-8")
        (tmp_path / "domains").mkdir()
        (tmp_path / "domains" / "kata-fit.md").write_text("# dominio", encoding="utf-8")
        monkeypatch.setattr(bs, "FONTE", tmp_path / "phases")
        monkeypatch.setattr(bs, "DOMINIOS", tmp_path / "domains")
        with pytest.raises(SystemExit, match="kata-fit"):
            _fontes()
