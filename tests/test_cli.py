"""Testes para kata.cli — helpers não-interativos."""

from __future__ import annotations

import subprocess

from kata import cli


class TestSerializeDeserialize:
    """Testa round-trip de serialização YAML/JSON."""

    def test_roundtrip_simple(self) -> None:
        data = {"task": "test", "status": "draft"}
        text = cli._serialize(data)
        result = cli._deserialize(text)
        assert result == data

    def test_roundtrip_nested(self) -> None:
        data = {
            "task": "test",
            "think": {
                "problem": "algo",
                "assumptions": ["a", "b"],
                "answered": True,
            },
        }
        text = cli._serialize(data)
        result = cli._deserialize(text)
        assert result == data

    def test_roundtrip_empty_dict(self) -> None:
        result = cli._deserialize(cli._serialize({}))
        assert result == {}


class TestExt:
    """Testa a extensão de arquivo (.yaml ou .json)."""

    def test_ext_returns_string(self) -> None:
        ext = cli._ext()
        assert ext in (".yaml", ".json")


class TestTaskPath:
    """Testa construção do caminho .kata/<task>.yaml."""

    def test_task_path_contains_kata_dir(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = cli._task_path("my-task")
        assert ".kata" in str(path)
        assert "my-task" in str(path)


class TestInitTask:
    """Testa criação do template .kata/<task>.yaml."""

    def test_init_creates_file(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        cli._kata_dir().mkdir(parents=True, exist_ok=True)
        cli._init_task("test-task")

        path = cli._task_path("test-task")
        assert path.exists()

        import kata.cli as cli_mod

        data = cli_mod._deserialize(path.read_text(encoding="utf-8"))
        assert data["task"] == "test-task"
        assert data["status"] == "draft"
        assert data["think"]["answered"] is False

    def test_init_existing_warns(self, tmp_path, monkeypatch, capsys) -> None:
        monkeypatch.chdir(tmp_path)
        cli._kata_dir().mkdir(parents=True, exist_ok=True)
        cli._init_task("existing-task")
        cli._init_task("existing-task")  # segunda vez deve avisar
        captured = capsys.readouterr()
        assert "já existe" in captured.out


class TestDetectTaskFromBranch:
    """Testa detecção de task a partir do branch git."""

    def test_detect_normal_branch(self, monkeypatch) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="feature/my-task\n", stderr=""
        )
        monkeypatch.setattr(
            "subprocess.run", lambda *a, **kw: mock_result
        )
        task = cli._detect_task_from_branch()
        assert task == "feature-my-task"

    def test_detect_detached_head(self, monkeypatch) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="HEAD\n", stderr=""
        )
        monkeypatch.setattr(
            "subprocess.run", lambda *a, **kw: mock_result
        )
        task = cli._detect_task_from_branch()
        assert task is None

    def test_detect_git_error(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(subprocess.CalledProcessError(1, [])),
        )
        task = cli._detect_task_from_branch()
        assert task is None

    def test_detect_underscores_replaced(self, monkeypatch) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="bug_fix_123\n", stderr=""
        )
        monkeypatch.setattr(
            "subprocess.run", lambda *a, **kw: mock_result
        )
        task = cli._detect_task_from_branch()
        assert task == "bug-fix-123"
