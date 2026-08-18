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
DOMINIOS = REPO / "domains"

# O arquivo da fonte que é o orquestrador, e não uma fase. Tem destino
# próprio em cada frontend (agente no OpenCode, skill no Claude Code).
ORQUESTRADOR = "kata"

# ── o contrato de um frontend ────────────────────────────────────────────

# Os papéis que o ciclo exige. Um frontend é definido por como *ele* chama
# cada um. São papéis, e não nomes de ferramenta, de propósito: `RUN` é
# "executar um comando", não "bash" — um frontend sem bash ainda executa
# comandos, e chamar a variável de BASH fazia o contrato parecer amarrado a
# um shell específico.
REQUIRED_ROLES: frozenset[str] = frozenset(
    {
        "LOAD_PHASE",  # carregar as instruções de uma fase
        "LOAD_DOMAIN",  # carregar as instruções de um domain adapter
        "ASK",  # perguntar ao usuário
        "RUN",  # executar um comando
        "READ",  # ler um arquivo
        "WRITE",  # criar/escrever um arquivo
        "EDIT",  # alterar um arquivo existente
        "SEARCH",  # buscar por conteúdo no projeto
        "LIST_FILES",  # encontrar arquivos por padrão de nome
    }
)

# Como o frontend se apresenta. Não é capacidade: é nome, e não muda o que
# o ciclo pode fazer. AGENTE_CAP morreu por desuso (nenhuma fonte a usava) e
# foi removida — uma variável de identidade que nada renderiza é custo morto
# para quem implementa frontend novo (R10-28).
REQUIRED_IDENTITY: frozenset[str] = frozenset(
    {
        "AGENTE",
        "AGENTE_CAP_MIN",
        "FRONTEND_NOME",
        "ESTE_ORQUESTRADOR",
        "INVOC",
        "INVOC_SEM_ARGS",
    }
)

# Capacidades conhecidas, para os blocos `<!--if:-->` / `<!--ifnot:-->`.
# Capacidade não declarada aqui é erro de build: um typo em `<!--if:-->`
# faria o bloco sumir calado dos dois frontends.
CAPABILITIES: frozenset[str] = frozenset(
    {
        # A ferramenta de perguntar é de escolha fechada, com teto de opções —
        # então pergunta narrativa vai em texto normal, e não nela. É o que
        # governa quase todo o conteúdo condicional do repositório.
        "closed_choice_ask",
        # Existe uma lista de tarefas na UI para espelhar as fases.
        "task_tracker",
    }
)

FRONTENDS: dict[str, dict] = {
    "opencode": {
        "roles": {
            "LOAD_PHASE": "`skill`",
            "LOAD_DOMAIN": "`skill`",
            "ASK": "`question`",
            "RUN": "`bash`",
            "READ": "`read`",
            "WRITE": "`write`",
            "EDIT": "`edit`",
            "SEARCH": "`grep`",
            "LIST_FILES": "`glob`",
        },
        "identity": {
            "AGENTE": "o agente @kata",
            "AGENTE_CAP_MIN": "o agente",
            "FRONTEND_NOME": "OpenCode",
            "ESTE_ORQUESTRADOR": "O prompt do agente",
            "INVOC": "@kata ",
            "INVOC_SEM_ARGS": "`@kata` (sem args)",
        },
        # `question` é uma ferramenta de pergunta geral, sem teto de opções.
        "capabilities": set(),
        "orquestrador": "opencode/agent/kata.md",
        "fase": "opencode/skills/{slug}/SKILL.md",
    },
    "claude-code": {
        "roles": {
            "LOAD_PHASE": "`Skill`",
            "LOAD_DOMAIN": "`Skill`",
            "ASK": "`AskUserQuestion`",
            "RUN": "`Bash`",
            "READ": "`Read`",
            "WRITE": "`Write`",
            "EDIT": "`Edit`",
            "SEARCH": "`Grep`",
            "LIST_FILES": "`Glob`",
        },
        "identity": {
            "AGENTE": "o kata",
            "AGENTE_CAP_MIN": "a skill",
            "FRONTEND_NOME": "Claude Code",
            "ESTE_ORQUESTRADOR": "Esta skill",
            "INVOC": "",
            "INVOC_SEM_ARGS": "(sem args)",
        },
        # AskUserQuestion é fechada e cabe até 4 opções; pergunta aberta vai
        # em texto normal. TaskCreate/TaskUpdate espelham as fases na UI.
        "capabilities": {"closed_choice_ask", "task_tracker"},
        "orquestrador": "claude-code/skills/kata/SKILL.md",
        "fase": "claude-code/skills/{slug}/SKILL.md",
    },
}


def validate_frontends() -> None:
    """Todo frontend declara o contrato inteiro, e nada além dele.

    Papel faltando só apareceria quando alguma fase o usasse, o que faz uma
    definição incompleta parecer funcional até a fase errada ser renderizada.
    Capacidade desconhecida é typo, e um typo em `<!--if:-->` some calado.
    """
    for nome, spec in FRONTENDS.items():
        faltando = REQUIRED_ROLES - set(spec["roles"])
        sobrando = set(spec["roles"]) - REQUIRED_ROLES
        if faltando:
            raise ValueError(f"{nome}: papéis não declarados: {sorted(faltando)}")
        if sobrando:
            raise ValueError(f"{nome}: papéis fora do contrato: {sorted(sobrando)}")
        if set(spec["identity"]) != REQUIRED_IDENTITY:
            diff = set(spec["identity"]) ^ REQUIRED_IDENTITY
            raise ValueError(f"{nome}: identidade divergente: {sorted(diff)}")
        desconhecidas = set(spec["capabilities"]) - CAPABILITIES
        if desconhecidas:
            raise ValueError(f"{nome}: capacidades desconhecidas: {sorted(desconhecidas)}")


def _vars(frontend: str) -> dict[str, str]:
    spec = FRONTENDS[frontend]
    return {**spec["roles"], **spec["identity"]}


def _bloco(marcador: str) -> re.Pattern[str]:
    return re.compile(
        rf"^[ \t]*<!--{marcador}:(?P<nomes>[\w\-, ]+)-->[ \t]*\n"
        rf"(?P<corpo>.*?)^[ \t]*<!--/{marcador}-->[ \t]*\n",
        re.DOTALL | re.MULTILINE,
    )


_ONLY = _bloco("only")
_IF = _bloco("if")
_IFNOT = _bloco("ifnot")
_VAR = re.compile(r"\{\{(\w+)\}\}")


# Marcadores condicionais que o render espera sempre em pares abertos.
_MARCADORES = ("only", "if", "ifnot")


def _verifica_balanceamento(texto: str, origem: str) -> None:
    """Marcador de abertura sem o par de fechamento é erro de build, nunca
    texto literal (R10-3).

    Um typo que apague um `<!--/only-->` deixava o marcador e o conteúdo
    visíveis na skill instalada de TODOS os frontends, e o --check comparava
    gerado contra gerado — passando com o arquivo corrompido. O mesmo
    contrato de variável não declarada (erro, não literal) vale aqui.

    K-24: `<!--if:-->` com lista de nomes VAZIA também é erro — a contagem
    de pares casava (a substring `<!--if:` existe), mas o regex de resolução
    exige 1+ nomes e o bloco vazava literalmente para o gerado. Um marcador
    sem nomes não tem significado; é typo, não conteúdo condicional.
    """
    for marca in _MARCADORES:
        abre = len(re.findall(rf"<!--{marca}:", texto))
        fecha = len(re.findall(rf"<!--/{marca}-->", texto))
        if abre != fecha:
            raise ValueError(
                f"{origem}: marcador <!--{marca}:--> sem fechamento correspondente "
                f"({abre} abertura(s), {fecha} fechamento(s))"
            )
        vazios = re.findall(rf"<!--{marca}:-->", texto)
        if vazios:
            raise ValueError(
                f"{origem}: marcador <!--{marca}:--> sem nomes ({len(vazios)} "
                "ocorrência(s)) — vazaria literal para o gerado"
            )


def _resolve_blocos(texto: str, frontend: str) -> str:
    """Resolve os blocos condicionais para um frontend.

    `<!--if:CAP-->` e `<!--ifnot:CAP-->` primeiro, `<!--only:NOME-->` depois.
    A ordem importa pouco porque não se aninham, mas a preferência importa
    muito: quase todo conteúdo condicional deste repositório depende de uma
    *capacidade* (a ferramenta de perguntar ser de escolha fechada), e não da
    identidade do frontend. Amarrá-lo ao nome obrigaria um terceiro frontend
    com a mesma forma a ser adicionado a treze blocos, um a um. `only:` fica
    para o que é identidade de verdade: frontmatter, título, invocação.
    """
    capacidades = FRONTENDS[frontend]["capabilities"]

    def por_capacidade(m: re.Match[str], quando: bool) -> str:
        nomes = {n.strip() for n in m.group("nomes").split(",")}
        desconhecidas = nomes - CAPABILITIES
        if desconhecidas:
            raise ValueError(f"capacidade desconhecida: {sorted(desconhecidas)}")
        tem = bool(nomes & capacidades)
        return m.group("corpo") if tem is quando else ""

    def por_frontend(m: re.Match[str]) -> str:
        nomes = {n.strip() for n in m.group("nomes").split(",")}
        desconhecidos = nomes - set(FRONTENDS)
        if desconhecidos:
            raise ValueError(f"frontend desconhecido em <!--only:-->: {sorted(desconhecidos)}")
        return m.group("corpo") if frontend in nomes else ""

    texto = _IF.sub(lambda m: por_capacidade(m, True), texto)
    texto = _IFNOT.sub(lambda m: por_capacidade(m, False), texto)
    return _ONLY.sub(por_frontend, texto)


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
    _verifica_balanceamento(fonte, origem)
    texto = _resolve_blocos(fonte, frontend)
    return _resolve_vars(texto, _vars(frontend), origem)


# Comentário HTML: não aparece no markdown renderizado, mas aparece para quem
# abre o arquivo — que é justamente quem está prestes a editá-lo à mão.
_AVISO = "<!-- Gerado por scripts/build_skills.py a partir de {origem}. Não edite aqui. -->\n"

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _com_aviso(texto: str, origem_relativa: str) -> str:
    """Insere o aviso de arquivo gerado logo após o frontmatter.

    Depois, e não antes: o frontmatter tem de ser a primeira coisa do arquivo
    ou os hosts não o reconhecem, e a skill perde nome e descrição.
    """
    aviso = _AVISO.format(origem=origem_relativa)
    m = _FRONTMATTER.match(texto)
    if m is None:
        return aviso + texto
    return texto[: m.end()] + aviso + texto[m.end() :]


def _destino(slug: str, frontend: str) -> Path:
    spec = FRONTENDS[frontend]
    if slug == ORQUESTRADOR:
        return REPO / spec["orquestrador"]
    return REPO / spec["fase"].format(slug=slug)


def _destino_dir(frontend: str) -> Path:
    """Diretório onde as skills de fase de um frontend são geradas.

    `fase` é `opencode/skills/{slug}/SKILL.md`; o diretório que agrupa as
    skills é dois níveis acima do arquivo (skills/<slug>/SKILL.md).
    """
    spec = FRONTENDS[frontend]
    caminho = REPO / spec["fase"].format(slug="kata-fit")
    return caminho.parent.parent


def _fontes() -> list[Path]:
    if not FONTE.is_dir():
        raise SystemExit(f"fonte não encontrada: {FONTE}")
    fontes = sorted(FONTE.glob("*.md"))
    if DOMINIOS.is_dir():
        # TEMPLATE.md é documentação do schema de adapters, não uma skill
        # instalável.
        dominios = sorted(p for p in DOMINIOS.glob("*.md") if p.stem != "TEMPLATE")
        # O orquestrador carrega adapters por nome `kata-<domínio>`
        # ({{LOAD_DOMAIN}}), e o doctor só os conhece assim. Um nome fora da
        # convenção geraria uma skill que ninguém carrega nem checa (R10-20).
        sem_prefixo = [p.name for p in dominios if not p.stem.startswith("kata-")]
        if sem_prefixo:
            raise SystemExit(
                "domínios devem ser nomeados kata-<domínio>: " + ", ".join(sem_prefixo)
            )
        colisao = sorted({p.stem for p in fontes} & {p.stem for p in dominios})
        if colisao:
            # O domínio renderizaria para o MESMO destino da fase
            # (opencode/skills/<slug>/SKILL.md) e a sobrescreveria em
            # silêncio (R10-18). Falha nomeada, não divergência confusa.
            raise SystemExit(
                "colisão de nomes entre phases/ e domains/: "
                + ", ".join(colisao)
                + " — um domínio sobrescreveria a fase no destino gerado"
            )
        fontes.extend(dominios)
    return fontes


def build(check: bool = False) -> int:
    """Gera (ou confere) todos os arquivos. Retorna a contagem de divergências."""
    validate_frontends()
    divergentes: list[str] = []
    gerados = set()

    for caminho in _fontes():
        slug = caminho.stem
        fonte = caminho.read_text(encoding="utf-8")
        for frontend in FRONTENDS:
            saida = _com_aviso(
                render(fonte, frontend, origem=str(caminho.relative_to(REPO))),
                str(caminho.relative_to(REPO)),
            )
            destino = _destino(slug, frontend)
            gerados.add(destino)
            atual = destino.read_text(encoding="utf-8") if destino.exists() else None

            if atual == saida:
                continue
            if check:
                divergentes.append(str(destino.relative_to(REPO)))
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(saida, encoding="utf-8")
            print(f"  ✅ {destino.relative_to(REPO)}")

    # K-24: gerados órfãos — deletar phases/kata-x.md deixa o SKILL.md
    # correspondente nos dois frontends sem fonte. O --check só compara o que
    # existe, então passava com a skill morta; e os instaladores derivam a
    # lista do filesystem e linkam o órfão. Remover (ou denunciar no --check)
    # o que não tem fonte correspondente.
    for frontend in FRONTENDS:
        dest_dir = _destino_dir(frontend)
        if not dest_dir.exists():
            continue
        for filho in dest_dir.iterdir():
            if not filho.is_dir():
                continue
            destino = filho / "SKILL.md"
            if destino in gerados or not destino.exists():
                continue
            rel = str(destino.relative_to(REPO))
            if check:
                divergentes.append(f"{rel} (órfão — sem fonte em phases/)")
                continue
            filho.unlink() if not any(filho.iterdir()) else destino.unlink()
            print(f"  🗑  {rel} (órfão — fonte removida)")

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
