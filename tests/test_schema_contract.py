"""O schema documentado tem de cobrir o que o código lê.

As skills não são documentação passiva: elas instruem o agente a escrever
`.kata/<task>.yaml` à mão. Uma chave que o código consulta e o schema não
documenta é uma chave que nenhum agente vai produzir — e a consequência é
silenciosa, porque `.get()` devolve o default e o gate simplesmente não
dispara.

Foi assim que a correção do M4 ficou inerte nos dois frontends: ela passou a
depender de `twins.defect_fixed`, que só o CLI sabia gravar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from kata import cli

REPO = Path(__file__).resolve().parent.parent

ORQUESTRADORES = [
    "opencode/agent/kata.md",
    "claude-code/skills/kata/SKILL.md",
]

# Módulos que leem o YAML da tarefa. `report.py` entrou no A3 da revisão
# estrutural: enquanto ficou de fora, 5 das 11 seções tinham zero leituras
# vistas e o contrato aprovava.
# `verify.py` entrou junto com o guarda de recorrência: `consistency_failures`
# lê `status`, `done` e o bloco `verify` do YAML da tarefa, e nunca esteve na
# varredura. `install.py` fica de fora de propósito — o `data.get("files")`
# dele é o marcador `.kata-managed`, não a tarefa.
FONTES_DE_LEITURA = ("cli.py", "judge.py", "report.py", "verify.py")


def _schema_documentado(arquivo: str) -> dict:
    """Extrai o bloco ```yaml do schema de tarefa."""
    texto = (REPO / arquivo).read_text(encoding="utf-8")
    bloco = re.search(r"```yaml\n(task:.*?)```", texto, re.S)
    assert bloco, f"{arquivo}: nenhum bloco de schema encontrado"
    return yaml.safe_load(bloco.group(1))


def _chaves(dic: dict, prefixo: str = "") -> set[str]:
    chaves: set[str] = set()
    for chave, valor in dic.items():
        chaves.add(prefixo + chave)
        if isinstance(valor, dict):
            chaves |= _chaves(valor, prefixo + chave + ".")
    return chaves


def _chaves_lidas_pelo_codigo() -> set[str]:
    """Chaves aninhadas que o código consulta no YAML da tarefa.

    Fontes: `cli.py`, `judge.py` e `report.py`. O terceiro entrou depois
    (achado A3 da revisão estrutural de 2026-10): quando o I/O de relatório e
    auditoria migrou para `report.py`, as seções que passaram a ser lidas lá
    saíram da varredura sem ninguém notar — `auth`, `pending`, `preflight`,
    `simplify` e `twins` ficaram com zero leituras vistas, e o teste que
    existe para impedir "chave documentada que ninguém lê" aprovava.

    Quatro formas de leitura, todas reconhecidas:

    1. direta: `data.get("secao").get("chave")`;
    2. helper inline: `_secao(data, "secao").get("chave")`,
       `bloco("secao").get("chave")`;
    3. duas etapas: `twins = data.get("twins", {})`, `verify = bloco("verify")`,
       `verify: dict[str, Any] = dict(_secao(data, "verify"))`, seguido de
       `{var}.get("chave")` — o mapa var→seção é explícito, então um nome de
       variável diferente do da seção não inventa uma seção falsa;
    4. topo: `data.get("domain", "coding")`.

    As seções são descobertas pelo receptor da chamada (`data`/`task_data`) ou
    pelo literal do helper, nunca por lista escrita à mão. O receptor importa:
    `config.get("tool", {}).get("coverage", {})`, em `_detect_cov_source`, lê o
    pyproject.toml e não o YAML da tarefa.
    """
    fonte = "".join(
        (REPO / "src" / "kata" / f).read_text(encoding="utf-8") for f in FONTES_DE_LEITURA
    )

    lidas: set[str] = set()

    # (1) Antes só casava aspas duplas com default exato `{}`: leituras com
    # aspas simples ou default ≠ {} (ex.: `intent.get('code_does','')`)
    # escapavam, e a chave `domain` nova passaria despercebida (R10-27).
    aninhada = re.compile(
        r'\b(?:data|task_data)\.get\(["\'](\w+)["\'](?:,\s*[^)]*)?\)\.get\(["\'](\w+)["\']'
    )
    for secao, chave in aninhada.findall(fonte):
        lidas.add(f"{secao}.{chave}")

    # (2) Helper inline. O `\)?` cobre `_secao(data, "x").get(` e
    # `bloco("x").get(` sem exigir que os dois helpers tenham a mesma aridade.
    helper_inline = re.compile(
        r"(?:(?:\b_secao\((?:data|task_data),\s*)|(?<![\w.])bloco\()"
        r'["\'](\w+)["\']\)?\.get\(["\'](\w+)["\']'
    )
    for secao, chave in helper_inline.findall(fonte):
        lidas.add(f"{secao}.{chave}")

    # (3) Duas etapas: `twins = data.get("twins", {})`,
    # `verify = bloco("verify")`, `verify: dict[str, Any] = dict(_secao(data,
    # "verify"))`, seguido de `{var}.get("chave")`. O mapa var→seção é
    # explícito: antes o nome da variável era usado como nome da seção, o que
    # funcionava só por convenção e inventava seção falsa quando divergia.
    atrib_get = re.compile(
        r"\b(\w+)\s*(?::\s*[^=\n]+)?=\s*(?:data|task_data)\.get\([\"\'](\w+)[\"\']"
    )
    atrib_helper = re.compile(
        r"\b(\w+)\s*(?::\s*[^=\n]+)?=\s*(?:dict\(\s*)?"
        r"(?:_secao\((?:data|task_data),\s*|(?<![\w.])bloco\()"
        r"[\"\'](\w+)[\"\']"
    )
    for var, secao in atrib_get.findall(fonte) + atrib_helper.findall(fonte):
        for chave in re.findall(rf"\b{var}\.get\(['\"](\w+)['\"]", fonte):
            lidas.add(f"{secao}.{chave}")

    # (4) Chaves de topo lidas de uma etapa só (`data.get("domain", "coding")`)
    # eram invisíveis para o teste: a chave `domain` podia sumir do schema
    # documentado sem ninguém ver (R10-27).
    for secao in re.findall(r"\b(?:data|task_data)\.get\(['\"](\w+)['\"]", fonte):
        lidas.add(secao)
    return lidas


def _chaves_escritas_pelo_codigo() -> set[str]:
    """Chaves que o CLI grava no YAML da tarefa (direção de escrita).

    A direção de leitura não vê chaves que o código grava mas nunca lê:
    `intent.conflict_resolution` e `simplify.notes` sumiram do schema
    documentado sem ninguém notar (R10-32). Um agente seguindo a skill
    documentada não grava o que o schema não lista.
    """
    fonte = (REPO / "src" / "kata" / "cli.py").read_text(encoding="utf-8")
    escritas: set[str] = set()

    # data["secao"] = { "chave": ..., ... } — bloco inteiro.
    for secao, corpo in re.findall(r'data\["(\w+)"\]\s*=\s*\{([^}]*)\}', fonte, re.DOTALL):
        for chave in re.findall(r'"(\w+)"\s*:', corpo):
            escritas.add(f"{secao}.{chave}")

    # Escrita incremental numa seção da tarefa (`verify["ruff_clean"] = ...`,
    # `simplify["notes"] = ...`) e top-level (`data["status"] = ...`).
    # Locais de UI (`checks["intent_present"]`) ficam de fora: não são schema.
    _SECOES = {
        "fit",
        "think",
        "intent",
        "simplify",
        "surgical",
        "verify",
        "twins",
        "preflight",
        "artifact",
        "auth",
        "pending",
    }
    for secao, chave in re.findall(r'\b(\w+)\["(\w+)"\]\s*=', fonte):
        if secao in {"data", "task_data"}:
            escritas.add(chave)
        elif secao in _SECOES:
            escritas.add(f"{secao}.{chave}")
    return escritas


@pytest.mark.parametrize("arquivo", ORQUESTRADORES)
def test_schema_documentado_cobre_o_que_o_codigo_le(arquivo: str) -> None:
    documentadas = _chaves(_schema_documentado(arquivo))
    faltando = sorted(k for k in _chaves_lidas_pelo_codigo() if k not in documentadas)
    assert not faltando, (
        f"{arquivo} não documenta chaves que o código lê: {faltando}. "
        "Um agente seguindo esta skill não vai gravá-las, e o gate "
        "correspondente nunca vai disparar."
    )


def _secoes_sem_leitura(schema: dict, lidas: set[str]) -> list[str]:
    """Seções documentadas para as quais nenhuma leitura foi vista.

    Separado do teste para poder ser exercitado com uma entrada falsa: um
    invariante que só sabe dizer "passou" é indistinguível do vácuo.
    """
    secoes = {k for k, v in schema.items() if isinstance(v, dict)}
    vistas = {k.split(".")[0] for k in lidas if "." in k}
    return sorted(secoes - vistas)


@pytest.mark.parametrize("arquivo", ORQUESTRADORES)
def test_toda_secao_documentada_tem_leitura_vista(arquivo: str) -> None:
    """A3: uma seção inteira pode escapar do contrato sem que nada acuse.

    Até a revisão estrutural de 2026-10, `auth`, `pending`, `preflight`,
    `simplify` e `twins` eram documentadas e nenhuma leitura delas era vista:
    o teste de chaves passava por vacuidade, e o `--audit` consumia
    `preflight.skills_missing` sem que nada validasse o nome.
    """
    schema = _schema_documentado(arquivo)
    faltando = _secoes_sem_leitura(schema, _chaves_lidas_pelo_codigo())
    assert not faltando, (
        f"{arquivo} documenta seção que nenhuma leitura vista alcança: {faltando}. "
        "Ou o módulo que a lê ficou fora de FONTES_DE_LEITURA, ou a seção virou "
        "peso morto no schema."
    )


def test_invariante_de_secao_nao_e_vacuo() -> None:
    """Prova que o invariante acima reprova de fato — com entrada falsa."""
    schema = {"fit": {"trivial": False}, "twins": {"searched": False}}
    assert _secoes_sem_leitura(schema, {"fit.trivial"}) == ["twins"]


@pytest.mark.parametrize("arquivo", ORQUESTRADORES)
def test_schema_documentado_cobre_o_que_o_cli_escreve(arquivo: str) -> None:
    """Direção de escrita (R10-32): chaves que o CLI grava no YAML da tarefa
    têm de estar no schema documentado. `intent.conflict_resolution` e
    `simplify.notes` sumiram da documentação sem ninguém notar — a direção de
    leitura não as pega porque o código nunca as lê."""
    documentadas = _chaves(_schema_documentado(arquivo))
    faltando = sorted(k for k in _chaves_escritas_pelo_codigo() if k not in documentadas)
    assert not faltando, (
        f"{arquivo} não documenta chaves que o CLI escreve: {faltando}. "
        "Um agente seguindo esta skill não vai gravá-las, e o YAML gerado "
        "diverge do schema."
    )


@pytest.mark.parametrize("arquivo", ORQUESTRADORES)
def test_template_do_init_cobre_o_schema_documentado(arquivo: str, tmp_path, monkeypatch) -> None:
    """`--init` e o schema documentado não podem divergir: quem começa pelo CLI
    e quem começa pela skill têm de acabar com o mesmo arquivo."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".kata").mkdir()
    cli._init_task("t")

    gerado = _chaves(yaml.safe_load((tmp_path / ".kata" / "t.yaml").read_text(encoding="utf-8")))
    documentado = _chaves(_schema_documentado(arquivo))

    # base_commit só existe dentro de um repo git; o template o omite fora dele.
    documentado.discard("base_commit")
    # approved_commit (R14) só é gravado no approve; o template do --init o omite.
    documentado.discard("approved_commit")
    faltando = sorted(documentado - gerado)
    assert not faltando, f"template de --init não tem: {faltando}"


def test_twins_gate_dispara_com_o_schema_documentado() -> None:
    """O teste que o M4 não teve: preencher o schema como um agente faria, e
    confirmar que o gate TWINS de fato reage."""
    schema = _schema_documentado("claude-code/skills/kata/SKILL.md")

    schema["twins"]["defect_fixed"] = True
    assert cli._detect_twins_owed(schema) is True

    schema["twins"]["defect_fixed"] = False
    assert cli._detect_twins_owed(schema) is False


@pytest.mark.parametrize("arquivo", ORQUESTRADORES)
def test_twin_check_esta_documentado_como_fase(arquivo: str) -> None:
    """A fase existia só no CLI, e a doc afirmava que os frontends tinham
    paridade com ele."""
    texto = (REPO / arquivo).read_text(encoding="utf-8")
    assert "TWIN CHECK" in texto
    assert "defect_fixed" in texto


def test_nenhum_modulo_fora_das_fontes_le_o_yaml_da_tarefa() -> None:
    """A lista de fontes é manual — e foi assim que `report.py` escapou.

    O A3 da revisão estrutural nasceu disto: quando o I/O de relatório e
    auditoria migrou do `cli.py` para o `report.py`, as seções que passaram a
    ser lidas lá saíram da varredura sem nenhum teste reclamar. Este guarda
    fecha a recorrência: módulo que leia o YAML da tarefa fora de
    `FONTES_DE_LEITURA` reprova, em vez de virar ponto cego silencioso.
    """
    # `data.get(` sozinho é largo demais: `install.py` lê o marcador
    # `.kata-managed` com a mesma forma. O padrão exige uma seção do schema.
    padrao = re.compile(
        r"_secao\(|\bbloco\(|\btask_data\.get\("
        r'|\bdata\.get\(\s*["\']'
        r"(?:verify|fit|think|simplify|intent|surgical|twins|auth|pending|preflight|artifact)[\"\']"
    )
    suspeitos = sorted(
        arq.name
        for arq in (REPO / "src" / "kata").glob("*.py")
        if arq.name not in FONTES_DE_LEITURA and padrao.search(arq.read_text(encoding="utf-8"))
    )
    assert not suspeitos, (
        f"módulo(s) leem o YAML da tarefa fora de FONTES_DE_LEITURA: {suspeitos}. "
        "Acrescente à lista — senão as chaves que eles leem ficam fora do contrato."
    )
