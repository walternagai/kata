"""Testes para kata.fit — fit gate (diff_stats, is_trivial, classify_route)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from kata.fit import TRIVIAL_MAX_LINES, diff_stats, is_trivial, untracked_stats
from kata.verify import MAX_UNTRACKED_FILE_BYTES


class TestIsTrivial:
    """Testa is_trivial — detecção de tarefas triviais."""

    def test_trivial_one_file_few_lines(self) -> None:
        assert is_trivial(["src/foo.py"], 5) is True

    def test_trivial_no_files_zero_lines(self) -> None:
        assert is_trivial([], 0) is True

    def test_not_trivial_two_files(self) -> None:
        assert is_trivial(["src/foo.py", "src/bar.py"], 3) is False

    def test_not_trivial_many_lines(self) -> None:
        assert is_trivial(["src/foo.py"], 15) is False

    def test_not_trivial_two_files_many_lines(self) -> None:
        assert is_trivial(["src/foo.py", "src/bar.py"], 20) is False

    def test_edge_10_lines_still_trivial(self) -> None:
        assert is_trivial(["src/foo.py"], 9) is True

    def test_edge_10_lines_not_trivial(self) -> None:
        assert is_trivial(["src/foo.py"], 10) is False


@patch("kata.fit.untracked_files", return_value=[])
class TestDiffStats:
    """Testa diff_stats — análise do diff git."""

    @patch("kata.fit._run")
    def test_unstaged_changes(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[], returncode=0,
                stdout="src/foo.py\nsrc/bar.py\n", stderr="",
            ),
            subprocess.CompletedProcess(
                args=[], returncode=0,
                stdout=" src/foo.py | 3 +--\n src/bar.py | 2 ++\n",
                stderr="",
            ),
        ]
        files, lines = diff_stats()
        assert files == ["src/foo.py", "src/bar.py"]
        assert lines == 5

    @patch("kata.fit._run")
    def test_staged_changes(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="",
            ),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="baz.py\n", stderr="",
            ),
            subprocess.CompletedProcess(
                args=[], returncode=0,
                stdout=" baz.py | 7 ++++++-\n", stderr="",
            ),
        ]
        files, lines = diff_stats()
        assert files == ["baz.py"]
        assert lines == 7

    @patch("kata.fit._run")
    def test_no_changes(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        files, lines = diff_stats()
        assert files == []
        assert lines == 0

    @patch("kata.fit._run")
    def test_empty_stat_no_lines(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        """diff --stat sem alterações não deve quebrar."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="file.py\n", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        files, lines = diff_stats()
        assert files == ["file.py"]
        assert lines == 0





class TestUntrackedIsNotInvisible:
    """Prova, com um repo git de verdade, que arquivos novos contam para o
    triviality gate. Mock não serve aqui: o defeito era exatamente o comando
    que nunca era chamado."""

    def _repo(self, tmp_path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)

    def test_new_module_is_not_trivial(self, tmp_path) -> None:
        """Criar um módulo de 200 linhas aparecia como diff vazio, e o
        triviality gate mandava pular SIMPLIFY, INTENT e SURGICAL."""
        self._repo(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "servico.py").write_text(
            "\n".join(f"def f{i}(): return {i}" for i in range(200)) + "\n", encoding="utf-8"
        )

        files, lines = diff_stats(cwd=tmp_path)

        assert files == ["src/servico.py"]
        assert lines == 200
        assert is_trivial(files, lines) is False

    def test_untracked_counted_alongside_modified(self, tmp_path) -> None:
        """Untracked é somado, não usado como fallback: um arquivo modificado
        não pode fazer os novos desaparecerem."""
        self._repo(tmp_path)
        (tmp_path / "README.md").write_text("modificado\n", encoding="utf-8")
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")

        files, lines = diff_stats(cwd=tmp_path)

        assert sorted(files) == ["README.md", "novo.py"]
        assert lines >= 2

    def test_single_small_new_file_stays_trivial(self, tmp_path) -> None:
        """O gate não pode passar a recusar tudo: um arquivo novo e curto
        continua trivial."""
        self._repo(tmp_path)
        (tmp_path / "nota.txt").write_text("uma linha\n", encoding="utf-8")

        files, lines = diff_stats(cwd=tmp_path)

        assert is_trivial(files, lines) is True

    def test_binary_file_counts_as_non_trivial(self, tmp_path) -> None:
        """Antes contava 0 linhas, e com um arquivo só isso virava "trivial".
        O que não pode ser lido não pode ser declarado trivial."""
        self._repo(tmp_path)
        (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00binario")

        files, lines = untracked_stats(cwd=tmp_path)

        assert files == ["blob.bin"]
        assert lines >= TRIVIAL_MAX_LINES
        assert is_trivial(files, lines) is False

    def test_oversized_file_counts_as_non_trivial(self, tmp_path) -> None:
        """Grande demais para contar linha por linha, e grande demais para ser
        trivial. Pular — o que o judge faz, porque precisa do conteúdo — daria
        0 linha e reabriria a cegueira do triviality gate."""
        self._repo(tmp_path)
        grande = tmp_path / "dados.csv"
        grande.write_text("x,y\n" * 200_000, encoding="utf-8")
        assert grande.stat().st_size > MAX_UNTRACKED_FILE_BYTES

        files, lines = untracked_stats(cwd=tmp_path)

        assert files == ["dados.csv"]
        assert lines >= TRIVIAL_MAX_LINES
        assert is_trivial(files, lines) is False

    def test_oversized_file_is_not_read(self, tmp_path, monkeypatch) -> None:
        """A contagem tem de vir do tamanho, não da leitura: ler é justamente
        o que o teto evita."""
        self._repo(tmp_path)
        (tmp_path / "dados.csv").write_text("x,y\n" * 200_000, encoding="utf-8")

        def recusa(*args, **kwargs):
            raise AssertionError("arquivo acima do teto não deve ser aberto")

        monkeypatch.setattr(Path, "open", recusa)
        files, lines = untracked_stats(cwd=tmp_path)

        assert files == ["dados.csv"]
        assert lines == TRIVIAL_MAX_LINES
