"""Exercita VERIFY e JUDGE contra um projeto real, sem mocks de subprocesso."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


def _executa(cwd: Path, *argv: str, code: int = 0) -> str:
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
    assert result.returncode == code, result.stdout + result.stderr
    return result.stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _executa(tmp_path, "git", "init", "-q")
    _executa(tmp_path, "git", "config", "user.email", "test@example.org")
    _executa(tmp_path, "git", "config", "user.name", "Test")
    (tmp_path / ".gitignore").write_text(".kata/\n/target/\n/Cargo.lock\n", encoding="utf-8")
    _executa(tmp_path, "git", "add", ".gitignore")
    _executa(tmp_path, "git", "commit", "-qm", "base")
    (tmp_path / ".kata").mkdir()
    return tmp_path


def _task(repo: Path, nome: str, arquivos: tuple[str, ...]) -> Path:
    task = repo / ".kata" / f"{nome}.yaml"
    task.write_text(
        yaml.safe_dump(
            {
                "task": nome,
                "status": "draft",
                "done": "O teste da soma passa na toolchain do projeto.",
                "surgical": {"files": [{"path": path, "necessary": True} for path in arquivos]},
            }
        ),
        encoding="utf-8",
    )
    return task


def _configura(repo: Path, **checks: list[str]) -> None:
    (repo / ".kata" / "config.yaml").write_text(
        yaml.safe_dump({"verify": {"profile": "declared", **checks}}), encoding="utf-8"
    )


def _kata(repo: Path, *argv: str, code: int = 0) -> str:
    return _executa(repo, sys.executable, "-m", "kata", *argv, code=code)


def _aprova(repo: Path, task: Path, argv: list[str]) -> tuple[str, ...]:
    nome = task.stem
    _kata(repo, "--verify-task", nome, "--criterion-met")
    verify = yaml.safe_load(task.read_text(encoding="utf-8"))["verify"]
    assert verify["command_argv"] == {"test": argv}
    assert verify["tests_pass"] is True
    assert verify["coverage_pct"] is None and verify["gate_used"] is None
    assert {"ruff_clean", "coverage_pass", "typecheck_clean"}.isdisjoint(verify)
    _executa(repo, "git", "add", ".")
    _executa(repo, "git", "commit", "-qm", "test: cover addition")
    _kata(repo, "--stamp", nome)
    assert "✅ teste: passou" in _kata(repo, "--report", "--task", nome)
    judge = ("--judge", "--task", nome, "--require-verified")
    assert "VERIFIED" in _kata(repo, *judge)
    return judge


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js não instalado")
def test_node_declared_verify_report_e_judge(repo: Path) -> None:
    nome = "a.test.cjs b.test.cjs"
    argv = ["node", "--test", nome]
    arquivos = (nome, *nome.split())
    task = _task(repo, "node", arquivos)
    _configura(repo, test=argv)
    teste = """const test = require('node:test');
const assert = require('node:assert/strict');
test('soma', () => assert.equal(2 + 3, 5));
"""
    for path in arquivos:
        (repo / path).write_text(teste, encoding="utf-8")

    judge = _aprova(repo, task, argv)
    # As duas formas têm a mesma string de exibição, mas argv diferente.
    _configura(repo, test=["node", "--test", *nome.split()])
    out = _kata(repo, *judge, code=1)
    assert "comando diferente do aprovado" in out
    assert "UNVERIFIABLE" in out
    assert "UNVERIFIABLE" in _kata(repo, *judge[:-1])  # política legada mantém exit 0

    _configura(repo, lint=["node", "--check", nome])
    assert "papel não configurado" in _kata(repo, *judge, code=1)

    _configura(repo, test=argv)
    (repo / nome).write_text(teste.replace("2 + 3, 5", "2 + 3, 6"), encoding="utf-8")
    assert "REFUTED" in _kata(repo, *judge, code=1)


@pytest.mark.parametrize(
    ("argv", "manifest", "conteudo", "arquivo", "teste"),
    [
        pytest.param(
            ["go", "test", "-count=1", "./..."],
            "go.mod",
            "module example.org/soma\n\ngo 1.22\n",
            "soma_test.go",
            'package soma\nimport "testing"\n'
            'func TestSoma(t *testing.T) { if 2+3 != esperado { t.Fatal("soma") } }\n'
            "const esperado = 5\n",
            marks=pytest.mark.skipif(shutil.which("go") is None, reason="Go não instalado"),
            id="go",
        ),
        pytest.param(
            ["cargo", "test", "--offline"],
            "Cargo.toml",
            '[package]\nname = "soma"\nversion = "0.1.0"\nedition = "2021"\n',
            "src/lib.rs",
            "#[test]\nfn soma() { let esperado = 5; assert_eq!(2 + 3, esperado); }\n",
            marks=pytest.mark.skipif(shutil.which("cargo") is None, reason="Cargo não instalado"),
            id="rust",
        ),
    ],
)
def test_toolchain_declared_confirma_e_refuta(
    repo: Path, argv: list[str], manifest: str, conteudo: str, arquivo: str, teste: str
) -> None:
    task = _task(repo, "soma", (manifest, arquivo))
    _configura(repo, test=argv)
    (repo / manifest).write_text(conteudo, encoding="utf-8")
    path = repo / arquivo
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(teste, encoding="utf-8")
    judge = _aprova(repo, task, argv)

    path.write_text(teste.replace("esperado = 5", "esperado = 6"), encoding="utf-8")
    out = _kata(repo, *judge, code=1)
    assert "REFUTED" in out
    assert "teste re-executado falhou" in out
    _kata(repo, "--verify-task", "soma", "--criterion-met", code=1)
    assert yaml.safe_load(task.read_text(encoding="utf-8"))["verify"]["tests_pass"] is False
