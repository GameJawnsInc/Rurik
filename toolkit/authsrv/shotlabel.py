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

def _thumb(src, out_dir, name, bbox=None, pad=40):
    """Write a page-sized copy, cropped to the changed region when there is one."""
    Image, _ = _pil()
    if Image is None:
        return None
    im = Image.open(src).convert("RGB")
    if bbox:
        x0, y0, x1, y1 = bbox
        box = (max(0, x0 - pad), max(0, y0 - pad),
               min(im.size[0], x1 + pad), min(im.size[1], y1 + pad))
        im = im.crop(box)
    if im.size[0] > THUMB_W:
        h = int(im.size[1] * THUMB_W / float(im.size[0]))
        im = im.resize((THUMB_W, max(1, h)), Image.LANCZOS)
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, name)
    im.save(dst, "JPEG", quality=78)
    return name


def _catalogue(opcode):
    """The opcode's catalogued field list, so the picture is read beside the layout."""
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "schema"))
        import codec as codec_mod
        c = codec_mod.Codec.load()
        fields = c.fields_for("GAME_SMSG", opcode)
        return ", ".join(f"{f['name']}:{f['type']}" for f in fields) or "(no fields)"
    except Exception:
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
            frames.append({"src": f"img/{b}", "cap": "baseline", "score": ""})
            for i, f in enumerate(r.get("strip") or []):
                n = _thumb(f["path"], img_dir, f"{key}_{i:02d}.jpg")
                frames.append({
                    "src": f"img/{n}",
                    "cap": f"+{f['dt']:.1f}s",
                    "score": "--" if f["score"] is None else f"{f['score']*100:.2f}%"})
        peak, sus = r.get("peak"), r.get("sustained")
        cards.append({
            "id": key, "op": op, "run": r["run"], "verdict": r["verdict"],
            "score": "--" if peak is None else f"{peak * 100:.2f}%",
            "sustained": "--" if sus is None else f"{sus * 100:.2f}%",
            "flag": "--" if not r.get("flag_at") else f"{r['flag_at'] * 100:.2f}%",
            "fields": _catalogue(r["opcode"]),
            "frames": frames, "shared": ", ".join(r.get("shared_with") or []),
        })
    # Drop images this build did not write. The page is rebuilt as the loop adds runs,
    # and a stale frame from an earlier scoring rule is worse than a missing one: it
    # looks like evidence and is not. The labels themselves live in the browser's
    # localStorage keyed by opcode+run, so they survive a rebuild -- which is the
    # whole reason the page is regenerated in place rather than into a new directory.
    keep = {os.path.basename(f["src"]) for c in cards for f in c["frames"]}
    for stale in os.listdir(img_dir):
        if stale not in keep:
            os.remove(os.path.join(img_dir, stale))
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
                f'<figure><img loading=lazy src="{html.escape(f["src"])}">'
                f'<figcaption>{html.escape(f["cap"])} '
                f'<b>{html.escape(f["score"])}</b></figcaption></figure>'
                for f in c["frames"])
            imgs = f'<div class=strip>{strip}</div>'
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
.strip img.big {{ width:min(94vw,1200px); }}
figure {{ margin:0; }} figcaption {{ font-size:.72rem; color:#888; }}
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
document.querySelectorAll('.strip img').forEach(im =>
  im.addEventListener('click', () => im.classList.toggle('big')));
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
    ap.add_argument("--out", default=None, help="page directory (under the vault)")
    ap.add_argument("--settle", type=float, default=SETTLE)
    ap.add_argument("--json", action="store_true", help="print the scoring, no page")
    a = ap.parse_args(argv)

    runs = list(a.run)
    if a.scan:
        base = os.path.join(vaultpath.vault_path("captures"), "harness")
        runs += [os.path.join(base, d) for d in sorted(os.listdir(base))
                 if d.startswith(a.scan)]
    if not runs:
        ap.error("name at least one --run or a --scan prefix")

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


if __name__ == "__main__":
    raise SystemExit(main())
