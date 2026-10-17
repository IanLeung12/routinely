#!/usr/bin/env python3
"""Print a compact, always-current map of the codebase (generated, never committed).

  python3 scripts/codemap.py              whole repo
  python3 scripts/codemap.py web/src      one area (any path prefix)
  python3 scripts/codemap.py --tests      include test files

For each source file: its one-line purpose (module docstring / leading comment) and
its top-level public names. Read this before exploring; open only the files you need.
Hand-written architecture notes live in docs/CODEMAP.md.
"""
import ast, os, re, subprocess, sys

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
SRC = (".py", ".ts", ".tsx", ".sh")
SKIP = re.compile(r"(^|/)(node_modules|\.venv|dist|__pycache__|fixtures)/|package-lock|\.lock$|vite-env\.d\.ts$")
TEST = re.compile(r"(^|/)tests?/|\.test\.(ts|tsx)$|(^|/)test_[^/]+\.py$|conftest\.py$")


def first_line(text):
    for ln in text.strip().splitlines():
        ln = ln.strip().strip("/*#- ").strip()
        if ln and not ln.startswith("!") and not ln.lower().startswith("eslint"):
            return ln[:110]
    return ""


def py_info(path):
    try:
        tree = ast.parse(open(path).read())
    except (SyntaxError, UnicodeDecodeError):
        return "", []
    doc = first_line(ast.get_docstring(tree) or "")
    names = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and not n.name.startswith("_")]
    return doc, names


def ts_info(path):
    s = open(path, errors="replace").read()
    m = re.match(r"\s*(/\*\*?([\s\S]*?)\*/|((?:\s*//[^\n]*\n)+))", s)
    doc = first_line(m.group(2) or m.group(3) or "") if m else ""
    names = re.findall(r"^export\s+(?:default\s+)?(?:async\s+)?(?:function|const|class|interface|type|enum)\s+(\w+)", s, re.M)
    return doc, names


def sh_info(path):
    lines = [ln for ln in open(path, errors="replace").read().splitlines()[1:6] if ln.startswith("#")]
    return first_line("\n".join(lines)), []


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tests = "--tests" in sys.argv
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    files = [f for f in files if f.endswith(SRC) and not SKIP.search(f) and (tests or not TEST.search(f))]
    if args:
        files = [f for f in files if any(f.startswith(a.rstrip("/")) for a in args)]
    cur = None
    for f in sorted(files, key=lambda f: (os.path.dirname(f), os.path.basename(f))):
        d = os.path.dirname(f) or "."
        if d != cur:
            print(f"\n{d}/")
            cur = d
        p = os.path.join(ROOT, f)
        doc, names = py_info(p) if f.endswith(".py") else sh_info(p) if f.endswith(".sh") else ts_info(p)
        line = f"  {os.path.basename(f)}"
        if doc:
            line += f" — {doc}"
        if names:
            shown = ", ".join(names[:8]) + (" …" if len(names) > 8 else "")
            line += f"  [{shown}]"
        print(line)
    print(f"\n{len(files)} files. Architecture notes: docs/CODEMAP.md. Scenarios: tests/scenarios/README.md.")


if __name__ == "__main__":
    main()
