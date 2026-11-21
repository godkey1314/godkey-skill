#!/usr/bin/env python3
"""GodKey Gate 真实链路集成与边界回归测试（真实临时 Git 仓库 + 真实 CLI / Git Hook 调用）。"""

from __future__ import annotations

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


def fill_feature_artifacts(pkg: Path, feature_title: str = "测试功能") -> None:
    (pkg / "01-方案.md").write_text(
        f"# 方案：{feature_title}\n\n## 背景\n- 实现{feature_title}并保持分层清晰\n- 涉及核心业务模块与对应单元测试\n- 验收标准为真实链路全部通过\n",
        encoding="utf-8",
    )
    prog_path = pkg / "02-进展.md"
    base_line = ""
    if prog_path.is_file():
        for ln in prog_path.read_text(encoding="utf-8").splitlines():
            if "godkey-base-commit:" in ln:
                base_line = ln
                break
    prog_path.write_text(
        f"# 进展：{feature_title}\n\n{base_line}\n\n"
        f"## 变更前快照\n- 原实现未支持 {feature_title}\n\n"
        f"## 迭代记录\n- 完成 {feature_title} 核心代码实现与本地联调验证\n- 已核对上下游调用方并清理废弃代码\n\n"
        f"## 静态文档同步记录\n- 已同步功能设计与相关静态快照\n",
        encoding="utf-8",
    )
    (pkg / "03-测试.md").write_text(
        f"# 测试：{feature_title}\n\n## 结果\n- 运行单元测试与真实链路测试覆盖正常、空值与异常路径\n- 执行结果：全部用例通过无跳过\n",
        encoding="utf-8",
    )
    (pkg / "04-审查.md").write_text(
        f"# 审查：{feature_title}\n\n## 结论\n- 架构合规与代码质量五维度逐项核查完毕，零跨层污染\n- 模式扩散已扫同目录全部文件，无同类值语义或并发缺陷\n",
        encoding="utf-8",
    )


class TestGodKeyGate(unittest.TestCase):
    def test_audit_discovery_and_fresh_template_accuracy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # 1) 空目录 -> uninitialized
            res = run_cli("audit", "--project-root", str(root), cwd=root)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("识别模式：uninitialized", res.stdout)

            # 2) GitHub/Gitee 新建空仓库（仅有极简 README + .gitignore，无源码）仍应判定 uninitialized
            (root / "README.md").write_text("# My New Repo\n", encoding="utf-8")
            (root / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
            res_empty_gh = run_cli("audit", "--project-root", str(root), cwd=root)
            self.assertIn("识别模式：uninitialized", res_empty_gh.stdout)

            # 3) 嵌套源码目录（无顶层 README 标志构建文件）应判定 external
            (root / "services" / "order").mkdir(parents=True)
            (root / "services" / "order" / "main.py").write_text("print('order')\n", encoding="utf-8")
            res_ext = run_cli("audit", "--project-root", str(root), cwd=root)
            self.assertIn("识别模式：external", res_ext.stdout)

        # 4) 刚 init 完一字未填的 full / lite 模板不得误报“✅ 有内容”
        with tempfile.TemporaryDirectory() as tmp:
            full_repo = Path(tmp) / "full"
            full_repo.mkdir()
            run_cli("init", "--profile", "full", "--project-root", str(full_repo), cwd=full_repo)
            res_full = run_cli("audit", "--project-root", str(full_repo), cwd=full_repo)
            self.assertEqual(res_full.returncode, 0)
            self.assertNotIn("✅ 有内容", res_full.stdout)
            self.assertIn("ℹ️ 默认通用规范（未定制）", res_full.stdout)

            lite_repo = Path(tmp) / "lite"
            lite_repo.mkdir()
            run_cli("init", "--profile", "lite", "--project-root", str(lite_repo), cwd=lite_repo)
            res_lite = run_cli("audit", "--project-root", str(lite_repo), cwd=lite_repo)
            self.assertEqual(res_lite.returncode, 0)
            self.assertNotIn("✅ 有内容", res_lite.stdout)
            self.assertIn("02-架构与设计.md", res_lite.stdout)
            self.assertIn("⚠️ 仅模板占位", res_lite.stdout)

            # 5) 多模块 *_doc 提示 + 非法配置优雅报错（无 Traceback）
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
            res_bad_json = run_cli("audit", "--doc-root", "backend_doc", "--project-root", str(multi), cwd=multi)
            self.assertNotEqual(res_bad_json.returncode, 0)
            self.assertNotIn("Traceback", res_bad_json.stderr)

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

            # 1) 同目录新增普通文件 src/helper.py 不应误报 archDocs
            run_cli("new", "工具函数", "--state", "active", "--project-root", str(repo), cwd=repo)
            (repo / "src" / "helper.py").write_text("def fmt(v): return str(v)\n", encoding="utf-8")
            (repo / "doc" / "04-功能设计" / "helper.md").write_text("# Helper\n\n提供字符串格式化工具。\n", encoding="utf-8")
            res_ok = run_cli("check-sync", "--package", "工具函数", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_ok.returncode, 0, res_ok.stdout + res_ok.stderr)

            # 2) 新增顶层子模块目录 src/billing/invoice.py 必须触发 archDocs
            (repo / "src" / "billing").mkdir()
            (repo / "src" / "billing" / "invoice.py").write_text("def bill(): return 1\n", encoding="utf-8")
            res_arch = run_cli("check-sync", "--package", "工具函数", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_arch.returncode, 0)
            self.assertIn("archDocs", res_arch.stderr)

            # 3) 常见 DB/运维文件名（models.py / user_schema.py / docker-compose.yml / Dockerfile.prod / nginx.conf / deploy.yaml）全部必须命中
            (repo / "src" / "models.py").write_text("class Order: pass\n", encoding="utf-8")
            (repo / "src" / "user_schema.py").write_text("class S: pass\n", encoding="utf-8")
            (repo / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
            (repo / "Dockerfile.prod").write_text("FROM python:3.12\n", encoding="utf-8")
            (repo / "nginx.conf").write_text("events {}\n", encoding="utf-8")
            (repo / "deploy.yaml").write_text("kind: Deployment\n", encoding="utf-8")
            res_hints = run_cli("check-sync", "--package", "工具函数", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_hints.returncode, 0)
            self.assertIn("dbDocs", res_hints.stderr)
            self.assertIn("opsDocs", res_hints.stderr)

            # 4) git mv 把 src/models/user.py 改名为 src/plain/user.py 仍应命中 dbDocs（保留旧路径）
            run_git(repo, "checkout", "--", ".")
            for extra in ("src/helper.py", "src/models.py", "src/user_schema.py", "docker-compose.yml", "Dockerfile.prod", "nginx.conf", "deploy.yaml", "doc/04-功能设计/helper.md"):
                p = repo / extra
                if p.exists():
                    p.unlink()
            if (repo / "src" / "billing").exists():
                import shutil
                shutil.rmtree(repo / "src" / "billing")
            (repo / "src" / "plain").mkdir()
            run_git(repo, "mv", "src/models/user.py", "src/plain/user.py")
            (repo / "doc" / "04-功能设计" / "user.md").write_text("# User\n\n调整模型位置。\n", encoding="utf-8")
            (repo / "doc" / "03-系统架构" / "架构设计.md").write_text("# 架构\n\n新增 plain 目录。\n", encoding="utf-8")
            run_git(repo, "add", "doc/04-功能设计/user.md", "doc/03-系统架构/架构设计.md")
            res_mv = run_cli("check-sync", "--staged", "--mode", "strict", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_mv.returncode, 0)
            self.assertIn("dbDocs", res_mv.stderr)

    def test_anti_bypass_deleted_static_blank_line_skip_git_and_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("def a(): return 1\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            (repo / "doc" / "04-功能设计" / "订单.md").write_text("# 订单模块\n\n下单逻辑说明。\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            # 1) --date 路径穿越必须被拒绝
            res_trav = run_cli("new", "evil", "--date", "../../../../pwned", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_trav.returncode, 0)
            self.assertFalse((repo.parent / "pwned").exists())

            run_cli("new", "防绕过测试", "--state", "active", "--project-root", str(repo), cwd=repo)
            pkg = [p for p in (repo / "doc" / "09-迭代变更" / "02-进行中").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(pkg, "防绕过测试")

            # 2) 改代码 + 删除静态文档 -> 必须 FAIL
            (repo / "src" / "app.py").write_text("def a(): return 2\n", encoding="utf-8")
            (repo / "doc" / "04-功能设计" / "订单.md").unlink()
            res_del = run_cli("check-sync", "--package", "防绕过测试", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_del.returncode, 0)
            self.assertIn("featureDocs", res_del.stderr)
            run_git(repo, "checkout", "--", "doc/04-功能设计/订单.md")

            # 3) 仅改 _模块设计模板.md 或给真实文档加空行 -> 必须 FAIL
            tpl_file = repo / "doc" / "04-功能设计" / "_模块设计模板.md"
            with tpl_file.open("a", encoding="utf-8") as fh:
                fh.write("\n")
            with (repo / "doc" / "04-功能设计" / "订单.md").open("a", encoding="utf-8") as fh:
                fh.write("\n   \n")
            res_blank = run_cli("check-sync", "--package", "防绕过测试", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_blank.returncode, 0)
            self.assertIn("featureDocs", res_blank.stderr)

            # 4) 真实 Git 仓库中 --skip-git 必须被拒绝
            res_skip = run_cli("archive", "防绕过测试", "--skip-git", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_skip.returncode, 0)
            self.assertIn("禁止使用 `--skip-git`", res_skip.stderr)

            # 5) 原封不动复制 _模块设计模板.md 为新静态文件 -> 必须 FAIL
            import shutil
            shutil.copy2(tpl_file, repo / "doc" / "04-功能设计" / "空复制模块.md")
            res_copy_tpl = run_cli("check-sync", "--package", "防绕过测试", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_copy_tpl.returncode, 0)
            self.assertIn("featureDocs", res_copy_tpl.stderr)
            (repo / "doc" / "04-功能设计" / "空复制模块.md").unlink()

            # 6) 普通功能包在 04-审查.md 中伪造 review 标记 -> 必须被拒绝，不能绕过门禁
            with (pkg / "04-审查.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- godkey-package-type: review -->\n")
            res_forge = run_cli("archive", "防绕过测试", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_forge.returncode, 0)
            self.assertIn("禁止伪造独立审查包", res_forge.stderr)

        # 5) 真正的非 Git 目录含 ops/*.sql 不应死锁
        with tempfile.TemporaryDirectory() as tmp:
            nongit = Path(tmp)
            run_cli("init", "--profile", "full", "--project-root", str(nongit), cwd=nongit)
            run_cli("new", "非Git功能", "--state", "active", "--project-root", str(nongit), cwd=nongit)
            pkg = [p for p in (nongit / "doc" / "09-迭代变更" / "02-进行中").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(pkg, "非Git功能")
            (pkg / "ops" / "01_alter.sql").write_text("ALTER TABLE t ADD COLUMN c INT;\n", encoding="utf-8")
            res_ng = run_cli("archive", "非Git功能", "--project-root", str(nongit), cwd=nongit)
            self.assertEqual(res_ng.returncode, 0, res_ng.stdout + res_ng.stderr)
            self.assertIn("ARCHIVE PASS", res_ng.stdout)

    def test_waiver_poison_pill_case_and_cheese_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            # 1) 在历史 hotfix记录.md 写过一次豁免并提交 -> 绝不能永久豁免未来无关改动
            with (repo / "doc" / "09-迭代变更" / "hotfix记录.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- doc-sync-waiver: featureDocs | 纯单行空值防护不改变任何接口与业务规则 -->\n")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "fix: old hotfix with waiver")

            (repo / "src" / "big_feature.py").write_text("def f(): return 42\n", encoding="utf-8")
            res_no_poison = run_cli("check-sync", "--mode", "strict", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_no_poison.returncode, 0)
            self.assertIn("featureDocs", res_no_poison.stderr)

            # 2) 敷衍模板替换（把 [待填写 改成 [已看）必须被产物检查拦截
            run_cli("new", "敷衍测试", "--state", "active", "--project-root", str(repo), cwd=repo)
            pkg = [p for p in (repo / "doc" / "09-迭代变更" / "02-进行中").iterdir() if p.is_dir()][0]
            for fname in ("01-方案.md", "02-进展.md", "03-测试.md", "04-审查.md"):
                p = pkg / fname
                p.write_text(p.read_text(encoding="utf-8").replace("[待填写", "[已看", 3), encoding="utf-8")
            res_cheese = run_cli("archive", "敷衍测试", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_cheese.returncode, 0)

            # 3) 敷衍 11 字套话 & 重复字符豁免被拦截；小写键 featuredocs + 含“具体原因”的正当理由正常生效
            fill_feature_artifacts(pkg, "敷衍测试")
            with (pkg / "02-进展.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- doc-sync-waiver: featureDocs | 本次改动不需要更新文档 -->\n")
            res_lazy = run_cli("check-sync", "--package", "敷衍测试", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_lazy.returncode, 0)
            self.assertIn("无效豁免声明", res_lazy.stderr)

            prog = (pkg / "02-进展.md").read_text(encoding="utf-8")
            (pkg / "02-进展.md").write_text(
                prog.replace(
                    "<!-- doc-sync-waiver: featureDocs | 本次改动不需要更新文档 -->",
                    "<!-- doc-sync-waiver: featuredocs | 具体原因在于仅内部辅助拆分，对外接口契约未变 -->",
                ),
                encoding="utf-8",
            )
            res_case_ok = run_cli("check-sync", "--package", "敷衍测试", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_case_ok.returncode, 0, res_case_ok.stdout + res_case_ok.stderr)
            self.assertIn("WAIVED [featureDocs", res_case_ok.stdout)

    def test_unborn_head_first_commit_and_same_day_archive_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            run_cli("init", "--profile", "lite", "--project-root", str(repo), cwd=repo)
            # 无任何 commit（unborn HEAD）时建包 -> 写源码 -> 做首次提交 -> archive 必须检查 root..HEAD
            run_cli("new", "首版功能", "--state", "active", "--project-root", str(repo), cwd=repo)
            pkg = [p for p in (repo / "doc" / "04-迭代变更" / "02-进行中").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(pkg, "首版功能")
            (repo / "app.py").write_text("def start(): return 'ok'\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "feat: initial commit without updating design doc")

            # 1) 未更新 02-架构与设计.md（原样 init 模板未填实质内容）在 unborn HEAD 首提交下也必须拦截！
            res_unborn_untouched = run_cli("archive", "首版功能", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_unborn_untouched.returncode, 0)
            self.assertIn("featureDocs", res_unborn_untouched.stderr)

            # 真实更新 02-架构与设计.md 后归档成功
            with (repo / "doc" / "02-架构与设计.md").open("a", encoding="utf-8") as fh:
                fh.write("\n### 启动模块\n- `app.py` 提供 `start()` 入口返回健康状态\n")
            res_first = run_cli("archive", "首版功能", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_first.returncode, 0, res_first.stdout + res_first.stderr)

            # 同日再建同名包 -> 自动递增 -2 且可正常归档
            res_new2 = run_cli("new", "首版功能", "--state", "active", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_new2.returncode, 0, res_new2.stderr)
            pkgs2 = [p for p in (repo / "doc" / "04-迭代变更" / "02-进行中").iterdir() if p.is_dir()]
            self.assertEqual(len(pkgs2), 1)
            self.assertTrue(pkgs2[0].name.endswith("-2"))

        # 2) 验证干净工作区回退 HEAD~1..HEAD：真实静态文档修改 & 新提交合法豁免均正常生效
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "app.py").write_text("print(1)\n", encoding="utf-8")
            run_cli("init", "--profile", "lite", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline")

            # Commit 1: 同时真实修改 app.py 和 02-架构与设计.md -> 工作区干净时 HEAD~1..HEAD 必须 PASS
            (repo / "app.py").write_text("print(2)\n", encoding="utf-8")
            with (repo / "doc" / "02-架构与设计.md").open("a", encoding="utf-8") as fh:
                fh.write("\n### 主入口模块\n- 新增命令行输出行为说明\n")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "feat: update app and design")
            res_head_doc = run_cli("check-sync", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_head_doc.returncode, 0, res_head_doc.stdout + res_head_doc.stderr)

            # Commit 2: 同时修改 app.py 并在 hotfix记录.md 追加新豁免 -> 工作区干净时 HEAD~1..HEAD 必须读到新豁免并 WAIVED PASS
            (repo / "app.py").write_text("print(3)\n", encoding="utf-8")
            with (repo / "doc" / "04-迭代变更" / "hotfix记录.md").open("a", encoding="utf-8") as fh:
                fh.write("\n<!-- doc-sync-waiver: featureDocs | 纯日志文本微调不改变对外接口与业务规则 -->\n")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "fix: log tweak with waiver")
            res_head_waiver = run_cli("check-sync", "--mode", "archive", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_head_waiver.returncode, 0, res_head_waiver.stdout + res_head_waiver.stderr)
            self.assertIn("WAIVED [featureDocs", res_head_waiver.stdout)

    def test_full_lifecycle_ops_noop_and_standalone_review_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "order.py").write_text("def create_order():\n    return 1\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: initial baseline")

            # 1) 独立审查包（--type review）：工作区有未提交代码改动时仍可干净建包并归档
            (repo / "src" / "order.py").write_text("def create_order():\n    return 99\n", encoding="utf-8")
            res_rev_new = run_cli("new", "审查_订单PR", "--type", "review", "--state", "active", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_rev_new.returncode, 0, res_rev_new.stderr)
            rev_pkg = [p for p in (repo / "doc" / "09-迭代变更" / "02-进行中").iterdir() if p.is_dir()][0]
            self.assertFalse((rev_pkg / "01-方案.md").exists())
            with (rev_pkg / "04-审查.md").open("a", encoding="utf-8") as fh:
                fh.write("\n## 实审结论\n- 位置 src/order.py:1 存在硬编码魔法值 99，建议抽取常量\n- 其余五维度均核查完毕，验收标准见上文\n")
            # 去掉模板剩余 [待填写] 以便通过实质检查
            (rev_pkg / "04-审查.md").write_text(
                "<!-- godkey-package-type: review -->\n# 审查：订单PR\n\n- 维度1架构合规：分层清晰无越界\n- 维度2代码质量：src/order.py:1 存在硬编码魔法值 99，建议改具名常量\n- 验收标准：清理魔法值并跑通回归测试\n",
                encoding="utf-8",
            )
            res_rev_arch = run_cli("archive", "审查_订单PR", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_rev_arch.returncode, 0, res_rev_arch.stdout + res_rev_arch.stderr)
            self.assertIn("ARCHIVE PASS", res_rev_arch.stdout)

            # 2) 标准功能包：draft -> active -> paused -> active -> archive，且 deploy-notes 写“无特殊上线步骤”不误报 opsDocs
            run_git(repo, "checkout", "--", "src/order.py")
            run_cli("new", "订单加优惠券", "--state", "draft", "--project-root", str(repo), cwd=repo)
            self.assertEqual(run_cli("move", "订单加优惠券", "active", "--project-root", str(repo), cwd=repo).returncode, 0)
            self.assertEqual(
                run_cli("move", "订单加优惠券", "paused", "--reason", "等产品确认满减规则", "--project-root", str(repo), cwd=repo).returncode,
                0,
            )
            self.assertNotEqual(run_cli("move", "订单加优惠券", "archive", "--project-root", str(repo), cwd=repo).returncode, 0)
            self.assertNotEqual(run_cli("archive", "订单加优惠券", "--project-root", str(repo), cwd=repo).returncode, 0)
            self.assertEqual(run_cli("move", "订单加优惠券", "active", "--project-root", str(repo), cwd=repo).returncode, 0)

            active_pkg = [p for p in (repo / "doc" / "09-迭代变更" / "02-进行中").iterdir() if p.is_dir()][0]
            fill_feature_artifacts(active_pkg, "订单加优惠券")
            (active_pkg / "ops" / "deploy-notes.md").write_text("# 运维\n\n- 无特殊上线步骤，常规发布即可\n- 本次无新增环境变量\n", encoding="utf-8")
            (active_pkg / "ops" / "01_alter_orders.sql").write_text("ALTER TABLE orders ADD COLUMN coupon_id BIGINT;\n", encoding="utf-8")
            (repo / "src" / "order.py").write_text("def create_order(coupon_id=None):\n    return 2 if coupon_id is not None else 1\n", encoding="utf-8")
            (repo / "doc" / "04-功能设计" / "订单.md").write_text("# 订单模块\n\n支持 coupon_id 入参。\n", encoding="utf-8")
            (repo / "doc" / "05-数据库" / "init_tables.sql").write_text("CREATE TABLE orders (id BIGINT, coupon_id BIGINT);\n", encoding="utf-8")

            res_pass = run_cli("archive", "订单加优惠券", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_pass.returncode, 0, res_pass.stdout + res_pass.stderr)
            archived_pkg = repo / "doc" / "09-迭代变更" / "99-已归档" / active_pkg.name
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

            # 1) hotfix 专用模式：单文件未记台账 -> FAIL；记台账 -> PASS；改 2 个文件 -> FAIL
            (repo / "app.py").write_text("def run(x=None): return 0 if x is None else x\n", encoding="utf-8")
            res_hf_missing = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_hf_missing.returncode, 0)

            run_cli(
                "hotfix",
                "--title", "修复空值",
                "--symptom", "None 入参报错",
                "--root-cause", "未判空",
                "--files", "app.py",
                "--verify", "pytest 通过",
                "--project-root", str(repo),
                cwd=repo,
            )
            res_hf_ok = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_hf_ok.returncode, 0, res_hf_ok.stdout + res_hf_ok.stderr)

            (repo / "other.py").write_text("def other(): return 2\n", encoding="utf-8")
            res_hf_two = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_hf_two.returncode, 0)
            self.assertIn("超出单文件小修上限", res_hf_two.stderr)
            run_git(repo, "checkout", "--", ".")

            # 2) Git Worktree 安装 pre-commit hook 并实测真实 git commit 拦截与放行
            wt = Path(tmp) / "wt-branch"
            run_git(repo, "worktree", "add", "-b", "wt-test", str(wt))
            res_wt_hook = run_cli("install-hook", "--project-root", str(wt), cwd=wt)
            self.assertEqual(res_wt_hook.returncode, 0, res_wt_hook.stdout + res_wt_hook.stderr)

            (wt / "app.py").write_text("def run(x=None): return 1 if x is None else x\n", encoding="utf-8")
            run_git(wt, "add", "app.py")
            res_block = run_git(wt, "commit", "-m", "fix: missing doc", check=False)
            self.assertNotEqual(res_block.returncode, 0, "worktree 中 pre-commit hook 应拦截无记录代码提交")

            run_cli(
                "hotfix",
                "--title", "worktree小修",
                "--symptom", "返回值偏差",
                "--root-cause", "默认值写错",
                "--files", "app.py",
                "--verify", "手工验证通过",
                "--project-root", str(wt),
                cwd=wt,
            )
            run_git(wt, "add", "doc/04-迭代变更/hotfix记录.md")
            res_allow = run_git(wt, "commit", "-m", "fix: with hotfix log", check=False)
            self.assertEqual(res_allow.returncode, 0, res_allow.stdout + res_allow.stderr)

            # 3) 拒绝覆盖已有非 godkey 自定义 hook
            hook_path = Path(run_git(wt, "rev-parse", "--git-path", "hooks/pre-commit").stdout.strip())
            if not hook_path.is_absolute():
                hook_path = (wt / hook_path).resolve()
            hook_path.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
            res_no_clobber = run_cli("install-hook", "--project-root", str(wt), cwd=wt)
            self.assertNotEqual(res_no_clobber.returncode, 0)

    def test_gitignored_changes_dir_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("def run(): return 1\n", encoding="utf-8")
            (repo / "src" / "other.py").write_text("def other(): return 2\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            (repo / ".gitignore").write_text("doc/09-迭代变更/\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: baseline with gitignored changes dir")

            # 1) audit 显式标注本地保留且正常工作
            res_audit = run_cli("audit", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_audit.returncode, 0, res_audit.stderr)
            self.assertIn("识别模式：full", res_audit.stdout)
            self.assertIn("已被 .gitignore 忽略", res_audit.stdout)

            # 2) hotfix 模式：未记台账 -> FAIL；记错文件名 -> FAIL；记对文件名 -> PASS
            (repo / "src" / "app.py").write_text("def run(x=None): return 1 if x is None else x\n", encoding="utf-8")
            self.assertNotEqual(run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo).returncode, 0)

            run_cli(
                "hotfix",
                "--title", "无关文件记录",
                "--symptom", "测试不匹配拦截",
                "--root-cause", "仅记录了 other.py",
                "--files", "src/other.py",
                "--verify", "单测通过",
                "--project-root", str(repo),
                cwd=repo,
            )
            res_hf_wrong = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_hf_wrong.returncode, 0)
            self.assertIn("未涵盖本次改动文件", res_hf_wrong.stderr)

            run_cli(
                "hotfix",
                "--title", "修复 app 空值",
                "--symptom", "None 入参未处理",
                "--root-cause", "缺少判空",
                "--files", "src/app.py",
                "--verify", "单测通过",
                "--project-root", str(repo),
                cwd=repo,
            )
            res_hf_ok = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_hf_ok.returncode, 0, res_hf_ok.stdout + res_hf_ok.stderr)
            self.assertIn("本地磁盘核验", res_hf_ok.stdout)

            # 3) pre-commit hook：改 2 文件 -> 无包拦截、空模板拦截、1 字敷衍拦截、实质进展放行
            self.assertEqual(run_cli("install-hook", "--project-root", str(repo), cwd=repo).returncode, 0)
            (repo / "src" / "other.py").write_text("def other(): return 3\n", encoding="utf-8")
            run_git(repo, "add", "src/app.py", "src/other.py")
            self.assertNotEqual(run_git(repo, "commit", "-m", "wip: no pkg", check=False).returncode, 0)

            run_cli("new", "忽略目录兼容功能", "--state", "active", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(run_git(repo, "commit", "-m", "wip: empty tpl", check=False).returncode, 0)

            pkg = [p for p in (repo / "doc" / "09-迭代变更" / "02-进行中").iterdir() if p.is_dir()][0]
            with (pkg / "02-进展.md").open("a", encoding="utf-8") as fh:
                fh.write("\n- x\n")
            self.assertNotEqual(run_git(repo, "commit", "-m", "wip: 1-char cheese", check=False).returncode, 0)

            fill_feature_artifacts(pkg, "忽略目录兼容功能")
            res_wip_ok = run_git(repo, "commit", "-m", "wip: with local progress", check=False)
            self.assertEqual(res_wip_ok.returncode, 0, res_wip_ok.stdout + res_wip_ok.stderr)

            # 4) archive：未同步静态文档 -> FAIL；同步后 -> ARCHIVE PASS 且 git status 无动态目录污染
            res_arch_fail = run_cli("archive", "忽略目录兼容功能", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_arch_fail.returncode, 0)
            self.assertIn("featureDocs", res_arch_fail.stderr)

            (repo / "doc" / "04-功能设计" / "核心逻辑.md").write_text("# 核心逻辑\n\n更新 app 与 other 行为契约。\n", encoding="utf-8")
            res_arch_ok = run_cli("archive", "忽略目录兼容功能", "--project-root", str(repo), cwd=repo)
            self.assertEqual(res_arch_ok.returncode, 0, res_arch_ok.stdout + res_arch_ok.stderr)
            self.assertIn("ARCHIVE PASS", res_arch_ok.stdout)
            self.assertNotIn("09-迭代变更", run_git(repo, "status", "--porcelain").stdout)

        # 5) 部分忽略（仅忽略 02-进行中/，不忽略已纳入 Git 的 hotfix记录.md）时，已跟踪 hotfix 不得跳过 Git diff 检查
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_git_repo(repo)
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("def run(): return 1\n", encoding="utf-8")
            run_cli("init", "--profile", "full", "--project-root", str(repo), cwd=repo)
            (repo / ".gitignore").write_text("doc/09-迭代变更/02-进行中/\n", encoding="utf-8")
            run_cli(
                "hotfix",
                "--title", "旧历史修复",
                "--symptom", "旧问题",
                "--root-cause", "旧原因",
                "--files", "src/app.py",
                "--verify", "旧验证",
                "--project-root", str(repo),
                cwd=repo,
            )
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "chore: tracked hotfix + ignored active dir")

            # 仅改 src/app.py 不改已跟踪的 hotfix记录.md -> 必须被 hotfix 门禁拦截（不得借历史同日条目绕过）
            (repo / "src" / "app.py").write_text("def run(): return 2\n", encoding="utf-8")
            res_tracked_block = run_cli("check-sync", "--mode", "hotfix", "--project-root", str(repo), cwd=repo)
            self.assertNotEqual(res_tracked_block.returncode, 0)


if __name__ == "__main__":
    unittest.main()
