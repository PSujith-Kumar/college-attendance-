#!/usr/bin/env python3
"""Workspace cleanup helper.

Features:
- Move .pdf and .docx files into Archive_References/
- Delete common temp files (.log, .tmp, .DS_Store, Thumbs.db)
- Remove __pycache__ folders
- Delete empty directories
- List .html/.js files not reachable from entry files

Default mode is dry-run. Use --apply to perform changes.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path
from typing import Iterable, Set

DOC_EXTS = {".pdf", ".docx"}
TEMP_FILE_NAMES = {".ds_store", "thumbs.db"}
TEMP_EXTS = {".log", ".tmp"}
ENV_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".vscode",
}

HTML_REF_RE = re.compile(r"(?:src|href)=[\"']([^\"'#?]+)", re.IGNORECASE)
JS_REF_RE = re.compile(
    r"(?:import\s+(?:[^;]*?from\s+)?|require\s*\()\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
PY_TEMPLATE_RE = re.compile(r"render_template\(\s*['\"]([^'\"]+\.html)['\"]", re.IGNORECASE)
PY_STATIC_RE = re.compile(
    r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def is_ignored_dir(path: Path) -> bool:
    return any(part.lower() in ENV_DIR_NAMES for part in path.parts)


def iter_files(root: Path) -> Iterable[Path]:
    for current_root, dirs, files in os.walk(root):
        cur_path = Path(current_root)
        dirs[:] = [d for d in dirs if not is_ignored_dir(cur_path / d)]
        for name in files:
            f = cur_path / name
            if not is_ignored_dir(f):
                yield f


def ensure_dir(path: Path, apply: bool, actions: list[str]) -> None:
    if not path.exists():
        actions.append(f"CREATE_DIR {path}")
        if apply:
            path.mkdir(parents=True, exist_ok=True)


def move_reference_docs(root: Path, archive_name: str, apply: bool, actions: list[str]) -> None:
    archive_dir = root / archive_name
    for file_path in iter_files(root):
        if file_path.suffix.lower() not in DOC_EXTS:
            continue
        if archive_name.lower() in [p.lower() for p in file_path.parts]:
            continue
        ensure_dir(archive_dir, apply, actions)
        target = archive_dir / file_path.name
        if target.exists():
            stem, suffix = file_path.stem, file_path.suffix
            i = 1
            while True:
                candidate = archive_dir / f"{stem}_{i}{suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                i += 1
        actions.append(f"MOVE {file_path} -> {target}")
        if apply:
            shutil.move(str(file_path), str(target))


def delete_temp_files(root: Path, apply: bool, actions: list[str]) -> None:
    for file_path in iter_files(root):
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()
        if suffix in TEMP_EXTS or name in TEMP_FILE_NAMES:
            actions.append(f"DELETE_FILE {file_path}")
            if apply:
                try:
                    file_path.unlink()
                except FileNotFoundError:
                    pass


def remove_pycache_dirs(root: Path, apply: bool, actions: list[str]) -> None:
    for current_root, dirs, _files in os.walk(root):
        cur_path = Path(current_root)
        dirs[:] = [d for d in dirs if not is_ignored_dir(cur_path / d)]
        for d in list(dirs):
            if d == "__pycache__":
                target = cur_path / d
                actions.append(f"DELETE_DIR {target}")
                if apply:
                    shutil.rmtree(target, ignore_errors=True)
                dirs.remove(d)


def remove_empty_dirs(root: Path, apply: bool, actions: list[str]) -> None:
    # Bottom-up walk to safely remove empties.
    for current_root, dirs, files in os.walk(root, topdown=False):
        path = Path(current_root)
        if is_ignored_dir(path):
            continue
        if dirs or files:
            # os.walk 'dirs/files' can be stale; check actual directory state.
            if any(path.iterdir()):
                continue
        if path == root:
            continue
        actions.append(f"DELETE_EMPTY_DIR {path}")
        if apply:
            try:
                path.rmdir()
            except OSError:
                pass


def resolve_ref(base: Path, ref: str) -> Path | None:
    if not ref or ref.startswith(("http://", "https://", "//", "mailto:", "tel:")):
        return None
    if ref.startswith("/"):
        return None
    return (base / ref).resolve()


def parse_references(file_path: Path) -> Set[Path]:
    refs: Set[Path] = set()
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return refs

    base = file_path.parent
    candidates = set()

    suffix = file_path.suffix.lower()

    if suffix in {".html", ".htm"}:
        for m in HTML_REF_RE.finditer(text):
            candidates.add(m.group(1).strip())
    if suffix == ".js":
        for m in JS_REF_RE.finditer(text):
            candidates.add(m.group(1).strip())
    if suffix == ".py":
        # Flask templates and static assets often appear only in Python routes.
        for m in PY_TEMPLATE_RE.finditer(text):
            template_rel = m.group(1).strip()
            candidates.add(f"frontend/templates/{template_rel}")
            candidates.add(f"templates/{template_rel}")
            candidates.add(f"../frontend/templates/{template_rel}")
        for m in PY_STATIC_RE.finditer(text):
            static_rel = m.group(1).strip()
            candidates.add(f"frontend/static/{static_rel}")
            candidates.add(f"static/{static_rel}")
            candidates.add(f"../frontend/static/{static_rel}")

    for raw in candidates:
        target = resolve_ref(base, raw)
        if target is None:
            continue

        # JS imports can omit .js extension.
        options = [target]
        if target.suffix == "":
            options.extend([target.with_suffix(".js"), target / "index.js"])

        for opt in options:
            if opt.exists() and opt.is_file():
                refs.add(opt)
                break

    return refs


def list_unlinked_html_js(root: Path, entry_files: list[Path]) -> list[Path]:
    all_targets = {
        p.resolve()
        for p in iter_files(root)
        if p.suffix.lower() in {".html", ".js"}
    }

    existing_entries = [p.resolve() for p in entry_files if p.exists()]
    if not existing_entries:
        return sorted(all_targets)

    visited: Set[Path] = set()
    stack = list(existing_entries)

    while stack:
        node = stack.pop()
        if node in visited or not node.exists() or not node.is_file():
            continue
        visited.add(node)
        refs = parse_references(node)
        for ref in refs:
            if ref in all_targets and ref not in visited:
                stack.append(ref)

    return sorted(p for p in all_targets if p not in visited)


def default_entry_candidates(root: Path) -> list[Path]:
    candidates = [
        root / "index.html",
        root / "frontend" / "index.html",
        root / "frontend" / "templates" / "base.html",
        root / "frontend" / "templates" / "counselor.html",
        root / "backend" / "app.py",
        root / "backend" / "webapp.py",
    ]
    # Also discover nested project roots in larger workspace folders.
    for pattern in ["**/backend/app.py", "**/backend/webapp.py", "**/frontend/templates/base.html"]:
        for p in root.glob(pattern):
            candidates.append(p)

    seen = set()
    existing = []
    for p in candidates:
        if p.exists():
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                existing.append(p)
    return existing


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean workspace clutter safely.")
    parser.add_argument("--root", default=".", help="Workspace root to clean")
    parser.add_argument("--archive", default="Archive_References", help="Archive folder name")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument(
        "--entry",
        action="append",
        default=[],
        help="Entry HTML/JS file for unused-link scan (repeatable)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    actions: list[str] = []

    move_reference_docs(root, args.archive, args.apply, actions)
    delete_temp_files(root, args.apply, actions)
    remove_pycache_dirs(root, args.apply, actions)
    remove_empty_dirs(root, args.apply, actions)

    entry_paths = [Path(e).resolve() for e in args.entry]
    if not entry_paths:
        entry_paths = default_entry_candidates(root)

    unlinked = list_unlinked_html_js(root, entry_paths)

    mode = "APPLY" if args.apply else "DRY_RUN"
    print(f"MODE={mode}")
    print(f"ROOT={root}")
    print(f"ACTIONS_COUNT={len(actions)}")
    for line in actions:
        print(line)

    print(f"ENTRY_FILES_COUNT={len(entry_paths)}")
    for e in entry_paths:
        print(f"ENTRY {e}")

    print(f"UNLINKED_HTML_JS_COUNT={len(unlinked)}")
    for p in unlinked:
        print(f"UNLINKED {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
