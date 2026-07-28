"""Testes para kata.judge — verificação adversarial (fable-judge)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from kata.judge import (
    JudgeFraud,
    JudgeResult,
    _changed_files,
    collect_claims,
    hunt_debris,
    hunt_false_completion,
    hunt_scope_creep,
    hunt_spec_betrayal,
    hunt_unauthorized_action,
    hunt_weakened_checks,
    judge_task,
)
from kata.verify import VerifyResult


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
        assert len(claims) == 6
        assert any("ruff" in c for c in claims)
        assert any("testes" in c for c in claims)
        assert any("coverage" in c for c in claims)
        assert any("critério" in c for c in claims)
        assert any("intenção" in c for c in claims)
        assert any("arquivo" in c for c in claims)

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
        assert len(frauds) >= 1
        assert any("assert True" in f.description for f in frauds)
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
        assert len(frauds) >= 2


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
        assert len(frauds) >= 1

    def test_scratch_file_detected(self) -> None:
        frauds = hunt_debris("", ["scratch/test.py"])
        assert len(frauds) >= 1

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
        # At least 3 debris items (file + print + TODO)
        assert len(frauds) >= 2


@patch("kata.judge._changed_files")
@patch("kata.judge._run_git_diff")
@patch("kata.judge.run_all")
class TestJudgeTask:
    """Testa judge_task end-to-end."""

    def test_verified_no_claims(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        result = judge_task({})
        assert result.verdict == "VERIFIED"
        assert result.frauds == []

    def test_verified_all_checks_pass(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
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
        assert len(result.claims) >= 2

    def test_false_completion_refuted(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
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
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
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
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = ["unexpected.py"]
        mock_run_all.return_value = {}
        task = {"surgical": {"files": [{"path": "expected.py", "necessary": True}]}}
        result = judge_task(task)
        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert any(f.type == "scope_creep" for f in result.frauds)

    def test_debris_combined_with_pass(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
    ) -> None:
        mock_diff.return_value = '+    print("debug")\n'
        mock_files.return_value = ["scratch/out.txt"]
        mock_run_all.return_value = {}
        result = judge_task({})
        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert any(f.type == "debris" for f in result.frauds)

    def test_unauthorized_action_refuted(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"artifact": {"auth_owed": True, "auth_present": False}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "unauthorized_action" for f in result.frauds)

    def test_spec_betrayal_refuted(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"intent": {"answered": True, "all_agree": False}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "spec_betrayal" for f in result.frauds)

    def test_claims_collected(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
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
        assert len(result.claims) == 4

    def test_re_ran_checks_populated(
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
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
        self, mock_run_all: MagicMock, mock_diff: MagicMock, mock_files: MagicMock
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


class TestRunGitDiff:
    """Testa o helper _run_git_diff."""

    @patch("kata.judge._run")
    def test_git_diff_unstaged(self, mock_run: MagicMock) -> None:
        from kata.judge import _run_git_diff
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="diff --git a/a.py b/a.py\n", stderr="",
        )
        diff = _run_git_diff()
        assert "diff --git" in diff
        assert mock_run.call_args[0][0] == ["git", "diff"]

    @patch("kata.judge._run")
    def test_git_diff_staged_fallback(self, mock_run: MagicMock) -> None:
        from kata.judge import _run_git_diff
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/staged.py b/staged.py\n", stderr=""
            ),
        ]
        diff = _run_git_diff()
        assert "staged.py" in diff
        assert mock_run.call_args[0][0] == ["git", "diff", "--cached"]


class TestChangedFiles:
    """Testa o helper _changed_files."""

    @patch("kata.judge._run")
    def test_unstaged_changes(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="a.py\nb.py\n", stderr="",
        )
        files = _changed_files()
        assert files == ["a.py", "b.py"]

    @patch("kata.judge._run")
    def test_staged_fallback(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="staged.py\n", stderr=""
            ),
        ]
        files = _changed_files()
        assert files == ["staged.py"]

    @patch("kata.judge._run")
    def test_no_changes(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        files = _changed_files()
        assert files == []
