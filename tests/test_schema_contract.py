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
    """Chaves aninhadas que cli.py e judge.py consultam no YAML da tarefa.

    Casa o padrão `.get("secao", {}).get("chave"` e as leituras via variável
    intermediária (`twins = data.get("twins", {})` seguido de
    `twins.get("defect_fixed")`).

    As seções são descobertas pelo receptor da chamada (`data` ou
    `task_data`), e não por uma lista escrita à mão. Enquanto a lista era
    fixa, uma seção nova ficava invisível para este teste: `preflight` foi
    lida pelo `--audit` e não documentada em nenhum orquestrador, e o teste
    que existe justamente para pegar isso passou.

    O receptor importa: `config.get("tool", {}).get("coverage", {})`, em
    _detect_cov_source, lê o pyproject.toml e não o YAML da tarefa.
    """
    fonte = "".join(
        (REPO / "src" / "kata" / f).read_text(encoding="utf-8") for f in ("cli.py", "judge.py")
    )
    # Antes só casava aspas duplas com default exato `{}`: leituras com aspas
    # simples ou default ≠ {} (ex.: `intent.get('code_does','')`) escapavam,
    # e a chave `domain` nova passaria despercebida (R10-27).
    aninhada = re.compile(
        r'\b(?:data|task_data)\.get\(["\'](\w+)["\'](?:,\s*[^)]*)?\)\.get\(["\'](\w+)["\']'
    )

    lidas: set[str] = set()
    secoes: set[str] = set()
    for secao, chave in aninhada.findall(fonte):
        secoes.add(secao)
        lidas.add(f"{secao}.{chave}")

    # Leituras em duas etapas: `twins = data.get("twins", {})` e depois
    # `twins.get("defect_fixed")`. A seção precisa ter sido vista acima ou
    # aqui, na atribuição.
    for secao in re.findall(
        r'\b(\w+)\s*=\s*(?:data|task_data)\.get\(["\']\w+["\'](?:,\s*[^)]*)?\)', fonte
    ):
        secoes.add(secao)
    for secao in secoes:
        for chave in re.findall(rf"\b{secao}\.get\(['\"](\w+)['\"]", fonte):
            lidas.add(f"{secao}.{chave}")
    # Chaves de topo lidas de uma etapa só (`data.get("domain", "coding")`)
    # eram invisíveis para o teste: a chave `domain` podia sumir do schema
    # documentado sem ninguém ver (R10-27).
    for secao in re.findall(r"\b(?:data|task_data)\.get\(['\"](\w+)['\"]", fonte):
        secoes.add(secao)
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
