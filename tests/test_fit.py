"""Testes para kata.fit — fit gate (diff_stats, is_trivial, classify_route)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from kata.fit import diff_stats, is_trivial


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


class TestDiffStats:
    """Testa diff_stats — análise do diff git."""

    @patch("kata.fit._run")
    def test_unstaged_changes(self, mock_run: MagicMock) -> None:
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
    def test_staged_changes(self, mock_run: MagicMock) -> None:
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
    def test_no_changes(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        files, lines = diff_stats()
        assert files == []
        assert lines == 0

    @patch("kata.fit._run")
    def test_empty_stat_no_lines(self, mock_run: MagicMock) -> None:
        """diff --stat sem alterações não deve quebrar."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="file.py\n", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        files, lines = diff_stats()
        assert files == ["file.py"]
        assert lines == 0



