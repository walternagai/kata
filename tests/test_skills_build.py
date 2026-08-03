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
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from build_skills import (  # noqa: E402 - depende do sys.path acima
    CAPABILITIES,
    FRONTENDS,
    REQUIRED_IDENTITY,
    REQUIRED_ROLES,
    _destino,
    _fontes,
    build,
    render,
    validate_frontends,
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
        assert render("rode {{RUN}}", "opencode") == "rode `bash`"
        assert render("rode {{RUN}}", "claude-code") == "rode `Bash`"


class TestFontes:
    """Invariantes das fontes em phases/."""

    def test_nenhum_marcador_sobra_no_gerado(self) -> None:
        """Marcador vazado vira `<!--if:...-->` visível na skill instalada."""
        for caminho in _fontes():
            for frontend in FRONTENDS:
                saida = render(caminho.read_text(encoding="utf-8"), frontend, str(caminho))
                for marcador in ("<!--only", "<!--if", "<!--ifnot", "<!--/"):
                    assert marcador not in saida, f"{caminho.stem}/{frontend}: {marcador}"
                assert "{{" not in saida, f"{caminho.stem}/{frontend}: variável não resolvida"

    @pytest.mark.parametrize("marcador", ["only", "if", "ifnot"])
    def test_blocos_estao_balanceados(self, marcador: str) -> None:
        abre = re.compile(rf"<!--{marcador}:")
        fecha = re.compile(rf"<!--/{marcador}-->")
        for caminho in _fontes():
            texto = caminho.read_text(encoding="utf-8")
            assert len(abre.findall(texto)) == len(fecha.findall(texto)), (
                f"{caminho.name}: <!--{marcador}:--> e <!--/{marcador}--> em número diferente"
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


class TestContratoDeFrontend:
    """Um frontend é definido por como ele chama cada papel do ciclo.

    Papéis, e não nomes de ferramenta: `RUN` é "executar um comando", não
    "bash". Enquanto a variável se chamava `BASH`, o contrato parecia
    amarrado a um shell específico — e o ponto do kata ser agnóstico é
    justamente não estar.
    """

    def test_frontends_declarados_satisfazem_o_contrato(self) -> None:
        validate_frontends()

    @pytest.mark.parametrize("frontend", sorted(FRONTENDS))
    def test_todo_papel_do_contrato_esta_declarado(self, frontend: str) -> None:
        assert set(FRONTENDS[frontend]["roles"]) == set(REQUIRED_ROLES)
        assert set(FRONTENDS[frontend]["identity"]) == set(REQUIRED_IDENTITY)

    def test_papel_faltando_e_erro(self) -> None:
        """Sem isto, a definição incompleta parece funcional até a fase que
        usa aquele papel ser renderizada."""
        with patch.dict(
            FRONTENDS["opencode"],
            {"roles": {k: v for k, v in FRONTENDS["opencode"]["roles"].items() if k != "SEARCH"}},
        ):
            with pytest.raises(ValueError, match="papéis não declarados.*SEARCH"):
                validate_frontends()

    def test_papel_fora_do_contrato_e_erro(self) -> None:
        with patch.dict(
            FRONTENDS["opencode"],
            {"roles": {**FRONTENDS["opencode"]["roles"], "TELEPATIA": "`mente`"}},
        ):
            with pytest.raises(ValueError, match="papéis fora do contrato.*TELEPATIA"):
                validate_frontends()

    def test_capacidade_desconhecida_e_erro(self) -> None:
        with patch.dict(FRONTENDS["opencode"], {"capabilities": {"voa"}}):
            with pytest.raises(ValueError, match="capacidades desconhecidas.*voa"):
                validate_frontends()

    def test_todo_papel_e_usado_por_alguma_fonte(self) -> None:
        """Papel que nenhuma fase usa é contrato cobrado à toa de quem for
        implementar um frontend novo."""
        texto = "".join(c.read_text(encoding="utf-8") for c in _fontes())
        nao_usados = sorted(p for p in REQUIRED_ROLES if f"{{{{{p}}}}}" not in texto)
        assert not nao_usados, f"papéis exigidos mas nunca usados: {nao_usados}"


class TestBlocosPorCapacidade:
    """O conteúdo condicional depende do que o host sabe fazer, não do nome dele."""

    def test_if_entra_so_com_a_capacidade(self) -> None:
        fonte = "<!--if:closed_choice_ask-->\nfechada\n<!--/if-->\n"
        assert render(fonte, "claude-code") == "fechada\n"
        assert render(fonte, "opencode") == ""

    def test_ifnot_e_o_complemento(self) -> None:
        fonte = "<!--ifnot:closed_choice_ask-->\naberta\n<!--/ifnot-->\n"
        assert render(fonte, "opencode") == "aberta\n"
        assert render(fonte, "claude-code") == ""

    def test_capacidade_com_typo_e_erro_e_nao_bloco_sumido(self) -> None:
        """Um typo aqui apagaria o bloco dos dois frontends em silêncio."""
        with pytest.raises(ValueError, match="capacidade desconhecida"):
            render("<!--if:closed_choise_ask-->\nx\n<!--/if-->\n", "opencode")

    def test_a_maioria_do_condicional_e_capacidade_e_nao_identidade(self) -> None:
        """`only:` é para identidade — frontmatter, título, invocação.

        Quando um bloco de capacidade era escrito como `only:<frontend>`, um
        terceiro host com a mesma forma tinha de ser adicionado a cada um
        deles à mão. É a duplicata que o item anterior removeu, voltando por
        outra porta.
        """
        texto = "".join(c.read_text(encoding="utf-8") for c in _fontes())
        por_identidade = texto.count("<!--only:")
        por_capacidade = texto.count("<!--if:") + texto.count("<!--ifnot:")
        assert por_capacidade > por_identidade, (
            f"{por_capacidade} blocos por capacidade vs {por_identidade} por identidade"
        )


def test_um_frontend_novo_e_so_uma_entrada_na_tabela() -> None:
    """A promessa do contrato, verificada: nenhuma fase precisa ser reescrita.

    Renderiza a árvore inteira para um host hipotético que não existe no
    repositório. Se alguma fonte tivesse acoplamento a um frontend real —
    uma variável só declarada lá, um `only:` sem contraparte — este teste
    quebraria, e é o único jeito de saber isso sem de fato portar o kata.
    """
    novo = {
        "roles": {p: f"`{p.lower()}`" for p in REQUIRED_ROLES},
        "identity": dict.fromkeys(REQUIRED_IDENTITY, "X"),
        "capabilities": set(CAPABILITIES),
        "orquestrador": "hipotetico/kata.md",
        "fase": "hipotetico/{slug}/SKILL.md",
    }
    with patch.dict(FRONTENDS, {"hipotetico": novo}):
        validate_frontends()
        for caminho in _fontes():
            saida = render(caminho.read_text(encoding="utf-8"), "hipotetico", str(caminho))
            assert saida.strip(), f"{caminho.stem} rendeu vazio"
            assert "{{" not in saida
            assert "<!--only" not in saida and "<!--if" not in saida
