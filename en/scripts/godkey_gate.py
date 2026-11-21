#!/usr/bin/env python3
"""GodKey Skill — Cross-harness deterministic doc audit, change-package state machine, and static doc sync gate.

Depends solely on the Python 3.8+ standard library. Works on Windows, Linux, and macOS.
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
    "draft": "01-draft",
    "active": "02-active",
    "paused": "03-paused",
    "archive": "99-archive",
}

STATE_ALIASES: Dict[str, str] = {
    "draft": "draft",
    "01-draft": "draft",
    "active": "active",
    "02-active": "active",
    "paused": "paused",
    "03-paused": "paused",
    "shelved": "paused",
    "archive": "archive",
    "archived": "archive",
    "99-archive": "archive",
}

FULL_STATIC_ITEMS: List[str] = [
    "01-product",
    "02-user-guide",
    "03-architecture",
    "04-feature-design",
    "05-database",
    "06-standards",
    "07-deployment",
    "08-assets",
]

LITE_STATIC_ITEMS: List[str] = [
    "01-project-overview.md",
    "02-architecture-and-design.md",
    "03-standards.md",
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
    "none", "n/a", "na", "skip", "no change", "no changes", "no need",
    "not needed", "no update", "no updates", "todo", "tbd", "unchanged",
}

LAZY_WAIVER_PATTERNS: List[re.Pattern] = [
    re.compile(
        r"^(this\s+)?(change|update|fix|task|commit)?\s*(does\s+not|doesn't|do\s+not|no|not|skip)\s+"
        r"(need|require|needs|requires)?\s*(any\s+)?(static\s+)?"
        r"(doc|docs|documentation|blueprint|snapshot|sync|update|updates)"
        r"(\s+(doc|docs|documentation|update|updates|sync|change|changes))*\.?$",
        re.IGNORECASE,
    ),
    re.compile(r"^(no|skip|none)\s+(doc|docs|update|sync|change|changes|need).*$", re.IGNORECASE),
]

NOOP_OPS_LINE_RE = re.compile(
    r"^[-*\d.\s\|]*(no|none|n/a|na|nothing|no\s+special|no\s+new|standard\s+release|standard\s+deploy|regular\s+release|not\s+applicable)",
    re.IGNORECASE,
)
OPS_REAL_SIGNAL_RE = re.compile(r"(=|`|but\s+must|however|still\s+need|\.sql\b|\.py\b|\.sh\b|\.ps1\b)", re.IGNORECASE)

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
        prog_rel = to_posix_rel(package_dir / "02-progress.md", project_root)
        if prog_rel:
            return is_git_ignored(project_root, prog_rel) and not is_git_tracked(project_root, prog_rel)
    probe_rel = f"{changes_rel}/{STATE_DIRS['active']}/_probe/02-progress.md"
    return is_git_ignored(project_root, probe_rel)


HOTFIX_ENTRY_HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*[—\-–]\s*(.+)$")


def parse_hotfix_entries(hotfix_path: Path) -> List[Tuple[str, str]]:
    """Parse hotfix-log.md entries into [(date_str, block_text), ...]."""
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
    """Verify the latest substantive hotfix-log.md entry on disk when gitignored and untracked."""
    entries = parse_hotfix_entries(hotfix_path)
    if not entries:
        return False, f"Local `{hotfix_path.name}` has no valid hotfix entries"

    entry_date, body = entries[-1]
    body_lines = strip_template_noise(body)
    if len(body_lines) < 2:
        return False, f"Latest entry ({entry_date}) in local `{hotfix_path.name}` lacks substantive details"

    if check_recent_date:
        try:
            d = dt.date.fromisoformat(entry_date)
        except ValueError:
            return False, f"Latest entry in local `{hotfix_path.name}` has invalid date ({entry_date})"
        today = dt.date.today()
        if abs((today - d).days) > 1:
            return False, f"Latest entry in local `{hotfix_path.name}` is dated {entry_date} (not today); append a record for this fix"

    missing = [cf for cf in code_files if not _hotfix_body_mentions_file(body, cf)]
    if missing:
        return False, f"Latest entry ({entry_date}) in local `{hotfix_path.name}` does not mention modified file(s): {', '.join(missing)}"

    return True, f"latest entry {entry_date} covers {', '.join(code_files)}"


def find_local_active_progress(
    project_root: Path, changes_root: Path, package_dir: Optional[Path] = None
) -> List[str]:
    """Inspect untracked local active packages for substantive 02-progress.md content when gitignored."""
    tpl_prog = TEMPLATES_ROOT / "change-package" / "02-progress.md"
    candidates: List[Path]
    if package_dir is not None:
        candidates = [package_dir]
    else:
        candidates = list_state_packages(changes_root).get("active", [])

    matched: List[str] = []
    for pkg in candidates:
        prog = pkg / "02-progress.md"
        if not prog.is_file():
            continue
        prog_rel = to_posix_rel(prog, project_root)
        if prog_rel and is_git_tracked(project_root, prog_rel):
            continue
        added = meaningful_added_lines(prog, tpl_prog)
        added_chars = sum(len(re.sub(r"\s+", "", ln)) for ln in added)
        if added and added_chars >= 18:
            mtime = dt.datetime.fromtimestamp(prog.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            matched.append(f"{pkg.name} (updated {mtime})")
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
        raise GateConfigError(f"Invalid JSON in config file: {cfg_path} ({exc})") from exc
    if not isinstance(raw, dict):
        raise GateConfigError(f"Config root must be a JSON object: {cfg_path}")

    profile = raw.get("profile", "full")
    if profile not in ("full", "lite"):
        raise GateConfigError(f"Invalid profile in {cfg_path} (expected 'full' or 'lite')")

    merged = default_config_for(profile)
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


def has_source_files_within_depth(project_root: Path, max_depth: int = 2) -> bool:
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
        if (cand / "09-changes").is_dir():
            found.append(("full", cand, default_config_for("full")))
            seen.add(cand)
        elif (cand / "04-changes").is_dir():
            found.append(("lite", cand, default_config_for("lite")))
            seen.add(cand)

    return found


def discover_project_doc(
    project_root: Path, explicit_doc_root: Optional[str] = None
) -> Tuple[str, Optional[Path], Optional[Dict], List[Path]]:
    """Return (mode, doc_root, config, extra_candidates).
    mode values: full | lite | external | uninitialized
    """
    if explicit_doc_root:
        cand = Path(explicit_doc_root)
        if not cand.is_absolute():
            cand = (project_root / cand).resolve()
        if not is_path_within(cand, project_root):
            raise GateConfigError(f"--doc-root must stay inside project root: {cand} (root: {project_root})")
        if cand.is_dir():
            cfg = load_config(cand)
            if cfg:
                return cfg["profile"], cand, cfg, []
            if (cand / "09-changes").is_dir():
                return "full", cand, default_config_for("full"), []
            if (cand / "04-changes").is_dir():
                return "lite", cand, default_config_for("lite"), []
        return "uninitialized", cand, None, []

    candidates = find_all_doc_candidates(project_root)
    if candidates:
        mode, chosen, cfg = candidates[0]
        extras = [c[1] for c in candidates[1:]]
        return mode, chosen, cfg, extras

    if has_source_files_within_depth(project_root, max_depth=2):
        return "external", None, None, []

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
    lines: List[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith(">") or s.startswith("---") or s.startswith("```"):
            continue
        if s.startswith("--"):
            continue
        if s.startswith("<!--") and s.endswith("-->"):
            continue
        if re.fullmatch(r"[\|\-\:\s]+", s):
            continue
        if "[TODO" in s or "[Leave blank if none]" in s or "[Original behavior]" in s or "[New behavior]" in s:
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
            if (
                line.startswith("- Initialized change package `")
                or line.startswith("- State transition:")
                or line.startswith("- Passed `godkey_gate.py")
            ):
                continue
            if line in tpl_lines:
                continue
            result.append(line)
        return result
    return actual_lines


def inspect_static_item(path: Path, template_equiv: Optional[Path] = None, is_default_spec: bool = False) -> str:
    if not path.exists():
        return "MISSING"

    if path.is_file():
        added = meaningful_added_lines(path, template_equiv)
        if not added:
            return "DEFAULT_STANDARDS (uncustomized)" if is_default_spec else "TEMPLATE_ONLY"
        return "READY"

    files = [f for f in path.rglob("*") if f.is_file() and f.name != ".gitkeep"]
    if not files:
        return "EMPTY_DIR"

    non_template_files = [f for f in files if not f.name.startswith("_")]
    if not non_template_files:
        return "TEMPLATE_ONLY"

    customized = 0
    for f in non_template_files:
        rel = f.relative_to(path)
        tpl_f = (template_equiv / rel) if (template_equiv and template_equiv.is_dir()) else None
        if tpl_f is None or not tpl_f.is_file():
            if f.suffix.lower() in {".md", ".txt", ".sql"}:
                if strip_template_noise(f.read_text(encoding="utf-8", errors="replace")):
                    customized += 1
            else:
                customized += 1
        else:
            if meaningful_added_lines(f, tpl_f):
                customized += 1

    if customized > 0:
        return "READY"
    return "DEFAULT_STANDARDS (uncustomized)" if is_default_spec else "TEMPLATE_ONLY"


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
        raise ValueError("Package name cannot be empty or a dot path segment")
    return cleaned


def validate_date_str(date_str: str) -> str:
    if not DATE_RE.fullmatch(date_str):
        raise ValueError(f"--date must match YYYY-MM-DD, got: {date_str}")
    try:
        dt.date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError(f"--date is not a valid calendar date: {date_str}") from exc
    return date_str


def is_valid_waiver_reason(reason: str) -> bool:
    s = reason.strip().strip(".!;,")
    if len(s) < 12:
        return False
    low = s.lower()
    if low in LAZY_WAIVER_PHRASES:
        return False
    if low in ("concrete reason", "concrete reason (min 12 chars)"):
        return False
    distinct_chars = {ch for ch in low if not ch.isspace()}
    if len(distinct_chars) < 6:
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
        if reason.lower() in ("concrete reason", "concrete reason (min 12 chars)"):
            continue
        if is_valid_waiver_reason(reason):
            valid[key] = reason
        else:
            invalid.append(
                f"{key}: '{reason}' (waiver reason too vague/short; provide at least 12 chars of concrete rationale)"
            )
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
    """Without --package, inspect only newly added waiver lines in this diff to prevent permanent poison waivers."""
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
            if reason.lower() in ("concrete reason", "concrete reason (min 12 chars)"):
                continue
            if is_valid_waiver_reason(reason):
                return reason
    return None


def read_base_commit(pkg_dir: Path) -> str:
    prog = pkg_dir / "02-progress.md"
    if not prog.is_file():
        return ""
    m = BASE_COMMIT_RE.search(prog.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else ""


def read_package_type(pkg_dir: Path) -> str:
    review_doc = pkg_dir / "04-review.md"
    has_review_marker = False
    if review_doc.is_file():
        m = PACKAGE_TYPE_RE.search(review_doc.read_text(encoding="utf-8", errors="replace"))
        if m and m.group(1).lower() == "review":
            has_review_marker = True
    if not has_review_marker:
        return "feature"

    feature_only_items = [
        name for name in ("01-plan.md", "02-progress.md", "03-test.md", "ops")
        if (pkg_dir / name).exists()
    ]
    if feature_only_items:
        raise GateConfigError(
            f"Feature package `{pkg_dir.name}` contains feature artifacts ({', '.join(feature_only_items)}) "
            "and a forged `godkey-package-type: review` marker; bypassing the archive gate is forbidden."
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
    if mode == "full" and sub.startswith("04-feature-design/") and sub.endswith(".md"):
        mod_tpl = TEMPLATES_ROOT / "full" / "04-feature-design" / "_module-design-template.md"
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
    if not actual_path.is_file():
        return False, f"Missing required file: {actual_path.name}"
    text = actual_path.read_text(encoding="utf-8", errors="replace")
    remaining_todos = text.count("[TODO")
    added = meaningful_added_lines(actual_path, template_path)
    added_chars = sum(len(re.sub(r"\s+", "", ln)) for ln in added)
    if len(added) < 2 or added_chars < 30:
        return False, f"{actual_path.name} lacks substantive content ({len(added)} lines / {added_chars} non-space chars added)"
    if remaining_todos >= 4:
        return False, f"{actual_path.name} still contains {remaining_todos} unfilled `[TODO` placeholders"
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
# Subcommands
# ---------------------------------------------------------------------------
def cmd_init(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    profile = args.profile
    tpl_dir = TEMPLATES_ROOT / profile
    if not tpl_dir.is_dir():
        print(f"ERROR: Template directory not found: {tpl_dir}", file=sys.stderr)
        return 1

    doc_target = args.doc_root or args.doc_dir or "doc"
    target_root = Path(doc_target)
    if not target_root.is_absolute():
        target_root = (project_root / target_root).resolve()
    if not is_path_within(target_root, project_root):
        print(f"ERROR: Target doc directory must stay inside project root: {target_root}", file=sys.stderr)
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

    print(f"PASS: Initialized documentation layout (profile={profile}) -> {target_root}")
    print(f"  Created/written: {len(created)} files")
    if skipped:
        print(f"  Skipped existing: {len(skipped)} files (pass --force to overwrite)")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, extras = discover_project_doc(project_root, args.doc_root)

    print("=== GodKey Documentation Audit ===")
    print(f"Project root: {project_root}")
    print(f"Detected mode: {mode}")

    if mode == "uninitialized":
        print("Docs root: No GodKey documentation detected and no existing source codebase found.")
        print("Next step: Ask the user to choose 'full' or 'lite', then run:")
        print(f"  python \"{Path(__file__).resolve()}\" init --profile full|lite --project-root \"{project_root}\"")
        return 0

    if mode == "external":
        existing_docs: List[str] = []
        for name in ("README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "docs", "doc"):
            if (project_root / name).exists():
                existing_docs.append(name)
        print("Docs root: No GodKey layout detected; switching to [external] mode automatically.")
        print(f"Existing repo docs: {', '.join(existing_docs) if existing_docs else '(none at repo root)'}")
        print("Strategy: Do not inject foreign folders; keep full anti-hallucination workflow and sync existing repo docs.")
        return 0

    assert doc_root is not None and cfg is not None
    print(f"Docs root: {doc_root}")
    if extras:
        extra_str = ", ".join(p.name for p in extras)
        print(f"WARN: Multiple candidate doc roots detected (others: {extra_str}). Pass `--doc-root <dir>` to target another.")

    print("\n--- Static Truth Layer ---")
    items = FULL_STATIC_ITEMS if mode == "full" else LITE_STATIC_ITEMS
    tpl_root = TEMPLATES_ROOT / mode
    for item in items:
        is_spec = item in ("06-standards", "03-standards.md")
        status = inspect_static_item(doc_root / item, tpl_root / item, is_default_spec=is_spec)
        print(f"  {item:<30} [{status}]")

    changes_dir_name = cfg["changesDir"]
    changes_root = doc_root / changes_dir_name
    doc_root_rel = to_posix_rel(doc_root, project_root)
    local_only_tag = ""
    if doc_root_rel is not None:
        changes_rel = f"{doc_root_rel}/{changes_dir_name}".strip("/")
        if is_active_progress_local_only(project_root, changes_rel) or is_hotfix_local_only(
            project_root, f"{changes_rel}/hotfix-log.md"
        ):
            local_only_tag = " [local-only, ignored by .gitignore]"
    print(f"\n--- Dynamic Change Layer ({changes_dir_name}/){local_only_tag} ---")
    if not changes_root.is_dir():
        print("  ERROR: Dynamic changes directory is missing")
        return 1

    pkgs = list_state_packages(changes_root)
    for key in ("draft", "active", "paused"):
        label = STATE_DIRS[key]
        names = [p.name for p in pkgs[key]]
        print(f"  {label}/ ({len(names)})" + (": " + ", ".join(names) if names else ": (empty)"))

    archived = pkgs["archive"]
    recent = [p.name for p in archived[-3:]]
    print(f"  {STATE_DIRS['archive']}/ ({len(archived)})" + (f" — recent: {', '.join(recent)}" if recent else ": (empty)"))

    hotfix_file = changes_root / "hotfix-log.md"
    print(f"  hotfix-log.md: {'present' if hotfix_file.is_file() else 'MISSING'}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"ERROR: Cannot create change package in mode '{mode}'. Run `init` first.", file=sys.stderr)
        return 1

    state_key = STATE_ALIASES.get(args.state.lower())
    if state_key not in ("draft", "active"):
        print("ERROR: Initial state must be 'draft' (01-draft) or 'active' (02-active).", file=sys.stderr)
        return 1

    try:
        feature_name = sanitize_name(args.name)
        date_part = validate_date_str(args.date) if args.date else today_str()
    except ValueError as exc:
        print(f"ERROR: Invalid argument: {exc}", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]

    for st in ("draft", "active", "paused"):
        for p in list_state_packages(changes_root).get(st, []):
            if p.name.endswith(f"_{feature_name}") or p.name == f"{date_part}_{feature_name}":
                print(
                    f"ERROR: An unarchived package with the same name already exists: {STATE_DIRS[st]}/{p.name}. "
                    "Resume, pause, or archive it first.",
                    file=sys.stderr,
                )
                return 1

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
        print(f"ERROR: Unsafe target path (path traversal detected): {target_dir}", file=sys.stderr)
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
        review_src = tpl_pkg / "04-review.md"
        content = review_src.read_text(encoding="utf-8")
        for k, v in replacements.items():
            content = content.replace(k, v)
        content = f"<!-- godkey-package-type: review -->\n{content}"
        (target_dir / "04-review.md").write_text(content, encoding="utf-8")
        print(f"PASS: Created standalone review package -> {target_dir}")
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

    print(f"PASS: Created feature package -> {target_dir}")
    if base_commit:
        print(f"  Recorded baseline commit (godkey-base-commit): {base_commit}")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"ERROR: Cannot move package in mode '{mode}'.", file=sys.stderr)
        return 1

    target_key = STATE_ALIASES.get(args.target.lower())
    if target_key == "archive":
        print("ERROR: Direct move to archive is forbidden. Use `archive` to pass the static sync gate.", file=sys.stderr)
        return 1
    if target_key not in ("draft", "active", "paused"):
        print("ERROR: Target state must be draft, active, or paused.", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]
    cur_state, pkg_dir, matches = find_package(changes_root, args.package)
    if pkg_dir is None or cur_state is None:
        if len(matches) > 1:
            print("ERROR: Multiple packages matched; specify a more exact name:", file=sys.stderr)
            for st, p in matches:
                print(f"  - {STATE_DIRS[st]}/{p.name}", file=sys.stderr)
        else:
            print(f"ERROR: Package not found in unarchived states: {args.package}", file=sys.stderr)
        return 1

    if cur_state == target_key:
        print(f"INFO: Package already in {STATE_DIRS[target_key]}/{pkg_dir.name}.")
        return 0

    dest_dir = changes_root / STATE_DIRS[target_key] / pkg_dir.name
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        print(f"ERROR: Destination already exists: {dest_dir}", file=sys.stderr)
        return 1

    shutil.move(str(pkg_dir), str(dest_dir))

    prog = dest_dir / "02-progress.md"
    if prog.is_file():
        reason_suffix = f" (reason: {args.reason})" if args.reason else ""
        note = f"\n### {now_str()} — State Transition\n- State transition: `{STATE_DIRS[cur_state]}` -> `{STATE_DIRS[target_key]}`{reason_suffix}\n"
        with prog.open("a", encoding="utf-8") as fh:
            fh.write(note)

    print(f"PASS: Moved `{pkg_dir.name}`: {STATE_DIRS[cur_state]} -> {STATE_DIRS[target_key]}")
    return 0


def cmd_hotfix(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"ERROR: Cannot record hotfix in mode '{mode}'.", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]
    hotfix_path = changes_root / "hotfix-log.md"
    hotfix_path.parent.mkdir(parents=True, exist_ok=True)
    if not hotfix_path.exists():
        hotfix_path.write_text("# Hotfix Log\n\n---\n", encoding="utf-8")

    files_list = [f.strip() for f in args.files.split(",") if f.strip()]
    files_md = ", ".join(f"`{f}`" for f in files_list) if files_list else "(unspecified)"
    entry = (
        f"\n## {today_str()} — {args.title.strip()}\n"
        f"- **Symptom**: {args.symptom.strip()}\n"
        f"- **Root cause**: {args.root_cause.strip()}\n"
        f"- **Files**: {files_md}\n"
        f"- **Verification**: {args.verify.strip()}\n"
    )
    with hotfix_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)

    print(f"PASS: Appended hotfix record -> {hotfix_path}")
    return 0


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
    infos: List[str] = []
    warnings: List[str] = []
    failures: List[str] = []

    if not is_git_repo(project_root):
        infos.append(f"Gate mode: {gate_mode} | Project mode: {mode} | Diff source: non-git")
        warnings.append("Non-Git directory: cannot verify static doc sync via git diff automatically; please review static snapshots manually.")
        return True, infos, warnings, failures

    effective_base = base_ref
    if not staged and not effective_base and package_dir is not None:
        recorded = read_base_commit(package_dir)
        if recorded:
            if commit_exists(project_root, recorded):
                effective_base = recorded
            else:
                warnings.append(
                    f"Recorded baseline commit `{recorded}` not found in Git history (rebased/amended); "
                    "falling back to working tree / latest commit. Pass `--base <commit>` if needed."
                )

    diff_source, entries, tree_baseline, _ = collect_changed_files(
        project_root, staged=staged, base_ref=effective_base
    )
    infos.append(f"Gate mode: {gate_mode} | Project mode: {mode} | Diff source: {diff_source} ({len(entries)} files)")

    if diff_source == "HEAD~1..HEAD" and not package_dir and not base_ref:
        warnings.append("Working tree is clean; inspected only HEAD~1..HEAD. Pass `--package` or `--base` for multi-commit checks.")

    if mode == "external":
        code_files = [
            e.path for e in entries
            if Path(e.path).suffix.lower() in DEFAULT_CODE_EXTS and not is_test_path(e.path)
        ]
        md_files = [e.path for e in entries if e.path.lower().endswith(".md") and e.status != "D"]
        if code_files and not md_files:
            warnings.append(
                f"External repo mode: {len(code_files)} code files changed with no Markdown updates; verify whether existing README/docs need syncing."
            )
        return True, infos, warnings, failures

    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        warnings.append(f"Project mode is '{mode}'; skipping static sync gate.")
        return True, infos, warnings, failures

    doc_root_rel = to_posix_rel(doc_root, project_root)
    if doc_root_rel is None:
        failures.append(f"Docs directory is outside project root: {doc_root}")
        return False, infos, warnings, failures

    changes_rel = f"{doc_root_rel}/{cfg['changesDir']}".strip("/")
    hotfix_rel = f"{changes_rel}/hotfix-log.md"
    changes_root = doc_root / cfg["changesDir"]
    hotfix_local_only = is_hotfix_local_only(project_root, hotfix_rel)
    active_local_only = is_active_progress_local_only(project_root, changes_rel, package_dir)
    if hotfix_local_only or active_local_only:
        scope_parts = []
        if active_local_only:
            scope_parts.append("active packages")
        if hotfix_local_only:
            scope_parts.append("hotfix-log.md")
        infos.append(
            f"Note: Dynamic changes ({' & '.join(scope_parts)}) are gitignored and untracked; falling back to local disk verification."
        )
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
                if rel.endswith("/02-progress.md") or rel == hotfix_rel:
                    dynamic_waiver_candidates.append(rel)
            continue

        if rel == doc_root_rel or rel.startswith(f"{doc_root_rel}/"):
            fname = Path(rel).name
            if entry.status == "D":
                warnings.append(f"Static doc deleted (does not satisfy sync): {rel}")
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
                warnings.append(f"Ignored whitespace-only or untouched-template static doc change: {rel}")
                continue
            static_docs_changed.append(rel)
            continue

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
                arch_triggers.append(f"new-module-dir:{mod}")

    if package_dir is not None and (package_dir / "ops").is_dir():
        for ops_file in sorted((package_dir / "ops").rglob("*")):
            if not ops_file.is_file() or ops_file.name == ".gitkeep":
                continue
            if ops_file.name == "deploy-notes.md":
                if deploy_notes_has_real_changes(ops_file):
                    ops_triggers.append(f"ops/{ops_file.name} (rollout changes recorded)")
            elif ops_file.suffix.lower() == ".sql":
                db_triggers.append(f"ops/{ops_file.name}")
            else:
                ops_triggers.append(f"ops/{ops_file.name}")

    db_triggers = sorted(set(db_triggers))
    ops_triggers = sorted(set(ops_triggers))
    arch_triggers = sorted(set(arch_triggers))

    if package_dir is not None:
        waivers, invalid_waivers = parse_doc_waivers_from_files([package_dir / "02-progress.md"])
    else:
        waivers, invalid_waivers = parse_doc_waivers_from_diff(
            project_root,
            dynamic_waiver_candidates,
            diff_source=diff_source,
            staged=staged,
            base_ref=effective_base,
        )

    for bad in invalid_waivers:
        failures.append(f"Invalid waiver: {bad}")

    infos.append(
        f"Changes: code={len(code_files)} | tests={len(test_files)} | static_docs={len(static_docs_changed)} | dynamic_docs={len(dynamic_docs_changed)}"
    )

    if gate_mode == "hotfix":
        if len(code_files) > 1:
            failures.append(
                f"Hotfix gate rejected: {len(code_files)} business code files modified ({', '.join(code_files[:5])}); "
                "exceeds single-file hotfix scope — create a feature package instead."
            )
        if db_triggers or ops_triggers or arch_triggers:
            trig = db_triggers + ops_triggers + arch_triggers
            failures.append(
                f"Hotfix gate rejected: DB/ops/architecture change detected ({', '.join(trig[:5])}); "
                "use a standard feature package."
            )
        if code_files and hotfix_rel not in dynamic_docs_changed:
            if hotfix_local_only:
                ok_local, detail = has_local_hotfix_for_files(
                    changes_root / "hotfix-log.md",
                    code_files,
                    check_recent_date=(diff_source != "HEAD~1..HEAD"),
                )
                if ok_local:
                    infos.append(f"  OK Hotfix log (local disk check): {detail}")
                else:
                    failures.append(
                        f"Hotfix gate rejected: {detail}. Run `godkey_gate.py hotfix` to record this change."
                    )
            else:
                failures.append(f"Hotfix gate rejected: code changed without updating `{hotfix_rel}`. Run `godkey_gate.py hotfix` first.")
        return len(failures) == 0, infos, warnings, failures

    if not code_files and not db_triggers and not ops_triggers and not arch_triggers:
        infos.append("No code/DB/ops changes requiring static doc sync.")
        return len(failures) == 0, infos, warnings, failures

    if gate_mode == "commit":
        has_any_doc = bool(static_docs_changed or dynamic_docs_changed)
        if not has_any_doc and (active_local_only or hotfix_local_only):
            local_progs = find_local_active_progress(project_root, changes_root, package_dir) if active_local_only else []
            if local_progs:
                has_any_doc = True
                infos.append(
                    f"  OK Dynamic progress (local disk check): matched active package(s) {', '.join(local_progs)}"
                )
            elif hotfix_local_only and len(code_files) <= 1 and not db_triggers and not ops_triggers and not arch_triggers:
                ok_hf, detail_hf = has_local_hotfix_for_files(
                    changes_root / "hotfix-log.md",
                    code_files,
                    check_recent_date=(diff_source != "HEAD~1..HEAD"),
                )
                if ok_hf:
                    has_any_doc = True
                    infos.append(f"  OK Hotfix log (local disk check): {detail_hf}")
        if not has_any_doc:
            if active_local_only or hotfix_local_only:
                failures.append(
                    "Code modified with no static doc updates and no substantive local progress in gitignored dynamic dirs "
                    "(`02-active/*/02-progress.md` or matching `hotfix-log.md`). Record iteration progress before committing."
                )
            else:
                failures.append(
                    "Code modified without updating progress (`02-progress.md` / `hotfix-log.md`) or static docs. "
                    "Record iteration progress before committing."
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
                warnings.append(f"WIP commit allowed; sync static docs before archiving: {', '.join(uniq)}")
        return len(failures) == 0, infos, warnings, failures

    checks = [
        ("featureDocs", "Feature Design Blueprints", bool(code_files), code_files[:5]),
        ("dbDocs", "Database Schema Snapshot", bool(db_triggers), db_triggers[:5]),
        ("opsDocs", "Deployment & Environments", bool(ops_triggers), ops_triggers[:5]),
        ("archDocs", "System Architecture & Stack", bool(arch_triggers), arch_triggers[:5]),
    ]

    if package_dir is not None:
        waiver_where = "package `02-progress.md`"
    elif active_local_only or hotfix_local_only:
        waiver_where = "package `02-progress.md` (pass `--package <pkg>` when dynamic dirs are gitignored)"
    else:
        waiver_where = "this change's progress log"

    for rule_key, label, triggered, evidence in checks:
        if not triggered:
            continue
        targets = sync_rules.get(rule_key, [])
        if doc_rule_satisfied(static_docs_changed, doc_root_rel, targets):
            infos.append(f"  OK {label} ({', '.join(targets)}): static doc sync detected")
        elif rule_key in waivers:
            warnings.append(f"  WAIVED [{rule_key} / {label}]: {waivers[rule_key]}")
        else:
            failures.append(
                f"{rule_key} not synced ({label}): changes detected in {', '.join(evidence)}, "
                f"but static targets {', '.join(targets)} have no substantive updates. "
                f"Update static docs or add an auditable waiver in {waiver_where}: "
                f"`<!-- doc-sync-waiver: {rule_key} | concrete reason (min 12 chars) -->`"
            )

    return len(failures) == 0, infos, warnings, failures


def cmd_check_sync(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)

    pkg_dir: Optional[Path] = None
    if args.package and doc_root is not None and cfg is not None:
        changes_root = doc_root / cfg["changesDir"]
        _, pkg_dir, _ = find_package(changes_root, args.package)
        if pkg_dir is None:
            print(f"ERROR: Package not found: {args.package}", file=sys.stderr)
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
        print(f"WARN: {line}")
    for line in failures:
        print(f"FAIL: {line}", file=sys.stderr)

    if passed:
        print("CHECK-SYNC PASS")
        return 0
    print("CHECK-SYNC FAIL", file=sys.stderr)
    return 1


def cmd_archive(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    mode, doc_root, cfg, _ = discover_project_doc(project_root, args.doc_root)
    if mode not in ("full", "lite") or doc_root is None or cfg is None:
        print(f"ERROR: Cannot run archive gate in mode '{mode}'.", file=sys.stderr)
        return 1

    if args.skip_git and is_git_repo(project_root):
        print("ERROR: `--skip-git` is forbidden inside a Git repository.", file=sys.stderr)
        return 1

    changes_root = doc_root / cfg["changesDir"]
    cur_state, pkg_dir, matches = find_package(changes_root, args.package, allowed_states=("draft", "active", "paused"))
    if pkg_dir is None or cur_state is None:
        if len(matches) > 1:
            print("ERROR: Multiple packages matched; specify a more exact name:", file=sys.stderr)
            for st, p in matches:
                print(f"  - {STATE_DIRS[st]}/{p.name}", file=sys.stderr)
        else:
            print(f"ERROR: Package not found: {args.package}", file=sys.stderr)
        return 1

    if cur_state != "active":
        print(
            f"ERROR: Package is in `{STATE_DIRS[cur_state]}/`; only packages in `{STATE_DIRS['active']}/` may be archived. "
            "Move it to active first.",
            file=sys.stderr,
        )
        return 1

    tpl_pkg = TEMPLATES_ROOT / "change-package"
    pkg_type = read_package_type(pkg_dir)
    artifact_errors: List[str] = []
    artifact_notes: List[str] = []

    if pkg_type == "review":
        ok, err = has_substantive_artifact(pkg_dir / "04-review.md", tpl_pkg / "04-review.md")
        if not ok:
            print(f"FAIL: Standalone review archive rejected: {err}", file=sys.stderr)
            return 1
        print("  OK Standalone review 04-review.md: substantive report present")
    else:
        for req_name in ("01-plan.md", "02-progress.md"):
            ok, err = has_substantive_artifact(pkg_dir / req_name, tpl_pkg / req_name)
            if not ok:
                artifact_errors.append(err)

        for opt_name, waiver_kind in (("03-test.md", "test"), ("04-review.md", "review")):
            fpath = pkg_dir / opt_name
            if not fpath.is_file():
                artifact_errors.append(f"Missing required file: {opt_name}")
                continue
            ok, err = has_substantive_artifact(fpath, tpl_pkg / opt_name)
            waiver = parse_artifact_waiver(fpath, waiver_kind)
            if ok:
                artifact_notes.append(f"  OK {opt_name}: filled")
            elif waiver:
                artifact_notes.append(f"  WAIVED [{waiver_kind} / {opt_name}]: {waiver}")
            else:
                artifact_errors.append(
                    f"{err}, and no valid waiver (`<!-- artifact-waiver: {waiver_kind} | concrete reason (min 12 chars) -->`)"
                )

        if artifact_errors:
            print("=== Archive Gate: Artifact Check Failed ===", file=sys.stderr)
            for err in artifact_errors:
                print(f"FAIL: {err}", file=sys.stderr)
            return 1

        for note in artifact_notes:
            print(note)

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
            print(f"WARN: {line}")
        if not passed:
            for line in failures:
                print(f"FAIL: {line}", file=sys.stderr)
            print("ARCHIVE FAIL: Static doc sync gate failed; refusing to move into 99-archive/.", file=sys.stderr)
            return 1

    dest_dir = changes_root / STATE_DIRS["archive"] / pkg_dir.name
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        print(f"ERROR: Archive destination already exists: {dest_dir}", file=sys.stderr)
        return 1

    shutil.move(str(pkg_dir), str(dest_dir))

    prog = dest_dir / "02-progress.md"
    if prog.is_file():
        with prog.open("a", encoding="utf-8") as fh:
            fh.write(
                f"\n### {now_str()} — Gate Verified & Archived\n"
                f"- Passed `godkey_gate.py archive` and moved to `{STATE_DIRS['archive']}/{pkg_dir.name}`\n"
            )

    print(f"ARCHIVE PASS: `{pkg_dir.name}` verified and archived -> {dest_dir}")
    return 0


HOOK_MARKER = "# GODKEY-SKILL-MANAGED-HOOK"


def cmd_install_hook(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    if not is_git_repo(project_root):
        print(f"ERROR: Not a Git repository: {project_root}", file=sys.stderr)
        return 1

    code, out, err = run_git(project_root, ["rev-parse", "--git-path", "hooks/pre-commit"])
    if code != 0 or not out.strip():
        print(f"ERROR: Could not locate Git hooks path: {err.strip()}", file=sys.stderr)
        return 1

    hook_path = Path(out.strip())
    if not hook_path.is_absolute():
        hook_path = (project_root / hook_path).resolve()
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    if hook_path.exists() and not args.force:
        existing = hook_path.read_text(encoding="utf-8", errors="replace")
        if HOOK_MARKER not in existing:
            print(
                f"ERROR: Custom pre-commit hook already exists at {hook_path}. Inspect it or pass --force.",
                file=sys.stderr,
            )
            return 1

    script_posix = Path(__file__).resolve().as_posix()
    doc_root_flag = f' --doc-root "{args.doc_root}"' if args.doc_root else ""
    hook_body = f"""#!/usr/bin/env sh
{HOOK_MARKER}
# Cross-harness pre-commit check verifying progress / static doc sync

GATE_SCRIPT="${{GODKEY_GATE_SCRIPT:-{script_posix}}}"
if [ ! -f "$GATE_SCRIPT" ]; then
  echo "[godkey-hook] Gate script not found: $GATE_SCRIPT (set GODKEY_GATE_SCRIPT if moved)" >&2
  exit 0
fi

if python3 -c "import sys" >/dev/null 2>&1; then
  PY_CMD="python3"
elif python -c "import sys" >/dev/null 2>&1; then
  PY_CMD="python"
elif py -3 -c "import sys" >/dev/null 2>&1; then
  PY_CMD="py -3"
else
  echo "[godkey-hook] No working Python 3 interpreter found; skipping check" >&2
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

    print(f"PASS: Installed Git pre-commit hook (mode={args.mode}) -> {hook_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="godkey_gate.py",
        description="GodKey Skill deterministic doc audit, change-package state machine, and static sync gate",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-root", default=".", help="Target project root directory (default: .)")
        p.add_argument("--doc-root", default=None, help="Explicit documentation directory path (optional)")

    p_init = sub.add_parser("init", help="Initialize full or lite documentation templates")
    p_init.add_argument("--profile", choices=("full", "lite"), required=True, help="Documentation profile")
    p_init.add_argument("--doc-root", default=None, help="Target docs directory (default: doc)")
    p_init.add_argument("--doc-dir", default=None, help="Alias for --doc-root")
    p_init.add_argument("--project-root", default=".", help="Target project root")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing files")
    p_init.set_defaults(func=cmd_init)

    p_audit = sub.add_parser("audit", help="Audit static doc status and 4-state change packages")
    add_common(p_audit)
    p_audit.set_defaults(func=cmd_audit)

    p_new = sub.add_parser("new", help="Create a new feature package or standalone review package")
    add_common(p_new)
    p_new.add_argument("name", help="Short descriptive feature name, e.g. export-users-excel")
    p_new.add_argument("--state", default="active", help="Initial state: draft or active (default)")
    p_new.add_argument("--type", choices=("feature", "review"), default="feature", help="Package type")
    p_new.add_argument("--date", default=None, help="Override date prefix (YYYY-MM-DD)")
    p_new.set_defaults(func=cmd_new)

    p_move = sub.add_parser("move", help="Move a package across draft / active / paused (cannot bypass archive)")
    add_common(p_move)
    p_move.add_argument("package", help="Package folder name or unique substring")
    p_move.add_argument("target", help="Target state: draft / active / paused")
    p_move.add_argument("--reason", default="", help="Reason for transition (e.g. pause rationale)")
    p_move.set_defaults(func=cmd_move)

    p_hotfix = sub.add_parser("hotfix", help="Append a single-file hotfix record to hotfix-log.md")
    add_common(p_hotfix)
    p_hotfix.add_argument("--title", required=True, help="Hotfix title")
    p_hotfix.add_argument("--symptom", required=True, help="Observed symptom")
    p_hotfix.add_argument("--root-cause", required=True, help="Root cause")
    p_hotfix.add_argument("--files", required=True, help="Comma-separated modified files")
    p_hotfix.add_argument("--verify", required=True, help="Verification command & result")
    p_hotfix.set_defaults(func=cmd_hotfix)

    p_check = sub.add_parser("check-sync", help="Verify static doc sync against git diff and package ops/")
    add_common(p_check)
    p_check.add_argument("--package", default=None, help="Target package for baseline commit & ops/ inspection")
    p_check.add_argument("--base", default=None, help="Explicit Git baseline ref")
    p_check.add_argument("--staged", action="store_true", help="Inspect staged changes only (for pre-commit)")
    p_check.add_argument(
        "--mode",
        choices=("archive", "commit", "strict", "hotfix"),
        default="archive",
        help="archive / commit / strict / hotfix",
    )
    p_check.set_defaults(func=cmd_check_sync)

    p_arch = sub.add_parser("archive", help="Verify artifacts + static sync gate, then move to 99-archive/")
    add_common(p_arch)
    p_arch.add_argument("package", help="Active package folder name or unique substring")
    p_arch.add_argument("--base", default=None, help="Explicit Git baseline ref")
    p_arch.add_argument("--skip-git", action="store_true", help="Non-Git directory only (rejected inside Git repos)")
    p_arch.set_defaults(func=cmd_archive)

    p_hook = sub.add_parser("install-hook", help="Install portable Git pre-commit hook")
    add_common(p_hook)
    p_hook.add_argument("--mode", choices=("commit", "strict"), default="commit", help="Hook strictness")
    p_hook.add_argument("--force", action="store_true", help="Overwrite existing non-godkey hook")
    p_hook.set_defaults(func=cmd_install_hook)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except GateConfigError as exc:
        print(f"ERROR: Config/Gate violation: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
