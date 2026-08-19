r"""The client's own VENDOR screens, and the GmView templates that draw them.

    python toolkit/clientscan/vendorscreens.py

WHY THIS EXISTS. `GAME_SMSG 0x00C3`'s field 1 is a window KIND -- `[11, 0]` adds
the Buy/Sell tab pair to a merchant panel (`studies/newopcodes/FINDINGS.md`) --
and the obvious way to learn the rest of the enum was to send every small
integer and photograph the result. That costs ONE VALUE PER RUN, because an
unhandled kind ends the session, and thirteen values is most of an hour of a
human's machine.

This is the desk route, and it is better than the sweep rather than merely
cheaper: the client carries the SOURCE FILE NAME of every vendor screen it can
build, one per screen, under `Ui\Game\Vendor`. That is a structural fact about
the client's own UI -- the same class of thing as a struct offset or a table
stride -- and it enumerates the answer space directly instead of probing it.

IT ALSO MAKES EVERY FATAL SWEEP ARM INFORMATIVE, which is the part worth
keeping. A crash dialog names its file: kind 6 died on
`No valid case for switch variable 'faction'` /
`Ui\Game\Vendor\VnGuildAdjustFaction.cpp(87)`, which does not say "6 is
invalid" -- it says **6 is the guild-faction vendor and it wants a faction
field we never sent**. So a run that kills the client still identifies that
kind's screen, and the sweep is a naming exercise rather than a survival test.

Read-only. Standard library only -- no disassembler, so this keeps working on a
bare machine (CLAUDE.md carve-out (1) scopes capstone to two other files).

    Ui\Game\Vendor\*.cpp   the screens
    GmView-*               the view templates the frame layer instantiates
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import gwpe  # noqa: E402
import pinned  # noqa: E402

SEP = re.escape(b"\\")
VENDOR = re.compile(b"Ui" + SEP + b"Game" + SEP + b"Vendor" + SEP
                    + rb"[A-Za-z0-9_]+\.cpp")
TEMPLATE = re.compile(("G\x00m\x00V\x00i\x00e\x00w\x00-\x00"
                       "(?:[ -~]\x00){2,40}").encode("latin-1"))


def _pe():
    p = pinned.find()
    return gwpe.PE(p[0] if isinstance(p, tuple) else p)


def vendor_screens(pe=None):
    """Sorted source-file names under `Ui\\Game\\Vendor`, deduplicated."""
    pe = pe or _pe()
    return sorted({m.group(0).decode().rsplit("\\", 1)[-1]
                   for m in VENDOR.finditer(pe.data)})


def gmview_templates(pe=None):
    """{name: virtual address} for every `GmView-*` UTF-16 template name."""
    pe = pe or _pe()
    out = {}
    for m in TEMPLATE.finditer(pe.data):
        name = m.group(0).decode("utf-16-le")
        out.setdefault(name, pe.image_base + pe.off_to_rva(m.start()))
    return out


def main():
    pe = _pe()
    print(f"client: {pe.path}")
    screens = vendor_screens(pe)
    print(f"\n{len(screens)} source file(s) under Ui\\Game\\Vendor:")
    for n in screens:
        print(f"    {n}")
    tpl = gmview_templates(pe)
    print(f"\n{len(tpl)} GmView-* view template(s):")
    for n in sorted(tpl):
        print(f"    0x{tpl[n]:08X}  {n}")
    if not screens or not tpl:
        raise SystemExit("measured nothing: the scan found no screens or no "
                         "templates, which is a failure and not an answer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
