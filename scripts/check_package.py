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
import tomllib
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "src" / "kata" / "assets"
# Código mínimo sem o qual o pacote não roda, independente dos assets.
ESSENCIAIS = ("kata/__init__.py", "kata/cli.py", "kata/install.py")


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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    wheels = [Path(a) for a in args] or sorted((REPO / "dist").glob("*.whl"))
    if not wheels:
        print("❌ nenhum wheel em dist/ — rode `python3 -m build` antes")
        return 1
    problemas: list[str] = []
    for wheel in wheels:
        encontrados = conferir(wheel)
        if encontrados:
            problemas.extend(f"{wheel.name}: {p}" for p in encontrados)
            continue
        print(
            f"  ✅ {wheel.name}: {len(assets_esperados())} asset(s) + {len(ESSENCIAIS)} módulo(s)"
        )
    if problemas:
        print("\n❌ artefato inconsistente com src/kata/assets/:")
        for p in problemas:
            print(f"  {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
