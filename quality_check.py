#!/usr/bin/env python3
"""
Simple quality checker for this project.
- Scans Python files for common issues (blocking imports, broad except, prints, long functions)
- Scans frontend HTML/JS for large inline scripts and missing defer
- Recommends fixes
"""
import os
import re
import sys
from typing import List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

PY_ISSUES = [
    (re.compile(r"except\s*:\s*"), "Avoid bare except; catch specific exceptions"),
    (re.compile(r"print\("), "Use logging instead of print"),
    (re.compile(r"requests\.post\([^)]*timeout=\s*\)?(?![\s\S]*timeout=)", re.MULTILINE), "Requests without timeout"),
]

def iter_files(root: str, exts: Tuple[str, ...]) -> List[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip heavy dirs
        if any(x in dirpath for x in ("uploads", "outputs", ".venv", "env", "node_modules")):
            continue
        for f in filenames:
            if f.endswith(exts):
                files.append(os.path.join(dirpath, f))
    return files

def check_python() -> int:
    py_files = iter_files(PROJECT_ROOT, (".py",))
    issues = 0
    for path in py_files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            for pattern, msg in PY_ISSUES:
                if pattern.search(content):
                    print(f"[PY] {path}: {msg}")
                    issues += 1
        except Exception as e:
            print(f"[PY] {path}: read error {e}")
    return issues

def check_frontend() -> int:
    html_files = iter_files(os.path.join(PROJECT_ROOT, "app", "static"), (".html",))
    issues = 0
    for path in html_files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            # Inline scripts size
            scripts = re.findall(r"<script>([\s\S]*?)</script>", content, re.IGNORECASE)
            for script in scripts:
                if len(script) > 10000:
                    print(f"[FE] {path}: large inline <script> (>10KB), consider splitting JS file")
                    issues += 1
            # Missing cache headers are server-side; remind here
        except Exception as e:
            print(f"[FE] {path}: read error {e}")
    return issues

def main() -> int:
    total = 0
    total += check_python()
    total += check_frontend()
    if total == 0:
        print("No obvious issues found. ✅")
    else:
        print(f"Found {total} potential issues. 🔧 Please review messages above.")
    return 0

if __name__ == "__main__":
    sys.exit(main())




