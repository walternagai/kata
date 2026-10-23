"""O verificador do wheel reprova o que ele promete reprovar.

`scripts/check_package.py` é o único guarda que olha o artefato publicado em
vez da árvore de fontes. Se ele passar sempre, o CI ganha um verde decorativo
— exatamente o defeito que ele existe para evitar. Cada teste monta um wheel
de mentira em `tmp_path` e confere que o problema nomeado aparece.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from check_package import conferir  # noqa: E402 - depende do sys.path acima


def _wheel(tmp_path: Path, membros: dict[str, str]) -> Path:
    caminho = tmp_path / "kata_dev-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, conteudo in membros.items():
            z.writestr(nome, conteudo)
    return caminho


def _completo() -> dict[str, str]:
    from check_package import ESSENCIAIS, versao_do_pyproject

    membros = {n: "" for n in ESSENCIAIS}
    membros["kata/__init__.py"] = f'__version__ = "{versao_do_pyproject()}"\n'
    return membros


class TestConferir:
    def test_wheel_completo_nao_tem_problema(self, tmp_path) -> None:
        from check_package import assets_esperados

        membros = _completo() | {n: "x" for n in assets_esperados()}
        assert conferir(_wheel(tmp_path, membros)) == []

    def test_asset_faltando_e_nomeado(self, tmp_path) -> None:
        from check_package import assets_esperados

        membros = _completo() | {n: "x" for n in assets_esperados()}
        alvo = "kata/assets/opencode/agents/kata-advisor.md"
        del membros[alvo]

        problemas = conferir(_wheel(tmp_path, membros))

        assert any(alvo in p for p in problemas), problemas

    def test_modulo_essencial_faltando_e_nomeado(self, tmp_path) -> None:
        from check_package import assets_esperados

        membros = _completo() | {n: "x" for n in assets_esperados()}
        del membros["kata/cli.py"]

        assert any("kata/cli.py" in p for p in conferir(_wheel(tmp_path, membros)))

    def test_versao_divergente_e_apontada_como_artefato_velho(self, tmp_path) -> None:
        from check_package import assets_esperados

        membros = _completo() | {n: "x" for n in assets_esperados()}
        membros["kata/__init__.py"] = '__version__ = "0.0.1"\n'

        problemas = conferir(_wheel(tmp_path, membros))

        assert any("artefato velho" in p for p in problemas), problemas

    def test_wheel_inexistente_nao_explode(self, tmp_path) -> None:
        assert conferir(tmp_path / "nao-existe.whl") == [
            f"{tmp_path / 'nao-existe.whl'}: não existe"
        ]


class TestMain:
    def test_sem_wheel_em_dist_sai_um(self, tmp_path, monkeypatch, capsys) -> None:
        import check_package as cp

        monkeypatch.setattr(cp, "REPO", tmp_path)
        assert cp.main([]) == 1
        assert "nenhum wheel" in capsys.readouterr().out

    def test_wheel_incompleto_sai_um_e_lista(self, tmp_path, monkeypatch, capsys) -> None:
        import check_package as cp

        monkeypatch.setattr(cp, "REPO", tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n', encoding="utf-8"
        )
        (tmp_path / "dist").mkdir()
        _wheel(tmp_path / "dist", {"kata/__init__.py": '__version__ = "0.0.0"'})

        assert cp.main([]) == 1
        assert "ausente no wheel" in capsys.readouterr().out


@pytest.mark.parametrize("nome", ["kata-advisor.md"])
def test_o_asset_do_subagente_esta_na_lista(nome: str) -> None:
    """Regressão da v0.7.4: o advisor ficou fora do wheel com tudo verde."""
    from check_package import assets_esperados

    assert any(p.endswith(nome) for p in assets_esperados())
