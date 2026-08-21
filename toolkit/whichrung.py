"""Resolve a bare identifier to the documents that DEFINE it. `studies/idents` sec 4.

THE SENTENCE THIS EXISTS FOR is `studies/idents/HANDOFF.md` sec 1: a session writes
*"C-8 finished, looking into C-9 next, before D-1 can be approached"* and the reader
cannot tell which document defines `C-8`, what kind of thing it is, or whether `D-1`
exists at all. That handoff calls this tool "the cheapest possible mitigation" and says
to ship it even if nothing else lands -- because a naming convention only helps
documents written after it, and eighty were written before.

    python toolkit/whichrung.py C8
    python toolkit/whichrung.py C-8 --full     # print the whole defining row
    python toolkit/whichrung.py C8 --root PATH # resolve against another checkout

`C8` and `C-8` resolve to the SAME three sites, deliberately. The handoff's own
one-liner is literal and would separate them; it also calls the hyphen "a *weak*
signal ... not a rule and must not be taught as one", and the ambiguous sentence it is
quoting uses the hyphenated form. A resolver that answers the question actually asked
has to cross that line, so `identlint.normalize()` drops it.

WHAT THIS DOES NOT DO. It does not find every MENTION -- `grep` already does that, and
the answer is hundreds of lines of prose. It matches only the two shapes that INTRODUCE
a token (a table row or a heading opening with it), which is `identlint.py`'s definition
and its documented floor: a token defined in prose or in a bold list item will not be
found here, and a `NOT FOUND` from this tool means "no defining ROW or HEADING", never
"this token does not exist".

standard library only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identlint  # noqa: E402
from checks import _say  # noqa: E402


def resolve(root, token):
    """Every defining site for `token`. One home for the pattern: identlint's."""
    return identlint.defining_sites(root, token)


def main(argv):
    argv = list(argv)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 >= len(argv):
            _say("--root needs a path")
            return 2
        root = os.path.abspath(argv[i + 1])
        del argv[i:i + 2]  # or the path is mistaken for the token
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        _say(__doc__.strip().splitlines()[0])
        _say("\nusage: python toolkit/whichrung.py <token> [--full] [--root PATH]")
        return 2
    token = args[0]

    sites = resolve(root, token)
    if not sites:
        _say(f"{token}: NOT FOUND as a defining row or heading in "
             f"{', '.join(identlint.ROOT_DOCS)} or {identlint.STUDY_DIR}/.")
        _say("That is not proof it does not exist -- see this module's docstring "
             "for what the pattern cannot see.")
        return 1

    docs = sorted({s.path for s in sites})
    _say(f"{token}: {len(sites)} defining site(s) in {len(docs)} document(s)"
         + ("  -- AMBIGUOUS, the bare token does not name one thing"
            if len(docs) > 1 else ""))
    for s in sites:
        _say(f"  {s.path}:{s.line}  [{s.kind}]  {s.token}")
        _say(f"      {s.text if '--full' in argv else s.text[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
