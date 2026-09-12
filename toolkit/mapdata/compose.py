"""ONE archive. Every authored thing a run needs, in one Gw.dat, from a manifest.

    python toolkit/mapdata/compose.py --name slice --plan
    python toolkit/mapdata/compose.py --name slice --build
    python toolkit/mapdata/compose.py --name slice --build --fresh
    python toolkit/mapdata/compose.py --name slice --verify
    python toolkit/mapdata/compose.py --name slice --readback

WHY IT EXISTS (SLICE-B9, studies/slice/PLAN.md section 5). `vault/run/` holds six
run directories and each is a separate Gw.dat with different authored content:
the quest name "A First Errand" renders only against `reskin-roster`, the
created map chains 0x5F0B0/1/2 live only in the July `-probe` copy, and the
canonical directory the harness launches by default holds NEITHER. Every run
so far reached its result by launching whichever archive happened to hold the
one thing it was testing. A vertical slice needs a corridor, a quest string and
its creature names ON ONE SCREEN, which means in one archive, and that assembly
had never been done.

WHAT IT IS. A manifest row in `content/compose.toml` names a run directory and
what goes into it, and this drives the two writers that already exist and are
already client-proven -- `textwrite.py` for strings, `deploy.py --install` for
areas -- one after the other into one archive, then reads the result back
through the client's own resolvers. It writes nothing itself: `datwrite`,
`datmove` and `datalloc` are reached only through those two tools, so every
guard they carry (the `C:\\gw` and `dat_study` refusals, the journal, the
allocation evidence, the bit-31 sibling check) is theirs and runs unchanged.

THE RECORD A STRING GOES IN IS DERIVED, NEVER TYPED. `[[strings]]` names its
CONSUMER -- `quest = "rurik_first_errand"` or `npc = "<key>"` -- and the record
comes from that row's own `enc_name`, the wire words the server actually sends,
through `codedstr.decode_id`. So a manifest cannot author a string no message
refers to, cannot put "A First Errand" at record 201 while the quest row says
200, and a retail name (four opaque ids, not ours) is refused rather than
overwritten. That is the join `textwrite.name_assignment` exists for, applied to
the two tables that carry names on the wire.

THE SOURCE IS A NAMED, UNCHANGING FILE. The archive is copied from the pristine
client snapshot the row names (`dat_source`), never from the canonical run
directory -- the client WRITES to the archive it runs from (`make_run_dir.py`'s
header), so "whatever the canonical copy holds today" is not a baseline anybody
can rebuild from. The exe and its support files come from the pinned build's
canonical run directory through `drive_client.select_run_exe`, by BUILD and by
name and never by mtime. A copied exe carries the source's digest, so
`pinned.py` already accepts it.

IDEMPOTENT, BY READING FIRST. A string whose record already holds its text is
not rewritten; an area whose chain already exists is re-installed in place by
`deploy`'s own idempotent loop. `--fresh` puts the archive back to the source
copy and removes the build products this tool and `deploy` left beside it, by
name, listing each one, because a stale allocation journal beside a fresh
archive is a `create_chain` refusal on the next line.

NOTHING HERE LAUNCHES A CLIENT. `overlay.py`'s separation is kept on purpose:
staging bytes is one tool and launching is another, so the launch re-runs its
own gates. `--verify` prints the harness recipe, in PowerShell, with `RURIK_DAT`
pointed at this archive -- the server must path against the mesh the client
draws (`deploy.launch`'s comment on why, and `contentids.preflight` refuses the
launch otherwise).

Exit codes follow `datcheck.py`: 0 the verb ran and verified, 1 a verification
found something (a string that does not read back, a chain that is not ours),
2 refused.
"""
import argparse
import datetime
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
for _p in (HERE, TOOLKIT, os.path.join(TOOLKIT, "clientscan"),
           os.path.join(TOOLKIT, "clientpatch"), os.path.join(TOOLKIT, "harness")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import content as content_mod                                    # noqa: E402
import vaultpath                                                 # noqa: E402
import codedstr                                                  # noqa: E402
import textrec                                                   # noqa: E402
import textwrite                                                 # noqa: E402
import mapchain                                                  # noqa: E402
from archive import Archive, file_id_table                       # noqa: E402

KIND = "compose"
# The files a run directory needs beside the exe. `make_run_dir.SUPPORT` minus
# Gw.dat, which comes from `dat_source` and not from the canonical directory.
SUPPORT = ("OpenAL32.dll", "steam_api.dll", "steam_appid.txt")
FILE_LO = textwrite.FILE_INDEX * textrec.RECORDS_PER_FILE
FILE_HI = FILE_LO + textrec.RECORDS_PER_FILE          # exclusive


class Refused(SystemExit):
    pass


# ---------------------------------------------------------------- the manifest

class Rec:
    """One authored string: where it goes and who reads it."""

    def __init__(self, record, text, consumer):
        self.record = record
        self.text = text
        self.consumer = consumer

    @property
    def string_id(self):
        return textwrite.string_id(self.record)

    def __repr__(self):
        return f"Rec({self.record}, {self.text!r}, {self.consumer})"


def consumer_words(world, entry):
    """(label, enc_name words) for one `[[strings]]` entry, or refuse."""
    keys = [k for k in ("quest", "npc") if k in entry]
    if len(keys) != 1:
        raise Refused(
            f"a [[strings]] entry names exactly one consumer, `quest = ` or "
            f"`npc = `; this one has {keys or 'neither'}: {dict(entry)}")
    kind, key = keys[0], entry[keys[0]]
    try:
        row = world.get(kind, key)
    except Exception as exc:                                  # noqa: BLE001
        raise Refused(f"{kind} row {key!r} does not exist ({exc}); a string "
                      f"with no consumer is one nothing will ever send")
    words = row.get("enc_name")
    if not words:
        raise Refused(f"{kind} row {key!r} has no enc_name, so no wire message "
                      f"names a record for its string to go in")
    return f"{kind}.{key}", list(words)


def derive_record(label, words):
    """The file-98 record `words` denotes, or refuse. -> int

    Refuses everything that is not ONE id in OUR text file: a retail name is
    several opaque ids (`content/npcs.toml`'s header), and an id in any other
    file is ArenaNet's record, which this must never overwrite.
    """
    try:
        sid, used = codedstr.decode_id(words)
    except ValueError as exc:
        raise Refused(f"{label}: enc_name {words} is not a coded id: {exc}")
    if used != len(words):
        raise Refused(
            f"{label}: enc_name {[hex(w) for w in words]} decodes to id {sid} "
            f"in {used} word(s) with {len(words) - used} left over -- several "
            f"ids, which is what a RETAIL name looks like, not one authored "
            f"record. Refusing to overwrite it.")
    if not FILE_LO <= sid < FILE_HI:
        raise Refused(
            f"{label}: string id {sid} is in text file {sid // textrec.RECORDS_PER_FILE}, "
            f"not our file {textwrite.FILE_INDEX} ({FILE_LO}..{FILE_HI - 1}). "
            f"That is one of ArenaNet's records; textwrite only writes ours.")
    rec = sid - FILE_LO
    if rec < textwrite.FIRST_FREE_RECORD:
        raise Refused(
            f"{label}: record {rec} is the IDENTITY tier (0..{textwrite.FIRST_FREE_RECORD - 1}, "
            f"RESKIN.md 19.5) -- a profession name or attribute already on "
            f"screen. Not a place for a quest or creature name.")
    return rec


def string_records(world, row):
    """[Rec] from the manifest row's `strings`, records derived. -> list

    Two consumers may share a record only if they agree on the text -- the
    same string sent by two messages is one record; two DIFFERENT strings at
    one record is one of them silently reading as the other on screen.
    """
    out, by_record = [], {}
    for entry in row.get("strings") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("text"), str):
            raise Refused(f"a [[strings]] entry needs `text = \"...\"`: {entry!r}")
        text = entry["text"]
        if not text.strip():
            raise Refused(f"empty text for {entry!r}; an empty record is what "
                          f"the file already holds")
        label, words = consumer_words(world, entry)
        rec = derive_record(label, words)
        prior = by_record.get(rec)
        if prior is not None and prior.text != text:
            raise Refused(
                f"record {rec} is named twice with different text: "
                f"{prior.consumer} says {prior.text!r}, {label} says {text!r}. "
                f"One record holds one string.")
        if prior is None:
            r = Rec(rec, text, label)
            by_record[rec] = r
            out.append(r)
        else:
            prior.consumer += f" + {label}"
    return out


def manifest(world, name):
    """The `[compose.<name>]` row, checked for the fields the verbs need."""
    try:
        row = world.get(KIND, name)
    except Exception as exc:                                  # noqa: BLE001
        raise Refused(f"no [{KIND}.{name}] in content/ ({exc})")
    if os.sep in name or "/" in name or name in ("", ".", ".."):
        raise Refused(f"{name!r} is not a directory name; the run directory is "
                      f"vault/run/<name>")
    if not isinstance(row.get("dat_source"), str) or not row["dat_source"]:
        raise Refused(f"[{KIND}.{name}] needs `dat_source`, a vault-relative "
                      f"path to the PRISTINE archive to copy from")
    areas = row.get("areas") or []
    if not isinstance(areas, list) or not all(isinstance(a, str) for a in areas):
        raise Refused(f"[{KIND}.{name}].areas must be a list of area keys")
    for a in areas:
        world.get("area", a)                 # raises on a key nothing defines
    return row


# ---------------------------------------------------------------- the places

def run_dir(name):
    return str(vaultpath.vault_path("run", name))


def dat_path(name):
    return os.path.join(run_dir(name), "Gw.dat")


def exe_path(name):
    return os.path.join(run_dir(name), "Gw.exe")


def sources(row):
    """(canonical run dir, pristine archive path). Both must exist."""
    import drive_client                                          # noqa: E402
    exe, why = drive_client.select_run_exe()
    if exe is None:
        raise Refused(f"no canonical client to copy: {why}")
    src_dat = str(vaultpath.vault_path(*row["dat_source"].replace("\\", "/").split("/")))
    if not os.path.isfile(src_dat):
        raise Refused(f"dat_source {row['dat_source']!r} is not a file under the "
                      f"vault: {src_dat}")
    return os.path.dirname(exe), src_dat, why


def products(name, row):
    """Every file a build leaves beside the archive, by name. -> [path]

    Listed rather than globbed so `--fresh` removes exactly what this tool and
    `deploy` produce and nothing a person put there.
    """
    d = run_dir(name)
    out = []
    for a in row.get("areas") or []:
        out += [os.path.join(d, f"{a}.bin"),
                os.path.join(d, f"{a}_alloc.json"),
                os.path.join(d, f"{a}_baseline.json"),
                os.path.join(d, f"{a}_rebloat.json")]
    if os.path.isdir(d):
        out += sorted(os.path.join(d, f) for f in os.listdir(d)
                      if f.startswith(f"{name}_text_") and f.endswith(".journal"))
    return out


# ---------------------------------------------------------------- assembling

def assemble(name, row, fresh=False):
    """Copy the client and the pristine archive into vault/run/<name>."""
    from make_run_dir import copy_with_progress                 # noqa: E402
    src_dir, src_dat, why = sources(row)
    dest = run_dir(name)
    os.makedirs(dest, exist_ok=True)
    print(f"run directory {dest}")
    print(f"  client from  {src_dir}  ({why})")
    print(f"  archive from {src_dat}")
    if fresh:
        for p in [dat_path(name)] + products(name, row):
            if os.path.exists(p):
                print(f"  --fresh: removing {os.path.basename(p)} "
                      f"({os.path.getsize(p)} B)")
                os.chmod(p, 0o666)
                os.remove(p)
    plan = [("Gw.exe", os.path.join(src_dir, "Gw.exe"))]
    plan += [(n, os.path.join(src_dir, n)) for n in SUPPORT]
    plan += [("Gw.dat", src_dat)]
    for n, src in plan:
        dst = os.path.join(dest, n)
        if not os.path.exists(src):
            raise Refused(f"{n} missing at {src}")
        size = os.path.getsize(src)
        if os.path.exists(dst) and os.path.getsize(dst) == size:
            print(f"  {n:18s}present ({size / 1e6:.1f} MB)")
            continue
        print(f"  {n:18s}copying {size / 1e6:.1f} MB ...", flush=True)
        if n == "Gw.dat":
            secs = copy_with_progress(src, dst)
            os.chmod(dst, 0o666)          # the writers open it r+b
        else:
            shutil.copy2(src, dst)
            secs = 0.0
        print(f"  {n:18s}done in {secs:.1f}s")


def text_state(exe, dat, recs):
    """[(rec, current text or None)] -- what the archive holds now."""
    with textrec.TextIndex(exe, dat) as ti:
        return [(r, ti.get(r.string_id)) for r in recs]


def write_strings(name, exe, dat, recs, plan_only=False):
    """Drive textwrite for the records that do not already hold their text."""
    todo = [r for r, cur in text_state(exe, dat, recs) if cur != r.text]
    for r, cur in text_state(exe, dat, recs):
        state = "holds it" if cur == r.text else f"holds {cur!r}"
        print(f"  record {r.record} (id {r.string_id}) <- {r.text!r}  "
              f"[{r.consumer}]  archive {state}")
    if not todo:
        print("  every string is already in the archive; nothing to write")
        return 0
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    journal = os.path.join(os.path.dirname(dat), f"{name}_text_{stamp}.journal")
    argv = [sys.executable, os.path.join(HERE, "textwrite.py"),
            "--dat", dat, "--exe", exe]
    for r in todo:
        argv += ["--set", str(r.record), r.text]
    argv += ["--plan"] if plan_only else ["--arm", "--journal", journal]
    print(f"  textwrite: {len(todo)} record(s)"
          + ("" if plan_only else f", journal {os.path.basename(journal)}"))
    rc = subprocess.run(argv, text=True).returncode
    if rc != 0:
        raise Refused(f"textwrite exited {rc}")
    return len(todo)


def install_areas(row, dat, plan_only=False):
    """Drive deploy --install for each area, into THIS archive."""
    for a in row.get("areas") or []:
        argv = [sys.executable, os.path.join(HERE, "deploy.py"), "--area", a,
                "--dat", dat]
        if not plan_only:
            argv.append("--install")
        print(f"\n  deploy --area {a}" + ("" if plan_only else " --install"))
        rc = subprocess.run(argv, text=True).returncode
        if rc != 0:
            raise Refused(f"deploy --area {a} exited {rc}")


# ---------------------------------------------------------------- verifying

def verify(world, name, row, recs, exe, dat):
    """[(ok, label, detail)] -- read back through the client's own resolvers."""
    import datcheck                                              # noqa: E402
    out = []

    def ck(ok, label, detail=""):
        out.append((bool(ok), label, detail))

    try:
        gate = datcheck.assert_archive_safe(dat, why="compose")
        ck(True, "the archive passes the launch gate", gate["summary"])
    except SystemExit as exc:
        ck(False, "the archive passes the launch gate", str(exc))
        return out
    for r, cur in text_state(exe, dat, recs):
        ck(cur == r.text,
           f"string id {r.string_id} reads back as {r.text!r} [{r.consumer}]",
           "" if cur == r.text else f"archive holds {cur!r}")
    here = os.path.dirname(dat)
    with Archive(dat) as ar:
        raw = file_id_table(ar, raw=True)
        for a in row.get("areas") or []:
            area = world.get("area", a)
            map_row = world.get("map", str(int(area["map_id"])))
            fid = int(map_row["file_id"])
            chain = mapchain.map_chain(ar, fid)
            ck(chain is not None,
               f"area {a!r}: file id {fid:#x} (map {area['map_id']}) binds a "
               f"map chain", "" if chain else f"raw table: {raw.get(fid)}")
            if chain is None:
                continue
            head, partner = chain
            if map_row.get("created"):
                ev = mapchain.created_evidence(dat, here, a, fid, head.index,
                                               partner.index)
                ck(ev is not None,
                   f"area {a!r}: the chain is OURS -- the allocation journal "
                   f"beside the archive describes rows {head.index}/{partner.index}",
                   os.path.basename(ev) if ev else "no journal binds to this copy")
            ck(partner.size > 0,
               f"area {a!r}: the Stripped partner (row {partner.index}) holds "
               f"{partner.size} B", f"compression {partner.compression}")
            ck(head.size == 0 or True,
               f"area {a!r}: head row {head.index} is {head.size} B "
               f"({'armed, the client will compile' if head.size == 0 else 'compiled'})")
    return out


def readback(world, name, row, dat):
    """After a client run: did the client compile each area's map? -> (lines, bad)"""
    import deploy                                                # noqa: E402
    lines, bad = [], []
    for a in row.get("areas") or []:
        area = world.get("area", a)
        map_row = world.get("map", str(int(area["map_id"])))
        fid = int(map_row["file_id"])
        staged = os.path.join(run_dir(name), f"{a}.bin")
        if not os.path.isfile(staged):
            lines.append(f"  [FAIL] area {a!r}: no staged {os.path.basename(staged)} "
                         f"beside the archive -- was it ever installed?")
            bad.append(a)
            continue
        with open(staged, "rb") as fh:
            blob = fh.read()
        lines.append(f"area {a!r} (file id {fid:#x}):")
        ls, bs = deploy.readback(dat, fid, blob, area)
        lines += ls
        bad += [f"{a}: {b}" for b in bs]
    return lines, bad


def launch_recipe(world, name, row, recs):
    """The harness command, in PowerShell, with both halves on THIS archive."""
    dat, exe = dat_path(name), exe_path(name)
    # A NEW run directory is a new binary path, and the firewall cage names
    # binaries by path: the first launch is refused at `cage.assert_launch_safe`
    # until an ELEVATED shell has run the isolate script for it. Said here
    # rather than discovered at the refusal, which is where it was discovered.
    lines = [f"# once, in an ELEVATED PowerShell (a new run directory is uncaged):",
             "#   & toolkit" + r"\clientpatch\isolate_client.ps1 -Exe " + f'"{exe}"',

             f'$env:RURIK_DAT = "{dat}"']
    for a in row.get("areas") or []:
        area = world.get("area", a)
        lines.append(
            f'python toolkit/harness/session.py --replace --keep-open --hold 60 '
            f'--warn 3 --exe "{exe}" --game-args "--map {int(area["map_id"])} '
            f'--area {a}"')
    if recs:
        lines.append(f"# the strings: add --probe quest_name_authored to --game-args "
                     f"(record {recs[0].record} is in THIS archive)")
    return lines


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--name", required=True, help="the [compose.<name>] row")
    ap.add_argument("--plan", action="store_true",
                    help="derive the records, resolve the sources, say what "
                         "--build would do. Writes nothing.")
    ap.add_argument("--build", action="store_true",
                    help="assemble the run directory, write the strings, "
                         "install the areas, then verify")
    ap.add_argument("--fresh", action="store_true",
                    help="with --build: re-copy the archive from dat_source "
                         "first and remove the build products beside it")
    ap.add_argument("--verify", action="store_true",
                    help="read the archive back and print the launch recipe")
    ap.add_argument("--readback", action="store_true",
                    help="after a client run: did the client compile each area")
    ap.add_argument("--repo-content-only", action="store_true",
                    help="load content from the repo alone (see deploy.py)")
    args = ap.parse_args(argv)
    if not (args.plan or args.build or args.verify or args.readback):
        ap.error("pass --plan, --build, --verify or --readback")
    # The two writers run as subprocesses and write straight to the console;
    # without this, their output lands ABOVE the section header that names
    # which of them is running. Seen on the first build.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    world = (content_mod.load(vault_dir="") if args.repo_content_only
             else content_mod.load())
    row = manifest(world, args.name)
    recs = string_records(world, row)
    print(f"[{KIND}.{args.name}] {row.get('name', '')}")
    print(f"  {len(recs)} string(s), {len(row.get('areas') or [])} area(s): "
          f"{', '.join(row.get('areas') or []) or '-'}")
    for r in recs:
        print(f"  record {r.record} = id {r.string_id} = {r.text!r}  <- {r.consumer}")

    if args.plan:
        src_dir, src_dat, why = sources(row)
        print(f"  would copy the client from {src_dir} ({why})")
        print(f"  would copy the archive from {src_dat}")
        print(f"  into {run_dir(args.name)}")
        if os.path.isfile(dat_path(args.name)):
            print("\n  the archive is already there; against it:")
            write_strings(args.name, exe_path(args.name), dat_path(args.name),
                          recs, plan_only=True)
            install_areas(row, dat_path(args.name), plan_only=True)
        print("\n--plan: nothing written.")
        return 0

    if args.build:
        assemble(args.name, row, fresh=args.fresh)
        exe, dat = exe_path(args.name), dat_path(args.name)
        print("\nstrings:")
        write_strings(args.name, exe, dat, recs)
        print("\nareas:")
        install_areas(row, dat)

    if args.build or args.verify:
        exe, dat = exe_path(args.name), dat_path(args.name)
        if not os.path.isfile(dat):
            raise Refused(f"nothing at {dat}; --build first")
        print("\nverify -- through the client's own resolvers:")
        results = verify(world, args.name, row, recs, exe, dat)
        bad = 0
        for ok, label, detail in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}"
                  + (f"  ({detail})" if detail else ""))
            bad += not ok
        print(f"\n{len(results) - bad} of {len(results)} verified")
        if bad:
            return 1
        print("\nlaunch (PowerShell; the server paths against THIS archive):")
        for line in launch_recipe(world, args.name, row, recs):
            print(f"  {line}")

    if args.readback:
        dat = dat_path(args.name)
        lines, bad = readback(world, args.name, row, dat)
        for line in lines:
            print(line)
        if bad:
            print(f"\n{len(bad)} READBACK CHECK(S) FAILED")
            return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as exc:
        print(f"\nREFUSED: {exc}")
        sys.exit(2)
