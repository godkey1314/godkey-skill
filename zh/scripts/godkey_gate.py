#!/usr/bin/env python3
"""GodKey Skill — 跨 Harness 确定性文档审计、变更包状态机与静态文档同步门禁。

仅依赖 Python 3.8+ 标准库，支持 Windows / Linux / macOS 与任意 Agent Harness。
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ROOT = SKILL_ROOT / "assets" / "templates"

STATE_DIRS: Dict[str, str] = {
    "draft": "01-待确认",
    "active": "02-进行中",
    "paused": "03-已搁置",
    "archive": "99-已归档",
}

STATE_ALIASES: Dict[str, str] = {
    "draft": "draft",
    "待确认": "draft",
    "01-待确认": "draft",
    "active": "active",
    "进行中": "active",
    "02-进行中": "active",
    "paused": "paused",
    "已搁置": "paused",
    "搁置": "paused",
    "03-已搁置": "paused",
    "archive": "archive",
    "已归档": "archive",
    "归档": "archive",
    "99-已归档": "archive",
}

FULL_STATIC_ITEMS: List[str] = [
    "01-产品介绍",
    "02-使用指南",
    "03-系统架构",
    "04-功能设计",
    "05-数据库",
    "06-开发规范",
    "07-部署运维",
    "08-资源文件",
]

LITE_STATIC_ITEMS: List[str] = [
    "01-项目说明.md",
    "02-架构与设计.md",
    "03-开发规范.md",
]

DEFAULT_CODE_EXTS: Set[str] = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
    ".go", ".rs", ".java", ".kt", ".kts", ".scala", ".cs", ".cpp", ".cc",
    ".c", ".h", ".hpp", ".rb", ".php", ".swift", ".dart", ".sh", ".bash",
    ".ps1", ".sql", ".graphql", ".proto",
}

CANONICAL_RULE_KEYS: Dict[str, str] = {
    "featuredocs": "featureDocs",
    "archdocs": "archDocs",
    "dbdocs": "dbDocs",
    "opsdocs": "opsDocs",
}

LAZY_WAIVER_PHRASES: Set[str] = {
    "无", "无需", "无需更新", "不需要", "不需要更新", "不用更新", "跳过",
    "无需同步", "不用同步", "不需要同步", "暂不更新", "略", "暂无",
    "none", "n/a", "na", "skip", "no change", "no need", "todo", "tbd",
}

LAZY_WAIVER_PATTERNS: List[re.Pattern] = [
    re.compile(r"^(本次|此次|当前|这个|该)?(改动|修改|变更|任务)?(不|无|免|无需|不需要|不用|不必|跳过|暂不)(需|需要|要|必)?(更新|同步|修改)?(静态)?(文档|蓝图|设计|快照)?$"),
    re.compile(r"^(no|not|skip|none)\s+(need|change|changes|doc|docs|update|sync).*$", re.IGNORECASE),
]

NOOP_OPS_LINE_RE = re.compile(
    r"^[-*\d.\s\|]*(本次|本轮|该功能|此功能)?(均)?(无|无需|无须|无变更|无新增|无特殊|不需要|不涉及|常规发布|正常发布|默认发布|暂无|none|n/a|na)",
    re.IGNORECASE,
)
OPS_REAL_SIGNAL_RE = re.compile(r"(=|`|但需|不过需|仍需|\.sql\b|\.py\b|\.sh\b|\.ps1\b)", re.IGNORECASE)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DOC_WAIVER_RE = re.compile(
    r"^\s*<!--\s*doc-sync-waiver:\s*(featureDocs|archDocs|dbDocs|opsDocs)\s*\|\s*([^|]+?)\s*-->\s*$",
    re.IGNORECASE,
)
ARTIFACT_WAIVER_RE = re.compile(
    r"^\s*<!--\s*artifact-waiver:\s*(test|review)\s*\|\s*([^|]+?)\s*-->\s*$",
    re.IGNORECASE,
)
BASE_COMMIT_RE = re.compile(r"<!--\s*godkey-base-commit:\s*([0-9a-fA-F]{7,40})\s*-->")
PACKAGE_TYPE_RE = re.compile(r"<!--\s*godkey-package-type:\s*(feature|review)\s*-->", re.IGNORECASE)


@dataclass
class ChangedEntry:
    status: str  # A, M, D, R, C, ?
    path: str
    old_path: Optional[str] = None


class GateConfigError(Exception):
    pass


def today_str() -> str:
    return dt.date.today().isoformat()


def now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def to_posix_rel(path: Path, root: Path) -> Optional[str]:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def is_path_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def run_git(project_root: Path, args: Sequence[str]) -> Tuple[int, str, str]:
    cmd = ["git", "-C", str(project_root), "-c", "core.quotepath=false", *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "git command not found"


def is_git_repo(project_root: Path) -> bool:
    code, out, _ = run_git(project_root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip().lower() == "true"


def get_head_commit(project_root: Path) -> str:
    if not is_git_repo(project_root):
        return ""
    code, out, _ = run_git(project_root, ["rev-parse", "--short=12", "HEAD"])
    return out.strip() if code == 0 else ""


def commit_exists(project_root: Path, ref: str) -> bool:
    if not ref or not is_git_repo(project_root):
        return False
    code, _, _ = run_git(project_root, ["cat-file", "-e", f"{ref}^{{commit}}"])
    return code == 0


def is_git_ignored(project_root: Path, rel_posix: str) -> bool:
    if not rel_posix or not is_git_repo(project_root):
        return False
    code, _, _ = run_git(project_root, ["check-ignore", "-q", "--", rel_posix])
    return code == 0


def is_git_tracked(project_root: Path, rel_posix: str) -> bool:
    if not rel_posix or not is_git_repo(project_root):
        return False
    code, _, _ = run_git(project_root, ["ls-files", "--error-unmatch", "--", rel_posix])
    return code == 0


def is_hotfix_local_only(project_root: Path, hotfix_rel: str) -> bool:
    return is_git_ignored(project_root, hotfix_rel) and not is_git_tracked(project_root, hotfix_rel)


def is_active_progress_local_only(
    project_root: Path, changes_rel: str, package_dir: Optional[Path] = None
) -> bool:
    if package_dir is not None:
        prog_rel = to_posix_rel(package_dir / "02-进展.md", project_root)
        if prog_rel:
            return is_git_ignored(project_root, prog_rel) and not is_git_tracked(project_root, prog_rel)
    probe_rel = f"{changes_rel}/{STATE_DIRS['active']}/_probe/02-进展.md"
    return is_git_ignored(project_root, probe_rel)


HOTFIX_ENTRY_HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*[—\-–]\s*(.+)$")


def parse_hotfix_entries(hotfix_path: Path) -> List[Tuple[str, str]]:
    """解析 hotfix记录.md 中的条目，返回 [(date_str, block_text), ...]。"""
    if not hotfix_path.is_file():
        return []
    entries: List[Tuple[str, str]] = []
    cur_date: Optional[str] = None
    cur_lines: List[str] = []
    for raw in hotfix_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = HOTFIX_ENTRY_HEADER_RE.match(raw.strip())
        if m:
            if cur_date is not None:
                entries.append((cur_date, "\n".join(cur_lines)))
            cur_date = m.group(1)
            cur_lines = [raw]
        elif cur_date is not None:
            cur_lines.append(raw)
    if cur_date is not None:
        entries.append((cur_date, "\n".join(cur_lines)))
    return entries


def _hotfix_body_mentions_file(body: str, rel_posix: str) -> bool:
    norm_body = body.replace("\\", "/").lower()
    norm_rel = rel_posix.replace("\\", "/").strip("./").lower()
    if norm_rel and norm_rel in norm_body:
        return True
    fname = Path(norm_rel).name
    if not fname:
        return False
    return bool(re.search(rf"(?<![a-z0-9_.\-/]){re.escape(fname)}(?![a-z0-9_.\-])", norm_body))


def has_local_hotfix_for_files(
    hotfix_path: Path,
    code_files: Sequence[str],
    check_recent_date: bool = True,
) -> Tuple[bool, str]:
    """当 hotfix记录.md 被 .gitignore 忽略且未纳入 Git 跟踪时，从本地磁盘核验最新实质记录。"""
    entries = parse_hotfix_entries(hotfix_path)
    if not entries:
        return False, f"本地 `{hotfix_path.name}` 无有效记录条目"

    entry_date, body = entries[-1]
    body_lines = strip_template_noise(body)
    if len(body_lines) < 2:
        return False, f"本地 `{hotfix_path.name}` 最新条目（{entry_date}）实质内容不足"

    if check_recent_date:
        try:
            d = dt.date.fromisoformat(entry_date)
        except ValueError:
            return False, f"本地 `{hotfix_path.name}` 最新条目日期非法（{entry_date}）"
        today = dt.date.today()
        if abs((today - d).days) > 1:
            return False, f"本地 `{hotfix_path.name}` 最新记录日期为 {entry_date}（非本次改动当天），请追加本次记录"

    missing = [cf for cf in code_files if not _hotfix_body_mentions_file(body, cf)]
    if missing:
        return False, f"本地 `{hotfix_path.name}` 最新记录（{entry_date}）未涵盖本次改动文件：{', '.join(missing)}"

    return True, f"最新条目 {entry_date} 已涵盖 {', '.join(code_files)}"


def find_local_active_progress(
    project_root: Path, changes_root: Path, package_dir: Optional[Path] = None
) -> List[str]:
    """当动态活跃目录被 .gitignore 忽略时，检查本地未跟踪活跃功能包是否存在已实质填写的 02-进展.md。"""
    tpl_prog = TEMPLATES_ROOT / "change-package" / "02-进展.md"
    candidates: List[Path]
    if package_dir is not None:
        candidates = [package_dir]
    else:
        candidates = list_state_packages(changes_root).get("active", [])

    matched: List[str] = []
    for pkg in candidates:
        prog = pkg / "02-进展.md"
        if not prog.is_file():
            continue
        prog_rel = to_posix_rel(prog, project_root)
        if prog_rel and is_git_tracked(project_root, prog_rel):
            continue
        added = meaningful_added_lines(prog, tpl_prog)
        added_chars = sum(len(re.sub(r"\s+", "", ln)) for ln in added)
        if added and added_chars >= 12:
            mtime = dt.datetime.fromtimestamp(prog.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            matched.append(f"{pkg.name}（更新于 {mtime}）")
    return matched


def default_config_for(profile: str) -> Dict:
    tpl_cfg = TEMPLATES_ROOT / profile / ".godkey.json"
    return json.loads(tpl_cfg.read_text(encoding="utf-8"))


def load_config(doc_root: Path) -> Optional[Dict]:
    cfg_path = doc_root / ".godkey.json"
    if not cfg_path.is_file():
        return None
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateConfigError(f"配置文件 JSON 语法错误：{cfg_path}（{exc}）") from exc
    if not isinstance(raw, dict):
        raise GateConfigError(f"配置文件根节点必须为 JSON 对象：{cfg_path}")

    profile = raw.get("profile", "full")
    if profile not in ("full", "lite"):
        raise GateConfigError(f"配置文件 profile 无效（仅支持 full / lite）：{cfg_path}")

    merged = default_config_for(profile)
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


def has_source_files_within_depth(project_root: Path, max_depth: int = 2) -> bool:
    """扫描项目根及有限深度子目录，判断是否存在实际业务源码或项目构建清单。"""
    build_markers = {
        "package.json", "pyproject.toml", "requirements.txt", "go.mod",
        "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts",
        "Makefile", "CMakeLists.txt", "AGENTS.md", "CLAUDE.md",
    }
    for marker in build_markers:
        if (project_root / marker).is_file():
            return True

    skip_dirs = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

    def _walk(cur: Path, depth: int) -> bool:
        try:
            entries = list(cur.iterdir())
        except OSError:
            return False
        for entry in entries:
            if entry.name.startswith(".") or entry.name in skip_dirs:
                continue
            if entry.is_file() and entry.suffix.lower() in DEFAULT_CODE_EXTS:
                return True
            if entry.is_dir() and depth < max_depth:
                if _walk(entry, depth + 1):
                    return True
        return False

    return _walk(project_root, 0)


def find_all_doc_candidates(project_root: Path) -> List[Tuple[str, Path, Dict]]:
    """返回全部匹配到的 GodKey 文档根目录候选列表。"""
    direct_dirs = [p for p in sorted(project_root.iterdir()) if p.is_dir() and not p.name.startswith(".")]
    preferred = [p for p in direct_dirs if p.name in ("doc", "docs") or p.name.endswith("_doc")]
    others = [p for p in direct_dirs if p not in preferred]

    found: List[Tuple[str, Path, Dict]] = []
    seen: Set[Path] = set()

    for cand in preferred + others:
        cfg = load_config(cand)
        if cfg:
            found.append((cfg["profile"], cand, cfg))
            seen.add(cand)

    for cand in preferred:
        if cand in seen:
            continue
        if (cand / "09-迭代变更").is_dir():
            found.append(("full", cand, default_config_for("full")))
            seen.add(cand)
        elif (cand / "04-迭代变更").is_dir():
            found.append(("lite", cand, default_config_for("lite")))
            seen.add(cand)

    return found


def discover_project_doc(
    project_root: Path, explicit_doc_root: Optional[str] = None
) -> Tuple[str, Optional[Path], Optional[Dict], List[Path]]:
    """返回 (mode, doc_root, config, extra_candidates)。
    mode 取值：full | lite | external | uninitialized
    """
    if explicit_doc_root:
        cand = Path(explicit_doc_root)
        if not cand.is_absolute():
            cand = (project_root / cand).resolve()
        if not is_path_within(cand, project_root):
            raise GateConfigError(f"--doc-root 必须位于项目根目录内：{cand}（项目根：{project_root}）")
        if cand.is_dir():
            cfg = load_config(cand)
            if cfg:
                return cfg["profile"], cand, cfg, []
            if (cand / "09-迭代变更").is_dir():
                return "full", cand, default_config_for("full"), []
            if (cand / "04-迭代变更").is_dir():
                return "lite", cand, default_config_for("lite"), []
        return "uninitialized", cand, None, []

    candidates = find_all_doc_candidates(project_root)
    if candidates:
        mode, chosen, cfg = candidates[0]
        extras = [c[1] for c in candidates[1:]]
        return mode, chosen, cfg, extras

    # 区分已有外部项目 vs 新建空仓库（仅有极简 README/LICENSE/gitignore 且无源码的仓库视为 uninitialized）
    if has_source_files_within_depth(project_root, max_depth=2):
        return "external", None, None, []

    # 若存在较丰富的 README（> 15 行非空内容）或已有非空 docs/ 目录，仍视为外部已有项目
    for readme_name in ("README.md", "README.rst"):
        rp = project_root / readme_name
        if rp.is_file():
            non_empty = [ln for ln in rp.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
            if len(non_empty) > 15:
                return "external", None, None, []
    docs_dir = project_root / "docs"
    if docs_dir.is_dir() and any(f.is_file() for f in docs_dir.rglob("*")):
        return "external", None, None, []

    return "uninitialized", None, None, []


def strip_template_noise(text: str) -> List[str]:
    """提取文本中非占位符、非纯框架骨架、非注释行的有意义内容。"""
    lines: List[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith(">") or s.startswith("---") or s.startswith("```"):
            continue
        if s.startswith("--"):  # SQL 注释行
            continue
        if s.startswith("<!--") and s.endswith("-->"):
            continue
        if re.fullmatch(r"[\|\-\:\s]+", s):
            continue
        if "[待填写" in s or "[无则留空]" in s or "[原始行为]" in s or "[当前行为]" in s:
            continue
        lines.append(s)
    return lines


def template_line_set(template_path: Path) -> Set[str]:
    if not template_path.is_file():
        return set()
    raw = template_path.read_text(encoding="utf-8")
    cleaned = re.sub(r"\{\{[A-Z0-9_]+\}\}", "", raw)
    return set(strip_template_noise(cleaned))


def meaningful_added_lines(actual_path: Path, template_path: Optional[Path] = None) -> List[str]:
    if not actual_path.is_file():
        return []
    actual_lines = strip_template_noise(actual_path.read_text(encoding="utf-8", errors="replace"))
    if template_path and template_path.is_file():
        tpl_lines = template_line_set(template_path)
        result = []
        for line in actual_lines:
            if line.startswith("- 已建立功能包 `") or line.startswith("- 变更状态：") or line.startswith("- 已通过 `godkey_gate.py"):
                continue
            if line in tpl_lines:
                continue
            result.append(line)
        return result
    return actual_lines


def inspect_static_item(path: Path, template_equiv: Optional[Path] = None, is_default_spec: bool = False) -> str:
    if not path.exists():
        return "❌ 缺失"

    if path.is_file():
        added = meaningful_added_lines(path, template_equiv)
        if not added:
            return "ℹ️ 默认通用规范（未定制）" if is_default_spec else "⚠️ 仅模板占位"
        return "✅ 有内容"

    files = [f for f in path.rglob("*") if f.is_file() and f.name != ".gitkeep"]
    if not files:
        return "⚠️ 空目录"

    non_template_files = [f for f in files if not f.name.startswith("_")]
    if not non_template_files:
        return "⚠️ 仅模板"

    customized = 0
    for f in non_template_files:
        rel = f.relative_to(path)
        tpl_f = (template_equiv / rel) if (template_equiv and template_equiv.is_dir()) else None
        if tpl_f is None or not tpl_f.is_file():
            # 用户新建的文档或非模板资源文件
            if f.suffix.lower() in {".md", ".txt", ".sql"}:
                if strip_template_noise(f.read_text(encoding="utf-8", errors="replace")):
                    customized += 1
            else:
                customized += 1
        else:
            if meaningful_added_lines(f, tpl_f):
                customized += 1

    if customized > 0:
        return "✅ 有内容"
    return "ℹ️ 默认通用规范（未定制）" if is_default_spec else "⚠️ 仅模板占位"


def list_state_packages(changes_root: Path) -> Dict[str, List[Path]]:
    result: Dict[str, List[Path]] = {}
    for key, dirname in STATE_DIRS.items():
        sdir = changes_root / dirname
        if not sdir.is_dir():
            result[key] = []
            continue
        pkgs = sorted(
            [p for p in sdir.iterdir() if p.is_dir() and not p.name.startswith(".")],
            key=lambda p: p.name,
        )
        result[key] = pkgs
    return result


def find_package(
    changes_root: Path, query: str, allowed_states: Sequence[str] = ("draft", "active", "paused")
) -> Tuple[Optional[str], Optional[Path], List[Tuple[str, Path]]]:
    matches: List[Tuple[str, Path]] = []
    pkgs_by_state = list_state_packages(changes_root)
    for st in allowed_states:
        for p in pkgs_by_state.get(st, []):
            if p.name == query:
                return st, p, [(st, p)]
            if query in p.name:
                matches.append((st, p))
    if len(matches) == 1:
        return matches[0][0], matches[0][1], matches
    return None, None, matches


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "-", name.strip()).strip("-")
    if not cleaned or cleaned in (".", ".."):
        raise ValueError("功能名称不能为空或非法路径字符")
    return cleaned


def validate_date_str(date_str: str) -> str:
    if not DATE_RE.fullmatch(date_str):
        raise ValueError(f"--date 格式必须为 YYYY-MM-DD，实际收到：{date_str}")
    try:
        dt.date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError(f"--date 不是合法日历日期：{date_str}") from exc
    return date_str


def is_valid_waiver_reason(reason: str) -> bool:
    s = reason.strip().strip("。.!！;；,，")
    if len(s) < 8:
        return False
    if s.lower() in LAZY_WAIVER_PHRASES:
        return False
    if s in ("具体原因", "具体原因（至少6字）", "具体原因（至少8字）"):
        return False
    # 拒绝无信息量重复字符（如 aaaaaaaa / 11111111）
    distinct_chars = {ch for ch in s if not ch.isspace()}
    if len(distinct_chars) < 5:
        return False
    for pat in LAZY_WAIVER_PATTERNS:
        if pat.match(s):
            return False
    return True


def parse_doc_waivers_from_lines(lines: Sequence[str]) -> Tuple[Dict[str, str], List[str]]:
    valid: Dict[str, str] = {}
    invalid: List[str] = []
    for raw_line in lines:
        m = DOC_WAIVER_RE.match(raw_line)
        if not m:
            continue
        raw_key = m.group(1).lower()
        key = CANONICAL_RULE_KEYS.get(raw_key, m.group(1))
        reason = m.group(2).strip()
        if reason in ("具体原因", "具体原因（至少6字）", "具体原因（至少8字）"):
            continue
        if is_valid_waiver_reason(reason):
            valid[key] = reason
        else:
            invalid.append(f"{key}: '{reason}'（理由过于空洞或敷衍，须至少 8 字且说明具体业务/技术依据）")
    return valid, invalid


def parse_doc_waivers_from_files(paths: Sequence[Path]) -> Tuple[Dict[str, str], List[str]]:
    lines: List[str] = []
    for p in paths:
        if p.is_file():
            lines.extend(p.read_text(encoding="utf-8", errors="replace").splitlines())
    return parse_doc_waivers_from_lines(lines)


def parse_doc_waivers_from_diff(
    project_root: Path,
    target_rel_paths: Sequence[str],
    diff_source: str = "working-tree",
    staged: bool = False,
    base_ref: Optional[str] = None,
) -> Tuple[Dict[str, str], List[str]]:
    """无 --package 场景：仅提取本次变更中新增的 waiver 行，杜绝历史 hotfix/活跃包形成永久全局毒丸。"""
    if not target_rel_paths or not is_git_repo(project_root):
        return {}, []
    added_lines: List[str] = []
    if diff_source == "root..HEAD":
        for rel in target_rel_paths:
            fp = project_root / rel
            if fp.is_file():
                added_lines.extend(fp.read_text(encoding="utf-8", errors="replace").splitlines())
        return parse_doc_waivers_from_lines(added_lines)

    if diff_source == "HEAD~1..HEAD":
        _, out, _ = run_git(project_root, ["diff", "-U0", "HEAD~1", "HEAD", "--", *target_rel_paths])
    elif staged:
        _, out, _ = run_git(project_root, ["diff", "--cached", "-U0", "--", *target_rel_paths])
    elif base_ref and commit_exists(project_root, base_ref):
        _, out, _ = run_git(project_root, ["diff", "-U0", base_ref, "--", *target_rel_paths])
    else:
        _, out1, _ = run_git(project_root, ["diff", "-U0", "--", *target_rel_paths])
        _, out2, _ = run_git(project_root, ["diff", "--cached", "-U0", "--", *target_rel_paths])
        out = out1 + "\n" + out2

    for line in out.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])

    # 兼容未跟踪的新建进展文件
    if diff_source not in ("HEAD~1..HEAD", "staged (--cached)"):
        _, untracked, _ = run_git(project_root, ["ls-files", "--others", "--exclude-standard", "--", *target_rel_paths])
        for u in untracked.splitlines():
            up = project_root / u.strip()
            if up.is_file():
                added_lines.extend(up.read_text(encoding="utf-8", errors="replace").splitlines())

    return parse_doc_waivers_from_lines(added_lines)


def parse_artifact_waiver(path: Path, kind: str) -> Optional[str]:
    if not path.is_file():
        return None
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ARTIFACT_WAIVER_RE.match(raw_line)
        if not m:
            continue
        if m.group(1).lower() == kind.lower():
            reason = m.group(2).strip()
            if reason in ("具体原因", "具体原因（至少6字）", "具体原因（至少8字）"):
                continue
            if is_valid_waiver_reason(reason):
                return reason
    return None


def read_base_commit(pkg_dir: Path) -> str:
    prog = pkg_dir / "02-进展.md"
    if not prog.is_file():
        return ""
    m = BASE_COMMIT_RE.search(prog.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else ""


def read_package_type(pkg_dir: Path) -> str:
    review_doc = pkg_dir / "04-审查.md"
    has_review_marker = False
    if review_doc.is_file():
        m = PACKAGE_TYPE_RE.search(review_doc.read_text(encoding="utf-8", errors="replace"))
        if m and m.group(1).lower() == "review":
            has_review_marker = True
    if not has_review_marker:
        return "feature"

    # 防止普通功能包在 04-审查.md 伪造 review 标记一键绕过全部产物与静态同步门禁
    feature_only_items = [
        name for name in ("01-方案.md", "02-进展.md", "03-测试.md", "ops")
        if (pkg_dir / name).exists()
    ]
    if feature_only_items:
        raise GateConfigError(
            f"检测到标准功能包 `{pkg_dir.name}` 含功能包文件（{', '.join(feature_only_items)}）"
            "却写入了 `godkey-package-type: review` 标记；禁止伪造独立审查包绕过归档门禁！"
        )
    return "review"


def is_test_path(rel_posix: str) -> bool:
    parts = [p.lower() for p in Path(rel_posix).parts]
    fname = parts[-1] if parts else ""
    if any(p in {"test", "tests", "__tests__", "spec", "specs", "evals"} for p in parts[:-1]):
        return True
    if fname.startswith("test_") or "_test." in fname or ".test." in fname or ".spec." in fname:
        return True
    return False


def matches_hints(rel_posix: str, hints: Sequence[str]) -> bool:
    """支持 glob 通配符、目录段匹配与文件名匹配。"""
    low = rel_posix.lower()
    parts = [p.lower() for p in Path(rel_posix).parts]
    fname = parts[-1] if parts else ""
    for h in hints:
        hl = h.lower().strip()
        if not hl:
            continue
        if "/" in hl:
            if fnmatch.fnmatch(low, hl) or fnmatch.fnmatch(low, f"*/{hl}") or hl in low:
                return True
        elif any(ch in hl for ch in "*?[]"):
            if fnmatch.fnmatch(fname, hl) or any(fnmatch.fnmatch(part, hl) for part in parts):
                return True
        else:
            if hl in parts or hl == fname:
                return True
    return False


def module_dir_of(rel_posix: str) -> str:
    """只对父目录计算模块目录，绝不把文件名当目录。"""
    parent_parts = Path(rel_posix).parent.parts
    if not parent_parts or parent_parts == (".",):
        return ""
    if len(parent_parts) >= 2:
        return "/".join(parent_parts[:2])
    return parent_parts[0]


def parse_name_status(raw: str) -> List[ChangedEntry]:
    entries: List[ChangedEntry] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0].strip()
        if code.startswith(("R", "C")) and len(parts) >= 3:
            entries.append(ChangedEntry(status=code[0], path=parts[2].strip(), old_path=parts[1].strip()))
        else:
            entries.append(ChangedEntry(status=code[0], path=parts[1].strip()))
    return entries


def merge_entries(all_entries: Sequence[ChangedEntry]) -> List[ChangedEntry]:
    by_path: Dict[str, ChangedEntry] = {}
    for e in all_entries:
        if e.path not in by_path or e.status in ("R", "C", "A"):
            by_path[e.path] = e
    return sorted(by_path.values(), key=lambda x: x.path)


def matching_static_template(mode: str, doc_root_rel: str, rel_posix: str) -> Optional[Path]:
    prefix = f"{doc_root_rel}/" if doc_root_rel and doc_root_rel != "." else ""
    sub = rel_posix[len(prefix):] if prefix and rel_posix.startswith(prefix) else rel_posix
    direct = TEMPLATES_ROOT / mode / sub
    if direct.is_file():
        return direct
    if mode == "full" and sub.startswith("04-功能设计/") and sub.endswith(".md"):
        mod_tpl = TEMPLATES_ROOT / "full" / "04-功能设计" / "_模块设计模板.md"
        if mod_tpl.is_file():
            return mod_tpl
    return None


def has_non_whitespace_change(
    project_root: Path,
    rel_posix: str,
    status: str,
    diff_source: str = "working-tree",
    mode: str = "full",
    doc_root_rel: str = "doc",
    staged: bool = False,
    base_ref: Optional[str] = None,
) -> bool:
    """校验静态文档是否确有实质内容变更（排除删除、纯空行与原样复制空模板）。"""
    if status == "D":
        return False

    if status in ("A", "?", "R", "C") or diff_source == "root..HEAD":
        p = project_root / rel_posix
        if not p.is_file():
            return True
        tpl = matching_static_template(mode, doc_root_rel, rel_posix)
        if tpl is not None:
            return bool(meaningful_added_lines(p, tpl))
        return bool(strip_template_noise(p.read_text(encoding="utf-8", errors="replace")))

    if diff_source == "HEAD~1..HEAD":
        _, out, _ = run_git(project_root, ["diff", "-w", "--ignore-blank-lines", "HEAD~1", "HEAD", "--", rel_posix])
    elif staged:
        _, out, _ = run_git(project_root, ["diff", "--cached", "-w", "--ignore-blank-lines", "--", rel_posix])
    elif base_ref and commit_exists(project_root, base_ref):
        _, out, _ = run_git(project_root, ["diff", "-w", "--ignore-blank-lines", base_ref, "--", rel_posix])
    else:
        _, o1, _ = run_git(project_root, ["diff", "-w", "--ignore-blank-lines", "--", rel_posix])
        _, o2, _ = run_git(project_root, ["diff", "--cached", "-w", "--ignore-blank-lines", "--", rel_posix])
        out = o1 + o2

    for line in out.splitlines():
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            if line[1:].strip():
                return True
    return False


def collect_changed_files(
    project_root: Path,
    staged: bool = False,
    base_ref: Optional[str] = None,
) -> Tuple[str, List[ChangedEntry], Optional[str], bool]:
    """返回 (diff_source_label, entries, tree_baseline_ref, is_root_head_diff)。"""
    if not is_git_repo(project_root):
        return "non-git", [], None, False

    if staged:
        _, out, _ = run_git(project_root, ["diff", "--cached", "--name-status"])
        baseline = "HEAD" if commit_exists(project_root, "HEAD") else None
        return "staged (--cached)", merge_entries(parse_name_status(out)), baseline, False

    if base_ref and commit_exists(project_root, base_ref):
        _, out, _ = run_git(project_root, ["diff", "--name-status", base_ref])
        entries = parse_name_status(out)
        _, untracked, _ = run_git(project_root, ["ls-files", "--others", "--exclude-standard"])
        for u in untracked.splitlines():
            u = u.strip()
            if u:
                entries.append(ChangedEntry(status="?", path=u))
        return f"base {base_ref}..working-tree", merge_entries(entries), base_ref, False

    # 工作区（暂存 + 未暂存 + 未跟踪）
    entries: List[ChangedEntry] = []
    for diff_args in (["diff", "--name-status"], ["diff", "--cached", "--name-status"]):
        _, out, _ = run_git(project_root, diff_args)
        entries.extend(parse_name_status(out))
    _, untracked, _ = run_git(project_root, ["ls-files", "--others", "--exclude-standard"])
    for u in untracked.splitlines():
        u = u.strip()
        if u:
            entries.append(ChangedEntry(status="?", path=u))

    if entries:
        baseline = "HEAD" if commit_exists(project_root, "HEAD") else None
        return "working-tree", merge_entries(entries), baseline, False

    # 工作区干净时：优先比对 HEAD~1..HEAD；若仅有首个根提交则用 diff-tree --root HEAD
    if commit_exists(project_root, "HEAD~1"):
        _, out, _ = run_git(project_root, ["diff", "--name-status", "HEAD~1", "HEAD"])
        return "HEAD~1..HEAD", merge_entries(parse_name_status(out)), "HEAD~1", False
    if commit_exists(project_root, "HEAD"):
        _, out, _ = run_git(project_root, ["diff-tree", "--no-commit-id", "--name-status", "-r", "--root", "HEAD"])
        return "root..HEAD", merge_entries(parse_name_status(out)), None, True

    return "working-tree (clean)", [], None, False


def doc_rule_satisfied(static_changed: Sequence[str], doc_root_rel: str, targets: Sequence[str]) -> bool:
    prefix = f"{doc_root_rel}/" if doc_root_rel and doc_root_rel != "." else ""
    for rel in static_changed:
        sub = rel[len(prefix):] if prefix and rel.startswith(prefix) else rel
        for t in targets:
            t_norm = t.strip("/")
            if sub == t_norm or sub.startswith(f"{t_norm}/"):
                return True
    return False


def has_substantive_artifact(actual_path: Path, template_path: Path) -> Tuple[bool, str]:
    """对抗弱模型把占位符机械替换成 2 字敷衍：检查实质行数、总字数与残留 [待填写] 数量。"""
    if not actual_path.is_file():
        return False, f"缺少必需文件：{actual_path.name}"
    text = actual_path.read_text(encoding="utf-8", errors="replace")
    remaining_todos = text.count("[待填写")
    added = meaningful_added_lines(actual_path, template_path)
    added_chars = sum(len(re.sub(r"\s+", "", ln)) for ln in added)
    if len(added) < 2 or added_chars < 24:
        return False, f"{actual_path.name} 实质内容过少（有效新增 {len(added)} 行 / {added_chars} 字），请完整填写"
    if remaining_todos >= 4:
        return False, f"{actual_path.name} 仍残留 {remaining_todos} 处 `[待填写]` 占位符，请清理或补全"
    return True, ""


def deploy_notes_has_real_changes(deploy_notes_path: Path) -> bool:
    tpl_deploy = TEMPLATES_ROOT / "change-package" / "ops" / "deploy-notes.md"
    added = meaningful_added_lines(deploy_notes_path, tpl_deploy)
    real = [
        ln for ln in added
        if not (NOOP_OPS_LINE_RE.match(ln) and not OPS_REAL_SIGNAL_RE.search(ln))
    ]
    return bool(real)


# ---------------------------------------------------------------------------
# Subcommand: init
# ---------------------------------------------------------------------------
def cmd_init(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    profile = args.profile
    tpl_dir = TEMPLATES_ROOT / profile
    if not tpl_dir.is_dir():
        print(f"❌ 未找到模板目录：{tpl_dir}", file=sys.stderr)
        return 1

    doc_target = args.doc_root or args.doc_dir or "doc"
    target_root = Path(doc_target)
    if not target_root.is_absolute():
        target_root = (project_root / target_root).resolve()
    if not is_path_within(target_root, project_root):
        print(f"❌ 目标文档目录必须位于项目根目录内：{target_root}", file=sys.stderr)
        return 1

    created: List[str] = []
    skipped: List[str] = []

    for src in sorted(tpl_dir.rglob("*")):
        rel = src.relative_to(tpl_dir)
        dst = target_root / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not args.force:
            skipped.append(rel.as_posix())
            continue
        shutil.copy2(src, dst)
        created.append(rel.as_posix())

    print(f"PASS: 已初始化文档体系（profile={profile}）-> {target_root}")
    print(f"  新建/写入：{len(created)} 个文件")
    if skipped:
        print(f"  已存在跳过：{len(skipped)} 个文件（如需覆盖请加 --force）")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: audit
# ---------------------------------------------------------------------------
def cmd_audit(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, extras = discover_project_doc(project_root, args.doc_root)

    print("=== GodKey 文档体系审计 ===")
    print(f"项目根目录：{project_root}")
    print(f"识别模式：{mode}")

    if mode == "uninitialized":
        print("文档目录：未检测到文档体系，且目录无既有源码。")
        print("建议动作：询问用户选择完整版（full）或简化版（lite），随后执行：")
        print(f"  python \"{Path(__file__).resolve()}\" init --profile full|lite --project-root \"{project_root}\"")
        return 0

    if mode == "external":
        existing_docs: List[str] = []
        for name in ("README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "docs", "doc"):
            if (project_root / name).exists():
                existing_docs.append(name)
        print("文档目录：未检测到 GodKey 文档体系，自动进入【外部/已有项目模式（external）】。")
        print(f"已有项目文档：{', '.join(existing_docs) if existing_docs else '（无顶层常见文档）'}")
        print("执行策略：不向仓库强塞文档目录；完整执行防幻觉工程纪律，并同步项目既有文档。")
        return 0

    assert doc_root is not None and cfg is not None
    print(f"文档目录：{doc_root}")
    if extras:
        extra_str = ", ".join(p.name for p in extras)
        print(f"⚠️ 检测到多个候选文档目录（其余：{extra_str}），如需切换请显式传 `--doc-root <目录>`。")

    print("\n--- 静态真相层 ---")
    items = FULL_STATIC_ITEMS if mode == "full" else LITE_STATIC_ITEMS
    tpl_root = TEMPLATES_ROOT / mode
    for item in items:
        is_spec = item in ("06-开发规范", "03-开发规范.md")
        status = inspect_static_item(doc_root / item, tpl_root / item, is_default_spec=is_spec)
        print(f"  {item:<16} [{status}]")

    changes_dir_name = cfg["changesDir"]
    changes_root = doc_root / changes_dir_name
    doc_root_rel = to_posix_rel(doc_root, project_root)
    local_only_tag = ""
    if doc_root_rel is not None:
        changes_rel = f"{doc_root_rel}/{changes_dir_name}".strip("/")
        if is_active_progress_local_only(project_root, changes_rel) or is_hotfix_local_only(
            project_root, f"{changes_rel}/hotfix记录.md"
        ):
            local_only_tag = " [本地保留，已被 .gitignore 忽略]"
    print(f"\n--- 动态变更层（{changes_dir_name}/）{local_only_tag} ---")
    if not changes_root.is_dir():
        print("  ❌ 动态变更目录缺失")
        return 1

    pkgs = list_state_packages(changes_root)
    for key in ("draft", "active", "paused"):
        label = STATE_DIRS[key]
        names = [p.name for p in pkgs[key]]
        print(f"  {label}/ ({len(names)})" + (": " + ", ".join(names) if names else ": （空）"))

    archived = pkgs["archive"]
    recent = [p.name for p in archived[-3:]]
    print(f"  {STATE_DIRS['archive']}/ ({len(archived)})" + (f" — 最近：{', '.join(recent)}" if recent else ": （空）"))

    hotfix_file = changes_root / "hotfix记录.md"
    print(f"  hotfix记录.md: {'存在' if hotfix_file.is_file() else '❌ 缺失'}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: new
# ---------------------------------------------------------------------------
def cmd_new(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"❌ 当前项目模式为 '{mode}'，无法新建功能包。请先运行 init。", file=sys.stderr)
        return 1

    state_key = STATE_ALIASES.get(args.state.lower())
    if state_key not in ("draft", "active"):
        print("❌ 新建功能包仅允许初始状态为 draft（01-待确认）或 active（02-进行中）。", file=sys.stderr)
        return 1

    try:
        feature_name = sanitize_name(args.name)
        date_part = validate_date_str(args.date) if args.date else today_str()
    except ValueError as exc:
        print(f"❌ 参数非法：{exc}", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]

    # 防止在未归档状态里重复建立同名功能包
    for st in ("draft", "active", "paused"):
        for p in list_state_packages(changes_root).get(st, []):
            if p.name.endswith(f"_{feature_name}") or p.name == f"{date_part}_{feature_name}":
                print(
                    f"❌ 已存在未归档的同名功能包：{STATE_DIRS[st]}/{p.name}。"
                    "请复用或先归档/搁置该包。",
                    file=sys.stderr,
                )
                return 1

    # 避开同日已归档同名碰撞（自动递增 -2, -3...）
    base_folder = f"{date_part}_{feature_name}"
    folder_name = base_folder
    archive_dir = changes_root / STATE_DIRS["archive"]
    seq = 2
    while (archive_dir / folder_name).exists():
        folder_name = f"{base_folder}-{seq}"
        seq += 1

    state_root = changes_root / STATE_DIRS[state_key]
    target_dir = (state_root / folder_name).resolve()
    if not is_path_within(target_dir, state_root):
        print(f"❌ 非法目标路径（疑似路径穿越）：{target_dir}", file=sys.stderr)
        return 1

    tpl_pkg = TEMPLATES_ROOT / "change-package"
    base_commit = get_head_commit(project_root)

    replacements = {
        "{{FEATURE_NAME}}": args.name.strip(),
        "{{DATE}}": date_part,
        "{{BASE_COMMIT}}": base_commit or "none",
        "{{PACKAGE_DIR}}": f"{STATE_DIRS[state_key]}/{folder_name}",
    }

    if args.type == "review":
        target_dir.mkdir(parents=True, exist_ok=True)
        review_src = tpl_pkg / "04-审查.md"
        content = review_src.read_text(encoding="utf-8")
        for k, v in replacements.items():
            content = content.replace(k, v)
        content = f"<!-- godkey-package-type: review -->\n{content}"
        (target_dir / "04-审查.md").write_text(content, encoding="utf-8")
        print(f"PASS: 已创建独立审查包 -> {target_dir}")
        return 0

    for src in sorted(tpl_pkg.rglob("*")):
        rel = src.relative_to(tpl_pkg)
        dst = target_dir / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        content = src.read_text(encoding="utf-8")
        for k, v in replacements.items():
            content = content.replace(k, v)
        dst.write_text(content, encoding="utf-8")

    print(f"PASS: 已创建功能包 -> {target_dir}")
    if base_commit:
        print(f"  记录基线提交（godkey-base-commit）：{base_commit}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: move
# ---------------------------------------------------------------------------
def cmd_move(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"❌ 当前项目模式为 '{mode}'，无法流转功能包。", file=sys.stderr)
        return 1

    target_key = STATE_ALIASES.get(args.target.lower())
    if target_key == "archive":
        print("❌ 禁止通过 move 直接归档！请使用 `archive` 子命令通过静态文档同步门禁。", file=sys.stderr)
        return 1
    if target_key not in ("draft", "active", "paused"):
        print("❌ 目标状态必须为 draft / active / paused（或对应中文）。", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]
    cur_state, pkg_dir, matches = find_package(changes_root, args.package)
    if pkg_dir is None or cur_state is None:
        if len(matches) > 1:
            print("❌ 匹配到多个功能包，请指定更完整名称：", file=sys.stderr)
            for st, p in matches:
                print(f"  - {STATE_DIRS[st]}/{p.name}", file=sys.stderr)
        else:
            print(f"❌ 未在未归档目录中找到功能包：{args.package}", file=sys.stderr)
        return 1

    if cur_state == target_key:
        print(f"INFO: 功能包已在 {STATE_DIRS[target_key]}/{pkg_dir.name}，无需移动。")
        return 0

    dest_dir = changes_root / STATE_DIRS[target_key] / pkg_dir.name
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        print(f"❌ 目标路径已存在：{dest_dir}", file=sys.stderr)
        return 1

    shutil.move(str(pkg_dir), str(dest_dir))

    prog = dest_dir / "02-进展.md"
    if prog.is_file():
        reason_suffix = f"（原因：{args.reason}）" if args.reason else ""
        note = f"\n### {now_str()} — 状态流转\n- 变更状态：`{STATE_DIRS[cur_state]}` → `{STATE_DIRS[target_key]}`{reason_suffix}\n"
        with prog.open("a", encoding="utf-8") as fh:
            fh.write(note)

    print(f"PASS: 已流转 `{pkg_dir.name}`：{STATE_DIRS[cur_state]} -> {STATE_DIRS[target_key]}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: hotfix
# ---------------------------------------------------------------------------
def cmd_hotfix(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"❌ 当前项目模式为 '{mode}'，无法写入 hotfix记录.md。", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]
    hotfix_path = changes_root / "hotfix记录.md"
    hotfix_path.parent.mkdir(parents=True, exist_ok=True)
    if not hotfix_path.exists():
        hotfix_path.write_text("# Hotfix 小修台账\n\n---\n", encoding="utf-8")

    files_list = [f.strip() for f in args.files.split(",") if f.strip()]
    files_md = "、".join(f"`{f}`" for f in files_list) if files_list else "（未指定）"
    entry = (
        f"\n## {today_str()} — {args.title.strip()}\n"
        f"- **症状**：{args.symptom.strip()}\n"
        f"- **根因**：{args.root_cause.strip()}\n"
        f"- **涉及文件**：{files_md}\n"
        f"- **验证结果**：{args.verify.strip()}\n"
    )
    with hotfix_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)

    print(f"PASS: 已追加 Hotfix 记录 -> {hotfix_path}")
    return 0


# ---------------------------------------------------------------------------
# Core check-sync engine
# ---------------------------------------------------------------------------
def evaluate_sync(
    project_root: Path,
    doc_root: Optional[Path],
    mode: str,
    cfg: Optional[Dict],
    package_dir: Optional[Path] = None,
    staged: bool = False,
    base_ref: Optional[str] = None,
    gate_mode: str = "archive",
) -> Tuple[bool, List[str], List[str], List[str]]:
    """返回 (passed, info_lines, warning_lines, failure_lines)。"""
    infos: List[str] = []
    warnings: List[str] = []
    failures: List[str] = []

    if not is_git_repo(project_root):
        infos.append(f"检查模式：{gate_mode} | 项目模式：{mode} | 变更来源：non-git")
        warnings.append("非 Git 仓库：无法通过 Git Diff 自动校验静态文档同步，请人工核对静态真相文档已更新。")
        return True, infos, warnings, failures

    effective_base = base_ref
    if not staged and not effective_base and package_dir is not None:
        recorded = read_base_commit(package_dir)
        if recorded:
            if commit_exists(project_root, recorded):
                effective_base = recorded
            else:
                warnings.append(
                    f"功能包记录的基线提交 `{recorded}` 在当前 Git 历史中不存在（可能经历过 rebase/amend），"
                    "将回退检查工作区/最近提交，建议显式传入 `--base <commit>`。"
                )

    diff_source, entries, tree_baseline, is_root_head = collect_changed_files(
        project_root, staged=staged, base_ref=effective_base
    )
    infos.append(f"检查模式：{gate_mode} | 项目模式：{mode} | 变更来源：{diff_source}（共 {len(entries)} 个文件）")

    if diff_source == "HEAD~1..HEAD" and not package_dir and not base_ref:
        warnings.append("工作区干净，仅检查了最近 1 次提交（HEAD~1..HEAD）；跨提交检查请传 `--package` 或 `--base`。")

    if mode == "external":
        code_files = [
            e.path for e in entries
            if Path(e.path).suffix.lower() in DEFAULT_CODE_EXTS and not is_test_path(e.path)
        ]
        md_files = [e.path for e in entries if e.path.lower().endswith(".md") and e.status != "D"]
        if code_files and not md_files:
            warnings.append(
                f"外部项目模式：检测到 {len(code_files)} 个代码文件变更，未检测到 Markdown 文档同步；请确认是否需要更新原仓库 README/docs。"
            )
        return True, infos, warnings, failures

    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        warnings.append(f"项目模式为 '{mode}'，跳过静态同步门禁。")
        return True, infos, warnings, failures

    doc_root_rel = to_posix_rel(doc_root, project_root)
    if doc_root_rel is None:
        failures.append(f"文档目录不在项目根目录下：{doc_root}")
        return False, infos, warnings, failures

    changes_rel = f"{doc_root_rel}/{cfg['changesDir']}".strip("/")
    hotfix_rel = f"{changes_rel}/hotfix记录.md"
    changes_root = doc_root / cfg["changesDir"]
    hotfix_local_only = is_hotfix_local_only(project_root, hotfix_rel)
    active_local_only = is_active_progress_local_only(project_root, changes_rel, package_dir)
    if hotfix_local_only or active_local_only:
        scope_parts = []
        if active_local_only:
            scope_parts.append("活跃功能包")
        if hotfix_local_only:
            scope_parts.append("hotfix记录.md")
        infos.append(f"提示：动态变更目录（{'/'.join(scope_parts)}）已被 .gitignore 忽略且未纳入 Git，动态记录将回退本地磁盘核验。")
    hints = cfg.get("codePathHints", {})
    sync_rules = cfg.get("staticSyncRules", {})

    static_docs_changed: List[str] = []
    dynamic_docs_changed: List[str] = []
    code_files: List[str] = []
    test_files: List[str] = []
    db_triggers: List[str] = []
    ops_triggers: List[str] = []
    arch_triggers: List[str] = []
    added_code_paths: List[str] = []
    dynamic_waiver_candidates: List[str] = []

    for entry in entries:
        rel = entry.path
        if rel == f"{doc_root_rel}/.godkey.json":
            continue

        if rel == changes_rel or rel.startswith(f"{changes_rel}/"):
            if entry.status != "D":
                dynamic_docs_changed.append(rel)
                if rel.endswith("/02-进展.md") or rel == hotfix_rel:
                    dynamic_waiver_candidates.append(rel)
            continue

        if rel == doc_root_rel or rel.startswith(f"{doc_root_rel}/"):
            fname = Path(rel).name
            if entry.status == "D":
                warnings.append(f"静态文档被删除（不计入文档同步）：{rel}")
                continue
            if fname.startswith("_") or fname == ".gitkeep":
                continue
            if not has_non_whitespace_change(
                project_root,
                rel,
                entry.status,
                diff_source=diff_source,
                mode=mode,
                doc_root_rel=doc_root_rel,
                staged=staged,
                base_ref=effective_base,
            ):
                warnings.append(f"忽略无实质内容/纯空白/空模板静态文档改动：{rel}")
                continue
            static_docs_changed.append(rel)
            continue

        # 业务代码及配置变更检查（同时检查 rename 的新旧路径）
        candidate_paths = [rel] + ([entry.old_path] if entry.old_path else [])
        if all(is_test_path(cp) for cp in candidate_paths):
            test_files.append(rel)
            continue

        for cp in candidate_paths:
            if matches_hints(cp, hints.get("db", [])):
                db_triggers.append(cp)
            if matches_hints(cp, hints.get("ops", [])):
                ops_triggers.append(cp)
            if matches_hints(cp, hints.get("arch", [])):
                arch_triggers.append(cp)

        if any(Path(cp).suffix.lower() in DEFAULT_CODE_EXTS for cp in candidate_paths):
            code_files.append(rel)
            if entry.status in ("A", "?", "R", "C"):
                added_code_paths.append(rel)

    # 检测新增源码顶层模块目录（仅对比父目录，绝不把文件名当目录）
    if tree_baseline and commit_exists(project_root, tree_baseline) and added_code_paths:
        _, tree_out, _ = run_git(project_root, ["ls-tree", "-r", "--name-only", tree_baseline])
        existing_dirs_before: Set[str] = set()
        for f in tree_out.splitlines():
            mod = module_dir_of(f.strip())
            if mod:
                existing_dirs_before.add(mod)
        for af in added_code_paths:
            mod = module_dir_of(af)
            if mod and mod not in existing_dirs_before:
                arch_triggers.append(f"新增模块目录:{mod}")

    # 检查指定功能包 ops/ 内的动态 SQL / 脚本 / 实质上线配置变更
    if package_dir is not None and (package_dir / "ops").is_dir():
        for ops_file in sorted((package_dir / "ops").rglob("*")):
            if not ops_file.is_file() or ops_file.name == ".gitkeep":
                continue
            if ops_file.name == "deploy-notes.md":
                if deploy_notes_has_real_changes(ops_file):
                    ops_triggers.append(f"ops/{ops_file.name}（已填写上线配置变更）")
            elif ops_file.suffix.lower() == ".sql":
                db_triggers.append(f"ops/{ops_file.name}")
            else:
                ops_triggers.append(f"ops/{ops_file.name}")

    # 去重
    db_triggers = sorted(set(db_triggers))
    ops_triggers = sorted(set(ops_triggers))
    arch_triggers = sorted(set(arch_triggers))

    # 解析豁免声明：传 --package 时仅读该包 02-进展.md；否则仅读本次 diff 新增行（防永久毒丸）
    if package_dir is not None:
        waivers, invalid_waivers = parse_doc_waivers_from_files([package_dir / "02-进展.md"])
    else:
        waivers, invalid_waivers = parse_doc_waivers_from_diff(
            project_root,
            dynamic_waiver_candidates,
            diff_source=diff_source,
            staged=staged,
            base_ref=effective_base,
        )

    for bad in invalid_waivers:
        failures.append(f"无效豁免声明：{bad}")

    infos.append(
        f"改动分类：源码={len(code_files)} | 测试={len(test_files)} | 静态文档={len(static_docs_changed)} | 动态记录={len(dynamic_docs_changed)}"
    )

    # hotfix 专用模式：核验仅改 <= 1 个业务文件、已记 hotfix记录.md、且未触及 DB/运维/架构变更
    if gate_mode == "hotfix":
        if len(code_files) > 1:
            failures.append(
                f"Hotfix 门禁拒绝：检测到 {len(code_files)} 个业务代码文件改动（{', '.join(code_files[:5])}），"
                "超出单文件小修上限，请走标准功能包流程。"
            )
        if db_triggers or ops_triggers or arch_triggers:
            trig = db_triggers + ops_triggers + arch_triggers
            failures.append(
                f"Hotfix 门禁拒绝：检测到数据库/运维/架构级变更（{', '.join(trig[:5])}），"
                "Hotfix 仅限不改变架构与表结构的局部修复，请走标准功能包。"
            )
        if code_files and hotfix_rel not in dynamic_docs_changed:
            if hotfix_local_only:
                ok_local, detail = has_local_hotfix_for_files(
                    changes_root / "hotfix记录.md",
                    code_files,
                    check_recent_date=(diff_source != "HEAD~1..HEAD"),
                )
                if ok_local:
                    infos.append(f"  ✅ Hotfix 台账（本地磁盘核验）：{detail}")
                else:
                    failures.append(
                        f"Hotfix 门禁拒绝：{detail}；请先运行 `godkey_gate.py hotfix` 记录本次改动。"
                    )
            else:
                failures.append(f"Hotfix 门禁拒绝：代码已改动但未更新 `{hotfix_rel}`，请先运行 `godkey_gate.py hotfix` 记录。")
        return len(failures) == 0, infos, warnings, failures

    if not code_files and not db_triggers and not ops_triggers and not arch_triggers:
        infos.append("未检测到需触发静态文档同步的代码/DB/运维改动。")
        return len(failures) == 0, infos, warnings, failures

    # commit 模式：WIP 友好，但要求至少有进展/hotfix 记录或静态文档更新
    if gate_mode == "commit":
        has_any_doc = bool(static_docs_changed or dynamic_docs_changed)
        if not has_any_doc and (active_local_only or hotfix_local_only):
            local_progs = find_local_active_progress(project_root, changes_root, package_dir) if active_local_only else []
            if local_progs:
                has_any_doc = True
                infos.append(
                    f"  ✅ 动态进展（本地磁盘核验）：命中已填写进展的活跃功能包 {', '.join(local_progs)}"
                )
            elif hotfix_local_only and len(code_files) <= 1 and not db_triggers and not ops_triggers and not arch_triggers:
                ok_hf, detail_hf = has_local_hotfix_for_files(
                    changes_root / "hotfix记录.md",
                    code_files,
                    check_recent_date=(diff_source != "HEAD~1..HEAD"),
                )
                if ok_hf:
                    has_any_doc = True
                    infos.append(f"  ✅ Hotfix 台账（本地磁盘核验）：{detail_hf}")
        if not has_any_doc:
            if active_local_only or hotfix_local_only:
                failures.append(
                    "代码已修改，静态文档未更新，且本地被 .gitignore 忽略的动态目录中未检测到已填写实质进展的活跃功能包"
                    "（02-进行中/*/02-进展.md）或匹配本次改动的 hotfix记录.md。请先记录本次迭代进展再提交。"
                )
            else:
                failures.append(
                    "代码已修改但未更新任何进展记录（02-进展.md / hotfix记录.md）或静态文档。"
                    "请先记录本次迭代进展再提交。"
                )
        else:
            pending: List[str] = []
            if code_files and not doc_rule_satisfied(static_docs_changed, doc_root_rel, sync_rules.get("featureDocs", [])):
                pending.extend(sync_rules.get("featureDocs", []))
            if db_triggers and not doc_rule_satisfied(static_docs_changed, doc_root_rel, sync_rules.get("dbDocs", [])):
                pending.extend(sync_rules.get("dbDocs", []))
            if ops_triggers and not doc_rule_satisfied(static_docs_changed, doc_root_rel, sync_rules.get("opsDocs", [])):
                pending.extend(sync_rules.get("opsDocs", []))
            if arch_triggers and not doc_rule_satisfied(static_docs_changed, doc_root_rel, sync_rules.get("archDocs", [])):
                pending.extend(sync_rules.get("archDocs", []))
            if pending:
                uniq = sorted(set(pending))
                warnings.append(f"WIP 提交放行；归档前须同步静态文档：{', '.join(uniq)}")
        return len(failures) == 0, infos, warnings, failures

    # archive / strict 模式：逐类强制校验静态文档同步
    checks = [
        ("featureDocs", "功能设计蓝图", bool(code_files), code_files[:5]),
        ("dbDocs", "数据库表结构快照", bool(db_triggers), db_triggers[:5]),
        ("opsDocs", "部署与环境配置", bool(ops_triggers), ops_triggers[:5]),
        ("archDocs", "系统架构与技术选型", bool(arch_triggers), arch_triggers[:5]),
    ]

    if package_dir is not None:
        waiver_where = "当前功能包 `02-进展.md`"
    elif active_local_only or hotfix_local_only:
        waiver_where = "对应功能包 `02-进展.md`（动态目录被 .gitignore 忽略时须显式传 `--package <功能包>` 读取豁免）"
    else:
        waiver_where = "本次改动记录（如 `02-进展.md`）"

    for rule_key, label, triggered, evidence in checks:
        if not triggered:
            continue
        targets = sync_rules.get(rule_key, [])
        if doc_rule_satisfied(static_docs_changed, doc_root_rel, targets):
            infos.append(f"  ✅ {label}（{', '.join(targets)}）：已检测到静态文档同步")
        elif rule_key in waivers:
            warnings.append(f"  ⚠️ WAIVED [{rule_key} / {label}]：{waivers[rule_key]}")
        else:
            failures.append(
                f"{rule_key} 未同步（{label}）：检测到 {', '.join(evidence)} 发生变更，"
                f"但静态真相目标 {', '.join(targets)} 无实质更新。"
                f"请更新对应静态文档，或如确不影响蓝图则在{waiver_where}中写明可审计豁免："
                f"`<!-- doc-sync-waiver: {rule_key} | 具体原因（至少8字） -->`"
            )

    return len(failures) == 0, infos, warnings, failures


# ---------------------------------------------------------------------------
# Subcommand: check-sync
# ---------------------------------------------------------------------------
def cmd_check_sync(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)

    pkg_dir: Optional[Path] = None
    if args.package and doc_root is not None and cfg is not None:
        changes_root = doc_root / cfg["changesDir"]
        _, pkg_dir, _ = find_package(changes_root, args.package)
        if pkg_dir is None:
            print(f"❌ 未找到指定功能包：{args.package}", file=sys.stderr)
            return 1

    passed, infos, warnings, failures = evaluate_sync(
        project_root=project_root,
        doc_root=doc_root,
        mode=mode,
        cfg=cfg,
        package_dir=pkg_dir,
        staged=args.staged,
        base_ref=args.base,
        gate_mode=args.mode,
    )

    for line in infos:
        print(line)
    for line in warnings:
        print(line)
    for line in failures:
        print(f"❌ {line}", file=sys.stderr)

    if passed:
        print("CHECK-SYNC PASS")
        return 0
    print("CHECK-SYNC FAIL（门禁校验未通过）", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Subcommand: archive
# ---------------------------------------------------------------------------
def cmd_archive(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"❌ 当前项目模式为 '{mode}'，无法执行归档门禁。", file=sys.stderr)
        return 1

    if args.skip_git and is_git_repo(project_root):
        print("❌ 当前目录为 Git 仓库，禁止使用 `--skip-git` 绕过静态文档同步门禁！", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]
    cur_state, pkg_dir, matches = find_package(changes_root, args.package, allowed_states=("draft", "active", "paused"))
    if pkg_dir is None or cur_state is None:
        if len(matches) > 1:
            print("❌ 匹配到多个功能包，请指定更完整名称：", file=sys.stderr)
            for st, p in matches:
                print(f"  - {STATE_DIRS[st]}/{p.name}", file=sys.stderr)
        else:
            print(f"❌ 未找到待归档的功能包：{args.package}", file=sys.stderr)
        return 1

    if cur_state != "active":
        print(
            f"❌ 功能包当前位于 `{STATE_DIRS[cur_state]}/`，仅允许从 `{STATE_DIRS['active']}/` 归档。"
            "如需归档请先用 `move` 流转至进行中。",
            file=sys.stderr,
        )
        return 1

    tpl_pkg = TEMPLATES_ROOT / "change-package"
    pkg_type = read_package_type(pkg_dir)
    artifact_errors: List[str] = []
    artifact_notes: List[str] = []

    if pkg_type == "review":
        ok, err = has_substantive_artifact(pkg_dir / "04-审查.md", tpl_pkg / "04-审查.md")
        if not ok:
            print(f"❌ 独立审查包归档失败：{err}", file=sys.stderr)
            return 1
        print("  ✅ 独立审查包 04-审查.md：已填写实质审查报告")
    else:
        # 1) 必选产物：01-方案.md 与 02-进展.md
        for req_name in ("01-方案.md", "02-进展.md"):
            ok, err = has_substantive_artifact(pkg_dir / req_name, tpl_pkg / req_name)
            if not ok:
                artifact_errors.append(err)

        # 2) 测试与审查产物：实质填写或显式可审计豁免
        for opt_name, waiver_kind in (("03-测试.md", "test"), ("04-审查.md", "review")):
            fpath = pkg_dir / opt_name
            if not fpath.is_file():
                artifact_errors.append(f"缺少必需文件：{opt_name}")
                continue
            ok, err = has_substantive_artifact(fpath, tpl_pkg / opt_name)
            waiver = parse_artifact_waiver(fpath, waiver_kind)
            if ok:
                artifact_notes.append(f"  ✅ {opt_name}：已填写")
            elif waiver:
                artifact_notes.append(f"  ⚠️ WAIVED [{waiver_kind} / {opt_name}]：{waiver}")
            else:
                artifact_errors.append(
                    f"{err}，且无有效豁免声明（`<!-- artifact-waiver: {waiver_kind} | 具体原因（至少8字） -->`）"
                )

        if artifact_errors:
            print("=== 归档门禁：功能包产物检查失败 ===", file=sys.stderr)
            for err in artifact_errors:
                print(f"❌ {err}", file=sys.stderr)
            return 1

        for note in artifact_notes:
            print(note)

        # 3) 静态文档同步门禁
        passed, infos, warnings, failures = evaluate_sync(
            project_root=project_root,
            doc_root=doc_root,
            mode=mode,
            cfg=cfg,
            package_dir=pkg_dir,
            staged=False,
            base_ref=args.base,
            gate_mode="archive",
        )
        for line in infos:
            print(line)
        for line in warnings:
            print(line)
        if not passed:
            for line in failures:
                print(f"❌ {line}", file=sys.stderr)
            print("ARCHIVE FAIL：静态文档同步门禁未通过，拒绝迁入 99-已归档/。", file=sys.stderr)
            return 1

    dest_dir = changes_root / STATE_DIRS["archive"] / pkg_dir.name
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        print(f"❌ 归档目标已存在：{dest_dir}", file=sys.stderr)
        return 1

    # 先移动目录，成功后再落盘归档时间戳，避免移动失败留脏记录
    shutil.move(str(pkg_dir), str(dest_dir))

    prog = dest_dir / "02-进展.md"
    if prog.is_file():
        with prog.open("a", encoding="utf-8") as fh:
            fh.write(
                f"\n### {now_str()} — 门禁验收并归档\n"
                f"- 已通过 `godkey_gate.py archive` 校验并迁入 `{STATE_DIRS['archive']}/{pkg_dir.name}`\n"
            )

    print(f"ARCHIVE PASS: `{pkg_dir.name}` 已通过门禁并归档 -> {dest_dir}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: install-hook
# ---------------------------------------------------------------------------
HOOK_MARKER = "# GODKEY-SKILL-MANAGED-HOOK"


def cmd_install_hook(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    if not is_git_repo(project_root):
        print(f"❌ 未检测到 Git 仓库：{project_root}", file=sys.stderr)
        return 1

    code, out, err = run_git(project_root, ["rev-parse", "--git-path", "hooks/pre-commit"])
    if code != 0 or not out.strip():
        print(f"❌ 无法定位 Git hooks 目录：{err.strip()}", file=sys.stderr)
        return 1

    hook_path = Path(out.strip())
    if not hook_path.is_absolute():
        hook_path = (project_root / hook_path).resolve()
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    if hook_path.exists() and not args.force:
        existing = hook_path.read_text(encoding="utf-8", errors="replace")
        if HOOK_MARKER not in existing:
            print(
                f"❌ 已存在自定义 pre-commit hook：{hook_path}。为避免覆盖请先检查或加 --force。",
                file=sys.stderr,
            )
            return 1

    script_posix = Path(__file__).resolve().as_posix()
    doc_root_flag = f' --doc-root "{args.doc_root}"' if args.doc_root else ""
    hook_body = f"""#!/usr/bin/env sh
{HOOK_MARKER}
# 自动校验本次提交是否同步了迭代进展或静态真相文档（跨 Harness 通用）

GATE_SCRIPT="${{GODKEY_GATE_SCRIPT:-{script_posix}}}"
if [ ! -f "$GATE_SCRIPT" ]; then
  echo "[godkey-hook] 未找到校验脚本：$GATE_SCRIPT（可设置 GODKEY_GATE_SCRIPT 环境变量）" >&2
  exit 0
fi

if python3 -c "import sys" >/dev/null 2>&1; then
  PY_CMD="python3"
elif python -c "import sys" >/dev/null 2>&1; then
  PY_CMD="python"
elif py -3 -c "import sys" >/dev/null 2>&1; then
  PY_CMD="py -3"
else
  echo "[godkey-hook] 未找到可用的 Python 3 解释器，跳过检查" >&2
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
$PY_CMD "$GATE_SCRIPT" check-sync --staged --mode {args.mode} --project-root "$REPO_ROOT"{doc_root_flag}
"""
    hook_path.write_text(hook_body, encoding="utf-8", newline="\n")
    try:
        os.chmod(hook_path, 0o755)
    except OSError:
        pass

    print(f"PASS: 已安装 Git pre-commit hook（mode={args.mode}）-> {hook_path}")
    return 0


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="godkey_gate.py",
        description="GodKey Skill 确定性文档审计、变更包状态机与静态同步门禁工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-root", default=".", help="目标项目根目录（默认当前目录）")
        p.add_argument("--doc-root", default=None, help="显式指定文档目录路径（可选，默认自动识别）")

    p_init = sub.add_parser("init", help="初始化 full 或 lite 文档体系模板")
    p_init.add_argument("--profile", choices=("full", "lite"), required=True, help="文档体系档位")
    p_init.add_argument("--doc-root", default=None, help="目标文档目录名（默认 doc，多模块可用 <name>_doc）")
    p_init.add_argument("--doc-dir", default=None, help="--doc-root 的兼容别名")
    p_init.add_argument("--project-root", default=".", help="目标项目根目录")
    p_init.add_argument("--force", action="store_true", help="覆盖已存在文件")
    p_init.set_defaults(func=cmd_init)

    p_audit = sub.add_parser("audit", help="审计静态文档健康度与 4 态变更包清单")
    add_common(p_audit)
    p_audit.set_defaults(func=cmd_audit)

    p_new = sub.add_parser("new", help="在 01-待确认 或 02-进行中 新建标准功能包或独立审查包")
    add_common(p_new)
    p_new.add_argument("name", help="功能包中文/英文短名，如 用户导出Excel")
    p_new.add_argument("--state", default="active", help="初始状态：draft（待确认）或 active（进行中，默认）")
    p_new.add_argument("--type", choices=("feature", "review"), default="feature", help="feature（默认功能包）或 review（独立审查包）")
    p_new.add_argument("--date", default=None, help="覆盖日期前缀（YYYY-MM-DD）")
    p_new.set_defaults(func=cmd_new)

    p_move = sub.add_parser("move", help="在 待确认 / 进行中 / 已搁置 间流转功能包（禁止跳过归档门禁）")
    add_common(p_move)
    p_move.add_argument("package", help="功能包目录名或唯一关键字")
    p_move.add_argument("target", help="目标状态：draft / active / paused")
    p_move.add_argument("--reason", default="", help="流转原因（如搁置原因）")
    p_move.set_defaults(func=cmd_move)

    p_hotfix = sub.add_parser("hotfix", help="向 hotfix记录.md 追加单文件小修记录")
    add_common(p_hotfix)
    p_hotfix.add_argument("--title", required=True, help="小修标题")
    p_hotfix.add_argument("--symptom", required=True, help="问题症状")
    p_hotfix.add_argument("--root-cause", required=True, help="根因分析")
    p_hotfix.add_argument("--files", required=True, help="涉及文件（逗号分隔）")
    p_hotfix.add_argument("--verify", required=True, help="验证方式与结果")
    p_hotfix.set_defaults(func=cmd_hotfix)

    p_check = sub.add_parser("check-sync", help="校验代码/SQL/运维改动是否已同步静态真相文档")
    add_common(p_check)
    p_check.add_argument("--package", default=None, help="指定功能包以读取基线提交与 ops/ 资产")
    p_check.add_argument("--base", default=None, help="显式指定 Git 基线提交（覆盖记录的基线）")
    p_check.add_argument("--staged", action="store_true", help="仅检查 git 暂存区（供 pre-commit hook 使用）")
    p_check.add_argument(
        "--mode",
        choices=("archive", "commit", "strict", "hotfix"),
        default="archive",
        help="archive（完整静态同步校验）/ commit（WIP 提交校验）/ strict（严格提交校验）/ hotfix（单文件小修门禁）",
    )
    p_check.set_defaults(func=cmd_check_sync)

    p_arch = sub.add_parser("archive", help="执行产物检查 + 静态同步门禁，通过后迁入 99-已归档/")
    add_common(p_arch)
    p_arch.add_argument("package", help="位于 02-进行中/ 的功能包目录名或唯一关键字")
    p_arch.add_argument("--base", default=None, help="显式指定 Git 基线提交")
    p_arch.add_argument("--skip-git", action="store_true", help="仅限非 Git 目录跳过 diff 检查（Git 仓库内禁止）")
    p_arch.set_defaults(func=cmd_archive)

    p_hook = sub.add_parser("install-hook", help="在目标 Git 仓库安装跨 Harness 的 pre-commit 校验钩子")
    add_common(p_hook)
    p_hook.add_argument("--mode", choices=("commit", "strict"), default="commit", help="commit（默认 WIP 友好）或 strict（每次提交强制同步静态文档）")
    p_hook.add_argument("--force", action="store_true", help="强制覆盖已有 pre-commit hook")
    p_hook.set_defaults(func=cmd_install_hook)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except GateConfigError as exc:
        print(f"❌ 配置错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
