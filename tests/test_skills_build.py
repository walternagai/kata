"""Os arquivos dos frontends são gerados, e não editados à mão.

Antes disto, uma fase existia em duas cópias mantidas por disciplina manual.
A disciplina falhou: as cópias acumularam 395 linhas divergentes, e parte
delas era melhoria aplicada num lado e esquecida no outro — a fase ARTIFACT
tinha uma seção "Ferramentas" só no Claude Code, o orquestrador do OpenCode
nunca recebeu a numeração corrigida nem o `base_commit`.

O teste que faltava é este: gerar de novo e comparar. Sem ele, editar
`opencode/` ou `claude-code/` à mão volta a ser possível, e a divergência
volta a ser silenciosa.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from build_skills import (  # noqa: E402 - depende do sys.path acima
    FRONTENDS,
    _destino,
    _fontes,
    build,
    render,
)


def test_gerados_estao_em_dia() -> None:
    """`make build-skills` não tem pendência. É o guarda contra o drift."""
    divergentes = build(check=True)
    assert divergentes == 0, (
        "arquivos de frontend divergem de phases/. "
        "Edite phases/ e rode `make build-skills` — não edite os gerados à mão."
    )


@pytest.mark.parametrize("frontend", sorted(FRONTENDS))
def test_todo_destino_existe(frontend: str) -> None:
    for caminho in _fontes():
        destino = _destino(caminho.stem, frontend)
        assert destino.is_file(), f"{destino} não foi gerado"


def test_uma_fonte_por_skill_instalavel() -> None:
    """Toda skill instalada tem fonte, e toda fonte vira skill instalada.

    Um diretório em `claude-code/skills/` sem fonte correspondente é um
    arquivo órfão que o instalador vai linkar e que ninguém mais atualiza.
    """
    fontes = {c.stem for c in _fontes()}
    for frontend, spec in FRONTENDS.items():
        raiz = REPO / spec["fase"].split("{slug}")[0]
        instaladas = {p.name for p in raiz.iterdir() if p.is_dir()}
        # As fases sempre viram diretório instalável. O orquestrador só no
        # Claude Code, onde ele também é uma skill; no OpenCode é um agente.
        esperadas = fontes - {"kata"}
        assert not instaladas - fontes, (
            f"{frontend}: skill sem fonte em phases/: {sorted(instaladas - fontes)}"
        )
        assert not esperadas - instaladas, (
            f"{frontend}: fonte sem skill gerada: {sorted(esperadas - instaladas)}"
        )


class TestTemplate:
    """A linguagem de template é mínima, mas erra alto quando erra."""

    def test_variavel_desconhecida_e_erro(self) -> None:
        """Variável com typo tem de estourar, não virar texto literal.

        `{{BSAH}}` sobrevivendo no output seria uma instrução quebrada
        entregue ao modelo, e ninguém veria.
        """
        with pytest.raises(ValueError, match="variável não declarada"):
            render("use {{BSAH}} aqui", "opencode")

    def test_frontend_desconhecido_em_bloco_e_erro(self) -> None:
        with pytest.raises(ValueError, match="frontend desconhecido"):
            render("<!--only:cursor-->\nx\n<!--/only-->\n", "opencode")

    def test_bloco_do_frontend_fica_e_o_outro_some(self) -> None:
        fonte = (
            "comum\n"
            "<!--only:opencode-->\nsó oc\n<!--/only-->\n"
            "<!--only:claude-code-->\nsó cc\n<!--/only-->\n"
        )
        assert render(fonte, "opencode") == "comum\nsó oc\n"
        assert render(fonte, "claude-code") == "comum\nsó cc\n"

    def test_bloco_aceita_mais_de_um_frontend(self) -> None:
        fonte = "<!--only:opencode, claude-code-->\nnos dois\n<!--/only-->\n"
        assert render(fonte, "opencode") == "nos dois\n"
        assert render(fonte, "claude-code") == "nos dois\n"

    def test_variaveis_sao_substituidas(self) -> None:
        assert render("rode {{BASH}}", "opencode") == "rode `bash`"
        assert render("rode {{BASH}}", "claude-code") == "rode `Bash`"


class TestFontes:
    """Invariantes das fontes em phases/."""

    def test_nenhum_marcador_sobra_no_gerado(self) -> None:
        """Marcador vazado vira `<!--only:...-->` visível na skill instalada."""
        for caminho in _fontes():
            for frontend in FRONTENDS:
                saida = render(caminho.read_text(encoding="utf-8"), frontend, str(caminho))
                assert "<!--only" not in saida, f"{caminho.stem}/{frontend}"
                assert "<!--/only" not in saida, f"{caminho.stem}/{frontend}"
                assert "{{" not in saida, f"{caminho.stem}/{frontend}: variável não resolvida"

    def test_blocos_estao_balanceados(self) -> None:
        abre = re.compile(r"<!--only:")
        fecha = re.compile(r"<!--/only-->")
        for caminho in _fontes():
            texto = caminho.read_text(encoding="utf-8")
            assert len(abre.findall(texto)) == len(fecha.findall(texto)), (
                f"{caminho.name}: <!--only:--> e <!--/only--> em número diferente"
            )

    def test_a_rota_question_nao_virou_nome_de_ferramenta(self) -> None:
        """`route: question` é valor de schema, igual nos dois frontends.

        A primeira derivação automática trocou a *rota* `question` pelo nome
        da *ferramenta* de perguntar, e o Claude Code passou a instruir
        `route: AskUserQuestion` — um valor que o CLI não reconhece.
        """
        enum = "code-loop | plan-first | question | research | inference"
        for caminho in _fontes():
            for frontend in FRONTENDS:
                saida = render(caminho.read_text(encoding="utf-8"), frontend, str(caminho))
                if "plan-first" not in saida:
                    continue
                assert enum in saida, (
                    f"{caminho.stem}/{frontend}: a lista de rotas foi corrompida — "
                    "`question` ali é valor de schema, não nome de ferramenta"
                )

    @pytest.mark.parametrize("frontend", sorted(FRONTENDS))
    def test_nenhuma_rota_virou_nome_de_ferramenta(self, frontend: str) -> None:
        proibidos = ("route: AskUserQuestion", "rota `AskUserQuestion`", "Se for `AskUserQuestion`")
        for caminho in _fontes():
            saida = render(caminho.read_text(encoding="utf-8"), frontend, str(caminho))
            for proibido in proibidos:
                assert proibido not in saida, f"{caminho.stem}/{frontend}: {proibido!r}"
