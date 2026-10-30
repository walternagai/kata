#!/usr/bin/env python3
"""Confere o artefato que vai para o PyPI, não a árvore de fontes.

Os testes provam que `src/kata/assets/` espelha o repositório, mas leem o
checkout — nunca o wheel. Um `package-data` quebrado, um `.md` novo fora do
glob ou um módulo que não entra no pacote passavam verdes em todos os gates e
só apareciam no dia do release (revisão completa de 2026-10, achado A2; a
v0.7.4 fechou uma lacuna dessa forma).

A lista de assets esperados é derivada de `src/kata/assets/`, não escrita à
mão: um asset novo entra na checagem sozinho, e um asset que deixe de ser
empacotado reprova nomeando o arquivo.

Uso:
    python3 scripts/check_package.py [dist/*.whl ...]
"""

from __future__ import annotations

import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "src" / "kata" / "assets"
# Código mínimo sem o qual o pacote não roda, independente dos assets.
ESSENCIAIS = ("kata/__init__.py", "kata/cli.py", "kata/install.py")
# Arquivos de documentação que o sdist precisa levar na raiz. O `MANIFEST.in`
# entra por conta do setuptools; a checagem existe para o dia em que deixar de
# entrar sem ninguém notar. O `CHANGELOG.md` não entra sem `include`.
SDIST_EXTRAS = ("CHANGELOG.md", "MANIFEST.in", "README.md", "LICENSE")


def assets_esperados() -> list[str]:
    """Caminhos de asset que o wheel tem de conter, com prefixo `kata/`."""
    return sorted(
        f"kata/assets/{p.relative_to(ASSETS).as_posix()}" for p in ASSETS.rglob("*") if p.is_file()
    )


def versao_do_pyproject() -> str:
    dados = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return str(dados["project"]["version"])


def conferir(wheel: Path) -> list[str]:
    """Devolve a lista de problemas; vazia significa artefato íntegro."""
    if not wheel.is_file():
        return [f"{wheel}: não existe"]
    problemas: list[str] = []
    with zipfile.ZipFile(wheel) as z:
        nomes = set(z.namelist())
        for caminho in (*ESSENCIAIS, *assets_esperados()):
            if caminho not in nomes:
                problemas.append(f"ausente no wheel: {caminho}")
        init = z.read("kata/__init__.py").decode("utf-8") if "kata/__init__.py" in nomes else ""
        esperada = versao_do_pyproject()
        if f'__version__ = "{esperada}"' not in init:
            problemas.append(
                f"versão do wheel diverge de pyproject.toml ({esperada!r}): artefato velho?"
            )
    return problemas


def conferir_sdist(tarball: Path) -> list[str]:
    """Devolve a lista de problemas do sdist; vazia significa artefato íntegro.

    O wheel é conferido arquivo a arquivo pelo `package-data`; o sdist não tem
    esse glob, vive do `MANIFEST.in` e das regras escondidas do setuptools.
    Foi assim que o changelog ficou de fora: o tarball saía, publicava, e o
    leitor da página do PyPI recebia um link para um arquivo que só existia no
    repositório.
    """
    if not tarball.is_file():
        return [f"{tarball}: não existe"]
    problemas: list[str] = []
    with tarfile.open(tarball) as t:
        # O sdist embrulha tudo num diretório `nome-versao/`: a raiz é o
        # primeiro componente, não uma constante.
        raizes = {Path(n).parts[0] for n in t.getnames() if n and not n.startswith("./")}
        if len(raizes) != 1:
            return [f"estrutura inesperada: {len(raizes)} diretório(s) de topo"]
        raiz = raizes.pop()
        nomes = {n for n in t.getnames()}
        for extra in SDIST_EXTRAS:
            if f"{raiz}/{extra}" not in nomes:
                problemas.append(f"ausente no sdist: {extra}")
    return problemas


def _artefatos(args: list[str]) -> list[Path]:
    """Wheels e sdists a conferir: os argumentos ou o que estiver em dist/."""
    if args:
        return [Path(a) for a in args]
    dist = REPO / "dist"
    return sorted(dist.glob("*.whl")) + sorted(dist.glob("*.tar.gz"))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    artefatos = _artefatos(args)
    if not artefatos:
        print("❌ nenhum artefato em dist/ — rode `python3 -m build` antes")
        return 1
    problemas: list[str] = []
    for artefato in artefatos:
        # `Path.suffix` de `.tar.gz` é `.gz`: o nome é que carrega as duas extensões.
        if artefato.name.endswith(".tar.gz"):
            encontrados = conferir_sdist(artefato)
            if encontrados:
                problemas.extend(f"{artefato.name}: {p}" for p in encontrados)
                continue
            print(f"  ✅ {artefato.name}: {len(SDIST_EXTRAS)} arquivo(s) de raiz")
            continue
        encontrados = conferir(artefato)
        if encontrados:
            problemas.extend(f"{artefato.name}: {p}" for p in encontrados)
            continue
        assets = len(assets_esperados())
        print(f"  ✅ {artefato.name}: {assets} asset(s) + {len(ESSENCIAIS)} módulo(s)")
    if problemas:
        print("\n❌ artefato inconsistente com src/kata/assets/:")
        for p in problemas:
            print(f"  {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
