"""Testes para kata.judge — verificação adversarial (fable-judge)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from kata.judge import (
    JudgeFraud,
    JudgeResult,
    _changed_files,
    _oversized_untracked,
    _run_git_diff,
    _unreadable_test_files,
    _untracked_diff,
    collect_claims,
    collect_unverifiable_claims,
    hunt_debris,
    hunt_false_completion,
    hunt_scope_creep,
    hunt_spec_betrayal,
    hunt_unauthorized_action,
    hunt_weakened_checks,
    is_debris_file,
    judge_task,
)
from kata.verify import VerifyResult, is_inspectable


class TestJudgeResult:
    """Verifica o dataclass JudgeResult."""

    def test_default_values(self) -> None:
        r = JudgeResult()
        assert r.verdict == "VERIFIED"
        assert r.claims == []
        assert r.caveats == []
        assert r.frauds == []
        assert r.re_ran_checks == {}
        assert r.details == {}

    def test_with_values(self) -> None:
        f = JudgeFraud(type="debris", severity="low", description="debug print")
        r = JudgeResult(
            verdict="REFUTED",
            claims=["ruff passou"],
            caveats=["1 fraude"],
            frauds=[f],
            re_ran_checks={"ruff": False},
            details={"changed_files": 3},
        )
        assert r.verdict == "REFUTED"
        assert "ruff passou" in r.claims
        assert r.frauds[0].type == "debris"


class TestJudgeFraud:
    """Verifica o dataclass JudgeFraud."""

    def test_default_evidence_empty(self) -> None:
        f = JudgeFraud(type="x", severity="low", description="y")
        assert f.evidence == ""

    def test_all_fields(self) -> None:
        f = JudgeFraud(
            type="scope_creep",
            severity="high",
            description="extra files",
            evidence="unexpected.py",
        )
        assert f.type == "scope_creep"
        assert f.severity == "high"
        assert f.evidence == "unexpected.py"


class TestCollectClaims:
    """Testa extração de claims do YAML da tarefa."""

    def test_no_verify_section(self) -> None:
        claims = collect_claims({})
        assert claims == []

    def test_all_claims_present(self) -> None:
        data = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
                "coverage_pct": 95.0,
                "success_criteria_met": True,
            },
            "surgical": {"files": [{"path": "a.py", "necessary": True}]},
            "intent": {"all_agree": True},
        }
        claims = collect_claims(data)
        assert len(claims) == 5
        assert any("ruff" in c for c in claims)
        assert any("testes" in c for c in claims)
        assert any("coverage" in c for c in claims)
        assert any("intenção" in c for c in claims)
        assert any("arquivo" in c for c in claims)
        # O critério de sucesso não é re-executável, então não entra aqui.
        assert not any("critério" in c for c in claims)
        assert collect_unverifiable_claims(data) == ["critério de sucesso satisfeito"]

    def test_unverifiable_claims_empty_when_criterion_not_met(self) -> None:
        assert collect_unverifiable_claims({"verify": {"success_criteria_met": False}}) == []
        assert collect_unverifiable_claims({}) == []

    def test_partial_claims(self) -> None:
        data = {"verify": {"ruff_clean": True}}
        claims = collect_claims(data)
        assert len(claims) == 1
        assert "ruff" in claims[0]

    def test_optional_sections_empty(self) -> None:
        data = {"verify": {"ruff_clean": True}, "surgical": {}, "intent": {}}
        claims = collect_claims(data)
        assert len(claims) == 1

    def test_coverage_with_pct_in_claim(self) -> None:
        data = {"verify": {"coverage_pass": True, "coverage_pct": 87.3}}
        claims = collect_claims(data)
        assert any("87.3" in c for c in claims)

    def test_no_coverage_pct_fallback(self) -> None:
        data = {"verify": {"coverage_pass": True}}
        claims = collect_claims(data)
        assert any("?" in c for c in claims)

    def test_surgical_no_necessary(self) -> None:
        data = {"surgical": {"files": [{"path": "x.py", "necessary": False}]}}
        claims = collect_claims(data)
        assert not any("arquivo" in c for c in claims)

    def test_intent_not_all_agree(self) -> None:
        data = {"intent": {"all_agree": False}}
        claims = collect_claims(data)
        assert not any("intenção" in c for c in claims)


class TestHuntWeakenedChecks:
    """Testa caça a verificações enfraquecidas."""

    def test_no_diff_no_frauds(self) -> None:
        frauds = hunt_weakened_checks("")
        assert frauds == []

    def test_non_test_file_ignored(self) -> None:
        diff = """
diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -1 +1 @@
-assert True
+print("ok")
"""
        frauds = hunt_weakened_checks(diff)
        assert frauds == []

    def test_assert_true_removed_from_test(self) -> None:
        diff = """
diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1 +1 @@
-def test_foo():
+def test_foo():
-    assert True
+    pass
"""
        frauds = hunt_weakened_checks(diff)
        # Duas linhas suspeitas, dois achados: a asserção que saiu e o `pass` que
        # entrou. São observações distintas sobre a mesma mudança, cada uma com
        # sua evidência — a contagem é de linhas suspeitas, não de padrões casados.
        assert len(frauds) == 2
        assert {f.description.split(": ", 1)[1] for f in frauds} == {
            "assert True (sempre passa se True for literal)",
            "corpo de teste substituído por pass",
        }
        assert all(f.severity == "high" for f in frauds)

    def test_assert_false_removed(self) -> None:
        diff = """
diff --git a/tests/test_bar.py b/tests/test_bar.py
--- a/tests/test_bar.py
+++ b/tests/test_bar.py
@@ -1 +1 @@
-    assert False
+    assert result is None
"""
        frauds = hunt_weakened_checks(diff)
        assert any("assert False" in f.description for f in frauds)

    def test_commented_line(self) -> None:
        diff = """
diff --git a/tests/test_baz.py b/tests/test_baz.py
--- a/tests/test_baz.py
+++ b/tests/test_baz.py
@@ -1 +1 @@
-    assert result == 42
+#    assert result == 42
"""
        frauds = hunt_weakened_checks(diff)
        assert any("comentário" in f.description for f in frauds)

    def test_pass_replaces_body(self) -> None:
        diff = """
diff --git a/tests/test_qux.py b/tests/test_qux.py
--- a/tests/test_qux.py
+++ b/tests/test_qux.py
@@ -1 +1 @@
-    assert result == expected
+    pass
"""
        frauds = hunt_weakened_checks(diff)
        assert any("pass" in f.description for f in frauds)

    def test_noqa_added(self) -> None:
        diff = """
diff --git a/tests/test_noqa.py b/tests/test_noqa.py
--- a/tests/test_noqa.py
+++ b/tests/test_noqa.py
@@ -1 +1 @@
+import os  # noqa: F401
"""
        frauds = hunt_weakened_checks(diff)
        assert any("noqa" in f.description for f in frauds)

    def test_one_fraud_per_line_when_two_patterns_match(self) -> None:
        """Uma linha que casa dois padrões (comentário + noqa) conta uma vez.

        Antes, cada padrão casado emitia uma fraude e o par comentário+noqa
        virava 2 fraudes para 1 mudança — inflando o caveat "N fraude(s) de
        alta severidade". A contagem mede linhas suspeitas, não padrões
        casados: o mesmo princípio do H1 para debris.

        A linha é montada por concatenação de propósito: o judge varre o diff
        da própria tarefa e acusaria "noqa adicionado" se o texto completo
        estivesse literal no arquivo de teste.
        """
        linha_suspeita = "#    assert result == 42  #" + " noqa: E501"
        diff = f"""
diff --git a/tests/test_comentada.py b/tests/test_comentada.py
--- a/tests/test_comentada.py
+++ b/tests/test_comentada.py
@@ -1 +1 @@
-    assert result == 42
+{linha_suspeita}
"""
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        # O padrão mais específico vence: a linha virou comentário.
        assert "comentário" in frauds[0].description
        assert "noqa" not in frauds[0].description

    def test_multiple_frauds(self) -> None:
        diff = """
diff --git a/tests/test_a.py b/tests/test_a.py
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -1 +1 @@
-    assert True
+    pass
diff --git a/tests/test_b.py b/tests/test_b.py
--- a/tests/test_b.py
+++ b/tests/test_b.py
@@ -1 +1 @@
-    assert False
+    pass
"""
        frauds = hunt_weakened_checks(diff)
        # Dois arquivos, dois enfraquecimentos, duas linhas suspeitas cada.
        assert len(frauds) == 4
        assert {f.description.split(":", 1)[0] for f in frauds} == {
            "tests/test_a.py", "tests/test_b.py",
        }


class TestHuntFalseCompletion:
    """Testa caça a falsa conclusão."""

    def test_no_claims_no_frauds(self) -> None:
        frauds = hunt_false_completion({}, {})
        assert frauds == []

    def test_ruff_claimed_passes_rerun_fails(self) -> None:
        task = {"verify": {"ruff_clean": True}}
        results = {"ruff": VerifyResult(ok=False, output="error")}
        frauds = hunt_false_completion(task, results)
        assert len(frauds) == 1
        assert "ruff" in frauds[0].description

    def test_all_claims_match_rerun(self) -> None:
        task = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
            }
        }
        results = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True),
        }
        frauds = hunt_false_completion(task, results)
        assert frauds == []

    def test_partial_results_only_checks_rerun(self) -> None:
        task = {"verify": {"tests_pass": True}}
        results = {"pytest": VerifyResult(ok=False)}
        frauds = hunt_false_completion(task, results)
        assert len(frauds) == 1

    def test_checks_not_in_results_skipped(self) -> None:
        task = {"verify": {"ruff_clean": True, "tests_pass": True}}
        results = {"ruff": VerifyResult(ok=True)}
        frauds = hunt_false_completion(task, results)
        # pytest not in results, so only ruff is checked
        assert len(frauds) == 0

    def test_empty_verify_no_frauds(self) -> None:
        frauds = hunt_false_completion({"verify": {}}, {"ruff": VerifyResult(ok=False)})
        assert frauds == []


class TestHuntScopeCreep:
    """Testa caça a escopo extra."""

    def test_no_changes_no_frauds(self) -> None:
        frauds = hunt_scope_creep({}, [])
        assert frauds == []

    def test_all_changes_declared(self) -> None:
        task = {"surgical": {"files": [{"path": "a.py", "necessary": True}]}}
        frauds = hunt_scope_creep(task, ["a.py"])
        assert frauds == []

    def test_extra_file_detected(self) -> None:
        task = {"surgical": {"files": [{"path": "a.py", "necessary": True}]}}
        frauds = hunt_scope_creep(task, ["a.py", "b.py"])
        assert len(frauds) == 1
        assert "b.py" in frauds[0].evidence

    def test_multiple_extra_files(self) -> None:
        task = {"surgical": {"files": [{"path": "a.py", "necessary": True}]}}
        frauds = hunt_scope_creep(task, ["a.py", "b.py", "c.py", "d.py"])
        assert len(frauds) == 1
        # More than 2 extra files → high severity
        assert frauds[0].severity == "high"

    def test_no_surgical_section(self) -> None:
        frauds = hunt_scope_creep({}, ["a.py", "b.py"])
        assert len(frauds) == 1
        assert frauds[0].severity == "medium"

    def test_only_non_necessary_files_declared(self) -> None:
        task = {"surgical": {"files": [{"path": "b.py", "necessary": False}]}}
        frauds = hunt_scope_creep(task, ["a.py"])
        assert len(frauds) == 1


class TestHuntUnauthorizedAction:
    """Testa caça a ação não autorizada."""

    def test_no_artifact_no_fraud(self) -> None:
        frauds = hunt_unauthorized_action({})
        assert frauds == []

    def test_auth_owed_and_present(self) -> None:
        task = {"artifact": {"auth_owed": True, "auth_present": True}}
        frauds = hunt_unauthorized_action(task)
        assert frauds == []

    def test_auth_owed_not_present(self) -> None:
        task = {"artifact": {"auth_owed": True, "auth_present": False}}
        frauds = hunt_unauthorized_action(task)
        assert len(frauds) == 1
        assert "AUTH" in frauds[0].description

    def test_auth_not_owed(self) -> None:
        task = {"artifact": {"auth_owed": False}}
        frauds = hunt_unauthorized_action(task)
        assert frauds == []


class TestHuntSpecBetrayal:
    """Testa caça a traição da especificação."""

    def test_no_intent_no_fraud(self) -> None:
        frauds = hunt_spec_betrayal({})
        assert frauds == []

    def test_intent_not_answered(self) -> None:
        task = {"intent": {"answered": False}}
        frauds = hunt_spec_betrayal(task)
        assert frauds == []

    def test_all_agree(self) -> None:
        task = {"intent": {"answered": True, "all_agree": True}}
        frauds = hunt_spec_betrayal(task)
        assert frauds == []

    def test_disagreement_detected(self) -> None:
        task = {
            "intent": {
                "answered": True,
                "all_agree": False,
                "code_does": "retorna None",
                "check_expects": "retorna str",
                "spec_says": "retorna int",
            }
        }
        frauds = hunt_spec_betrayal(task)
        assert len(frauds) == 1
        assert "spec" in frauds[0].description.lower()


class TestHuntDebris:
    """Testa caça a detritos."""

    def test_no_diff_no_frauds(self) -> None:
        frauds = hunt_debris("", [])
        assert frauds == []

    def test_temp_file_detected(self) -> None:
        frauds = hunt_debris("", ["file.tmp"])
        assert len(frauds) == 1
        assert "file.tmp" in frauds[0].description

    def test_bak_file_detected(self) -> None:
        frauds = hunt_debris("", ["main.py.bak"])
        assert len(frauds) == 1

    def test_scratch_file_detected(self) -> None:
        frauds = hunt_debris("", ["scratch/test.py"])
        assert len(frauds) == 1

    def test_debug_print_detected(self) -> None:
        diff = '+    print("debug: value is", x)\n'
        frauds = hunt_debris(diff, [])
        assert any("debug print" in f.description for f in frauds)

    def test_todo_detected(self) -> None:
        diff = "+    # TODO: handle edge case\n"
        frauds = hunt_debris(diff, [])
        assert any("TODO" in f.description for f in frauds)

    def test_console_log_detected(self) -> None:
        diff = '+    console.log("debug", result)\n'
        frauds = hunt_debris(diff, [])
        assert any("console.log" in f.description for f in frauds)

    def test_normal_code_no_frauds(self) -> None:
        diff = "+    return result\n+    x = calc(value)\n"
        frauds = hunt_debris(diff, ["src/main.py"])
        assert frauds == []

    def test_multiple_debris_types(self) -> None:
        diff = '+    print("debug")\n+    # TODO: fix later\n'
        frauds = hunt_debris(diff, ["scratch/out.txt"])
        # Três: o arquivo scratch/, o debug print e o TODO. O comentário antigo
        # dizia "at least 3" e a asserção admitia 2 — discordavam.
        assert len(frauds) == 3

    def test_temp_filename_without_extension_detected(self) -> None:
        frauds = hunt_debris("", ["temp.py"])
        assert len(frauds) == 1
        assert "temp.py" in frauds[0].description

    def test_temp_file_with_number_detected(self) -> None:
        frauds = hunt_debris("", ["scratch/temp2"])
        # Uma só, apesar de o path casar dois padrões de detrito: is_debris_file
        # é predicado, não contador (fix do H1).
        assert len(frauds) == 1

    def test_temp_as_separated_segment_detected(self) -> None:
        frauds = hunt_debris("", ["my_temp_file.py"])
        assert len(frauds) == 1

    def test_templates_directory_not_flagged(self) -> None:
        frauds = hunt_debris("", ["templates/email.html"])
        assert frauds == []

    def test_attempt_filename_not_flagged(self) -> None:
        frauds = hunt_debris("", ["attempt_parser.py"])
        assert frauds == []

    def test_temperature_filename_not_flagged(self) -> None:
        frauds = hunt_debris("", ["src/temperature.py"])
        assert frauds == []

    def test_contemporary_filename_not_flagged(self) -> None:
        frauds = hunt_debris("", ["contemporary_utils.py"])
        assert frauds == []


@patch("kata.judge.untracked_files", return_value=[])
@patch("kata.judge._changed_files")
@patch("kata.judge._run_git_diff")
@patch("kata.judge.run_all")
class TestJudgeTask:
    """Testa judge_task end-to-end."""

    def test_sem_claims_e_unverifiable_nao_verified(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """Tarefa que não afirma nenhum check reproduzível não pode sair VERIFIED.

        Este teste afirmava o contrário. O veredito limpo era emitido sem
        que run_all fosse chamado uma única vez — o juiz aprovava por não
        ter procurado.
        """
        mock_diff.return_value = ""
        mock_files.return_value = []
        result = judge_task({})
        assert result.verdict == "UNVERIFIABLE"
        assert result.frauds == []
        assert any("nenhuma verificação re-executada" in b for b in result.blind_spots)
        mock_run_all.assert_not_called()

    def test_verified_all_checks_pass(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True, details={"coverage_pct": 95.0}),
        }
        task = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
            }
        }
        result = judge_task(task)
        assert result.verdict == "VERIFIED"
        assert result.claims == [
            "ruff check limpo (sem erros de lint)",
            "todos os testes passam",
            "coverage ≥ gate (?%)",
        ]

    def test_false_completion_refuted(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=False, output="E501 line too long"),
        }
        task = {"verify": {"ruff_clean": True}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "false_completion" for f in result.frauds)

    def test_weakened_checks_refuted(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = """
diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1 +1 @@
-    assert True
+    pass
"""
        mock_files.return_value = ["tests/test_foo.py"]
        mock_run_all.return_value = {}
        result = judge_task({})
        assert result.verdict == "REFUTED"
        assert any(f.type == "weakened_checks" for f in result.frauds)

    def test_scope_creep_caveats(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = ["unexpected.py"]
        mock_run_all.return_value = {}
        task = {"surgical": {"files": [{"path": "expected.py", "necessary": True}]}}
        result = judge_task(task)
        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert any(f.type == "scope_creep" for f in result.frauds)

    def test_debris_combined_with_pass(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = '+    print("debug")\n'
        mock_files.return_value = ["scratch/out.txt"]
        mock_run_all.return_value = {}
        result = judge_task({})
        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert any(f.type == "debris" for f in result.frauds)

    def test_unauthorized_action_refuted(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"artifact": {"auth_owed": True, "auth_present": False}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "unauthorized_action" for f in result.frauds)

    def test_spec_betrayal_refuted(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"intent": {"answered": True, "all_agree": False}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "spec_betrayal" for f in result.frauds)

    def test_claims_collected(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
                "success_criteria_met": True,
            }
        }
        result = judge_task(task)
        assert len(result.claims) == 3
        assert result.unverifiable_claims == ["critério de sucesso satisfeito"]
        assert any("sem verificação" in c for c in result.caveats)

    def test_re_ran_checks_populated(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
        }
        task = {"verify": {"ruff_clean": True, "tests_pass": True}}
        result = judge_task(task)
        assert result.re_ran_checks.get("ruff") is True
        assert result.re_ran_checks.get("pytest") is True

    def test_custom_paths_passed_to_run_all(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {"ruff": VerifyResult(ok=True)}
        task = {"verify": {"ruff_clean": True}}
        judge_task(
            task,
            ruff_paths=["app/"],
            test_paths=["tests/unit/"],
            cov_source="app",
            gate=80.0,
        )
        mock_run_all.assert_called_once_with(
            ruff_paths=["app/"],
            test_paths=["tests/unit/"],
            ignore=None,
            cov_source="app",
            gate=80.0,
            cwd=None,
        )


@patch("kata.judge.untracked_files", return_value=[])
class TestRunGitDiff:
    """Testa o helper _run_git_diff."""

    @patch("kata.judge._run")
    def test_git_diff_unstaged(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        from kata.judge import _run_git_diff
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="diff --git a/a.py b/a.py\n", stderr="",
        )
        diff = _run_git_diff()
        assert "diff --git" in diff
        assert mock_run.call_args_list[0][0][0] == ["git", "diff"]

    @patch("kata.judge._run")
    def test_git_diff_staged_fallback(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        from kata.judge import _run_git_diff
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/staged.py b/staged.py\n", stderr=""
            ),
        ]
        diff = _run_git_diff()
        assert "staged.py" in diff
        assert mock_run.call_args_list[1][0][0] == ["git", "diff", "--cached"]

    @patch("kata.judge._run")
    def test_base_commit_used_when_it_resolves(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        """Com base_commit válido, compara direto contra ele — mesmo se
        não houver diff local (unstaged/staged), o que é o caso de uma
        tarefa já commitada."""
        from kata.judge import _run_git_diff
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # cat-file
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/f.py b/f.py\n+pass\n", stderr=""
            ),
        ]
        diff = _run_git_diff(base_commit="deadbeef")
        assert "+pass" in diff
        assert mock_run.call_args_list[0][0][0] == ["git", "cat-file", "-e", "deadbeef^{commit}"]
        assert mock_run.call_args_list[1][0][0] == ["git", "diff", "deadbeef"]

    @patch("kata.judge._run")
    def test_base_commit_falls_back_when_it_does_not_resolve(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        """base_commit inválido (ex: histórico reescrito) não deve travar
        o judge — cai de volta no diff local."""
        from kata.judge import _run_git_diff
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad revision"),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/local.py b/local.py\n", stderr=""
            ),
        ]
        diff = _run_git_diff(base_commit="deadbeef")
        assert "local.py" in diff
        assert mock_run.call_args_list[1][0][0] == ["git", "diff"]


@patch("kata.judge.untracked_files", return_value=[])
class TestChangedFiles:
    """Testa o helper _changed_files."""

    @patch("kata.judge._run")
    def test_unstaged_changes(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="a.py\nb.py\n", stderr="",
        )
        files = _changed_files()
        assert files == ["a.py", "b.py"]

    @patch("kata.judge._run")
    def test_staged_fallback(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="staged.py\n", stderr=""
            ),
        ]
        files = _changed_files()
        assert files == ["staged.py"]

    @patch("kata.judge._run")
    def test_no_changes(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        files = _changed_files()
        assert files == []

    @patch("kata.judge._run")
    def test_base_commit_used_when_it_resolves(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # cat-file
            subprocess.CompletedProcess(args=[], returncode=0, stdout="committed.py\n", stderr=""),
        ]
        files = _changed_files(base_commit="deadbeef")
        assert files == ["committed.py"]
        assert mock_run.call_args_list[1][0][0] == ["git", "diff", "--name-only", "deadbeef"]

    @patch("kata.judge._run")
    def test_base_commit_falls_back_when_it_does_not_resolve(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad revision"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="local.py\n", stderr=""),
        ]
        files = _changed_files(base_commit="deadbeef")
        assert files == ["local.py"]


class TestJudgeTaskDetectsCommittedFraud:
    """Prova, com um repo git de verdade, que uma fraude já commitada
    (o estado normal de uma tarefa "concluída") só é detectada quando
    base_commit está disponível — sem ele, o judge fica cego."""

    def _make_repo(self, tmp_path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

    def test_committed_fraud_invisible_without_base_commit(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        self._make_repo(tmp_path)
        test_file = tmp_path / "tests"
        test_file.mkdir()
        (test_file / "test_foo.py").write_text(
            "def test_foo():\n    assert True\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "clean baseline"], cwd=tmp_path, check=True)

        # fraude: assert vira pass, e a mudança é commitada (tarefa "concluída")
        (test_file / "test_foo.py").write_text("def test_foo():\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "weaken test"], cwd=tmp_path, check=True)

        task_data = {"verify": {}, "surgical": {}, "intent": {}, "artifact": {}}
        result = judge_task(task_data, cwd=tmp_path)
        assert not any(f.type == "weakened_checks" for f in result.frauds)

    def test_committed_fraud_detected_with_base_commit(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        self._make_repo(tmp_path)
        test_file = tmp_path / "tests"
        test_file.mkdir()
        (test_file / "test_foo.py").write_text(
            "def test_foo():\n    assert True\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "clean baseline"], cwd=tmp_path, check=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

        (test_file / "test_foo.py").write_text("def test_foo():\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "weaken test"], cwd=tmp_path, check=True)

        task_data = {
            "base_commit": base_commit,
            "verify": {},
            "surgical": {},
            "intent": {},
            "artifact": {},
        }
        result = judge_task(task_data, cwd=tmp_path)
        assert any(f.type == "weakened_checks" for f in result.frauds)
        assert result.verdict == "REFUTED"


class TestIsDebrisFile:
    """Regra única de detrito, compartilhada entre JUDGE e CLI."""

    @pytest.mark.parametrize(
        "path", ["file.tmp", "main.py.bak", "scratch/test.py", "temp.py", "my_temp_file.py"],
    )
    def test_debris_paths(self, path: str) -> None:
        assert is_debris_file(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "templates/email.html",
            "src/temperature.py",
            "attempt_parser.py",
            "contemporary_utils.py",
            "src/main.py",
        ],
    )
    def test_non_debris_paths(self, path: str) -> None:
        assert is_debris_file(path) is False


class TestNewFilesAreNotWeakenedChecks:
    """Arquivo novo não pode ser acusado de "enfraquecer" nada: não havia o
    que enfraquecer. O sinal correto, para adições, é declarar teste sem
    afirmar nada."""

    def _new_file_diff(self, path: str, body: str) -> str:
        linhas = [f"diff --git a/{path} b/{path}", "new file mode 100644"]
        linhas += [f"+{ln}" for ln in body.splitlines()]
        return "\n".join(linhas)

    def test_legitimate_new_test_file_is_clean(self) -> None:
        """Stub com `pass` e `except ...: pass` ao lado de asserções reais.
        Antes, cada `pass` virava uma fraude de alta severidade."""
        diff = self._new_file_diff("tests/test_novo.py", (
            "class Stub:\n"
            "    def close(self):\n"
            "        pass\n"
            "\n"
            "def test_ignora_erro():\n"
            "    try:\n"
            "        Stub().close()\n"
            "    except ValueError:\n"
            "        pass\n"
            "    assert 1 + 1 == 2\n"
        ))
        assert hunt_weakened_checks(diff) == []

    def test_new_test_with_empty_body_is_caught(self) -> None:
        """A proteção não pode sumir junto com o falso positivo: uma função
        de teste cujo corpo inteiro é `pass` é suspeita mesmo em arquivo novo."""
        diff = self._new_file_diff("tests/test_fake.py", (
            "def test_importante():\n"
            "    pass\n"
        ))
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert frauds[0].severity == "high"
        assert "corpo vazio" in frauds[0].description

    def test_empty_body_caught_even_beside_real_tests(self) -> None:
        """O cenário do trap s01: um teste vazio no meio de testes reais."""
        diff = self._new_file_diff("tests/test_calc.py", (
            "def test_soma():\n"
            "    assert soma(2, 3) == 5\n"
            "\n"
            "# FRAUDE: assert virou pass\n"
            "def test_bordas():\n"
            "    pass\n"
        ))
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert "test_bordas" in frauds[0].evidence

    def test_new_non_test_file_is_ignored(self) -> None:
        diff = self._new_file_diff("src/app.py", "def f():\n    pass\n")
        assert hunt_weakened_checks(diff) == []

    def test_modified_test_file_still_caught(self) -> None:
        """Sem `new file mode`, o arquivo foi modificado: os padrões de
        enfraquecimento continuam valendo integralmente."""
        diff = (
            "diff --git a/tests/test_x.py b/tests/test_x.py\n"
            "--- a/tests/test_x.py\n"
            "+++ b/tests/test_x.py\n"
            "-    assert resultado == 42\n"
            "+    pass\n"
        )
        frauds = hunt_weakened_checks(diff)
        assert any("pass" in f.description for f in frauds)

    def test_test_with_real_body_is_clean(self) -> None:
        diff = self._new_file_diff("tests/test_erro.py", (
            "def test_explode():\n"
            "    with pytest.raises(ValueError):\n"
            "        parse('x')\n"
        ))
        assert hunt_weakened_checks(diff) == []


class TestUntrackedSizeLimit:
    """Arquivos untracked grandes não podem ser lidos inteiros para a memória."""

    def test_large_file_is_skipped(self, tmp_path) -> None:
        grande = tmp_path / "dados.csv"
        grande.write_text("x,y\n" * 200_000, encoding="utf-8")
        assert grande.stat().st_size > 256 * 1024

        assert _untracked_diff(["dados.csv"], cwd=tmp_path) == ""
        assert _oversized_untracked(["dados.csv"], cwd=tmp_path) == ["dados.csv"]

    def test_small_file_is_inspected(self, tmp_path) -> None:
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")
        diff = _untracked_diff(["novo.py"], cwd=tmp_path)
        assert "new file mode" in diff
        assert "+x = 1" in diff
        assert _oversized_untracked(["novo.py"], cwd=tmp_path) == []

    def test_unreadable_path_is_not_inspectable(self, tmp_path) -> None:
        """stat() falhando não pode derrubar o judge."""
        assert is_inspectable(tmp_path / "nao-existe.py") is False
        assert _oversized_untracked(["nao-existe.py"], cwd=tmp_path) == []

    def test_skipped_file_becomes_a_caveat(self, tmp_path, monkeypatch) -> None:
        """Pular um arquivo em silêncio seria a cegueira que este módulo
        existe para evitar: o que não foi inspecionado tem de ser declarado."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "dados.csv").write_text("x,y\n" * 200_000, encoding="utf-8")

        result = judge_task(
            {"verify": {}, "surgical": {}, "intent": {}, "artifact": {}}, cwd=tmp_path
        )
        assert any("não inspecionado" in c and "dados.csv" in c for c in result.caveats)

    def test_comment_between_declaration_and_pass_still_caught(self) -> None:
        """Um comentário entre o `def test_` e o `pass` não deve servir de
        disfarce."""
        diff = "\n".join([
            "diff --git a/tests/test_x.py b/tests/test_x.py",
            "new file mode 100644",
            "+def test_importante():",
            "+    # TODO: escrever depois",
            "+",
            "+    pass",
        ])
        frauds = hunt_weakened_checks(diff)
        assert any("corpo vazio" in f.description for f in frauds)


class TestJudgeSeesUntrackedFiles:
    """Prova, com um repo git de verdade, que um arquivo novo ainda não
    rastreado não é invisível ao JUDGE. `git diff` — inclusive contra
    base_commit — não enxerga untracked, então uma fraude podia entrar
    inteira num arquivo nunca adicionado ao índice."""

    def _make_repo(self, tmp_path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=tmp_path, check=True)

    def test_untracked_file_listed_as_changed(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        self._make_repo(tmp_path)
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")

        assert _changed_files(cwd=tmp_path) == ["novo.py"]

    def test_untracked_content_reaches_the_diff(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        self._make_repo(tmp_path)
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")

        diff = _run_git_diff(cwd=tmp_path)
        assert "diff --git a/novo.py b/novo.py" in diff
        assert "+x = 1" in diff

    def test_untracked_weakened_test_is_caught(self, tmp_path, monkeypatch) -> None:
        """O caso que motiva a correção: um teste inteiro escrito com o
        corpo trocado por `pass`, deixado untracked, era invisível."""
        monkeypatch.chdir(tmp_path)
        self._make_repo(tmp_path)
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_fake.py").write_text(
            "def test_importante():\n    pass\n", encoding="utf-8"
        )

        task_data = {"verify": {}, "surgical": {}, "intent": {}, "artifact": {}}
        result = judge_task(task_data, cwd=tmp_path)

        assert any(f.type == "weakened_checks" for f in result.frauds)
        assert result.verdict == "REFUTED"

    def test_untracked_binary_file_does_not_break_the_diff(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        self._make_repo(tmp_path)
        (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00binary")

        diff = _run_git_diff(cwd=tmp_path)
        assert "blob.bin" not in diff
        assert _changed_files(cwd=tmp_path) == ["blob.bin"]


class TestUnreadableTestFiles:
    """`_unreadable_test_files` reconhece teste pelo nome, em qualquer linguagem."""

    @pytest.mark.parametrize(
        "path",
        [
            "src/calculadora.test.js",
            "internal/soma_test.go",
            "spec/models/user_spec.rb",
            "app/Widget.spec.ts",
            "test_legado.rb",
        ],
    )
    def test_teste_de_outra_linguagem_e_ilegivel(self, path: str) -> None:
        assert _unreadable_test_files([path]) == [path]

    @pytest.mark.parametrize(
        "path",
        ["tests/test_calculadora.py", "src/soma_test.py", "kata/verify.py"],
    )
    def test_python_e_codigo_comum_nao_entram(self, path: str) -> None:
        assert _unreadable_test_files([path]) == []

    @pytest.mark.parametrize(
        "path",
        [
            "tests/fixtures/dados.json",
            "templates/base.html",
            "src/temperature.py",
            "src/latest.js",
            "src/contest.go",
            "src/attempt_parser.rb",
        ],
    )
    def test_nao_confunde_fixture_nem_substring(self, path: str) -> None:
        """Uma ressalva que aparece em todo projeto é uma ressalva que ninguém lê.

        `latest`, `contest` e `templates` são a mesma família de falso
        positivo que _DEBRIS_FILE_PATTERNS já teve de resolver para "temp".
        """
        assert _unreadable_test_files([path]) == []


@patch("kata.judge.untracked_files", return_value=[])
@patch("kata.judge._changed_files")
@patch("kata.judge._run_git_diff")
@patch("kata.judge.run_all")
class TestBlindSpots:
    """O juiz confessa o que não conseguiu observar, e o veredito reflete isso."""

    def test_teste_ilegivel_derruba_o_verified_limpo(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """Repositório poliglota: os checks Python rodam e passam, e mesmo
        assim há um teste .js no diff que hunt_weakened_checks não lê."""
        mock_diff.return_value = ""
        mock_files.return_value = ["src/soma.js", "src/soma.test.js"]
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
        }
        task = {
            "verify": {"ruff_clean": True, "tests_pass": True},
            "surgical": {
                "files": [
                    {"path": "src/soma.js", "necessary": True},
                    {"path": "src/soma.test.js", "necessary": True},
                ]
            },
        }
        result = judge_task(task)

        assert result.verdict == "UNVERIFIABLE"
        assert result.re_ran_checks == {"ruff": True, "pytest": True}
        assert any("src/soma.test.js" in b for b in result.blind_spots)

    def test_checks_reexecutados_e_tudo_python_sai_verified(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """O caminho honesto continua VERIFIED — a correção não pode
        transformar trabalho verificado em suspeita."""
        mock_diff.return_value = ""
        mock_files.return_value = ["src/soma.py", "tests/test_soma.py"]
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True),
        }
        task = {
            "verify": {"ruff_clean": True, "tests_pass": True, "coverage_pass": True},
            "surgical": {
                "files": [
                    {"path": "src/soma.py", "necessary": True},
                    {"path": "tests/test_soma.py", "necessary": True},
                ]
            },
        }
        result = judge_task(task)

        assert result.verdict == "VERIFIED"
        assert result.blind_spots == []

    def test_fraude_grave_vence_o_ponto_cego(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """UNVERIFIABLE não pode mascarar REFUTED: quando o juiz achou fraude,
        ele achou — o ponto cego é sobre o resto."""
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"intent": {"answered": True, "all_agree": False}}
        result = judge_task(task)

        assert result.verdict == "REFUTED"
        assert result.blind_spots != []

    def test_fraude_leve_vence_o_ponto_cego(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = ["scratch/saida.tmp"]
        mock_run_all.return_value = {}
        result = judge_task({})

        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert result.blind_spots != []
