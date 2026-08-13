"""Turn a sweep run's screenshots into a page a person can label opcodes from.

`smsgsweep` scores an opcode by what the CLIENT SENDS BACK, and 239 of its rows came
back SILENT. Four of those four, re-sent with a meaningful payload, turned out to be
opening windows and printing chat (`studies/smsgsweep/FINDINGS.md` 3.4) -- a UI update
produces no network traffic, so the sweep's instrument cannot see it BY CONSTRUCTION.
This module reads the other channel: the screen, joined to the wire by wall clock.

    python toolkit/authsrv/shotlabel.py --run <harness run dir> [...]   # score + page
    python toolkit/authsrv/shotlabel.py --scan 20260813          # every run of a day
    python toolkit/authsrv/shotlabel.py --merge labels.json      # fold answers back

THE PAGE IS THE DELIVERABLE AND IT STAYS IN THE VAULT. A screenshot of the retail
client is ArenaNet's rendered expression, not a measurement of ours, so `resolve_out`
refuses every checkout of this repository the way `mapbuild` does and the page is
written under `vault/labelling/`. It is a local file. It never goes on the internet:
`CLAUDE.md` -- the vault is personal data from the owner's own account.

WHAT IS MEASURED, AND WHAT THE OPERATOR DECIDES. This module does not name anything.
It answers "did the screen change when this opcode landed, and where", which is a
number; the NAME comes from a person reading the picture, because that is what
`0x0033` -> Message of the Day was: the client's own title bar, read by eye. So the
page carries the evidence and an empty box, and `--merge` folds the answers back.

THE JOIN IS BY WALL CLOCK, NOT BY INDEX, and the first version of this got it wrong in
the way that matters. Hold shots are `hold001.png`... at a fixed cadence, and the
obvious reading -- "the send lands N seconds in, so shot N/cadence is the baseline" --
uses the CAPTURE's clock, which starts at the server connection and not at the hold.
Scored that way, `0x0033`'s Message of the Day window -- a 306x443 panel, unmissable to
the eye -- came out at 0.00008, because the baseline frame already had the window in
it and was being compared against another frame that also did. Joined by wall clock the
same run reads 0.05043 against a noise floor of 0.0037. The mtimes are the fact; the
cadence is an assumption.

FOUR REFUSALS, each a run this cannot honestly score:

  NO_BASELINE    no shot strictly before the send. Nothing to compare against.
  NO_AFTER       no shot after the send + `settle`. The effect had nowhere to land.
  SHARED_WINDOW  two or more sends inside one shot interval, so a change cannot be
                 attributed to either. This is the cadence/dwell contract: shots must
                 be faster than sends. It is REPORTED per opcode rather than fixed by
                 guessing which of the two did it -- same rule `smsgsweep` applies to
                 a crash window with two suspects.
  NO_FLOOR       no shot interval in the run is free of sends, so the run cannot
                 measure its own noise. A fixed threshold would be a number from
                 another machine, another map and another day.

THE NOISE FLOOR IS MEASURED IN THE RUN, for the reason the sweep measures its control
window in the run: a Guild Wars client is never still. Water animates, torches flicker,
the compass sweeps, and an idle frame pair in these runs scores 0.0015-0.0037 of pixels
changed. The flag threshold is `max(3 x floor, MIN_FLAG)` -- three times what this
client did while nothing was being asked of it, with a floor under it so a preternaturally
quiet run cannot flag a single antialiased pixel.

A CHANGED SCREEN IS NOT A NAMED OPCODE, and the page says so on every row. The score
says the pixels moved; whether they moved BECAUSE of this opcode is the operator's
call, and the adjacent-frame column is there to be read against it.
"""

import argparse
import datetime
import glob
import html
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import vaultpath                                                # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PIXEL_DELTA = 24        # per-channel delta before a pixel counts as changed
MIN_FLAG = 0.002        # 0.2% of pixels: the floor under the 3x-noise threshold
NOISE_MULT = 3.0
SETTLE = 0.30           # seconds after a send before a shot can show its effect
THUMB_W = 560           # page thumbnails; the full frame stays one click away

# The capture stamps `wall` to the SECOND, so a send recorded 21:47:09Z happened
# somewhere in [09.000, 10.000). A shot taken at 09.697 is therefore on an unknown
# side of it and may serve as NEITHER baseline nor after-frame. Ignoring this is not
# a rounding matter: run 20260812T174647 put hold005 at 09.697 and the Message of the
# Day window does not appear until hold006, so pairing 004->005 scored 0.37% and
# called a 306x443 panel QUIET. Discarding the ambiguous second scores it 5.04%.
STAMP_GRAN = 1.0

# The idle window the noise floor is measured in: the seconds before the send, which
# the probe guarantees are quiet (it waits `settle + control` before sending anything).
# It must NOT reach back to the start of the hold -- the first frames span the map
# load, and a loading screen against a world frame is 64% of pixels changed. Measured
# that way the floor was 64% and every one of the four KNOWN positives read QUIET.
CONTROL_SPAN = 8.0

# Below this many idle pairs the floor is not measured at all and the run is refused.
# Three, not two: with two pairs a median is their mean, so one load transition inside
# the window drags it half way -- and the point of the median is to survive exactly
# that. At --shots 1.0 an 8 s window yields about seven.
MIN_FLOOR_PAIRS = 3

# Pool drift pairs within this many seconds of the requested lag before taking their
# median. See `floor_at` -- a single load-to-world pair can otherwise own a lag outright.
LAG_POOL = 1.5

# A frame-to-frame change this large is not idle -- it is the map load finishing. The
# idle window is trimmed at the last one. See `drift_floor`: 64-82% for a loading
# screen against a world frame, 0.05-0.4% for an idle pair.
LOAD_JUMP = 0.20

MARK = "PROBE[smsgsweep]"


# ---------------------------------------------------------------- where it may write

def _inside(path, root):
    path, root = os.path.abspath(path), os.path.abspath(root)
    return path == root or path.startswith(root + os.sep)


def working_tree_roots():
    """Every checkout of this repository a write could land in.

    Same shape and the same reason as `mapbuild.working_tree_roots`: in a git worktree
    `REPO_ROOT` is NOT the main checkout, so a refusal that tested it alone would let
    a page of client screenshots be written straight into the other tree of the same
    repository.
    """
    roots = [os.path.abspath(REPO_ROOT)]
    dotgit = os.path.join(REPO_ROOT, ".git")
    if not os.path.isfile(dotgit):
        return roots
    try:
        with open(dotgit, "r", encoding="utf-8", errors="replace") as fh:
            line = fh.read().strip()
    except OSError:
        return roots
    if not line.startswith("gitdir:"):
        return roots
    gitdir = line.split(":", 1)[1].strip()
    if not os.path.isabs(gitdir):
        gitdir = os.path.join(REPO_ROOT, gitdir)
    node = os.path.abspath(gitdir)
    while os.path.basename(node) != ".git":
        parent = os.path.dirname(node)
        if parent == node:
            return roots
        node = parent
    main = os.path.dirname(node)
    if main and not _inside(main, roots[0]):
        roots.append(main)
    return roots


def resolve_out(path):
    """Where the page may be written. Every checkout is refused, always.

    The page embeds cropped frames of the retail client. That is ArenaNet's rendered
    expression rather than anything we measured, and `CLAUDE.md`'s provenance gate
    keeps it out of this repository permanently -- in EVERY tree, not just this one.
    """
    path = os.path.abspath(path)
    vault = os.path.abspath(vaultpath.vault_root())
    if _inside(path, vault):
        return path
    for root in working_tree_roots():
        if _inside(path, root):
            raise ValueError(
                f"refusing to write client screenshots into the working tree: {path}\n"
                f"  That tree is {root}"
                + (" -- the MAIN checkout, which this worktree shares a repository "
                   "with.\n" if root != os.path.abspath(REPO_ROOT) else "\n")
                + f"  Write under {vaultpath.vault_path('labelling')}.")
    return path


# ---------------------------------------------------------------- reading a run

def _wall(s):
    """A capture's `wall` stamp as a UTC-aware datetime. Granularity is one second."""
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc)


def sweep_sends(run_dir):
    """(opcode, wall, label) for every sweep send this run's own capture recorded.

    Read from the GAMESRV capture the run's report names, never from the newest file
    in the directory -- `smsgsweep --from-report` exists for the same reason.
    """
    rep = os.path.join(run_dir, "report.json")
    if not os.path.isfile(rep):
        return None, "no report.json -- the run did not finish"
    with open(rep, encoding="utf-8") as fh:
        report = json.load(fh)
    sends = []
    for cap in report.get("captures") or []:
        if "gamesrv" not in cap or not os.path.isfile(cap):
            continue
        with open(cap, encoding="utf-8") as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("kind") == "sent" and MARK in (ev.get("label") or ""):
                    sends.append((ev["opcode"], _wall(ev["wall"]), ev.get("label", "")))
    sends.sort(key=lambda s: s[1])
    return sends, None


def hold_shots(run_dir):
    """(path, mtime) for the hold screenshots, in time order.

    Only `hold*.png`. The action shots (`1-play.png`) and `final.png` bracket the run
    rather than sampling it, and `final.png` is taken AFTER the probe has finished --
    folding it in would give the last opcode a baseline from a different phase.
    """
    out = []
    for p in sorted(glob.glob(os.path.join(run_dir, "hold*.png"))):
        out.append((p, datetime.datetime.fromtimestamp(
            os.path.getmtime(p), datetime.timezone.utc)))
    out.sort(key=lambda s: s[1])
    return out


# ---------------------------------------------------------------- scoring

def _pil():
    try:
        from PIL import Image, ImageChops
        return Image, ImageChops
    except ImportError:
        return None, None


def diff_score(a_path, b_path):
    """(fraction of pixels changed, bbox) or (None, None) if the frames disagree in size.

    A size mismatch is REPORTED rather than resized away: the client window changed
    shape mid-run, and a resize would put a real difference on every pixel.
    """
    Image, ImageChops = _pil()
    if Image is None:
        return None, None
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    if a.size != b.size:
        return None, None
    d = ImageChops.difference(a, b)
    r, g, bl = d.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    mask = m.point(lambda p: 255 if p > PIXEL_DELTA else 0)
    changed = mask.histogram()[255]
    return changed / float(a.size[0] * a.size[1]), mask.getbbox()


def drift_floor(shots, wall, span=CONTROL_SPAN):
    """How much the screen moves ON ITS OWN over a lag of `lag` seconds: {lag: fraction}.

    THE FLOOR MUST BE MEASURED THE WAY THE SCORE IS, and the first two versions of this
    module were not. They compared CONSECUTIVE idle frames -- about 1 s apart -- while
    scoring every post-send frame against ONE baseline up to 9 s behind it. A scene that
    drifts slowly accumulates against a fixed baseline and barely moves between
    neighbours, so the two sides were not comparable and the difference was charged to
    the opcode.

    MEASURED 2026-08-13, and it is not subtle: six consecutive opcodes -- `0x0016`,
    `0x0032`, `0x0034`, `0x0036`, `0x003D`, `0x003F` -- all scored CHANGED at 0.37%
    against an adjacent-pair floor of 0.05%, and every one of them reported the SAME
    bounding box, (824, 491, 1113, ~724). That is the player standing in the middle of
    the screen, breathing. The opcode had nothing to do with it.

    So: for every lag k that fits inside the idle window, take the MEDIAN diff over all
    idle pairs separated by k. Median rather than max because a map-load transition can
    still land in the window and one such pair would otherwise be the whole curve, and
    over all pairs at that lag rather than one so a single frame cannot set it.
    """
    lo = wall - datetime.timedelta(seconds=span)
    idle = [s for s in shots if lo <= s[1] < wall]
    # TRIM AT THE LAST BIG TRANSITION, which is what `CONTROL_SPAN` was approximating
    # with a fixed number of seconds and could not do reliably. If the map load ends
    # inside the window, EVERY long-lag pair straddles it -- the load frame is at the
    # start, so there is nothing else at that lag to take a median against, and pooling
    # cannot help: `sustained` came out at -66.77% for a panel plainly on screen for the
    # whole strip. Dropping everything up to and including the jump leaves a genuinely
    # idle window, which is what this measurement claims to be about.
    #
    # LOAD_JUMP is not delicately tuned. A loading screen against a world frame is
    # 64-82% of pixels; an idle pair is 0.05-0.4%. Two and a half orders of magnitude
    # separate them and anything in between would do.
    for k in range(len(idle) - 1, 0, -1):
        s, _ = diff_score(idle[k - 1][0], idle[k][0])
        if s is not None and s > LOAD_JUMP:
            idle = idle[k:]
            break
    pairs = []
    for i in range(len(idle)):
        for j in range(i + 1, len(idle)):
            lag = round((idle[j][1] - idle[i][1]).total_seconds(), 1)
            s, _ = diff_score(idle[i][0], idle[j][0])
            if s is not None:
                pairs.append((lag, s))
    return pairs, len(idle)


def floor_at(pairs, lag, window=LAG_POOL):
    """The drift floor for a lag: the median over pairs at a SIMILAR lag.

    POOLED, not looked up exactly, and that is not a smoothing preference. The idle
    window can still contain the tail of the map load, and a load-to-world pair may be
    the ONLY pair at its particular lag -- at which point a per-lag median is that one
    contaminated value, and the excess for a frame near it comes out around -67%.
    MEASURED on the test's own standard fixture, where the load frame sits alone at
    lags 1.0, 2.5, 4.0, 5.5 and 7.0 while the clean pairs cluster at 1.5, 3.0, 4.5 and
    6.0. Pooling +/- `window` seconds puts several clean pairs beside each dirty one and
    the median goes back to describing the scene.

    Falls back to the nearest lag when the pool is empty, so a short strip still gets an
    answer rather than None. Returns None only when there are no pairs at all.
    """
    if not pairs:
        return None
    # WIDEN UNTIL THERE ARE ENOUGH TO TAKE A MEDIAN OF, rather than falling back to the
    # single nearest lag. A strip runs ~9 s past its baseline while the idle window is
    # 8 s, so lags past everything measured are the NORMAL case, not an edge one -- and
    # the nearest lag out there is the longest, which is exactly where a lone
    # load-to-world pair sits. Falling back to it put `sustained` at -66.77% on a panel
    # that was plainly on screen for the whole strip.
    span = window
    while True:
        near = [s for lg, s in pairs if abs(lg - lag) <= span]
        if len(near) >= MIN_FLOOR_PAIRS or span > 3600:
            break
        span += window
    if not near:
        near = [s for _lg, s in pairs]
    near.sort()
    mid = len(near) // 2
    return near[mid] if len(near) % 2 else (near[mid - 1] + near[mid]) / 2.0


def noise_floor(shots, wall, span=CONTROL_SPAN):
    """The MEDIAN change between consecutive shots in the idle window before a send.

    Returns (floor, n_pairs). THE WINDOW IS BOUNDED ON BOTH SIDES and both bounds are
    load-bearing. Later than `wall` and the effect is in the floor; earlier than
    `wall - span` and the MAP LOAD is -- the first hold frames are a loading screen,
    which against a world frame is 64% of pixels, and a floor of 64% scored all four
    known positives QUIET.

    THE MEDIAN RATHER THAN THE MAX, and that is the second version of this function.
    The max is the conservative reading of "ambient", and it is only as good as the
    assumption that everything in the window IS ambient -- but the window is a fixed
    number of seconds and the load is not, so a send early in the hold pulls the tail
    of the loading screen inside it. One such pair then IS the floor: measured on the
    test's own fixture, a window holding one load transition and two idle pairs scored
    81.86% by max and put the flag threshold above 100%, where nothing can ever be
    CHANGED. The median survives any minority of contaminated pairs, which is why
    MIN_FLOOR_PAIRS exists -- with two pairs a median is just their mean and a single
    load frame moves it half way, so a run that cannot produce three is REFUSED rather
    than scored against a number one frame can drag.

    A run with too few pairs returns (None, n) and its rows come back NO_FLOOR, rather
    than being given a constant from another machine, another map and another day.
    """
    lo = wall - datetime.timedelta(seconds=span)
    vals = []
    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        if a[1] < lo or b[1] >= wall:
            continue
        s, _ = diff_score(a[0], b[0])
        if s is not None:
            vals.append(s)
    if len(vals) < MIN_FLOOR_PAIRS:
        return None, len(vals)
    vals.sort()
    mid = len(vals) // 2
    floor = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2.0
    return floor, len(vals)


def score_run(run_dir, settle=SETTLE):
    """One row per sweep send, joined to the shots that bracket it.

    Every row carries its own verdict, and the four refusals are rows too -- an opcode
    this run could not score must be VISIBLE, so the next run can take it again.
    Dropping it is how a sweep silently reports a subset as the whole.
    """
    sends, err = sweep_sends(run_dir)
    if err:
        return {"run": run_dir, "error": err, "rows": []}
    shots = hold_shots(run_dir)
    if not sends:
        return {"run": run_dir, "error": "no sweep sends in the capture", "rows": []}
    if len(shots) < 2:
        return {"run": run_dir, "error": f"{len(shots)} hold shot(s) -- run with "
                                         f"--shots", "rows": []}
    # ONE OPCODE PER RUN, and this is a refusal rather than a preference. A window an
    # earlier opcode opened is still on screen when the next one lands, so it sits in
    # the next opcode's BASELINE and its own effect is scored against a contaminated
    # frame; worse, an opcode may only do anything BECAUSE of the state a previous one
    # left. Owner's call, 2026-08-13: take the extra hours and keep the readings clean.
    # A batched run is not scored badly here -- it is not scored.
    if len(sends) > 1:
        return {"run": run_dir, "rows": [],
                "error": f"{len(sends)} sweep sends in one run -- refusing to score. "
                         f"UI effects STACK: the window opened by "
                         f"0x{sends[0][0]:04X} is still on screen when "
                         f"0x{sends[1][0]:04X} lands, so it is in that opcode's own "
                         f"baseline. Re-run with one opcode per client launch "
                         f"(--only), which is what sweeploop_shots.py does."}

    opcode, wall, label = sends[0]
    floor, n_floor = noise_floor(shots, wall)
    pairs, n_idle = drift_floor(shots, wall)
    flag_at = None if floor is None else max(floor * NOISE_MULT, MIN_FLAG)
    row = {"opcode": opcode, "wall": wall.isoformat(), "label": label,
           "run": os.path.basename(run_dir)}
    # The stamp is only good to the second, so the whole second is ambiguous and no
    # frame inside it may play either role. See STAMP_GRAN.
    after_t = wall + datetime.timedelta(seconds=STAMP_GRAN + settle)
    before = [s for s in shots if s[1] < wall]
    after = [s for s in shots if s[1] >= after_t]
    if not before:
        row["verdict"] = "NO_BASELINE"
    elif not after:
        row["verdict"] = "NO_AFTER"
    elif floor is None:
        row["verdict"] = "NO_FLOOR"
    else:
        # A STRIP, NOT A PAIR, and the fourth known positive is why. `0x00C0` puts
        # UNFRAMED FLOATING TEXT in the world, which rises and fades in about two
        # seconds -- at a 2.3 s cadence it can land entirely between two frames, and
        # scored as one before/after pair it read 0.190%, BELOW the same run's idle
        # noise. Every frame after the send is therefore scored against the one
        # baseline and all of them are shown. `peak` catches a transient; `sustained`
        # -- the smallest of the last few -- is what a window that STAYS on screen
        # looks like, and the two together tell those apart without either being a
        # verdict.
        b = before[-1]
        strip = []
        for path, t in after:
            s, bbox = diff_score(b[0], path)
            # EXCESS over what the screen does by itself across the SAME lag. The raw
            # fraction is kept beside it because it is what a person sees in the
            # picture, but the verdict is on the excess -- see `drift_floor`.
            lag = (t - b[1]).total_seconds()
            fl = floor_at(pairs, lag)
            strip.append({"path": path, "score": s, "bbox": bbox,
                          "dt": (t - wall).total_seconds(), "lag": lag,
                          "drift": fl,
                          "excess": None if (s is None or fl is None) else s - fl})
        vals = [f["excess"] for f in strip if f["excess"] is not None]
        peak = max(vals) if vals else None
        raws = [f["score"] for f in strip if f["score"] is not None]
        raw_peak = max(raws) if raws else None
        tail = [f["excess"] for f in strip[-3:] if f["excess"] is not None]
        sustained = min(tail) if tail else None
        best = max(strip, key=lambda f: (f["excess"] is not None, f["excess"] or 0))
        row.update(before=b[0], strip=strip, peak=peak, sustained=sustained,
                   raw_peak=raw_peak, drift_lags=len({lg for lg, _ in pairs}),
                   after=best["path"], score=peak, bbox=best["bbox"],
                   verdict=("UNSCORABLE" if peak is None else
                            "CHANGED" if peak > flag_at else "QUIET"))
    return {"run": run_dir, "floor": floor, "floor_pairs": n_floor,
            "flag_at": flag_at, "shots": len(shots), "rows": [row], "error": None}


# ---------------------------------------------------------------- the page

def _thumb(src, out_dir, name, bbox=None, pad=40, width=THUMB_W, quality=78):
    """Write a page-sized copy, cropped to the changed region when there is one.

    `width=0` writes at NATIVE resolution. That is what the detail crop uses: the
    frames are 1936x1040 and the strip shows them at 560, a 3.5x downscale that turns
    every line of client text into grey mush. An operator naming a panel needs to READ
    it, and a native crop of the changed region is the only image here that lets them.
    """
    Image, _ = _pil()
    if Image is None:
        return None
    im = Image.open(src).convert("RGB")
    if bbox:
        x0, y0, x1, y1 = bbox
        box = (max(0, x0 - pad), max(0, y0 - pad),
               min(im.size[0], x1 + pad), min(im.size[1], y1 + pad))
        im = im.crop(box)
    if width and im.size[0] > width:
        h = int(im.size[1] * width / float(im.size[0]))
        im = im.resize((width, max(1, h)), Image.LANCZOS)
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, name)
    im.save(dst, "JPEG", quality=quality)
    return name


def _full_rel(out_dir, src):
    """A page-relative path to the ORIGINAL png, for the lightbox.

    The strip is thumbnails and must stay that way -- 2,400 full frames is 8 GB and a
    page no browser will open -- so the full-resolution image is LINKED rather than
    copied. Both live under the vault, so this is a short relative hop and the page
    keeps working from `file://` with nothing copied and nothing served.
    """
    try:
        return os.path.relpath(src, out_dir).replace("\\", "/")
    except ValueError:
        return None            # different drive; the lightbox degrades to the thumbnail


_catalogue_failed = set()


def _catalogue(opcode):
    """The opcode's catalogued field list, so the picture is read beside the layout."""
    # `Codec()` -- there is no `Codec.load()`, and the first version called one behind a
    # bare `except Exception: return ""`. Every card on the page carried an EMPTY field
    # list and the build printed nothing, so the layout an operator reads the picture
    # against was silently absent from all 238. The except stays (a page is still worth
    # having without the schema) but it now reports, because a swallowed failure that
    # renders as a blank field is indistinguishable from an opcode that has no fields.
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "schema"))
        from codec import Codec
        # A field carries `type` and `length`; `name` is present only where the catalogue
        # has one, so the first version's `f['name']` raised KeyError on EVERY opcode.
        # The header row is dropped -- its `length` is the opcode, not a payload width,
        # and printing it as a field invites reading it as one.
        fields = [f for f in Codec().fields_for("GAME_SMSG", opcode)
                  if f.get("type") != "msg_header"]
        return ", ".join(
            (f"{f['name']}:{f['type']}" if f.get("name") else str(f.get("type")))
            + (f"[{f['length']}]" if f.get("length") else "")
            for f in fields) or "(no payload fields)"
    except Exception as exc:
        _catalogue_failed.add(f"0x{opcode:04X}: {type(exc).__name__}: {exc}")
        return ""


def build_page(results, out_dir, title="smsgsweep -- name the silent opcodes"):
    """Write the labelling page and its images. Returns the page path."""
    out_dir = resolve_out(out_dir)
    img_dir = os.path.join(out_dir, "img")
    os.makedirs(img_dir, exist_ok=True)
    rows = []
    for res in results:
        for r in res["rows"]:
            r = dict(r)
            r["flag_at"] = res.get("flag_at")
            r["floor"] = res.get("floor")
            rows.append(r)
    rows.sort(key=lambda r: (r.get("verdict") != "CHANGED", r["opcode"]))
    cards = []
    for i, r in enumerate(rows):
        op = f"0x{r['opcode']:04X}"
        key = f"{op}_{r['run']}"
        frames = []
        if r.get("before"):
            # The WHOLE FRAME for the baseline and every strip frame: a crop to the
            # changed region answers "what moved" and hides "what else is on screen",
            # and the operator is reading these to recognise a panel, a chat line or
            # a world label -- all of which are identified by WHERE they sit.
            b = _thumb(r["before"], img_dir, f"{key}_base.jpg")
            frames.append({"src": f"img/{b}", "cap": "baseline", "score": "",
                           "full": _full_rel(out_dir, r["before"])})
            for i, f in enumerate(r.get("strip") or []):
                n = _thumb(f["path"], img_dir, f"{key}_{i:02d}.jpg")
                frames.append({
                    "src": f"img/{n}",
                    "cap": f"+{f['dt']:.1f}s",
                    "score": "--" if f["score"] is None else f"{f['score']*100:.2f}%",
                    "full": _full_rel(out_dir, f["path"])})
        # THE DETAIL CROP, and it is the one image on this page meant to be READ rather
        # than recognised. The strip answers "did something appear and where"; it cannot
        # answer "what does it say", because 1936 px of client downscaled to 560 loses
        # every glyph. So a CHANGED row also gets the peak frame cropped to the changed
        # region at NATIVE resolution -- which for a dialog or a toast is the text.
        detail = None
        if r.get("verdict") == "CHANGED" and r.get("after") and r.get("bbox"):
            d = _thumb(r["after"], img_dir, f"{key}_detail.jpg", bbox=r["bbox"],
                       pad=12, width=0, quality=92)
            if d:
                detail = {"src": f"img/{d}", "full": _full_rel(out_dir, r["after"])}
        peak, sus = r.get("peak"), r.get("sustained")
        cards.append({
            "id": key, "op": op, "run": r["run"], "verdict": r["verdict"],
            "score": "--" if peak is None else f"{peak * 100:.2f}%",
            "sustained": "--" if sus is None else f"{sus * 100:.2f}%",
            "flag": "--" if not r.get("flag_at") else f"{r['flag_at'] * 100:.2f}%",
            "fields": _catalogue(r["opcode"]),
            "frames": frames, "shared": ", ".join(r.get("shared_with") or []),
            "detail": detail,
        })
    # A PARTIAL BUILD IS ADDITIVE, and this is the correction to a destructive design.
    # The cleanup below drops images the page no longer references, which is right in
    # itself -- a stale frame from an earlier scoring rule looks like evidence and is
    # not. But the first version took "referenced" to mean "written by THIS build", so
    # scoring one run rebuilt index.html with ONE card and deleted the other 2,400
    # images. It happened: a `--run` over a single opcode reduced a 238-card page to a
    # single card, and only the run directories being untouched made it recoverable.
    #
    # So the cards are persisted beside the page and every build renders the UNION:
    # this build's rows replace their own ids and everything else carries. That also
    # makes adding a run CHEAP -- the 25 minutes is the SCORING, and re-scoring 237
    # unchanged runs to add one was always the wrong shape.
    ledger_path = os.path.join(out_dir, "cards.json")
    prior = []
    if os.path.isfile(ledger_path):
        try:
            with open(ledger_path, encoding="utf-8") as fh:
                prior = json.load(fh)
        except (OSError, ValueError):
            prior = []                      # unreadable: this build is the whole page
    fresh_ids = {c["id"] for c in cards}
    merged = cards + [c for c in prior if c.get("id") not in fresh_ids]
    merged.sort(key=lambda c: (c.get("verdict") != "CHANGED", c.get("op", "")))
    # A card whose images are gone would render as broken boxes and read as a run that
    # produced nothing, so a carried card is kept only while its frames are on disk.
    def _present(c):
        srcs = [f["src"] for f in c.get("frames") or []]
        if c.get("detail"):
            srcs.append(c["detail"]["src"])
        return all(os.path.isfile(os.path.join(out_dir, s.replace("/", os.sep)))
                   for s in srcs) if srcs else True
    dropped = [c["id"] for c in merged if c.get("id") not in fresh_ids and not _present(c)]
    if dropped:
        print(f"  {len(dropped)} carried card(s) dropped -- their frames are gone from "
              f"img/ (rebuild them with --from-state). First: {dropped[0]}")
    merged = [c for c in merged if c.get("id") in fresh_ids or _present(c)]
    cards = merged
    with open(ledger_path, "w", encoding="utf-8") as fh:
        json.dump(cards, fh)
    keep = {os.path.basename(f["src"]) for c in cards for f in c["frames"]}
    keep |= {os.path.basename(c["detail"]["src"]) for c in cards if c.get("detail")}
    for stale in os.listdir(img_dir):
        if stale not in keep:
            os.remove(os.path.join(img_dir, stale))
    if _catalogue_failed:
        print(f"  WARNING: no field layout for {len(_catalogue_failed)} opcode(s) -- "
              f"the cards show a blank layout. First: {sorted(_catalogue_failed)[0]}")
    page = os.path.join(out_dir, "index.html")
    with open(page, "w", encoding="utf-8") as fh:
        fh.write(_render(cards, title))
    return page, len(cards)


def _render(cards, title):
    changed = sum(1 for c in cards if c["verdict"] == "CHANGED")
    quiet = sum(1 for c in cards if c["verdict"] == "QUIET")
    refused = len(cards) - changed - quiet
    body = []
    for c in cards:
        if c["frames"]:
            strip = "".join(
                f'<figure><img loading=lazy src="{html.escape(f["src"])}" '
                f'data-full="{html.escape(f.get("full") or f["src"])}" '
                f'data-cap="{html.escape(c["op"])} {html.escape(f["cap"])}">'
                f'<figcaption>{html.escape(f["cap"])} '
                f'<b>{html.escape(f["score"])}</b></figcaption></figure>'
                for f in c["frames"])
            det = ""
            if c.get("detail"):
                d = c["detail"]
                det = (f'<figure class=detail><img loading=lazy '
                       f'src="{html.escape(d["src"])}" '
                       f'data-full="{html.escape(d.get("full") or d["src"])}" '
                       f'data-cap="{html.escape(c["op"])} changed region">'
                       f'<figcaption>the changed region, full resolution '
                       f'-- click for the whole frame</figcaption></figure>')
            imgs = f'<div class=strip>{strip}</div>{det}'
        else:
            imgs = (f'<p class=none>no frames -- {html.escape(c["verdict"])}'
                    + (f' with {html.escape(c["shared"])}' if c["shared"] else "")
                    + '</p>')
        body.append(f"""
<article class="card {c['verdict']}" data-op="{c['op']}" data-id="{c['id']}">
  <header>
    <h2>{c['op']}</h2>
    <span class="pill {c['verdict']}">{c['verdict']}</span>
    <span class=meta>peak {c['score']} &middot; sustained {c['sustained']}
      &middot; idle noise flags above {c['flag']} &middot; {c['run']}</span>
  </header>
  <p class=fields>{html.escape(c['fields'])}</p>
  {imgs}
  <div class=controls>
    <input class=label placeholder="what did it do? (the client's own words if it gave any)"
           data-id="{c['id']}" data-op="{c['op']}">
    <button data-v=ui>UI</button><button data-v=chat>chat</button>
    <button data-v=world>world</button><button data-v=nothing>nothing</button>
    <button data-v=unsure>unsure</button>
  </div>
</article>""")
    return f"""<!doctype html>
<meta charset=utf-8><title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: light dark; --bg:#fff; --fg:#111; --line:#d8d8d8; --card:#fafafa; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#14161a; --fg:#e8e8e8; --line:#31353c; --card:#1b1e24; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui,sans-serif;
        margin:0; padding:1.5rem; }}
h1 {{ font-size:1.3rem; margin:0 0 .3rem; }}
.summary {{ color:#888; margin:0 0 1rem; }}
.bar {{ position:sticky; top:0; background:var(--bg); padding:.6rem 0; border-bottom:1px solid var(--line); z-index:5; display:flex; gap:.6rem; flex-wrap:wrap; align-items:center; }}
.card {{ border:1px solid var(--line); background:var(--card); border-radius:10px;
         padding:1rem; margin:1rem 0; }}
.card header {{ display:flex; gap:.75rem; align-items:baseline; flex-wrap:wrap; }}
h2 {{ font:600 1.05rem ui-monospace,monospace; margin:0; }}
.pill {{ font-size:.72rem; padding:.15rem .5rem; border-radius:999px; border:1px solid var(--line); }}
.pill.CHANGED {{ background:#2b7a2b; color:#fff; border-color:#2b7a2b; }}
.pill.QUIET {{ opacity:.65; }}
.meta {{ color:#888; font-size:.8rem; }}
.fields {{ font:12px ui-monospace,monospace; color:#888; margin:.4rem 0 .7rem;
           overflow-x:auto; white-space:nowrap; }}
.strip {{ display:flex; gap:.5rem; overflow-x:auto; padding-bottom:.4rem; }}
.strip figure {{ flex:0 0 auto; width:270px; }}
.strip img {{ width:270px; cursor:zoom-in; }}
figure {{ margin:0; }} figcaption {{ font-size:.72rem; color:#888; }}
/* The detail crop is native resolution and must NOT be scaled to the card: shrinking
   it to fit is exactly the downscale it exists to undo. It scrolls instead. */
.detail {{ margin-top:.6rem; max-width:100%; overflow:auto; }}
.detail img {{ max-width:none; cursor:zoom-in; }}
#lb {{ position:fixed; inset:0; background:#000e; z-index:99; display:none;
       overflow:auto; text-align:center; }}
#lb.on {{ display:block; }}
#lb img {{ max-width:none; margin:2.2rem auto; border:0; cursor:zoom-out; }}
#lb img.fit {{ max-width:96vw; }}
#lbbar {{ position:fixed; top:0; left:0; right:0; padding:.4rem .8rem; background:#000c;
          color:#eee; font:12px ui-monospace,monospace; display:flex; gap:.8rem;
          align-items:center; }}
img {{ max-width:100%; border:1px solid var(--line); border-radius:6px; display:block; }}
.none {{ color:#a33; font-size:.85rem; }}
.controls {{ display:flex; gap:.4rem; margin-top:.8rem; flex-wrap:wrap; }}
input.label {{ flex:1 1 22rem; padding:.45rem .6rem; border:1px solid var(--line);
               border-radius:6px; background:var(--bg); color:var(--fg); }}
button {{ padding:.4rem .7rem; border:1px solid var(--line); border-radius:6px;
          background:var(--bg); color:var(--fg); cursor:pointer; }}
button.on {{ background:#2b7a2b; color:#fff; border-color:#2b7a2b; }}
.hide {{ display:none; }}
</style>
<h1>{html.escape(title)}</h1>
<p class=summary>{len(cards)} opcode run(s): <b>{changed} CHANGED</b>, {quiet} QUIET,
{refused} unscorable. A changed screen is evidence, not a name &mdash; read the picture.</p>
<div class=bar>
  <label><input type=checkbox id=onlych> only CHANGED (a hint, not a verdict)</label>
  <label><input type=checkbox id=onlyun> hide ones I've labelled</label>
  <button id=save>copy labels JSON</button>
  <button id=dl>download labels.json</button>
  <span id=count class=meta></span>
</div>
{''.join(body)}
<div id=lb>
  <div id=lbbar><b id=lbfit>fit to window</b><span id=lbcap></span>
    <span style="margin-left:auto">click anywhere or Esc to close</span></div>
  <img id=lbimg alt="">
</div>
<script>
const KEY = 'rurik-shotlabel';
const store = JSON.parse(localStorage.getItem(KEY) || '{{}}');
function put(id, op, patch) {{
  store[id] = Object.assign({{opcode: op}}, store[id] || {{}}, patch);
  localStorage.setItem(KEY, JSON.stringify(store));
  paint();
}}
document.querySelectorAll('.card').forEach(card => {{
  const id = card.dataset.id, op = card.dataset.op;
  const inp = card.querySelector('input.label');
  if (store[id]) {{ inp.value = store[id].text || '';
    card.querySelectorAll('button[data-v]').forEach(b =>
      b.classList.toggle('on', b.dataset.v === store[id].verdict)); }}
  inp.addEventListener('change', () => put(id, op, {{text: inp.value}}));
  card.querySelectorAll('button[data-v]').forEach(b =>
    b.addEventListener('click', () => {{
      card.querySelectorAll('button[data-v]').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      put(id, op, {{verdict: b.dataset.v}});
    }}));
}});
function paint() {{
  const ch = document.getElementById('onlych').checked;
  const un = document.getElementById('onlyun').checked;
  let shown = 0;
  document.querySelectorAll('.card').forEach(card => {{
    const done = !!store[card.dataset.id];
    let hide = false;
    if (ch && !card.classList.contains('CHANGED')) hide = true;
    if (un && done) hide = true;
    card.classList.toggle('hide', hide);
    if (!hide) shown++;
  }});
  document.getElementById('count').textContent =
    Object.keys(store).length + ' labelled, ' + shown + ' shown';
}}
// THE LIGHTBOX LOADS THE ORIGINAL PNG, not the thumbnail. The old handler widened the
// 560 px thumbnail to 1200 px, which is an upscale: it made the picture bigger and no
// more readable, which is the one thing an operator trying to read a toast needs.
const lb = document.getElementById('lb'), lbi = document.getElementById('lbimg'),
      lbc = document.getElementById('lbcap'), lbf = document.getElementById('lbfit');
function openLb(im) {{
  lbi.src = im.dataset.full || im.src;
  lbc.textContent = (im.dataset.cap || '') + '  ' + (im.dataset.full || '');
  lb.classList.add('on');
}}
document.addEventListener('click', e => {{
  const im = e.target.closest('.strip img, .detail img');
  if (im) {{ openLb(im); return; }}
  if (e.target.id === 'lbfit') {{
    lbi.classList.toggle('fit');
    lbf.textContent = lbi.classList.contains('fit') ? 'actual size' : 'fit to window';
    return;
  }}
  if (lb.classList.contains('on') && e.target.id !== 'lbcap') lb.classList.remove('on');
}});
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') lb.classList.remove('on');
}});
document.getElementById('onlych').addEventListener('change', paint);
document.getElementById('onlyun').addEventListener('change', paint);
document.getElementById('save').addEventListener('click', () =>
  navigator.clipboard.writeText(JSON.stringify(store, null, 1)));
document.getElementById('dl').addEventListener('click', () => {{
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(store, null, 1)],
                                        {{type: 'application/json'}}));
  a.download = 'labels.json'; a.click();
}});
paint();
</script>
"""


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", default=[], metavar="DIR",
                    help="a harness run directory; repeatable")
    ap.add_argument("--scan", default=None, metavar="PREFIX",
                    help="every harness run whose name starts with PREFIX")
    ap.add_argument("--merge", default=None, metavar="LABELS.JSON",
                    help="fold the operator's answers into schema/overrides.json")
    ap.add_argument("--apply", action="store_true",
                    help="with --merge: actually write. Default is a dry run.")
    ap.add_argument("--from-state", action="store_true",
                    help="the runs shotloop RECORDED, one per opcode (recommended)")
    ap.add_argument("--out", default=None, help="page directory (under the vault)")
    ap.add_argument("--settle", type=float, default=SETTLE)
    ap.add_argument("--json", action="store_true", help="print the scoring, no page")
    a = ap.parse_args(argv)

    if a.merge:
        r = merge_labels(a.merge, apply=a.apply)
        for op, name in r["wrote"]:
            print(f"  {op}  {name}")
        for op, text in r["skipped"]:
            print(f"  {op}  NO IDENTIFIER -- left out of the schema on purpose: "
                  f"{text[:60]}")
        for op, prior, name in r["conflicts"]:
            print(f"  {op}  REFUSED: already named {prior}, screen reading says {name}")
        print(f"{len(r['wrote'])} row(s) {'written to' if r['applied'] else 'would go to'} "
              f"{r['path']}; {len(r['skipped'])} skipped, {len(r['conflicts'])} refused")
        if not r["applied"]:
            print("  dry run -- pass --apply to write")
        return 0

    runs = list(a.run)
    base = os.path.join(vaultpath.vault_path("captures"), "harness")
    if a.scan:
        runs += [os.path.join(base, d) for d in sorted(os.listdir(base))
                 if d.startswith(a.scan)]
    if a.from_state:
        # ONE RUN PER OPCODE, and the loop's own state file is the authority on which.
        # A `--scan` over a date picks up superseded runs too -- an opcode whose first
        # attempt lost the foreground has two directories under the same prefix, and
        # scoring both puts two cards for one opcode on the page, one of them a refusal
        # for a reading that was retaken. The state file records exactly the run that
        # measured each opcode.
        sp = os.path.join(vaultpath.vault_path("probes"), "shotloop-state.json")
        if not os.path.isfile(sp):
            ap.error(f"no shotloop state at {sp} -- run shotloop.py first")
        with open(sp, encoding="utf-8") as fh:
            st = json.load(fh)
        runs += [os.path.join(base, e["run"])
                 for e in st.get("done", {}).values() if e.get("run")]
    seen, ordered = set(), []
    for r in runs:
        if os.path.abspath(r) not in seen:
            seen.add(os.path.abspath(r))
            ordered.append(r)
    runs = ordered
    if not runs:
        ap.error("name at least one --run, a --scan prefix, or --from-state")

    results, scored, refused = [], 0, 0
    for d in runs:
        res = score_run(d, a.settle)
        if res.get("error"):
            print(f"  skip {os.path.basename(d)}: {res['error']}")
            continue
        results.append(res)
        for r in res["rows"]:
            if r["verdict"] in ("CHANGED", "QUIET"):
                scored += 1
            else:
                refused += 1
        print(f"  {os.path.basename(d)}: {len(res['rows'])} send(s), "
              f"{res['shots']} shot(s), floor "
              + ("n/a" if res["floor"] is None else f"{res['floor'] * 100:.2f}%")
              + f" over {res['floor_pairs']} idle pair(s)")
        for r in res["rows"]:
            mark = "  <<<" if r["verdict"] == "CHANGED" else ""
            sc = "" if r.get("score") is None else f" {r['score'] * 100:6.2f}%"
            print(f"     0x{r['opcode']:04X} {r['verdict']:<14}{sc}{mark}")

    if not results:
        print("nothing scored -- no run produced both sweep sends and hold shots")
        return 2
    print(f"\n{scored} opcode(s) scored, {refused} unscorable")
    if a.json:
        print(json.dumps([{k: v for k, v in r.items() if k != "rows"} | {
            "rows": [{k: v for k, v in row.items()} for row in r["rows"]]}
            for r in results], indent=1, default=str))
        return 0
    out = a.out or os.path.join(vaultpath.vault_path("labelling"), "smsgsweep")
    page, n = build_page(results, out)
    print(f"page: {page}  ({n} card(s))")
    print("  local file, vault only -- it holds frames of the retail client")
    return 0


# ---------------------------------------------------------------- folding answers back

OVERRIDES = os.path.join(REPO_ROOT, "..", "schema", "overrides.json")


def merge_labels(labels_path, apply=False, overrides_path=None):
    """Fold the operator's answers into the wire schema, one row per NAMED opcode.

    `--merge` was in this module's docstring from the day it was written and was
    implemented by nothing -- the same shape as the blank field list: a promise with no
    code behind it, which reads as a finished feature.

    A row is written ONLY where the labels file carries an identifier. A screen reading
    that says WHAT THE OPCODE DRAWS does not always say what to CALL it: five opcodes in
    this run produce an indistinguishable account-name dialog, and naming them five
    things invents a distinction while naming them one thing asserts they are
    interchangeable. Neither is supported by a picture, so they are recorded in the
    study and left out of the schema. This function does not guess.

    The operator's VERBATIM text goes into `why` beside the run id, because the
    identifier is a reading and the words are the evidence for it.
    """
    with open(labels_path, encoding="utf-8") as fh:
        labels = json.load(fh)
    path = overrides_path or os.path.abspath(OVERRIDES)
    with open(path, encoding="utf-8") as fh:
        ov = json.load(fh)
    chan = ov.setdefault("channels", {}).setdefault("GAME_SMSG", {})
    wrote, skipped, conflicts = [], [], []
    for key, row in sorted(labels.items()):
        op = int(row["opcode"], 16)
        name = (row.get("name") or "").strip()
        if not name:
            skipped.append((row["opcode"], row.get("text", "")))
            continue
        slot = chan.setdefault(str(op), {"opcode": op})
        prior = slot.get("name")
        if prior and prior != name:
            # Never silently rename. A name already in the schema came from the wire or
            # from the binary; a screen reading is a weaker witness than either.
            conflicts.append((row["opcode"], prior, name))
            continue
        slot["name"] = name
        # The schema demands a declared confidence per name (test_codec), and a screen
        # reading has two grades: the client WROTE the words, or we inferred a purpose
        # from an animation. Default MEDIUM -- the weaker one -- so an unstated grade
        # cannot quietly enter the catalogue as a strong claim.
        slot["name_confidence"] = row.get("confidence") or "medium"
        run = key.split("_", 1)[1] if "_" in key else "?"
        slot["why"] = (
            f"OBSERVED on screen, {run}. One opcode sent to a fresh client with a real "
            f"encoded string, screenshots joined to the send by wall clock; the operator "
            f"read the frame and wrote: \"{row.get('text', '').strip()}\". "
            f"Class: {row.get('verdict', 'unclassified')}. The wire sweep scored this "
            f"row SILENT -- a UI update produces no c2s reply. "
            f"studies/smsgsweep/FINDINGS.md 7.6.")
        wrote.append((row["opcode"], name))
    if apply:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(ov, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    return {"wrote": wrote, "skipped": skipped, "conflicts": conflicts,
            "path": path, "applied": bool(apply)}


if __name__ == "__main__":
    raise SystemExit(main())
