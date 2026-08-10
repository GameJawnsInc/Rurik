"""Find names a function reads that nothing anywhere could have bound.

WHY THIS EXISTS. On 2026-08-10 `session.py` computed `labelling` in `main()` and read
it in `run_client()` -- a different scope. `ast.parse` accepts it, `py_compile` accepts
it, and every one of the 32 tests in the suite passed. It failed as
`NameError: name 'labelling' is not defined` thirty seconds into a real session, after
the client had launched, tearing the stack down and taking a capture with it. That is the
second bug in one session whose only witness was a human sitting in front of the thing.

This is a deliberately SMALL and DELIBERATELY CONSERVATIVE checker, not a pyflakes
clone. The design rule is that a false positive is much worse than a miss: a linter
people learn to ignore is a linter that is off. So it over-binds at every ambiguity --
a name is considered bound if it is stored ANYWHERE in the function's whole subtree
(including nested functions), anywhere at module scope, in any enclosing function, or in
builtins. What survives that is a name with no binder at all, which is the bug above.

WHAT IT CANNOT SEE, stated so the green is not read as more than it is:
  * anything reached through `globals()`, `setattr`, or a star-import (files with a
    star-import are SKIPPED and named, never silently passed)
  * names bound by a wildcard `except` alias after its block ends (Python deletes those;
    we treat them as bound, which is the conservative direction)
  * conditional definitions that never actually run
  * every runtime error that is not an unbound name

standard library only.
"""
import ast
import builtins
import os
import sys

BUILTINS = set(dir(builtins)) | {
    "__file__", "__name__", "__doc__", "__spec__", "__package__", "__loader__",
    "__builtins__", "__debug__", "WindowsError",
}


class StarImport(Exception):
    """A file we refuse to judge rather than judge wrongly."""


def _bound_in(node):
    """Every name this subtree could bind, being as generous as the grammar allows."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name == "*":
                    raise StarImport
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and getattr(n, "name", None):
            out.add(n.name)
        elif isinstance(n, ast.MatchMapping) and getattr(n, "rest", None):
            out.add(n.rest)
    return out


def _bound_at_module(tree):
    """Names bound at MODULE scope, without descending into function or class bodies.

    THE FIRST VERSION OF THIS FUNCTION MADE THE WHOLE CHECKER VACUOUS. It used the
    same full-subtree walk as `_bound_in`, so every local variable in every function
    counted as a module-level binding -- which is exactly the binding the bug needed
    to hide behind. Run against the committed source that actually crashed, it
    reported zero. A check that cannot fail is not a check, and this one was proved
    against the real defect before it was believed.

    `global X` anywhere in the file DOES bind X at module scope, so those are
    collected from the whole tree; nothing else is.
    """
    out = set()

    def visit(n):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
            return                      # its body is a different scope
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name == "*":
                    raise StarImport
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        for c in ast.iter_child_nodes(n):
            visit(c)

    for c in ast.iter_child_nodes(tree):
        visit(c)
    for n in ast.walk(tree):
        if isinstance(n, ast.Global):
            out.update(n.names)
    return out


def _functions(tree):
    """(node, enclosing_chain) for every function in the module, outermost first."""
    found = []

    def walk(node, chain):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((child, chain))
                walk(child, chain + [child])
            else:
                walk(child, chain)

    walk(tree, [])
    return found


def check_source(src, filename="<src>"):
    """[(lineno, name)] -- names read with no possible binder. Raises StarImport."""
    tree = ast.parse(src, filename)
    module_bound = _bound_at_module(tree)
    bad = []
    for fn, chain in _functions(tree):
        bound = set(module_bound) | BUILTINS | _bound_in(fn)
        for enc in chain:
            bound |= _bound_in(enc)
        for n in ast.walk(fn):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in bound:
                    bad.append((n.lineno, n.id))
    return sorted(set(bad))


def check_file(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return check_source(fh.read(), path)


def python_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in sorted(files):
            if f.endswith(".py"):
                yield os.path.join(base, f)


def main(argv=None):
    root = (argv or sys.argv[1:] or [os.path.dirname(os.path.abspath(__file__))])[0]
    bad, skipped, n = {}, [], 0
    for path in python_files(root):
        n += 1
        try:
            hits = check_file(path)
        except StarImport:
            skipped.append(path)
            continue
        except SyntaxError as ex:
            bad[path] = [(ex.lineno or 0, f"SyntaxError: {ex.msg}")]
            continue
        if hits:
            bad[path] = hits
    for path, hits in sorted(bad.items()):
        rel = os.path.relpath(path, root)
        for lineno, name in hits:
            print(f"{rel}:{lineno}: undefined name {name!r}")
    for path in skipped:
        print(f"SKIPPED (star-import, cannot judge): {os.path.relpath(path, root)}")
    print(f"\n{n} file(s) checked, {len(bad)} with an unbound name, "
          f"{len(skipped)} skipped")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
