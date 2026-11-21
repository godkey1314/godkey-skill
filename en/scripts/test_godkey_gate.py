#!/usr/bin/env python3
"""Real-Git end-to-end integration and regression tests for the English GodKey Gate CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE_SCRIPT = Path(__file__).resolve().parent / "godkey_gate.py"


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE_SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "core.quotepath=false", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def init_git_repo(repo: Path) -> None:
    run_git(repo, "init")
    run_git(repo, "config", "user.name", "Test User")
    run_git(repo, "config", "user.email", "test@example.com")


def fill_feature_artifacts(pkg: Path, title: str = "sample-feature") -> None:
    (pkg / "01-plan.md").write_text(
        f"# Plan: {title}\n\n## Objectives\n- Deliver {title} cleanly with strict layering boundaries\n- Update target service module and add integration tests\n- Acceptance criteria: real-chain tests green\n",
        encoding="utf-8",
    )
    prog_path = pkg / "02-progress.md"
    base_line = ""
    if prog_path.is_file():
        for ln in prog_path.read_text(encoding="utf-8").splitlines():
            if "godkey-base-commit:" in ln:
                base_line = ln
                break
    prog_path.write_text(
        f"# Progress: {title}\n\n{base_line}\n\n"
        f"## Pre-Change Snapshot\n- Previous implementation lacked {title} support\n\n"
        f"## Iteration Log\n- Implemented {title} core behavior and verified callers\n- Cleaned up unused helpers and verified layering\n\n"
        f"## Static Doc Sync Record\n- Synchronized feature blueprints and schema snapshots\n",
        encoding="utf-8",
    )
    (pkg / "03-test.md").write_text(
        f"# Testing: {title}\n\n## Report\n- Executed real-chain unit and integration tests covering happy, null, and error paths\n- Result: all test cases passed without skips\n",
        encoding="utf-8",
    )
    (pkg / "04-review.md").write_text(
        f"# Review: {title}\n\n## Findings\n- Verified all five dimensions across modified files with zero layering breaches\n- Pattern spread checked sibling modules with zero value-semantics bugs found\n",
        encoding="utf-8",
    )


class TestEnglishGodKeyGate(unittest.TestCase):
    def test_audit_discovery_and_fresh_template_accuracy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            res = run_cli("audit", "--project-root", str(root), cwd=root)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("Detected mode: uninitialized", res.stdout)

            # Minimal empty repo README + .gitignore with zero source stays uninitialized
            (root / "README.md").write_text("# My Repo\n", encoding="utf-8")
            (root / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
            res_empty = run_cli("audit", "--project-root", str(root), cwd=root)
            self.assertIn("Detected mode: uninitialized", res_empty.stdout)

            # Nested source directory detected as external
            (root / "services" / "order").mkdir(parents=True)
            (root / "services" / "order" / "main.py").write_text("print('order')\n", encoding="utf-8")
            res_ext = run_cli("audit", "--project-root", str(root), cwd=root)
            self.assertIn("Detected mode: external", res_ext.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            full_repo = Path(tmp) / "full"
            full_repo.mkdir()
            run_cli("init", "--profile", "full", "--project-root", str(full_repo), cwd=full_repo)
            res_full = run_cli("audit", "--project-root", str(full_repo), cwd=full_repo)
            self.assertEqual(res_full.returncode, 0)
            self.assertNotIn("[READY]", res_full.stdout)
            self.assertIn("DEFAULT_STANDARDS", res_full.stdout)

            lite_repo = Path(tmp) / "lite"
            lite_repo.mkdir()
            run_cli("init", "--profile", "lite", "--project-root", str(lite_repo), cwd=lite_repo)
            res_lite = run_cli("audit", "--project-root", str(lite_repo), cwd=lite_repo)
            self.assertEqual(res_lite.returncode, 0)
            self.assertNotIn("[READY]", res_lite.stdout)
            self.assertIn("02-architecture-and-design.md", res_lite.stdout)
            self.assertIn("TEMPLATE_ONLY", res_lite.stdout)

            multi = Path(tmp) / "multi"
            multi.mkdir()
            run_cli("init", "--profile", "lite", "--doc-root", "backend_doc", "--project-root", str(multi), cwd=multi)
            run_cli("init", "--profile", "lite", "--doc-root", "frontend_doc", "--project-root", str(multi), cwd=multi)
            res_multi = run_cli("audit", "--project-root", str(multi), cwd=multi)
            self.assertEqual(res_multi.returncode, 0)
            self.assertIn("frontend_doc", res_multi.stdout)

            res_oob = run_cli("audit", "--doc-root", "../outside", "--project-root", str(multi), cwd=multi)
            self.assertNotEqual(res_oob.returncode, 0)
            self.assertNotIn("Traceback", res_oob.stderr)

            (multi / "backend_doc" / ".godkey.json").write_text("{bad json", encoding="utf-8")
            res_bad = run_cli("audit", "--doc-root", "backend_doc", "--project-root", str(multi), cwd=multi)
            self.assertNotEqual(res_bad.returncode, 0)
            self.assertNotIn("Traceback", res_bad.stderr)

    def test_matches_hints_new_module_and_rename_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "existing.py").write_text("x = 1\n", encoding="utf-8")
            (repo / "src" / "models").mkdir()
            (repo / "src" / "models" / "user.py").write_text("class User: pass\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            # Adding src/helper.py in existing dir must not falsely trigger archDocs
            run_cli("new", "helper-util", "--state", "active", "--project-root", str(repo), cwd=repo)
            (repo / "src" / "helper.py").write_text("def fmt(v): return str(v)\n", encoding="utf-8")
            (repo / "doc" / "04-feature-design" / "helper.md").write_text("# Helper\n\nString formatting utility.\n", encoding="utf-8")
            res_ok = run_cli("check-sync", "--package", "helper-util", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_ok.returncode, 0, res_ok.stdout + res_ok.stderr)

            # New module directory src/billing/invoice.py triggers archDocs
            (repo / "src" / "billing").mkdir()
            (repo / "src" / "billing" / "invoice.py").write_text("def bill(): return 1\n", encoding="utf-8")
            res_arch = run_cli("check-sync", "--package", "helper-util", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_arch.returncode, 0)
            self.assertIn("archDocs", res_arch.stderr)

            # Common DB/ops/arch filenames must trigger
            (repo / "src" / "models.py").write_text("class Order: pass\n", encoding="utf-8")
            (repo / "src" / "user_schema.py").write_text("class S: pass\n", encoding="utf-8")
            (repo / "compose.yml").write_text("services: {}\n", encoding="utf-8")
            (repo / ".env.sample").write_text("FOO=bar\n", encoding="utf-8")
            (repo / "uv.lock").write_text("version = 1\n", encoding="utf-8")
            res_hints = run_cli("check-sync", "--package", "helper-util", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_hints.returncode, 0)
            self.assertIn("dbDocs", res_hints.stderr)
            self.assertIn("opsDocs", res_hints.stderr)
            self.assertIn("archDocs", res_hints.stderr)

            # git mv preserves old path for dbDocs trigger
            run_git(repo, "checkout", "--", ".")
            for extra in ("src/helper.py", "src/models.py", "src/user_schema.py", "compose.yml", ".env.sample", "uv.lock", "doc/04-feature-design/helper.md"):
                p = repo / extra
                if p.exists():
                    p.unlink()
            shutil.rmtree(repo / "src" / "billing")
            (repo / "src" / "plain").mkdir()
            run_git(repo, "mv", "src/models/user.py", "src/plain/user.py")
            (repo / "doc" / "04-feature-design" / "user.md").write_text("# User\n\nMoved model module.\n", encoding="utf-8")
            (repo / "doc" / "03-architecture" / "architecture.md").write_text("# Arch\n\nAdded plain package.\n", encoding="utf-8")
            run_git(repo, "add", "doc/04-feature-design/user.md", "doc/03-architecture/architecture.md")
            res_mv = run_cli("check-sync", "--staged", "--mode", "strict", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_mv.returncode, 0)
            self.assertIn("dbDocs", res_mv.stderr)

    def test_anti_bypass_deleted_static_blank_template_skip_git_forged_review_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("def a(): return 1\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            (repo / "doc" / "04-feature-design" / "orders.md").write_text("# Orders\n\nOrder workflow blueprint.\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            # Path traversal via --date blocked
            res_trav = run_cli("new", "evil", "--date", "../../../../pwned", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_trav.returncode, 0)
            self.assertFalse((repo.parent / "pwned").exists())

            run_cli("new", "anti-bypass", "--state", "active", "--project-root", str(repo), cwd=repo)
            pkg = [p for p in (repo / "doc" / "09-changes" / "02-active").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(pkg, "anti-bypass")

            # Deleting a static doc must not pass
            (repo / "src" / "app.py").write_text("def a(): return 2\n", encoding="utf-8")
            (repo / "doc" / "04-feature-design" / "orders.md").unlink()
            res_del = run_cli("check-sync", "--package", "anti-bypass", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_del.returncode, 0)
            run_git(repo, "checkout", "--", "doc/04-feature-design/orders.md")

            # Blank-line edits & copying untouched template must not pass
            tpl_file = repo / "doc" / "04-feature-design" / "_module-design-template.md"
            with (repo / "doc" / "04-feature-design" / "orders.md").open("a", encoding="utf-8") as fh:
                fh.write("\n   \n")
            shutil.copy2(tpl_file, repo / "doc" / "04-feature-design" / "empty-copy.md")
            res_blank = run_cli("check-sync", "--package", "anti-bypass", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_blank.returncode, 0)
            (repo / "doc" / "04-feature-design" / "empty-copy.md").unlink()

            # --skip-git inside Git repo rejected
            res_skip = run_cli("archive", "anti-bypass", "--skip-git", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_skip.returncode, 0)

            # Forged review marker in feature package rejected
            with (pkg / "04-review.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- godkey-package-type: review -->\n")
            res_forge = run_cli("archive", "anti-bypass", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_forge.returncode, 0)
            self.assertIn("forged", res_forge.stderr)

        # True non-Git dir with ops/*.sql must not deadlock
        with tempfile.TemporaryDirectory() as tmp:
            nongit = Path(tmp)
            run_cli("init", "--profile", "full", "--project-root", str(nongit), cwd=nongit)
            run_cli("new", "non-git-feat", "--state", "active", "--project-root", str(nongit), cwd=nongit)
            pkg = [p for p in (nongit / "doc" / "09-changes" / "02-active").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(pkg, "non-git-feat")
            (pkg / "ops" / "01_alter.sql").write_text("ALTER TABLE t ADD COLUMN c INT;\n", encoding="utf-8")
            res_ng = run_cli("archive", "non-git-feat", "--project-root", str(nongit), cwd=nongit)
            self.assertEqual(res_ng.returncode, 0, res_ng.stdout + res_ng.stderr)

    def test_waiver_poison_pill_case_and_cheese_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            # Historical hotfix waiver must not poison future commits
            with (repo / "doc" / "09-changes" / "hotfix-log.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- doc-sync-waiver: featureDocs | Single-line null check preserving all public API behavior -->\n")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "fix: old hotfix")

            (repo / "src" / "big_feature.py").write_text("def f(): return 42\n", encoding="utf-8")
            res_no_poison = run_cli("check-sync", "--mode", "strict", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_no_poison.returncode, 0)

            # Replacing [TODO with [DONE fails artifact check
            run_cli("new", "cheese-test", "--state", "active", "--project-root", str(repo), cwd=repo)
            pkg = [p for p in (repo / "doc" / "09-changes" / "02-active").iterdir() if p.is_dir()][0]
            for fname in ("01-plan.md", "02-progress.md", "03-test.md", "04-review.md"):
                p = pkg / fname
                p.write_text(p.read_text(encoding="utf-8").replace("[TODO", "[DONE", 3), encoding="utf-8")
            self.assertNotEqual(run_cli("archive", "cheese-test", "--project-root", str(repo), cwd=repo).returncode, 0)

            # Lazy waiver rejected; lowercase featuredocs + concrete rationale passes
            fill_feature_artifacts(pkg, "cheese-test")
            with (pkg / "02-progress.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- doc-sync-waiver: featureDocs | This change does not need doc updates -->\n")
            res_lazy = run_cli("check-sync", "--package", "cheese-test", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_lazy.returncode, 0)
            self.assertIn("Invalid waiver", res_lazy.stderr)

            prog = (pkg / "02-progress.md").read_text(encoding="utf-8")
            (pkg / "02-progress.md").write_text(
                prog.replace(
                    "<!-- doc-sync-waiver: featureDocs | This change does not need doc updates -->",
                    "<!-- doc-sync-waiver: featuredocs | Internal helper extraction with zero public API or domain changes -->",
                ),
                encoding="utf-8",
            )
            res_ok = run_cli("check-sync", "--package", "cheese-test", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_ok.returncode, 0, res_ok.stdout + res_ok.stderr)
            self.assertIn("WAIVED [featureDocs", res_ok.stdout)

    def test_unborn_head_head_fallback_and_same_day_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            run_cli("init", "--profile", "lite", "--project-root", str(repo), cwd=repo)
            run_cli("new", "initial-feat", "--state", "active", "--project-root", str(repo), cwd=repo)
            pkg = [p for p in (repo / "doc" / "04-changes" / "02-active").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(pkg, "initial-feat")
            (repo / "app.py").write_text("def start(): return 'ok'\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "feat: initial commit")

            # Untouched init template 02-architecture-and-design.md must fail on root..HEAD
            res_block = run_cli("archive", "initial-feat", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_block.returncode, 0)
            self.assertIn("featureDocs", res_block.stderr)

            # Updating static doc passes archive; same-day duplicate name gets -2
            with (repo / "doc" / "02-architecture-and-design.md").open("a", encoding="utf-8") as fh:
                fh.write("\n### Entrypoint\n- `app.py` exposes `start()` returning ok\n")
            res_ok = run_cli("archive", "initial-feat", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_ok.returncode, 0, res_ok.stdout + res_ok.stderr)

            res_new2 = run_cli("new", "initial-feat", "--state", "active", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_new2.returncode, 0, res_new2.stderr)
            pkgs2 = [p for p in (repo / "doc" / "04-changes" / "02-active").iterdir() if p.is_dir()]
            self.assertTrue(pkgs2[0].name.endswith("-2"))

        # Clean working tree HEAD~1..HEAD fallback supports both real static doc edit and fresh waiver
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "app.py").write_text("print(1)\n", encoding="utf-8")
            run_cli("init", "--profile", "lite", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            (repo / "app.py").write_text("print(2)\n", encoding="utf-8")
            with (repo / "doc" / "02-architecture-and-design.md").open("a", encoding="utf-8") as fh:
                fh.write("\n### CLI\n- Updated console output behavior\n")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "feat: update app and design")
            res_head_doc = run_cli("check-sync", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_head_doc.returncode, 0, res_head_doc.stdout + res_head_doc.stderr)

            (repo / "app.py").write_text("print(3)\n", encoding="utf-8")
            with (repo / "doc" / "04-changes" / "hotfix-log.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- doc-sync-waiver: featureDocs | Log string wording tweak with zero API or design impact -->\n")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "fix: log wording with waiver")
            res_head_waiver = run_cli("check-sync", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_head_waiver.returncode, 0, res_head_waiver.stdout + res_head_waiver.stderr)
            self.assertIn("WAIVED [featureDocs", res_head_waiver.stdout)

    def test_full_lifecycle_ops_noop_and_standalone_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "order.py").write_text("def create_order():\n    return 1\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            # Standalone review package works cleanly even with uncommitted code
            (repo / "src" / "order.py").write_text("def create_order():\n    return 99\n", encoding="utf-8")
            res_rev = run_cli("new", "review-order-pr", "--type", "review", "--state", "active", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_rev.returncode, 0, res_rev.stderr)
            rev_pkg = [p for p in (repo / "doc" / "09-changes" / "02-active").iterdir() if p.is_dir()][0]
            self.assertFalse((rev_pkg / "01-plan.md").exists())
            (rev_pkg / "04-review.md").write_text(
                "<!-- godkey-package-type: review -->\n# Review: order PR\n\n- Dimension 1 layering clean\n- Dimension 2 magic value 99 at src/order.py:2 should become a named constant\n- Acceptance: replace magic number and re-run tests\n",
                encoding="utf-8",
            )
            res_rev_arch = run_cli("archive", "review-order-pr", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_rev_arch.returncode, 0, res_rev_arch.stdout + res_rev_arch.stderr)

            # Standard package lifecycle + natural English no-op deploy-notes
            run_git(repo, "checkout", "--", "src/order.py")
            run_cli("new", "order-coupons", "--state", "draft", "--project-root", str(repo), cwd=repo)
            self.assertEqual(run_cli("move", "order-coupons", "active", "--project-root", str(repo), cwd=repo).returncode, 0)
            self.assertEqual(
                run_cli("move", "order-coupons", "paused", "--reason", "Waiting on discount rules", "--project-root", str(repo), cwd=repo).returncode,
                0,
            )
            self.assertNotEqual(run_cli("move", "order-coupons", "archive", "--project-root", str(repo), cwd=repo).returncode, 0)
            self.assertEqual(run_cli("move", "order-coupons", "active", "--project-root", str(repo), cwd=repo).returncode, 0)

            active_pkg = [p for p in (repo / "doc" / "09-changes" / "02-active").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(active_pkg, "order-coupons")
            (active_pkg / "ops" / "deploy-notes.md").write_text("# Ops\n\n- No special rollout steps, standard release only\n- No new env vars\n", encoding="utf-8")
            (active_pkg / "ops" / "01_alter_orders.sql").write_text("ALTER TABLE orders ADD COLUMN coupon_id BIGINT;\n", encoding="utf-8")
            (repo / "src" / "order.py").write_text("def create_order(coupon_id=None):\n    return 2 if coupon_id is not None else 1\n", encoding="utf-8")
            (repo / "doc" / "04-feature-design" / "orders.md").write_text("# Orders\n\nAdded optional coupon_id parameter.\n", encoding="utf-8")
            (repo / "doc" / "05-database" / "init_tables.sql").write_text("CREATE TABLE orders (id BIGINT, coupon_id BIGINT);\n", encoding="utf-8")

            res_pass = run_cli("archive", "order-coupons", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_pass.returncode, 0, res_pass.stdout + res_pass.stderr)
            archived_pkg = repo / "doc" / "09-changes" / "99-archive" / active_pkg.name
            self.assertTrue((archived_pkg / "ops" / "01_alter_orders.sql").is_file())

    def test_hotfix_mode_and_git_worktree_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "main-repo"
            repo.mkdir()
            init_git_repo(repo)
            (repo / "app.py").write_text("def run(): return 0\n", encoding="utf-8")
            (repo / "other.py").write_text("def other(): return 1\n", encoding="utf-8")
            run_cli("init", "--profile", "lite", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: init lite")

            (repo / "app.py").write_text("def run(x=None): return 0 if x is None else x\n", encoding="utf-8")
            self.assertNotEqual(run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo).returncode, 0)

            run_cli(
                "hotfix",
                "--title", "Guard None input",
                "--symptom", "Crash on None",
                "--root-cause", "Missing None check",
                "--files", "app.py",
                "--verify", "pytest passed",
                "--project-root", str(repo),
                cwd=repo,
            )
            res_ok = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_ok.returncode, 0, res_ok.stdout + res_ok.stderr)

            (repo / "other.py").write_text("def other(): return 2\n", encoding="utf-8")
            res_two = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_two.returncode, 0)
            run_git(repo, "checkout", "--", ".")

            # Worktree hook installation & real git commit enforcement
            wt = Path(tmp) / "wt-branch"
            run_git(repo, "worktree", "add", "-b", "wt-test", str(wt))
            res_hook = run_cli("install-hook", "--project-root", str(wt), cwd=wt)
            self.assertEqual(res_hook.returncode, 0, res_hook.stdout + res_hook.stderr)

            (wt / "app.py").write_text("def run(x=None): return 1 if x is None else x\n", encoding="utf-8")
            run_git(wt, "add", "app.py")
            res_block = run_git(wt, "commit", "-m", "fix: missing log", check=False)
            self.assertNotEqual(res_block.returncode, 0)

            run_cli(
                "hotfix",
                "--title", "Worktree fix",
                "--symptom", "Wrong default",
                "--root-cause", "Off by one",
                "--files", "app.py",
                "--verify", "Verified locally",
                "--project-root", str(wt),
                cwd=wt,
            )
            run_git(wt, "add", "doc/04-changes/hotfix-log.md")
            res_allow = run_git(wt, "commit", "-m", "fix: with hotfix log", check=False)
            self.assertEqual(res_allow.returncode, 0, res_allow.stdout + res_allow.stderr)


if __name__ == "__main__":
    unittest.main()
