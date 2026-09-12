"""The server's command line -- every flag, its default and its help.

WHAT THIS FILE IS. `build_parser()` and nothing else: the 195 `add_argument`
registrations `authsrv.py`'s `main()` parses `argv` with, lifted out of that file
verbatim (REFACTOR-SERVERARGS, 2026-09-11) with ONE line changed --
`description=__doc__` became `description=doc`, because `__doc__` here is THIS
module's docstring and the banner `--help` prints is `authsrv.py`'s. `main()`
passes it in, and `--help` is byte-identical across the move.

WHERE THE REST OF EACH FLAG LIVES: `authsrv.main()`. This file only DECLARES the
command line. Every flag's post-parse plumbing -- the `X = not a.no_x` global
rebinds, the pairwise refusals and `SystemExit` messages, the `[map]` startup
banners that print what each lever resolved to -- stays in `main()`, and that
split is deliberate: a reader asking "what does this flag do" goes to `main()`,
a reader asking "what is it called and what does it default to" comes here.

WHY KEYWORD-ONLY, REQUIRED, AND UPPER CASE. The defaults below READ module
globals of `authsrv.py`, and three of them (`GAME_SRV_HOST`, `GAME_SRV_PORT`,
`HOST_FIELD_ENCODING`) are `global`-rebound inside `main()`. A default here would
be evaluated at `def` time; a required keyword is read AT THE CALL, which is the
semantics the block had when it was inline. Same shape as
`zeroleadcompose.zero_lead_composition`'s four constants, and for the same reason.
NOTHING here imports `authsrv` -- that is the whole point, and a cycle would take
out every test file that imports the server, before one check of theirs ran.

WHO READS THIS FILE'S TEXT. Nine test files assert against the registrations
below -- test_agentlife, test_agtrack_guard, test_cancelwalk, test_clickecho,
test_d1lead, test_kbdsync, test_keepalive, test_router, test_stalepair -- and
they bind it as `ARGS_SRC` beside their existing read of `authsrv.py`.
`test_srclint` sec 9 walks every `help=` string here for a lone `%`.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labelrun  # noqa: E402


def build_parser(*, doc, GAME_SRV_HOST, GAME_SRV_PORT, HOST_FIELD_ENCODING,
                 TEST_SKILLBAR, GRANT_MIN_INTERVAL, PROF_WARRIOR,
                 VAULT_DEFAULT):
    ap = argparse.ArgumentParser(description=doc,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=6112)
    ap.add_argument("--bind", default="127.0.0.1",
                    help="Loopback address to listen on. Any 127.x.y.z works "
                         "without setup on Windows; a second alias (127.0.0.2) "
                         "lets a probe show WHICH configured host the client "
                         "dials, since ports alone cannot when they collide. "
                         "Refuses anything outside 127/8 -- this server is "
                         "local-only by design.")
    ap.add_argument("--skills", default=",".join(str(s) for s in TEST_SKILLBAR),
                    help="Comma-separated skill ids for the bar, 0 for an empty "
                         "slot. Ids are row indices into the client's own skill "
                         "table, so they must exist in the build being launched "
                         "(0..3442 here). Fewer than 8 are padded with zeros.")
    # DEFAULT CHANGED 2026-08-13, all -> corpus. `all` is MEASURED to crash the
    # client's own Skills panel: it unlocks 2,109 weapon modifiers and other
    # non-player rows that have no skill icon, and the loader asserts `fileId`
    # (File.cpp:367) building the list. `corpus` is the same run with membership
    # corrected and was observed listing 1,333 skills in 43 attribute groups with
    # the client answering every ping. A default that breaks the game the moment
    # a player presses K is not a default. studies/profession/RUNS.md §11.
    ap.add_argument("--unlocks", default="corpus",
                    help="Unlock bitmap sent as opcodes 29 and 219: 'all' "
                         "(ids 1..3442 -- NOT 0, see refuse_skill_zero), "
                         "'corpus' (only the 1,333 player-usable skills, "
                         "derived from the owner's own client at run time), "
                         "'none', 'bar' (exactly the --skills ids), or an "
                         "explicit comma-separated id list. Whether the client "
                         "REFUSES to draw a bar skill that is not unlocked is "
                         "NOT FOUND in every source we have; this flag exists "
                         "to settle it by experiment. 'all' is known to reach "
                         "a `fileId` assert (File.cpp:367) when the Skills "
                         "panel opens -- it unlocks 2,109 weapon modifiers and "
                         "other non-player rows that have no skill icon "
                         "(studies/profession/RUNS.md §11).")
    ap.add_argument("--keys")
    ap.add_argument("--vault", default=VAULT_DEFAULT)
    ap.add_argument("--host-encoding", choices=["sockaddr", "string"],
                    default=HOST_FIELD_ENCODING,
                    help="How to fill GAME_SERVER_INFO's 24-byte host field.")
    ap.add_argument("--game-host", default=GAME_SRV_HOST,
                    help="Address handed to the client in GAME_SERVER_INFO.")
    ap.add_argument("--game-port", type=int, default=GAME_SRV_PORT,
                    help="Port handed to the client in GAME_SERVER_INFO. "
                         "OBSERVED 2026-08-06 (handshake PLAN §10): the client "
                         "never dials it -- it dials --game-host at hardcoded "
                         "6112. Kept on the wire because retail put a real "
                         "value here and a probe may yet find what reads it.")
    ap.add_argument("--sessions",
                    help="Session store path. The self-test passes its own so it "
                         "cannot overwrite the token record a real client "
                         "established — the two used to share one file, and a "
                         "test run silently clobbered live state.")
    ap.add_argument("--once", action="store_true", help="exit after one connection")
    ap.add_argument("--tape", metavar="CAPTURE_DIR",
                    help="R1.5: replay a recorded LIVE session's server plaintext "
                         "on the game channel instead of our own map load, at the "
                         "timing the wire capture recorded. The auth channel stays "
                         "ours -- a verbatim auth replay answers the wrong request "
                         "ids. Refuses a capture that is not origin: live.")
    ap.add_argument("--tape-connection", metavar="CLIENT->SERVER", default=None,
                    help="which game channel of the capture to play; default is "
                         "the one with the most server plaintext.")
    ap.add_argument("--tape-no-transfer", action="store_true",
                    help="Stop the tape before the messages that hand the client to "
                         "another game server (0x01A5 + 0x0099 MAP_UPDATE_CURRENT), "
                         "so it stays in the map instead of dialling ArenaNet and "
                         "being refused by the cage. Implied by --labelrun, which "
                         "cannot survive the transfer.")
    ap.add_argument("--tape-rewrite-next", metavar="HOST[:PORT]", default=None,
                    help="R1.5 chaining: instead of stopping before the handoff, "
                         "repoint it at a loopback server we control, so the client "
                         "walks from this tape straight into the next one. 127/8 "
                         "only, and REFUSED otherwise -- a rewritten tape is "
                         "ArenaNet's own bytes with a destination of our choosing. "
                         "Mutually exclusive with --tape-no-transfer. Note the port "
                         "is probably decorative: the client is OBSERVED to dial "
                         "<host>:6112 regardless on the AUTH handoff, and whether "
                         "the GAME handoff behaves the same is UNVERIFIED, because "
                         "every recorded 0x01A5 advertises 6112 anyway. Passing an "
                         "explicit port is how that gets settled.")
    ap.add_argument("--tape-speed", type=float, default=1.0, metavar="X",
                    help="play faster or slower than recorded. 1.0 reproduces the "
                         "observed cadence; anything else changes the one property "
                         "the tape exists to reproduce, so say so when reporting.")
    ap.add_argument("--labelrun", nargs="?", const="combat", default=None,
                    choices=sorted(labelrun.SCRIPTS),
                    help="After the world is up (or after --tape finishes), walk "
                         "the operator through a numbered script printed to THIS "
                         "terminal, marking each step into the capture. Turns c2s "
                         "traffic into named human actions. THE SCRIPT MUST MATCH "
                         "THE WORLD THE TAPE LEAVES: `combat` (default) needs the "
                         "Lakeside tape, whose character has skills and whose map "
                         "has hostiles; `town` needs Ascalon City, which has NPCs, "
                         "merchants and 40 players but a skillbar of all zeros. "
                         "`labelrun.py --script NAME` prints one; "
                         "`labelrun.py --analyse` reads a result back.")
    ap.add_argument("--netgraph", nargs="?", const="0x04", default=None,
                    metavar="BYTE",
                    help="Send GAME_SMSG 0x016E once after the instance loads, "
                         "carrying this byte of UI-overlay flags. Default 0x04, "
                         "which is the bit the client tests before building the "
                         "net graph's LATENCY widget -- the readout our 0x000D "
                         "round trip feeds. The graph FRAME is a separate "
                         "object toggled by a keypress, so this alone may set "
                         "a bit nothing draws. studies/smsg, s_netGraph.")
    ap.add_argument("--probe", metavar="NAME",
                    help="After the character spawns, fire a scripted experiment at "
                         "the client. See --list-probes. Only affects a session you "
                         "ask for it in; the default path is untouched.")
    ap.add_argument("--persist", action="store_true",
                    help="Arm the character store (studies/character/"
                         "STORAGE.md §6): the roster, the char-select "
                         "settings write-back and the character sheet "
                         "(level, xp, skill points, attributes, factions "
                         "with their caps, titles) come from one JSON per "
                         "account under vault/state/characters/, seeded "
                         "with the default character on first login. OFF by "
                         "default and deliberately so: the suite, probes "
                         "and selftest captures rely on a deterministic "
                         "Test Warrior, and a store that armed itself would "
                         "make every run depend on the runs before it. "
                         "Professions, skillbar and unlocks stay flag-"
                         "driven (charstore.py says why).")
    ap.add_argument("--enemy-hit", type=float, default=None, metavar="FRACTION",
                    help="How much of the player's MAXIMUM health a hostile "
                         "swing takes, as a fraction. Default 0.10, which is "
                         "~10 swings and ~17 s to a death -- longer than the "
                         "14 s resurrection grace, so at the default a second "
                         "death can never land inside the window and that rule "
                         "cannot be watched at a client. This constant is ours "
                         "and always said so, which is why overriding it is a "
                         "knob rather than a lie. 0.35 gives a death in about "
                         "6 s.")
    ap.add_argument("--death-penalty", action="store_true",
                    help="Charge -15%% morale for every player death in every "
                         "map, instead of asking the map. OFF by default and "
                         "the default is RETAIL's answer rather than a stub: "
                         "GWW's \"Death Penalty\" lists pre-Searing deaths "
                         "among those that never incur one, and every map this "
                         "server ships is pre-Searing, so a faithful world "
                         "never fires the mechanic. This is how it gets "
                         "watched anyway -- the --explorable idiom, a switch "
                         "rather than a lie in content/maps.toml. "
                         "studies/morale/FINDINGS.md.")
    ap.add_argument("--secondary-bits", default=None, metavar="MASK|all|ids",
                    help="Send GAME_SMSG 0x00B6 in the spawn burst: which "
                         "professions the character may take as a SECONDARY. "
                         "'all' = ids 1..10, or a comma-separated id list, or "
                         "an integer mask (0x.. accepted). Default: not sent "
                         "at all, which reproduces ArenaNet -- 11 of 11 live "
                         "samples carry mask 0 for characters with nothing "
                         "unlocked. THE DROP-DOWN THAT READS THIS ONLY EXISTS "
                         "IN 15 ARENA MAPS (796 Codex Arena, 823-836), so "
                         "expect no visible effect anywhere else "
                         "(studies/profession/RUNS.md §13).")
    ap.add_argument("--spawn-profession", type=int, default=None, metavar="N",
                    help="Primary profession the SPAWN BURST's 0x00B7 carries "
                         f"(default {PROF_WARRIOR}). The clean delivery for a "
                         "custom id: bar, unlocks and attributes all arrive "
                         "AFTER it in the same burst, nothing is re-sent "
                         "mid-session, and opening the skills panel is the "
                         "session's first provocation (RUNS.md s8 -- a "
                         "mid-session re-send asserts the client even at a "
                         "legal profession). Out-of-band ids (11..255) are the "
                         "experiment and are announced loudly; the appearance "
                         "nibble stays at the default on purpose, being "
                         "different bound-checked storage.")
    ap.add_argument("--click-echo", action="store_true",
                    help="MOVECODE-K2. When a click is refused for STALENESS "
                         "(geo-stale) -- which during click-moving is "
                         "unsatisfiable, because the client sends no position "
                         "in that mode -- answer it with the VERBATIM clicked "
                         "point instead of saying nothing. Geometry refusals "
                         "still refuse. Off by default; it is the seventh "
                         "candidate in a family that killed six, and its "
                         "registered prediction is studies/movecode/FINDINGS.md "
                         "sec.1m.")
    ap.add_argument("--echo-any-refusal", action="store_true",
                    help="MOVECODE-R1-B2. Requires --click-echo. Answer a "
                         "refused click with the verbatim point for ANY "
                         "refusal reason, not just staleness -- deleting the "
                         "1.0 s freshness gate from the ANSWER decision while "
                         "leaving it on every path that COMPUTES from our "
                         "position belief. Warranted by ArenaNet rather than "
                         "by us: retail answered 22 of 32 live clicks with a "
                         "report over 1.0 s old, 13 over 10 s, and 5 with no "
                         "client position ever reported, all inside 0.065 s "
                         "(studies/movecode/FINDINGS.md sec.1p.3). Off by "
                         "default; it crosses sec.1m.3's deliberate scoping "
                         "and its registered prediction is beside "
                         "ECHO_ANY_REFUSAL in this file.")
    ap.add_argument("--answer-kbd-click", action="store_true",
                    help="MOVECODE-R1-B1. Stop dropping a click because the "
                         "player is also using the keyboard. Rule 1 of the "
                         "click grant refuses whenever the locally-driving "
                         "latch is younger than 3.0 s; retail answered 7 of 7 "
                         "such clicks within one RTT, so the refusal is ours "
                         "(sec.1p.10 item 1). On the LEGACY path the click "
                         "falls through to the RATE FLOOR, which still "
                         "holds-and-coalesces -- that is the pair contract "
                         "REALFIX sec.0.15 actually states, and it "
                         "deliberately stays. SINCE 2026-09-05 (1z-bh, review "
                         "sec.1.7) it also reaches the ROUTER's own drop in "
                         "router_answer_click, which the legacy path bypasses "
                         "-- under the shipped --router this flag was inert "
                         "and that drop had no arm. Off by default, and it is "
                         "a REVERT/DIAGNOSTIC arm, not a candidate default: "
                         "R1-B1 is REFUTED on the legacy path (sec.1q).")
    ap.add_argument("--keepalive-grant", action="store_true",
                    help="MOVECODE-K1. Re-grant the player's own last REPORTED "
                         "position, unclipped, whenever our model says the "
                         "client's SYNC copy has parked more than 100 u away. "
                         "The client keeps the agent twice and only the sync "
                         "copy is reachable from the wire, so this cannot move "
                         "the displayed body -- see studies/movecode/FINDINGS.md "
                         "sec.1i-1j. Off by default; it is the sixth candidate "
                         "in a family that killed five, and its registered "
                         "prediction is sec.1k.")
    ap.add_argument("--keepalive-separation", type=float, default=None,
                    metavar="U",
                    help="Override the 100.0 u band at which a parked twin is "
                         "re-granted. Refused without --keepalive-grant. Exists "
                         "for the NEGATIVE CONTROL: a huge value disarms the "
                         "re-grant while leaving every other term of the run "
                         "identical, which is the arm that tells a real effect "
                         "from a quiet session.")
    ap.add_argument("--list-probes", action="store_true",
                    help="Print the available probes, their questions and their "
                         "predictions, then exit.")
    ap.add_argument("--ping-seconds", type=float, default=None, metavar="S",
                    help="Override the 0x000C cadence (default 5.000, ArenaNet's own "
                         "measured value). Raise it ONLY for a run that needs the "
                         "client's reply as a liveness heartbeat -- the opcode sweep "
                         "localises a crash to the gap between two replies.")
    ap.add_argument("--click-sweep", action="store_true",
                    help="Cycle MOVE_TO_POINT's two plane fields through every "
                         "plausible assignment, one per click, and label each in "
                         "the log. Click the same wall or staircase repeatedly "
                         "and report which attempt numbers behaved; that "
                         "identifies the fields from the client instead of from "
                         "two sources that contradict each other.")
    ap.add_argument("--map", type=int, metavar="ID",
                    help="Put the character in this map instead of the one its "
                         "character record asks for. 146 is Lakeside County, "
                         "which is explorable and therefore the first place "
                         "combat can be tested; 148 is Ascalon City. INERT "
                         "under --tape: the tape's own 0x0195 decides what the "
                         "client loads, and it will happily draw a map it never "
                         "asked for.")
    ap.add_argument("--area", metavar="NAME",
                    help="Serve the POPULATION of this authored area: the "
                         "`content/world.toml` spawn rows carrying "
                         "`area = NAME`, at their own coordinates, each checked "
                         "against the navmesh before a body goes out. Replaces "
                         "the single global test enemy rather than adding to "
                         "it, since that one is placed by offset from the "
                         "player and would land in the middle of a zone that "
                         "has its own idea of what stands where.")
    ap.add_argument("--trace-move", action="store_true",
                    help="Trace every client position report against the "
                         "server's own belief, plus the verdict, the budget it "
                         "was scored against and the arm it arrived on, and the "
                         "origin each click's collision ray is cast from. The "
                         "drift story this flag was added to test is REFUTED -- "
                         "the integrator runs 282.3 u/s effective against a "
                         "client at 282 -- but a click-walk still sends no "
                         "position report at all, for up to 12.9 s measured, "
                         "and that silence is what the trace is now for.")
    ap.add_argument("--client-endpoint", action="store_true",
                    help="Answer every keyboard heading with the "
                         "CLIENT'S OWN endpoint -- its reported "
                         "position plus its own vec2 plus 0.5 u "
                         "along it, unclipped, which is retail's "
                         "own expression. The fifth candidate fix; "
                         "four are dead. Its prediction is stated at CLIENT_ENDPOINT and bounds BOTH the separation and the jump RATE, because the last one bounded size while the harm arrived as frequency.")
    ap.add_argument("--heading-grant", action="store_true",
                    help="REFUTED 2026-08-19 -- it CAUSES warps. Kept only so "
                         "the negative result is reproducible. Answers every "
                         "keyboard heading with a "
                         "0x0029 at the client's own proposed endpoint "
                         "(reported position + its own vec2, clipped), so the "
                         "destination armed in the client is refreshed roughly "
                         "twice a second and never matures. MEASURED in client "
                         "memory: agent+0x48 is set once at a grant and never "
                         "re-armed, and the client SNAPS to the granted point "
                         "at that exact millisecond -- seven arrivals observed, "
                         "98u to 5238u, all one code path. A far click is "
                         "therefore an 18-second time bomb. ArenaNet refreshes "
                         "at a median 0.492 s and 88.5%% of its player grants "
                         "answer a heading, so this is the shape we were "
                         "missing rather than a workaround. Score it with "
                         "toolkit/clientscan/movetap.py.")
    ap.add_argument("--zero-lead", action="store_true", default=None,
                    help="REALFIX-P2. ON BY DEFAULT since 2026-08-22 (owner's "
                         "ruling after REALFIX-L9; --no-zero-lead reverts). "
                         "Answer every keyboard "
                         "heading while moving with 0x0025 (unit direction, the "
                         "client's own movementType) and a 0x0029 at the "
                         "client's REPORTED POSITION VERBATIM -- no lead, no "
                         "clip, no staleness gate, no straight-shot gate -- "
                         f"rate-limited to one per {GRANT_MIN_INTERVAL:.2f} s "
                         "by _heading_grant_ok "
                         "(rule 2 only; the click arm's _grant_verdict would "
                         "emit ZERO here because the heading arm arms its own "
                         "locally-driving latch ten lines earlier). THE GROUND: "
                         "the client's history polyline extends only BACKWARDS "
                         "while it holds no destination, so LAG is on it by "
                         "construction and LEAD is not -- and both dead "
                         "candidates in this family granted 766 u ahead. It "
                         "DROPS the shipped `turned or not walking` gate, which "
                         "on click-free play opens on 11-81%% of moving "
                         "reports, and that extra cadence is NOT free: the "
                         "drafted claim that a zero-distance grant takes the "
                         "<=1.0 u short-circuit is RETRACTED (that compare "
                         "measures from the SYNC COPY, and 353 of 358 "
                         "synthesized grants bake a real leg). Stop arm and "
                         "click arm untouched -- a stop-arm grant is "
                         "--stop-echo and is refuted. A report the "
                         "position-trust guard REFUSES is still granted "
                         "verbatim and the SYNC model follows it: the client "
                         "says it is standing there, so the point is on its own "
                         "history polyline whatever we believe. REFUSES to "
                         "combine with --heading-grant, --client-endpoint or "
                         "--stop-echo (every other arm that answers the "
                         "player's movement with a player 0x0029, all three "
                         "refuted, all on the one shared grant clock); combines "
                         "with --grant-suppress, --resync and --click-sweep, "
                         "each with a printed note. Its prediction is printed "
                         "at startup. This is REALFIX-L1's treatment arm.")
    ap.add_argument("--no-zero-lead", action="store_false", dest="zero_lead",
                    help="Revert --zero-lead to the pre-2026-08-22 default "
                         "(no heading-arm grants). Also drops --plane-carry "
                         "unless that flag is passed explicitly, in which case "
                         "the composition check refuses -- the modifier cannot "
                         "run without its policy.")
    ap.add_argument("--plane-carry", action="store_true", default=None,
                    help="REALFIX-F1, the plane echo fix, and a MODIFIER ON "
                         "--zero-lead rather than a policy of its own: passed "
                         "without it the server REFUSES to start, because it "
                         "would otherwise be inert while the run log said 'F1 "
                         "arm'. It changes ONE wire field. Under --zero-lead "
                         "the 0x0029 carries (reported_plane, reported_plane); "
                         "field 4 is what the client writes to agent+0x80 on "
                         "the SYNC COPY, and that copy is one report-chord "
                         "(~515 u, REALFIX-W2) behind the client -- so on a "
                         "plane boundary we stamp the plane of where the CLIENT "
                         "is onto a copy standing somewhere else. F1 sends "
                         "instead the plane that arrived WITH the point the "
                         "copy is standing on, which under zero lead is the "
                         "PREVIOUS GRANT'S plane by construction, defaulting to "
                         "the current plane when there is no previous grant. No "
                         "navmesh: the rejected variant computes field 4 from "
                         "plane_at(copy_estimate), and plane_at's 9 failures out "
                         "of 198 are EXACTLY bridge-over-ground, which is this "
                         "map's site. WHAT EARNS IT: REALFIX-L3 measured 8 "
                         "plane-rewriting above-cut grants producing 3 warps "
                         "against 28 unchanged above-cut grants producing 0, "
                         "Fisher p=0.0078, with a P0 control that carried 7x "
                         "the plane mismatch and never moved its rendered copy "
                         "more than 43 u. Still NECESSARY-NOT-SUFFICIENT (5 of "
                         "the 8 did not warp). GROUNDED IN NPC GRANTS: retail's "
                         "field 3 leads field 4 in 75.4%% of 1,245 differing "
                         "rows, but that population is overwhelmingly NPCs and "
                         "the player-identified version is UNVERIFIED at 87%% "
                         "vs 39%% under two identification rules. Its prediction "
                         "and its named limit are printed at startup. ON BY "
                         "DEFAULT since 2026-08-22 whenever --zero-lead is on "
                         "(owner's ruling; --no-plane-carry reverts).")
    ap.add_argument("--no-plane-carry", action="store_false", dest="plane_carry",
                    help="Revert --plane-carry: send (reported_plane, "
                         "reported_plane) under --zero-lead, the pre-F1 wire "
                         "shape. The plane-echo warp class (REALFIX-L3/L4/L8) "
                         "comes back with it at plane boundaries.")
    ap.add_argument("--arrival-carry", action="store_true",
                    help="REALFIX-F1b, and it exists because F1's OWN PRIMARY "
                         "FALSIFIER FIRED. Also a MODIFIER ON --zero-lead "
                         "(refused without it), and MUTUALLY EXCLUSIVE with "
                         "--plane-carry -- the two write the same wire field. "
                         "F1 sends the PREVIOUS grant's plane, which corrects "
                         "a ONE-interval lag; its run (20260821T143411) left 5 "
                         "of 93 grants still mismatched against the SYNC "
                         "copy's own agent+0x80, all 5 above the gate-1 cut, "
                         "and every one is F1's own named limit -- a TWO-"
                         "interval lag, where the client had been on the new "
                         "plane for two grants while the copy was still on the "
                         "old one. F1b sends the plane of the grant the copy "
                         "has ARRIVED at, computed with the client's own bake "
                         "(arrival = send time + |dest - copy| / 288 u/s, the "
                         "0x005FE950 formula over our existing SYNC model) -- "
                         "no navmesh, no new constant. A grant that supersedes "
                         "a leg still in flight DISCARDS it, because the copy "
                         "re-aims mid-leg and never reaches that destination. "
                         "WHAT GROUNDS IT: in F1's own capture the SYNC copy's "
                         "plane word changes 24 times and 17 of those are NOT "
                         "at a grant -- all 17 land on a modelled ARRIVAL, "
                         "median |dt| 0.070 s against a 9.5 Hz tap, zero free "
                         "parameters. So field 3 is written to agent+0x80 at "
                         "arrival and field 4 at the grant, which is retail's "
                         "own lead/lag shape. Its prediction is printed at "
                         "startup, and so is the fact that F1's event "
                         "reduction was NOT significant (Fisher p = 0.196).")
    ap.add_argument("--cancel-answer", default=None, metavar="ARM",
                    help="CANCELWALK's pre-registered experiment arms, "
                         "DIAGNOSTIC ONLY, OFF by default, refused without "
                         "--zero-lead and with --arrival-carry. Changes the "
                         "answer to the ONE report whose movement press "
                         "cancelled a held action (the freeze: that press "
                         "opens a movement episode that moves 0.0 u while an "
                         "ordinary press walks -- "
                         "studies/movement/CANCELWALK.md F6, and 5 for the "
                         "run ladder these arms exist for). 'suppress' (R1) "
                         "answers with the release burst alone -- no 0x0025, "
                         "no 0x0029, zero warp exposure. 'retail-lead' (R2) "
                         "sends retail's cancel tail verbatim: 0x0025, "
                         "0x002B [1.0, movementType], 0x0029 at reported + "
                         "vec2 + 0.5u -- the D1 formula confirmed at cancel "
                         "instants 3 of 3. Its pre-registered cost: the SYNC "
                         "copy bakes a <=768.5 u leg along a STALE vector "
                         "and a +0x48 resync before the next report's "
                         "re-pin may snap visibly; that lands AFTER the walk "
                         "readout and is why R2 can never ship as-is. "
                         "'lead:<units>' (R3) is the bisection arm, 16 the "
                         "registered first rung. Either lead form takes an "
                         "optional ',stop' modifier (R4): while that leg is "
                         "in flight, a 0x0047 release is answered with "
                         "retail's own stop shape (0x002B [1.0, 9] + a "
                         "zero-distance 0x0029 at the reported point) -- "
                         "scoped to the leg window, never the general stop "
                         "arm, which is what keeps it from being the refuted "
                         "--stop-echo. NO ARM SHIPS FROM A RUN "
                         "DIRECTLY; a PASS licenses a candidate for a "
                         "separate audited step, and the zero-lead policy "
                         "is untouched on every other report.")
    ap.add_argument("--stop-answer", default=None, metavar="ARM",
                    help="CANCELWALK-R6's stop-closure arm, DIAGNOSTIC "
                         "ONLY, OFF by default, refused without --zero-lead "
                         "and with --cancel-answer. 'ack' answers EVERY "
                         "player 0x0047 stop report with s2c 0x0028 "
                         "[agent] -- retail's bare stop-ack, the LAST "
                         "movement-family message its client received "
                         "before the study capture's casts (CANCELWALK-F5/"
                         "F9). NOT a grant: no destination armed, no grant "
                         "clock stamped, and the 0x0028 handler is a no-op "
                         "on a body that already stopped itself. Tests "
                         "CANCELWALK-H6 (stop-closure prior state): H6 "
                         "predicts the single mid-cast press now WALKS; "
                         "H5-without-H6/H7/H4 predict it still freezes. "
                         "'repin' is deliberately unbuilt and refuses with "
                         "the reason. studies/movement/CANCELWALK.md 7.4.")
    ap.add_argument("--cast-stop", nargs="?", const="halt", default=None,
                    metavar="ARM",
                    help="CANCELWALK's cast-start halt. 'pin' is the "
                         "SHIPPED DEFAULT since 2026-08-25 (owner's "
                         "ruling, CANCELWALK.md 8.3g, after two clean "
                         "runs; --no-cast-stop reverts): the F28 fix -- "
                         "at a free-caster NON-ATTACK cast start, a "
                         "0x002C hard-set at the DEAD-RECKONED player "
                         "position then the 0x0028 halt on co-located "
                         "copies, or NOTHING when any belief door "
                         "refuses (pin-or-nothing, F34; the console "
                         "line names the door). Backward 0.00 u on 6 "
                         "of 6 measured casts. 'halt' (also bare "
                         "--cast-stop; R8): the diagnostic control -- "
                         "one bare 0x0028, which WARPS onto the sync "
                         "copy (F31 110-207 u; F34 167.6 u even "
                         "parked), REFUSED as a ship; explicit only. "
                         "Explicit arms are refused without --zero-lead "
                         "and with --cancel-answer, --stop-answer or "
                         "--arrival-carry ('pin' also with --resync); "
                         "the DEFAULT instead yields to those levers "
                         "with a printed note. "
                         "studies/movement/CANCELWALK.md 8.")
    ap.add_argument("--no-cast-stop", action="store_true",
                    help="Turn OFF the shipped cast-stop default "
                         "(--cast-stop=pin, ON by default since "
                         "2026-08-25 -- owner's ruling, CANCELWALK.md "
                         "8.3g). Contradicts an explicit --cast-stop "
                         "and is refused alongside one.")
    ap.add_argument("--resync", action="store_true",
                    help="SEVENTH candidate. Send GAME_SMSG 0x002C "
                         "AGENT_UPDATE_POSITION carrying the CLIENT'S OWN last "
                         "accepted position report, when our model of the "
                         "server-authoritative copy has drifted "
                         "RESYNC_SEPARATION units from it. It is the only "
                         "catalogued primitive whose handler reaches BOTH the "
                         "SYNC array at [agentMgr+0xE8] and the ASYNC array at "
                         "[agentMgr+0x14C] with no gate, and it calls "
                         "AgTrack::Clear first, so the three-gate desync test "
                         "cannot reseed the roster behind it. The trade it is "
                         "for: a small, frequent, correct correction against a "
                         "rare 3,648 u one. An earlier build sent five of these "
                         "carrying OUR INTEGRATOR'S position and they were "
                         "removed as 'the warp the player described' -- this "
                         "sends the client's own figure and refuses to send "
                         "anything else. OFF by default; independent of "
                         "--heading-grant and --client-endpoint, both REFUTED.")
    ap.add_argument("--no-agtrack-shadow", action="store_true",
                    help="Disable the AgTrack guard entirely (ON by "
                         "default; MOVECODE-1z-s): the history-chain mirror, "
                         "its telemetry (agtrack_guard rows per grant, "
                         "agtrack_repin transitions) AND the active re-pin, "
                         "which cannot run without the guard.")
    ap.add_argument("--windup-ratio", action="store_true",
                    help="Revert the swing windup to the legacy constant "
                         "fraction (0.4458 x declared interval). The default "
                         "is the derived law interval/2 - 0.1 s (ANIMREF-R1, "
                         "studies/animref/FINDINGS.md sec.1: residuals flat "
                         "at every declared interval, Power Shot retrodicted "
                         "to 1.3 ms; the constant was one law sampled at two "
                         "intervals).")
    ap.add_argument("--legacy-attack-e5", action="store_true",
                    help="Revert ANIMREF-R3 fix 3: a zero-activation attack "
                         "skill's E5 fires AT THE PRESS again, instead of one "
                         "weapon windup later. The A/B arm for 'attacks block "
                         "movement longer than stock' -- the fix widened that "
                         "window from 0 to ~0.775 s on a 1.75 s weapon, which "
                         "makes it the first suspect and therefore the thing "
                         "that has to be switchable.")
    ap.add_argument("--legacy-attack-finish", action="store_true",
                    help="Revert ANIMREF-R6: an attack skill's execution "
                         "goes back to the old shape -- no property 46, and "
                         "the damage through the interval-gated swing path "
                         "(so a press mid-chain deals nothing). The default "
                         "is the corpus batch (40/40): 46 opens, then "
                         "adrenaline, damage, E3, with no swing brackets. "
                         "This is also the movement-lock arm: without 46 the "
                         "client's attack-skill action never closes, and a "
                         "held movement key after a press moves 0.0 u where "
                         "retail moves within ~0.25 s of E3 (FINDINGS 11b, "
                         "13).")
    ap.add_argument("--no-skill-visuals", action="store_true",
                    help="Stop sending the on-body effect visual (properties "
                         "20/21) at a cast's landing. ON by default since "
                         "ANIMREF-R8: the component ids are read from the "
                         "client's own s_skill record (+0x78 caster, +0x7c "
                         "recipient) and carried per row in "
                         "content/world.toml's skill_visual block, so nothing "
                         "here is invented -- which is the condition R4's "
                         "refusal named. A skill with no row, or with the "
                         "client's own 2077 'no visual' default, sends "
                         "nothing either way.")
    ap.add_argument("--move-keeps-chain", action="store_true",
                    help="No-op since ANIMREF-RE 31: LAW A is the default "
                         "again, composed with the chain pause. Kept so "
                         "older runsheets parse.")
    ap.add_argument("--legacy-move-stops-chain", action="store_true",
                    help="THE REVERT ARM for the composed ANIMREF-RE 31 "
                         "default: movement closes the attack chain with "
                         "property 3 again AND the swing clock free-runs "
                         "while the body moves. Both halves off together, "
                         "because they are meaningless apart -- with the "
                         "chain closed on every move there is no chain to "
                         "pace. What the default does instead: keep the "
                         "chain (325 of 343 corpus mid-chain moves carry no "
                         "property 3) and freeze the swing clock while the "
                         "body moves, so the next attack-started fires one "
                         "interval after motion ends. Retail's ratio of "
                         "move-containing to quiet gaps is 1.51 (2.007 s "
                         "against a 1.330 s metronome); ours was 1.003. The "
                         "point is the ANIMATION: the client refuses a walk "
                         "cycle by priority while an attack animation is "
                         "latched (table 0x00A92ED8, locomotion 0x0040 "
                         "against 0x0110/0x0120), and retail sends no "
                         "pose-ender -- it lets the animation finish.")
    ap.add_argument("--e3-release", action="store_true",
                    help="Opt into the ANIMREF-RE E3 release: free the "
                         "action hold in the E3 batch, the caster-freed "
                         "instant (retail does, 19/19 unmoved corpus "
                         "cycles). This is the arm that ARMS the client's "
                         "250 ms resume poll via prop 8's gate-clear "
                         "(0x0081C090) -- and therefore the arm that can "
                         "move the body with no c2s report, which the "
                         "active re-pin would then yank. Shipped default "
                         "2026-09-01, reverted the same day; turn it on "
                         "ALONE to convict or clear it (FINDINGS 29).")
    ap.add_argument("--swing-holds-walk-gate", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 35: send the "
                         "property-8 action hold on every auto swing "
                         "again, as every build before 2026-09-01 did. "
                         "The default sends NONE, because property 8 "
                         "drives the client's walk gate and retail holds "
                         "it on 83 of 1,332 attack starts (6.2%%) against "
                         "our 52 of 52 (100%%). With the hold set a "
                         "pre-landing movement press met a shut gate 25 "
                         "times in 32, and a fifth of those episodes "
                         "travelled under 5 units in 1.5 seconds. Run "
                         "this arm to reproduce that on purpose. The CAST "
                         "path keeps its hold either way -- that one is "
                         "retail-correct and corpus-backed.")
    ap.add_argument("--click-latch-window", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 37: bound the "
                         "click-walk latch by the 3.0 s GRANT_LOCAL_WINDOW "
                         "constant again (34's shape) instead of by the "
                         "click leg's own travel time. Under the constant "
                         "a press after a short click waits out the rest "
                         "of the 3 s on a parked body (every one of the 13 "
                         "unanswered CLICK-last presses on the 14:32 "
                         "capture), and a press 3 s into a long click opens "
                         "a swing on a body still walking.")
    ap.add_argument("--attack-approach", action="store_true",
                    help="No-op since ANIMREF-RE 39: the approach is the "
                         "default. Kept so the CASE 7 command line still "
                         "parses.")
    ap.add_argument("--no-attack-approach", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 38: the press-time "
                         "reach back to the unmeasured 1500 u and no "
                         "follow -- a press from anywhere swings from where "
                         "you stand (the operator's 'i can attack from far "
                         "away'). The default is the derived 144 u reach "
                         "and retail's 0x002A follow to the target, "
                         "re-pathed every 0.5 s while it moves, the swing "
                         "opening when the body stops at r+r+56 = 80 u.")
    ap.add_argument("--enemy-chase-rate", type=float, default=None,
                    metavar="FRAC",
                    help="Override ENEMY_MOVE_RATE (default 1.0 = the 0x0020's "
                         "declared base, 288 u/s) for the run. ANIMREF-RE 40.9: "
                         "retail's hostiles CHASE at 1.0 (6 of 6 on the tapes); "
                         "0.2778-0.3472 is their pre-aggro walk, and the client "
                         "plays the walk animation there. 0.75 was the 40.1 "
                         "default (\"so you can walk away\", ours); 0.35 was "
                         "CASE 8 v2's arm C.")
    ap.add_argument("--halt-on-arrival", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 40.9: send a hostile's "
                         "0x0028 halt the instant the server's copy reaches the "
                         "80 u disc. The default waits for the follow's "
                         "half-second clock, as retail does (halt p50 0.496 s "
                         "after the last follow), because the client's rendered "
                         "body trails its sync copy and an instant halt froze "
                         "it short of the disc -- CASE 8 v2's 'long range "
                         "attacks' with the server's copy at exactly 80 u.")
    ap.add_argument("--no-model-avoid-halt", action="store_true",
                    help="MOVECODE-1z-dj REVERT: when the AgTrack mirror's "
                         "avoidance pass halts the player's copy at another "
                         "agent's disc, the position model keeps walking the "
                         "lead -- RUN-1zDB leg A's ghost (drift 520 u, the "
                         "Hatcher marched to the phantom and hit from there). "
                         "Known-bad arm.")
    ap.add_argument("--no-mirror-avoid", action="store_true",
                    help="NPCTRACK-F14 REVERT: the server's mirror of the "
                         "player's world-0 copy walks every leg straight, "
                         "ignoring the client's agent-avoidance pass -- the "
                         "sidestep around a parked hostile 80 u ahead and the "
                         "halt when our lead ends inside its disc. Measured on "
                         "seven tapes: the pass reproduces 24 of 26 sidesteps "
                         "to 0.2 u and 14 of 14 halts; without it every first "
                         "press carries ~100 u of frame error for 0.3 s.")
    ap.add_argument("--no-npc-client-model", action="store_true",
                    help="NPCTRACK-Q1 REVERT: walk the server's copy of a "
                         "hostile along its own corridor toward the live "
                         "player and park it 80 u out, instead of running the "
                         "client's own dead-reckoner and disc stop over the "
                         "orders we send. Measured cost over 40 halts on three "
                         "stairs runs: the server's copy sat a median 53.8 u "
                         "(p90 193, max 526) from the body the client drew, "
                         "while the client's own two copies agreed to 12 u. "
                         "Known-bad arm; RUN-NPCTRACK-R1's control.")
    ap.add_argument("--no-npc-plane-reach", action="store_true",
                    help="GROUNDZ-F11 REVERT: where our navmesh has no "
                         "trapezoid under a hostile, keep the plane word it "
                         "already carried instead of taking the player's own "
                         "reported plane for ground within the follow's reach. "
                         "Measured cost (the operator's 2026-09-06 session): "
                         "the Hatcher drawn 52 u into the terrace above the "
                         "stairs for 16 s, its client plane 29 on plane-0 "
                         "ground the player had reported 8-45 u away.")
    ap.add_argument("--no-plane-repath", action="store_true",
                    help="GROUNDZ-Q5 REVERT: do not correct a hostile's plane "
                         "word after it stops. GROUNDZ-R1 measured what that "
                         "costs: the follow resolves the mover's plane AT SEND "
                         "TIME, the hostile crossed onto plane-29 ground 0.6 s "
                         "AFTER its last order, halted, and nothing re-sends to "
                         "a parked body -- so the client held plane 0 for the "
                         "whole 22 s hold, MapQueryAltitude skipped the prop "
                         "branch (which it does whenever the plane is 0) and "
                         "drew the body 32.5 u down in the terrain under the "
                         "staircase. Reverts BOTH faces: the stationary "
                         "correction and the plane-change re-path. Known-bad "
                         "arm.")
    ap.add_argument("--no-npc-plane-track", action="store_true",
                    help="ANIMREF-RE 42.5 / MOVECODE-1z-bz REVERT: a hostile's "
                         "follow carries the plane it SPAWNED on in both wire "
                         "words, frozen for the session, instead of the "
                         "mover's tracked plane and the destination's. Retail "
                         "tracks: 1,164 NPC grants carry field 3 != field 4 "
                         "and 128 of 377 NPCs change their words over a "
                         "session. Ours matched only on flat ground, which is "
                         "why this had zero exposure until RUN-1zBW sent four "
                         "follow orders onto bridge deck stamped plane 0 and "
                         "the operator watched the Hatcher walk underneath. "
                         "This is also the arm to test with if the client "
                         "refuses (dest, cur): sec.42.5's stated fallback is "
                         "the mover's plane twice. Known-bad arm.")
    ap.add_argument("--no-model-plane-clip", action="store_true",
                    help="MOVECODE-1z-cc REVERT: the server's own model leg is "
                         "clipped PLANE-BLIND again, as it was until 2026-09-06 "
                         "-- pathmap.clip with no plane term, so a ray that "
                         "leaves the ground and re-enters on a staircase "
                         "stacked above it scores clear the whole way. This is "
                         "the 604 u in RUN-NPCTRACK-R1's five-second silence: "
                         "the client's body never left (10012, 8524), the "
                         "grant's own plane-aware clip stopped 108 u out "
                         "naming plane-seam, and state['pos'] walked to "
                         "(10616, 8524) with every follow order in the window "
                         "carrying it. Nothing on the wire changes either way "
                         "-- state['dest'] feeds the world tick's integrator "
                         "and no send site. Known-bad arm.")
    ap.add_argument("--model-origin-exact", action="store_true",
                    help="MOVECODE-1z-cf REVERT (door 1): the server's own "
                         "position model suspends collision whenever its "
                         "standing point is outside exact containment, as it "
                         "did until 2026-09-06 -- including the edge class the "
                         "client reports from (0.0-0.4 u outside a side), so "
                         "on a wall slide the model walks the raw heading into "
                         "the wall and the NPC follow aims the hostile at that "
                         "phantom (RUN-FEEL2: the Hatcher 145 u off the stairs, "
                         "drawn on the terrain below). Known-bad arm.")
    ap.add_argument("--no-model-wall-slide", action="store_true",
                    help="MOVECODE-1z-cf REVERT (door 2): a model leg the clip "
                         "stops at the body STANDS instead of sliding to the "
                         "wall's next vertex; the model then lags a sliding "
                         "body by a report's worth (~100 u) and the follow aims "
                         "behind it. Known-bad arm.")
    ap.add_argument("--no-model-leg-bound", action="store_true",
                    help="MOVECODE-1z-cc REVERT: the server's own model leg may "
                         "again end further along its ray than the lead grant "
                         "our own mesh just cut short. The bound reads a mesh "
                         "REFUSAL only -- a CLEAR lead is untouched, because "
                         "its 520 u against the model ray's 768 is derived "
                         "(1z-ab.4) and capping it would park the model at the "
                         "client's own report trigger. Corpus residual behind "
                         "the plane term: 2 events of 783, <= 1.4 u. Known-bad "
                         "arm.")
    ap.add_argument("--no-hero-follow", action="store_true",
                    help="SLICE-B7b REVERT: a party body (hero or henchman, "
                         "anything carrying ALLEGIANCE_PLAYER) stands where it "
                         "spawned instead of walking to the player. That is the "
                         "behaviour every hero run before 2026-09-12 had, and "
                         "it is the known-bad arm for anything about the "
                         "follow: studies/heroes' own summary was 'the movement "
                         "messages exist and the hero stands still because "
                         "nothing drives it'. The follow itself is the HOSTILE "
                         "follow with two numbers changed -- an infinite leash "
                         "and a 200 u formation stop -- so this flag also "
                         "isolates the party arm from any hostile-follow "
                         "regression.")
    ap.add_argument("--no-npc-corridor", action="store_true",
                    help="NPCTRACK-Q9 REVERT: a hostile's follow is a bare "
                         "0x002A naming the player across any geometry, which "
                         "the client walks DEAD STRAIGHT (the owner's stairs "
                         "session: the Hatcher through the hole above the "
                         "stairs, 45 u off any trapezoid, parked 8 u inside "
                         "the wall). The default routes the copy and sends "
                         "0x0029 legs to the corridor's vertices while one "
                         "intervenes, the 0x002A once the line is clear -- "
                         "retail's own shape on its 6 corpus chases. Known-bad "
                         "arm.")
    ap.add_argument("--no-npc-follow-router", action="store_true",
                    help="MOVECODE-1z-by REVERT: a hostile's own server-side "
                         "copy walks a STRAIGHT LINE clipped by the pathmap "
                         "instead of a routed corridor, which is what "
                         "enemy_move_tick's docstring has described since "
                         "ANIMREF-RE 40. RUN-1zBW measured the cost: the "
                         "copy wedged 7 u from a trapezoid edge, all 15 "
                         "later follow orders clipped 0.000 u, the chase was "
                         "dead for 155 s and the client drew the body 965 u "
                         "away with no protocol path back (0x0028 carries no "
                         "point, an NPC never gets a 0x002C). pm.route "
                         "escapes that corner 49 of 49. The wire is identical "
                         "either way -- the follow's 0x002A names the PLAYER "
                         "and the client paths itself; this is only our own "
                         "copy, which every range check reads. Known-bad arm.")
    ap.add_argument("--legacy-npc-chase", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 40: a hostile chases "
                         "with a 0x0029 to the player's POINT, re-announced "
                         "every 120 u, turning to face them every tick, and "
                         "stops to swing at the invented 150 u. The default "
                         "is retail's shape, read off 7 live chases: one "
                         "0x002A NAMING the player at the server's copy of "
                         "their position, re-pathed every 0.5 s while they "
                         "move, no swing until the client's own disc parks "
                         "the body at r+r+56 = 80 u, and a bare 0x0028 "
                         "marking the halt.")
    ap.add_argument("--press-waits-for-leg", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 39's first rule: "
                         "an attack press during a click-walk waits for "
                         "the modelled leg to end (37's shape) instead of "
                         "ending it -- the behaviour the operator refused "
                         "on CASE 6.")
    ap.add_argument("--press-waits-for-stop", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 41: the swing gate "
                         "keeps reading the keyboard latch until a 0x0047 "
                         "clears it, even when an attack press is newer. "
                         "The 2026-09-03 08:46 shape -- a keyboard walk our "
                         "own grant turned into a silent click-order leg, "
                         "no stop ever sent, and 22 presses starved on a "
                         "parked body. Retail answers such a press within "
                         "0.2 s (24 of 48 live, the rest no-ops).")
    ap.add_argument("--move-keeps-target", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 39's second rule: "
                         "a post-landing move keeps the attack target and "
                         "the chain resumes when the body stops (32's "
                         "shape). The default forgets the target on ANY "
                         "move command, as retail's player does: 28 of 28 "
                         "mid-chain moves on the live tapes are followed by "
                         "a re-press before the next swing, none by a "
                         "resumed chain.")
    ap.add_argument("--no-landing-hold-release", action="store_true",
                    help="THE REVERT ARM for ANIMREF-RE 33's one behaviour "
                         "change: keep the property-8 action hold set past "
                         "the swing's landing, as every build before "
                         "2026-09-01 did. The default RELEASES it at the "
                         "landing, because property 8 drives the client's "
                         "walk gate (ChCliBase+0x64 bit 0) and both "
                         "begin-move entries refuse on that bit -- so a "
                         "held gate makes the post-landing movement that "
                         "ANIMREF-RE 32 declared legal impossible until a "
                         "round trip clears it. MEASURED on the operator's "
                         "own sessions: hold to first movement report p10 "
                         "0.601s / p50 0.869s / p90 1.015s over 104 hold "
                         "windows, ZERO reports arriving strictly inside a "
                         "hold, and 39.3%% of fight time spent gated. Run "
                         "this arm to reproduce that stall on purpose.")
    ap.add_argument("--no-e3-release", action="store_true",
                    help="No-op since the 2026-09-01 revert: the hold "
                         "already rides through E3 by default. Kept so "
                         "runsheets from that half-day parse.")
    ap.add_argument("--legacy-chain-restart", action="store_true",
                    help="Revert ANIMREF-R7b: the chain reopens in the same "
                         "tick as an attack skill's execution again. The "
                         "default paces the next START one weapon windup "
                         "out, the corpus's 46->START law (0.749..0.783 s "
                         "cluster, 21/38 -- FINDINGS 14 LAW B).")
    ap.add_argument("--legacy-cast-form", action="store_true",
                    help="Revert cast-animation properties to the old "
                         "always-0x00A0 form (target 0 when none). The "
                         "default follows retail's form rule (ANIMREF-R1, "
                         "studies/animref/FINDINGS.md sec.2, 758/758): "
                         "0x00A0 when the cast names a target, 0x009F when "
                         "it does not -- retail never sends target 0 on the "
                         "targeted channel.")
    ap.add_argument("--suppress-grant-during-hold", action="store_true",
                    help="ANIMREF-R11, REFUTED and kept as an A/B lever: do "
                         "not answer a movement report with a destination "
                         "grant while our own action hold is set. It removes "
                         "the body relocation it was built to remove (2 of 15 "
                         "post-refusal grants relocated, 0 of 29 otherwise; "
                         "retail suppresses 10:1) -- and it costs the SLIDE, "
                         "because the slide was the grant's: recovery lag "
                         "47-172 ms becomes 313-828 ms and dispatches fall "
                         "333 to 59 (FINDINGS sec.27). OFF by default.")
    ap.add_argument("--no-agtrack-repin", action="store_true",
                    help="Keep the guard's telemetry but disable its ACTIVE "
                         "arm: the single 0x002C re-pin at the client's own "
                         "fresh report when the next snap-test evaluation is "
                         "predicted to fail (MOVECODE-1z-s). OFF BY DEFAULT "
                         "since MOVECODE-1z-cy, so this flag is the default "
                         "spelled out; --agtrack-repin is the revert arm.")
    ap.add_argument("--agtrack-repin", action="store_true",
                    help="MOVECODE-1z-cy's revert arm: switch the guard's "
                         "ACTIVE re-pin back ON (the 1z-s default until "
                         "2026-09-09). Retail's server never sends the player "
                         "a 0x002C mid-walk (0 of 51 live connections); ours "
                         "sent 17 across six hand-driven sessions, all "
                         "mid-walk, each shutting the fence for ~1 s of "
                         "parked copy -- FINDINGS 1z-cy.")
    ap.add_argument("--no-plane-repair", action="store_true",
                    help="Disable the plane-lock repair (ON by default). The "
                         "repair sends ONE labelled 0x002C -- the client's own "
                         "accepted frozen position with the mesh's plane -- "
                         "when accepted 0x003D movement reports have repeated "
                         "an identical (x, y) for PLANE_REPAIR_HOLD seconds "
                         "claiming a plane the mesh does not offer there: the "
                         "measured signature of the r5stuck movement LOCK "
                         "(FINDINGS sec.1z-c/1z-d), which a client cannot "
                         "escape alone because its path queries start from "
                         "the impossible plane. In a healthy run it fires "
                         "ZERO times. Pass this to run a strict one-0x002C-"
                         "policy session (e.g. a --resync or --cast-stop=pin "
                         "A/B that wants no third sender armed).")
    ap.add_argument("--resync-separation", type=float, default=None,
                    metavar="UNITS",
                    help="Override RESYNC_SEPARATION (shipped 100.0 u -- "
                         "reconciled 2026-08-25, the ruling is on the "
                         "constant) for ONE run. Requires --resync; refused "
                         "alone, and refused non-positive or non-finite. "
                         "Registered use: P8 of studies/movement/"
                         "followon-notes/p5-resync-disarm.md sec.8 -- "
                         "--resync --resync-separation 2000, the negative "
                         "control under which nothing fires and the F35 "
                         "snap must RETURN.")
    ap.add_argument("--refusal-silent", action="store_true",
                    help="answer a refused skill press with NOTHING, which is "
                         "what this server did until 2026-08-22. It is an A/B "
                         "ARM, not a fallback: E2 watched a refused slot "
                         "re-animate for about 10 seconds against a silent "
                         "server, nobody established whether that duration is "
                         "real, and once 0x00E2 releases the slot immediately "
                         "the old behaviour is unreachable. Pair a run of this "
                         "with a default run, same script, and the difference "
                         "is the answer. It suppresses the WHOLE batch -- "
                         "sentence and release -- because a half-suppressed "
                         "refusal is a third behaviour retail never produces "
                         "and would answer neither question.")
    ap.add_argument("--grant-suppress", action="store_true", default=None,
                    help="EIGHTH candidate, and the first that acts by SAYING "
                         "LESS. Two refusals on the click grant: (1) never send "
                         "0x0029 while the player is driving with the keyboard "
                         "-- the client emits 0x003D only while moving and "
                         "0x0047 only on a stop, so that state is readable off "
                         "the wire -- and (2) never send them faster than one "
                         "per %.2f s, holding the NEWEST superseded destination "
                         "rather than sending both. 0x0029 is SYNC-ONLY, so a "
                         "grant issued mid-keyboard drives the authoritative "
                         "copy away from the rendered one AND re-runs the "
                         "client's desync test, which is the warp. Scored "
                         "against run 20260820T183311: 196 clicks -> 140 grants "
                         "in 44 s and 5 hard jumps, four of them 0.10-0.23 s "
                         "after a grant. Rule 1 refuses 196 of those 196 and 0 "
                         "of the 5 ordinary clicks in run 20260820T182934. ON "
                         "BY DEFAULT since 2026-08-22 (owner's ruling after "
                         "REALFIX-L9; --no-grant-suppress reverts); independent "
                         "of every other movement flag."
                         % GRANT_MIN_INTERVAL)
    ap.add_argument("--checksum-probe", choices=("wrong", "model"),
                    metavar="MODE",
                    help="Send GAME_SMSG 0x0023, ArenaNet's own movement-state "
                         "checksum, on every 0x003D while the player moves, and "
                         "make the client's OWN desync verdict appear in its "
                         "Gw.log. The client XORs five raw dwords off its SYNC "
                         "copy (velocity +0xB4/+0xB0, plane +0x80, position "
                         "+0x7C/+0x78, at 0x005FEEA0) and logs `Agent %%u "
                         "position out of sync with server` when field 2 "
                         "disagrees -- it LOGS ONLY, so the readout is the log "
                         "file and never the wire. TWO MODES, and the first is "
                         "the positive control: `wrong` sends a value that "
                         "CANNOT match (our model XOR a nonzero sentinel), so "
                         "the line MUST appear -- if it does not, the fault is "
                         "the opcode, the field order, the agent id or the "
                         "suppression latch, and no silence anywhere else in "
                         "this probe means anything until it does. `model` "
                         "sends our own best reconstruction of the client's "
                         "five fields, where SILENCE is the result and means we "
                         "reproduce the sync copy bit-exactly. Expect `model` "
                         "to fire too: the compare is integer equality over "
                         "float bits, and our velocity model is not the "
                         "client's bake. Off by default; needs no other flag.")
    ap.add_argument("--d1-lead", action="store_true",
                    help="REALFIX-A2, the accuracy campaign's lead rung -- "
                         "THE BUNDLE (REALFIX.md sec.0.9): the zero-lead "
                         "grant's point becomes the client's own proposed "
                         "endpoint (reported + vec2 + 0.5*unit(vec2), "
                         "unclipped, fallback-on-garbage recorded per row); "
                         "the A1-proven 0x002B family float rides the burst "
                         "as edge-triggered POLICY; plane truth stays "
                         "--plane-carry (retail's own one-grant-lag "
                         "pattern, 306-crossing census); and every 0x0047 "
                         "gets retail's stop reply (0x002B [1.0,9] + "
                         "zero-distance 0x0029). Requires --zero-lead and "
                         "--plane-carry; refused with the probe/diagnostic "
                         "arms. Protocol: click-free, cast-free.")
    ap.add_argument("--legacy-kbd-sync", action="store_true",
                    help="MOVECODE-1z-t REVERT: restore the pre-1z-t keyboard "
                         "wire exactly (heading grant at the reported point "
                         "verbatim, no player 0x002B, nothing at all on a "
                         "0x0047). The default keeps the client's WORLD-0 "
                         "copy of the player near the body it draws: the "
                         "heading grant is LED 520 u along the client's own "
                         "reported heading and clipped to the navmesh, the "
                         "0x002B family rate rides the burst edge-triggered, "
                         "and every 0x0047 draws retail's stop reply "
                         "(0x002B [1.0,9] + a zero-distance 0x0029). Measured "
                         "against the client's own world-0 track: separation "
                         "from the drawn body p50 237 -> 0 u, max 516 -> 86 u.")
    ap.add_argument("--kbd-lead", action="store_true",
                    help="MOVECODE-1z-t term 1: lead the heading grant 520 u "
                         "along the client's own reported heading, clipped "
                         "to the navmesh. THE DEFAULT since MOVECODE-1z-bu "
                         "(2026-09-05, PLAN sec.7 Q13) -- opt-in between "
                         "1z-u and 1z-bt while its four gates were built and "
                         "the AgTrack guard's rewind was localised and "
                         "removed. This flag now parses as a no-op so the "
                         "opt-in era's runsheets keep their meaning.")
    ap.add_argument("--no-kbd-lead", action="store_true",
                    help="MOVECODE-1z-bu REVERT: term 1 OFF, the 1z-u..1z-bt "
                         "default -- the heading grant lands at the reported "
                         "point and world-0 parks a report behind the walking "
                         "body (p50 252 u / p90 509 u, RUN-1zBM). Wins over "
                         "--kbd-lead.")
    ap.add_argument("--no-kbd-speed-truth", action="store_true",
                    help="MOVECODE-1z-t term 2 OFF: send the player no 0x002B "
                         "family rate, so world-0 walks every family at "
                         "288 u/s. Terms 1 and 3 stay on.")
    ap.add_argument("--no-kbd-stop-echo", action="store_true",
                    help="MOVECODE-1z-t term 3 OFF: a 0x0047 draws nothing "
                         "again. Terms 1 and 2 stay on -- and this is the "
                         "arm the counterfactual says is WORSE than the "
                         "shipped default (p50 425 u against 237), because "
                         "the lead's overshoot has nothing to collect it.")
    ap.add_argument("--kbd-lead-refresh", action="store_true",
                    help="MOVECODE-1z-ae ON (OPT-IN since 1z-af, which "
                         "convicted it): re-aim an in-flight keyboard lead "
                         "before its arrival can snap. Two verification runs "
                         "with it on both locked, one of them past a "
                         "`refresh-late`, so this is a diagnostic arm and not "
                         "a fix. Inert without a lead arm (--no-kbd-lead).")
    ap.add_argument("--no-kbd-lead-refresh", action="store_true",
                    help="MOVECODE-1z-ae OFF: let an in-flight keyboard "
                         "lead reach its arrival. The arrival is a SNAP "
                         "(agent+0x48 fires once and the client snaps to "
                         "the granted point) and it arms REALFIX 0.11 "
                         "stage 1, which the lead's own click-walk regime "
                         "then keeps shut -- RUN-1zAB's rerun locked five "
                         "of eight legs that way. Inert without a lead arm. "
                         "Diagnostic arm.")
    ap.add_argument("--no-lead-plane-clip", action="store_true",
                    help="MOVECODE-1z-ap OFF: the D1/keyboard lead clip goes "
                         "back to the PLANE-BLIND ray. pm.walkable() means "
                         "'inside any trapezoid, on ANY plane', so a ray from "
                         "a bridge to the ground beneath it scores CLEAR at "
                         "full length -- there is no height in the pathing "
                         "file. RUN-1zAO measured what that costs: a plane 29 "
                         "to plane 0 lead passed at 520 u, the drawn body "
                         "parked 3.0 s under a held key, and the arrival "
                         "warped it 520 u and shut AgTrack's fence for good.")
    ap.add_argument("--lead-seam-clip", action="store_true",
                    help="MOVECODE-1z-bc OPT-IN: clip the D1/keyboard lead's "
                         "ray with pathmap.seam_clip (a plane may end only at "
                         "a portal) instead of 1z-ap's any-plane-change stop. "
                         "REFUTED as a default by retrodiction: all six fatal "
                         "leads of the six measured locks cross a FILE-LINKED "
                         "portal and go out at the full 520 u under it, so "
                         "this arm re-opens the lead's lock door on the "
                         "spawn-side bridge. Diagnostic arm only.")
    ap.add_argument("--lead-origin-exact", action="store_true",
                    help="MOVECODE-1z-bg OFF: a keyboard lead's origin must be "
                         "INSIDE a trapezoid (pathmap.walkable) again; a report "
                         "the mesh holds within 1 u of an edge -- where the "
                         "client's body stands and reports from at the wedge "
                         "tip -- is refused as origin-unwalkable and the lead "
                         "becomes a zero-lead (179 of them in 26 runs). "
                         "Known-bad arm.")
    ap.add_argument("--no-lead-disc-clear", action="store_true",
                    help="MOVECODE-1z-cg REVERT (door A): a keyboard lead may END "
                         "inside a hostile's 80 u disc, where the client's "
                         "avoidance pass halts world-0 (NPCTRACK-F14/Q8) while "
                         "the body sidesteps on -- RUN-FEEL2 63.8 s: world-0 "
                         "stalled 1.2 s, the body 230 u ahead. Known-bad arm.")
    ap.add_argument("--no-lead-plane-words", action="store_true",
                    help="MOVECODE-1z-cl REVERT: the keyboard lead's two plane "
                         "words are the REPORT's plane, matched, even where the "
                         "destination (a door-B vertex) or world-0 sits on "
                         "another plane -- RUN-1zCG session 4 ended with the "
                         "body hanging in mid-air on such a word, unable to walk. "
                         "Known-bad arm.")
    ap.add_argument("--no-kbd-lead-chain", action="store_true",
                    help="MOVECODE-1z-cl REVERT: a door-B lead names one corridor "
                         "vertex and world-0 idles there until the next 0.5 s "
                         "heading tick (11.6 s idle over session 4's 39 door "
                         "leads; six gate-1 snaps). Known-bad arm. Also turns "
                         "off 1z-di's arrival re-grant, which is this chain's "
                         "second branch.")
    ap.add_argument("--no-arrival-regrant", action="store_true",
                    help="MOVECODE-1z-di REVERT: when the copy reaches the end of "
                         "a keyboard lead and the client has said nothing, the "
                         "copy PARKS there until the next report instead of "
                         "being sent the next chord along the held heading -- "
                         "retail re-grants at arrival unprompted (50 of 50 first "
                         "re-grants at p50 +0.04 s after arrival; 0 of 323 "
                         "full-chord silences before it). RUN-1zDB leg 4's "
                         "parked copy is this arm.")
    ap.add_argument("--no-bound-clear-leads", action="store_true",
                    help="MOVECODE-1z-ct REVERT: the model leg is bounded by the order "
                         "ONLY when our own mesh cut the grant short, so on a clear lead "
                         "it walks the client's full ~768 u ray while the grant reached "
                         "520 u (session 4 t=48.98: 247 u of drift, 356 u of aim error "
                         "across two follow orders). Known-bad arm.")
    ap.add_argument("--kbd-grant-floor", type=float, default=None, metavar="SECONDS",
                    help="MOVECODE-1z-cw REVERT at 0.5: the keyboard arm refuses a heading "
                         "report inside this many seconds of the previous player grant "
                         "(the floor it shared with the click arm until 2026-09-09; 934 of "
                         "1,619 evaluations refused over five sessions, 65%% of world-0's "
                         "lag behind the body). Shipped 0.0: retail answers every report. "
                         "Known-bad arm at 0.5.")
    ap.add_argument("--no-model-family-rate", action="store_true",
                    help="MOVECODE-1z-cu REVERT: the position model integrates every "
                         "keyboard leg at a flat 288 u/s, so a backpedalling body "
                         "(190.08 u/s) is modelled 51%% ahead of where it is even while "
                         "it moves (September corpus: backpedal drift 83 u mean against "
                         "28 under the fix). Known-bad arm.")
    ap.add_argument("--no-npc-leg-disc-clip", action="store_true",
                    help="MOVECODE-1z-co REVERT: a corridor whose first vertex is inside "
                         "the player's disc is DISCARDED and the bare 0x002A goes out "
                         "straight through the wall (1z-cn: 2 of 6 bad chords, one 21.5 u "
                         "off our mesh). Known-bad arm.")
    ap.add_argument("--route-gate-coarse", action="store_true",
                    help="MOVECODE-1z-co REVERT: route()'s gate samples the unpulled "
                         "candidate at 16 u again, so a 2-point 'clear' path can carry a "
                         "chord that leaves the mesh (1z-cn: 3 of 6 bad chords). Known-bad "
                         "arm.")
    ap.add_argument("--no-stale-pair-gate", action="store_true",
                    help="MOVECODE-1z-cm REVERT: the send lock is per message again, so "
                         "the world tick's 0x001E may land between a 0x002B and its "
                         "0x0029/0x002A (24 splits in 2,701 September pairs; session "
                         "5's AgAgent.cpp:1198 assert). Known-bad arm.")
    ap.add_argument("--no-lead-w0-origin", action="store_true",
                    help="MOVECODE-1z-cg REVERT (door B): the lead is clipped "
                         "from the REPORT only, though the client bakes it from "
                         "its own settled world-0 -- RUN-FEEL2 63.8 s: a leg "
                         "clear from the report crossed the hole above the "
                         "stairs from world-0, gate 2 snapped the body 166 u "
                         "into it. Known-bad arm.")
    ap.add_argument("--no-lead-wall-slide", action="store_true",
                    help="MOVECODE-1z-ce REVERT: a keyboard lead whose heading "
                         "ray is blocked at the body stays a ZERO lead instead "
                         "of retail's next-vertex slide along the wall "
                         "(pathmap.wall_slide, 49 of 62 live cases to 0.0 u). "
                         "On RUN-R3's stair climb that is 15 zero leads in 8 s "
                         "and the sync copy trailing the body by 100-139 u. "
                         "Known-bad arm.")
    ap.add_argument("--no-client-reseed-latch", action="store_true",
                    help="MOVECODE-1z-cj REVERT: only our own 0x002C stamps the "
                         "fence latch; the client's own gate snaps (a report that "
                         "jumps back onto world-0) do not, and leads keep going "
                         "into the shut window -- the owner's 2.9 s of dead keys "
                         "and 190 u/s enslaved walking on session 3. Known-bad arm.")
    ap.add_argument("--no-fence-rearm-moved", action="store_true",
                    help="MOVECODE-1z-ci REVERT: the fence we shut re-arms only "
                         "at a keyboard walk-start (a moving report after a "
                         "stop). A player who never stops then keeps the latch "
                         "to its 8 s bound after every re-pin while the client's "
                         "fence is open in 0.5 s -- 79 of 151 leads refused on "
                         "the owner's session, world-0 579 u behind. Known-bad arm.")
    ap.add_argument("--no-fence-latch-timeout", action="store_true",
                    help="MOVECODE-1z-bw REVERT: restore the UNBOUNDED "
                         "fence-gate latch, cleared only by a keyboard "
                         "walk-start. The bound exists because the client's "
                         "own fence dword re-opens on its own within 6.087 s "
                         "(26 measured shuts over 14 tapes, "
                         "studies/movecode/review/fencelatency.py) while our "
                         "latch had no upper bound and held 45.25 s on "
                         "RUN-1zBW, zeroing 72 of 163 fired grants. Inert "
                         "without a lead arm and without "
                         "--no-kbd-lead-fence-gate's gate being ON.")
    ap.add_argument("--no-kbd-lead-fence-gate", action="store_true",
                    help="MOVECODE-1z-aa OFF: a keyboard or D1 lead may "
                         "be sent into a fence the server itself shut with "
                         "a 0x002C (AGTRACK RE-PIN, PRESS ENDS THE WALK, "
                         "CAST-STOP PIN, ...) -- REALFIX 0.11's lock "
                         "armer. With the gate ON such a lead degrades to "
                         "the zero-lead point (lead_clip_why fence-shut) "
                         "until a walk-start report re-arms the fence. "
                         "Inert without a lead arm. Diagnostic arm.")
    ap.add_argument("--no-kbd-matched-plane", action="store_true",
                    help="MOVECODE-1z-z OFF: the keyboard lead grant "
                         "carries the plane-carry word raw again (dest 29 "
                         "/ cur 0 at a crossing, 1z-u.4's shape) instead "
                         "of field 4 matched to field 3 (REALFIX 0.11's "
                         "armer-kill, retail's 222/222). Inert without a "
                         "lead arm (--no-kbd-lead). Diagnostic arm.")
    ap.add_argument("--no-kbd-hold", action="store_true",
                    help="MOVECODE-1z-y (a1) OFF: a rate-refused heading "
                         "report is DROPPED again instead of held and "
                         "re-baked at the floor -- the pre-1z-y behaviour "
                         "whose premise (the next report is 0.3 s away) "
                         "failed in the 08:46 session. Diagnostic arm.")
    ap.add_argument("--no-kbd-lead-kill", action="store_true",
                    help="MOVECODE-1z-y (a2) OFF: an in-flight keyboard "
                         "lead (--kbd-lead only) is left to mature on a "
                         "press or a click instead of being ended by a "
                         "zero-lead grant at the modelled body. Inert "
                         "without a lead arm (--no-kbd-lead). Diagnostic arm.")
    ap.add_argument("--no-router", action="store_true",
                    help="MOVECODE-1z-v: turn the router OFF (it is the "
                         "default click policy since 2026-09-03). Restores "
                         "the pre-1z-v click path exactly: the 1.0 s "
                         "freshness gate, its geo-stale refusals (40 of 40 "
                         "clicks in the operator's 08:46 session), and the "
                         "hold/void/rate tower. Needed beside the diagnostic "
                         "arms the composition matrix refuses with the "
                         "router (--click-sweep, --arrival-carry, "
                         "--cancel-answer, --stop-answer, "
                         "--family-rate-probe, --checksum-probe, --pc-spoof, "
                         "--interact-walk, --move-speed-effects).")
    ap.add_argument("--router-raw-leg", action="store_true",
                    help="MOVECODE-1z-v condition (a) OFF: the click-leg "
                         "record stays on the RAW click chord instead of "
                         "being re-aimed at the routed leg. PRESS ENDS THE "
                         "WALK then re-pins the body onto the unclipped "
                         "chord on a mid-chain press. Diagnostic arm only.")
    ap.add_argument("--router-report-plane", action="store_true",
                    help="MOVECODE-1z-v condition (b) OFF, and 1z-w's (b') "
                         "with it: the one-leg verbatim answer's field 4 is "
                         "the last accepted report's plane again (frozen "
                         "across the click walk) instead of the mesh's "
                         "plane under the modelled sync copy, and the "
                         "routing origin's plane (route()'s start "
                         "preference, the clip-fallback's stop-plane carry) "
                         "is the report's plane instead of the mesh's under "
                         "the body model. One construction, two places, one "
                         "revert. Diagnostic arm only.")
    ap.add_argument("--router-blind-clip", action="store_true",
                    help="MOVECODE-1z-bb condition (c) OFF: the router's two "
                         "rays -- route()'s pull/gate and the clip fallback "
                         "-- go back to the plane-blind clip() that RUN-1zBA "
                         "convicted (a body parked 7 s at a bridge deck's "
                         "edge, then a 2,021 u teleport). Diagnostic arm "
                         "only; RUN-1zBB's known-bad arm.")
    ap.add_argument("--agtrack-gate2-exact", action="store_true",
                    help="MOVECODE-1z-bf OFF: the AgTrack guard's gate 2 goes "
                         "back to EXACT trapezoid containment of the modelled "
                         "sync copy (pathmap.walkable) instead of on_mesh with "
                         "the 1 u edge tolerance. Known-bad arm: 17 of 17 "
                         "gate2-offmesh re-pins in the corpus were false "
                         "vetoes on sub-unit edge slivers, and one of them "
                         "halted a walking keyboard body for 3.7 s (RUN-1zBD).")
    ap.add_argument("--router", action="store_true",
                    help="NO-OP since 2026-09-03 (MOVECODE-1z-v): the "
                         "router is the default click policy and needs no "
                         "flag; kept so runsheets written before 1z-v still "
                         "parse. --no-router turns it off. "
                         "ROUTER-B2 (studies/movement/ROUTER.md; the "
                         "owner's 2026-08-26 ruling on RETHINK-H3): answer "
                         "clicks the way retail measurably does -- a route "
                         "over OUR navmesh (pathmap.route(): A* + "
                         "string-pull + a clip gate that refuses paths "
                         "through walls), first leg within the click's own "
                         "handling, further legs granted at leg-completion "
                         "cadence at 288 u/s, terminal grant the bit-exact "
                         "clicked point, chain abandoned on any new input. "
                         "One 0x002B per chain (retail's grammar), "
                         "per-waypoint planes matched. Routed clicks "
                         "bypass the hold/void/rate tower (Rule 1's "
                         "keyboard drop stays); no-route clicks get a "
                         "clip-fallback leg or a LOGGED refusal, never the "
                         "unclipped point. Composes with "
                         "--d1-lead; refused with the probe/diagnostic "
                         "arms. Bench: toolkit/clientscan/routerbench.py "
                         "(13/13 retail-verbatim clicks reproduced "
                         "bit-identically offline before this shipped).")
    ap.add_argument("--pc-spoof", type=int, default=None, metavar="PLANE",
                    help="REALFIX sec.0.7 cell 2's lever (the parked+pc-flip "
                         "cell -- the seam is a bridge too narrow to stage it "
                         "by geography). The FIRST fired zero-lead grant "
                         "after >= 4.0s of grant silence sends THIS plane id "
                         "as wire field 4 instead of the carry value, once "
                         "per park; the client stamps it raw at +0x80 "
                         "(0x00602A74, no compare), flipping the parked "
                         "copy's plane word. Registered prediction: NO snap; "
                         "a snap means gate 2 is plane-keyed. Requires "
                         "--zero-lead; refused negative; refused with "
                         "--cancel-answer. Stand on ground whose plane "
                         "differs from the value (26 on plane-0 ground is "
                         "the registered cell).")
    ap.add_argument("--family-rate-probe", action="store_true",
                    help="REALFIX-A1, the accuracy campaign's first rung: "
                         "send GAME_SMSG 0x002B AGENT_UPDATE_SPEED "
                         "[player, FAMILY_RATE[mt], mt] alongside each "
                         "granted 0x003D report, in retail's own burst slot "
                         "(before the 0x0029 -- last in 3,023 of 3,071 "
                         "retail bursts). THE QUESTION is SPEED TRUTH: does "
                         "the wire float steer the SYNC copy's reckoning "
                         "speed? The static decode says the handler is a "
                         "pure store to sync +0x60 (moveSpeed) -- never "
                         "+0x5C -- consumed only at the NEXT grant's bake; "
                         "this probe is the dynamic confirmation, read in "
                         "movetap's `movespeed` column (the same SYNC block "
                         "the handler writes; `maxspeed` must hold 288.0). "
                         "All 42,784 corpus samples read movespeed 1.0 with "
                         "1.0 the only float we ever sent, so any movement "
                         "off 1.0 under the probe is the probe's. Off by "
                         "default; requires --zero-lead; refused with "
                         "--cancel-answer (its lead arms hardcode a rival "
                         "0x002B). Run recipe: sustained backpedal and "
                         "strafe legs, click-free, movetap attached -- "
                         "studies/movement/REALFIX.md sec.0.3.")
    ap.add_argument("--no-grant-suppress", action="store_false",
                    dest="grant_suppress",
                    help="Revert --grant-suppress: click grants go out while "
                         "the player keyboards and with no rate floor -- the "
                         "spam-click warp regime (round 4, REALFIX-L5) comes "
                         "back with it.")
    ap.add_argument("--stop-echo", action="store_true",
                    help="REFUTED 2026-08-19, kept only so the negative result "
                         "is reproducible -- do not reach for this as a fix. On "
                         "a client move-cancel (0x0047) echo the player's own "
                         "reported position straight back as a zero-distance "
                         "0x0029. Prediction, stated before the run: this "
                         "overwrites the destination armed in the client by an "
                         "earlier granted click -- which the client clears ONLY "
                         "by consuming it at its arrival tick or by a newer "
                         "grant, since its own 0x0047 is send-only and has no "
                         "receive handler -- so the pending teleport becomes a "
                         "no-op and the character stops warping onto stale "
                         "click destinations seconds after cancelling. Attested "
                         "in retail: 70 of 88 of ArenaNet's move-cancel replies "
                         "are exactly this echo. It may fix nothing for the 13 "
                         "grant-triggered jumps that do NOT land on a granted "
                         "point; those have no established cause.")
    ap.add_argument("--interact-walk", action="store_true",
                    help="Send GAME_SMSG 0x002A when an interact arrives from "
                         "out of range. OFF by default and it should stay off "
                         "until somebody measures what carries the PATHING: on "
                         "run 20260819T111841 a lone 0x002A dragged the "
                         "character straight through a staircase in a straight "
                         "line, left it clipping through the geometry, and "
                         "produced no position report at all -- so the held "
                         "interact never saw an arrival and no dialog opened. "
                         "The flag exists so the next measurement is one "
                         "argument away, not so this is shipped.")
    ap.add_argument("--practice-target", action="store_true",
                    help="The standing hostile neither chases nor attacks -- a "
                         "PRACTICE TARGET. WIKI (GWW, \"Practice target\", rev. "
                         "2014-02-07): practice targets are stationary NPCs, there "
                         "are allied and hostile ones, and 'They do not use any "
                         "skills'; a slain hostile one resurrects after 30 s at full "
                         "health. So this is a real Guild Wars creature's behaviour "
                         "rather than a test switch. It is what makes an agent "
                         "death REACHABLE unattended: with the hostile fighting back "
                         "the player loses the race (25 damage a hit into 100 HP, "
                         "four hits, against the seven the player needs) and never "
                         "lands one.")
    ap.add_argument("--enemies", type=int, default=1, metavar="N",
                    help="spawn N standing hostiles instead of one (ids 10..10+N-1, "
                         "one shared definition, walkable spots around the "
                         "arrival point). 1..8. NPCTRACK-Q10: two chasers share "
                         "the player's frame and each other's disc, and nothing "
                         "has measured that.")
    ap.add_argument("--no-enemy", action="store_true",
                    help="Do not spawn the standing hostile NPC. The world is "
                         "then the player alone, which is what most probes "
                         "assume and what every session before 2026-08-06 was.")
    ap.add_argument("--no-move-cancel-displacement", action="store_true",
                    help="a keyboard movement report cancels the auto-attack "
                         "chain even when the player's own reported position "
                         "did not move. The revert for MOVECODE-1z-db "
                         "(studies/movecode 1z-db): retail's player loses "
                         "1.0%% of its still-player swings to a cancel and "
                         "ours lost 7.9%%, because `any 0x003D is movement` "
                         "reads a field that is always set. Reverts all three "
                         "doors on the same trigger: the wire stop (1z-db), "
                         "the target-forget (1z-dd) and the chain pause's "
                         "read of a REPEATED still report as a body in "
                         "motion (1z-df).")
    ap.add_argument("--no-pause-charge-without-target", action="store_true",
                    help="the chain pause charges only ticks that reach the "
                         "accumulator (below the no-target return), and a "
                         "re-press after a move restarts the swing clock. "
                         "The revert for MOVECODE-1z-dg: the shipped arm "
                         "charges the whole moving span whatever the target "
                         "holds and resumes the chain on that clock when the "
                         "client re-presses the target the move forgot -- "
                         "retail's START-to-START gap across a move is "
                         "interval + span (1z-dc.3, within 1.7%%); ours "
                         "charged 19%% of the span.")
    ap.add_argument("--no-spell-armour", action="store_true",
                    help="an incoming armour-respecting spell (Flare's `Fire "
                         "damage`) deals its stated amount instead of "
                         "scaling by the player's elemental armour rating. "
                         "The revert for SKILLS-FA (studies/skills 43); "
                         "--no-armour-term drops it too, along with the "
                         "swing's.")
    ap.add_argument("--no-armour-term", action="store_true",
                    help="drop the armour exponent and criticals from the "
                         "player's swing, leaving the weapon's raw range. The "
                         "control for anything reading a damage number: with "
                         "it a swing is 3-5 flat, without it 3-5 is scaled by "
                         "2^((SL-AR)/40) and a critical replaces it "
                         "(studies/isle rung 7).")
    ap.add_argument("--enemy-skills", default=None, metavar="IDS",
                    help="Comma-separated skill ids for the standing hostile's "
                         "bar, using the client's own activation and recharge "
                         "for each. The mirror of --skills, and it exists for "
                         "the same reason: changing what the enemy casts "
                         "should not need a content edit. Ids must exist in "
                         "the build being launched.")
    ap.add_argument("--no-enemy-skills", action="store_true",
                    help="Empty the standing hostile's bar: it swings and "
                         "does nothing else. The content row could always "
                         "express this (an empty `skills` list leaves the "
                         "agent on plain swings) but the FLAG could not -- "
                         "`--enemy-skills ''` is falsy and was silently "
                         "ignored, leaving the default bar up while the "
                         "command line said otherwise. Use this to isolate "
                         "the swing channel from the cast channel.")
    ap.add_argument("--move-speed-effects", action="store_true",
                    help="declare the player's speed base (GAME_SMSG 0x0027) "
                         "from open movement-speed episodes -- Rush's +25%% "
                         "becomes a 360 u/s base while the stance is up. OFF "
                         "by default because every REALFIX fence and copy "
                         "model was measured at 288 u/s; see "
                         "MOVE_SPEED_EFFECTS' comment before flipping it "
                         "under the movement composite.")
    ap.add_argument("--no-deep-wound", action="store_true",
                    help="SKILLS-DW REVERT: Deep Wound (482) opens and closes "
                         "as an icon and moves nothing -- no 0x009F 42, no "
                         "health delta, full healing. Retail moves the "
                         "maximum by exactly 20%% in the apply's own batch "
                         "(2 of 2, isle 8.2 / deepwoundjoin.py).")
    ap.add_argument("--no-condition-heal-rule", action="store_true",
                    help="SKILLS-RC REVERT: Restore Condition is a flat "
                         "self-heal again -- no condition removal, no "
                         "per-condition amount, no target legality -- the "
                         "pre-2026-09-10 wire that healed the enemy to full "
                         "every three seconds. GWW: 'Remove all conditions "
                         "from target other ally. For each condition "
                         "removed, that ally is healed'.")
    ap.add_argument("--no-blind", action="store_true",
                    help="SKILLS-BL REVERT: Blind (479) is an icon and every "
                         "swing under it lands -- the pre-2026-09-10 wire. "
                         "WIKI (GWW 'Blind'): melee and missile attacks miss "
                         "90%%; the miss is the client's own attack-fail word "
                         "0x00A0 [38, target, attacker, 3].")
    ap.add_argument("--no-overheal-number", action="store_true",
                    help="SKILLS-HN REVERT: a heal on a full pool sends "
                         "nothing, and a partial one sends only what landed "
                         "-- the pre-2026-09-09 wire. Retail sends the "
                         "skill's own amount regardless (healjoin.py P4: 46 "
                         "heals onto full pools) and the client draws the "
                         "blue number even then (GWW 'Heal').")
    ap.add_argument("--no-status-word", action="store_true",
                    help="SKILLS-DW REVERT: send no 0x00F1 status word when a "
                         "condition, hex or enchantment opens or closes -- "
                         "the pre-2026-09-09 wire, where the only status "
                         "messages were death and revive. Retail sends the "
                         "word behind every such apply and close.")
    ap.add_argument("--no-effects", action="store_true",
                    help="do not open or close effect episodes. The control "
                         "for the 0x0042/0x0044 channel: with it a stance is "
                         "a cast that leaves nothing behind and the effect "
                         "bar stays empty, which is the state this server "
                         "shipped in until 2026-08-20. Use it to say whether "
                         "something the client did was THIS channel rather "
                         "than the cast cycle it rides on.")
    ap.add_argument("--no-energy", action="store_true",
                    help="do not charge for skills: no energy gate, no "
                         "property-62 spend, no regeneration and no "
                         "adrenaline -- and, since 2026-08-21, none of the "
                         "four 0x00CF/0x00D0/0x00D2 adrenaline messages. The "
                         "control for the cost channel, and it restores "
                         "exactly the behaviour this server shipped with "
                         "until 2026-08-20 -- every skill free, the orb flat "
                         "at 25, the skill icons dark, the enemy casting on "
                         "its recharge alone. Use it to say whether something "
                         "a run saw was THIS channel rather than the cast "
                         "cycle it rides on.")
    ap.add_argument("--no-armour", action="store_true",
                    help="leave the five armour slots empty. The control for "
                         "anything that reads an armour RATING off the client: "
                         "with it the paper doll shows five empty slots and no "
                         "tooltip can be hovered, which is the state this "
                         "server shipped in until 2026-08-20.")
    ap.add_argument("--costume", action="store_true",
                    help="Wear content/items.toml's `costume_body` (wire type "
                         "44) in equip slot 7. THE OVERRIDE PROBE: "
                         "studies/playercomposite 9.2 read a path where slots "
                         "7/8 feed a registry that REPLACES the armour slots' "
                         "cached fileId/flags/dye at m_slotItemData build "
                         "time, so a costume should change what the ARMOUR "
                         "components draw rather than adding a piece. Pair it "
                         "with clientscan/compositetrap.py: the prediction is "
                         "that the chest rebuild stops fetching record 91 and "
                         "fetches the costume's 2806 instead.")
    ap.add_argument("--costume-head", nargs="?", const="",
                    metavar="CONTENT_KEY", dest="costume_head",
                    help="Wear `costume_head` (wire type 45) in equip slot 8. "
                         "The other half of 9.9: the body costume overrode "
                         "run members 0..3 and left the head. This row is "
                         "member 4 of a DIFFERENT run, so with both worn "
                         "record 2809 -- the body run's own head member -- "
                         "must stay unfetched. Takes an optional content key: "
                         "bare it wears `costume_head` (record 2654, type 17, "
                         "component 2), and `--costume-head "
                         "costume_head_second` wears the STANDALONE type-19 "
                         "kind (record 2817, component 1) -- the same wire "
                         "type and the same slot through the identical path, "
                         "so the record's component is the only variable.")
    ap.add_argument("--armour-flags-clear", metavar="HEX",
                    dest="armour_flags_clear",
                    help="Clear these bits from every armour row's declared "
                         "flags before sending. A probe INPUT, not a content "
                         "claim. 9.11 could not separate the costume "
                         "override's `or edx,0x20000006` from a plain copy, "
                         "because all five of our rows already declare the "
                         "whole mask; clearing a bit and watching whether the "
                         "client puts it back does separate them. "
                         "--armour-flags-clear 0x20000000 is the intended "
                         "value: retail itself wears composite armour with "
                         "that bit clear on 28 of 5,281 corpus wears, so the "
                         "shape is one the client already handles. The row is "
                         "re-validated after the edit, so a clear that took "
                         "the composite bit out dies here.")
    ap.add_argument("--no-weapon", action="store_true",
                    help="Log in with empty weapon slots, as every session before "
                         "2026-08-06 did. Attacking and weapon skills were both "
                         "unavailable then; this flag is what makes that "
                         "re-testable instead of merely remembered.")
    ap.add_argument("--explorable", action="store_true",
                    help="Tell the client this instance is explorable rather than "
                         "a town. Guild Wars forbids attacking in a town, so this "
                         "is the cheap way to find out whether combat is gated on "
                         "the map or on this one field — the alternative is "
                         "recovering a real explorable's file id out of Gw.dat.")
    ap.add_argument("--file-id", type=lambda s: int(s, 0), default=None,
                    metavar="ID",
                    help="Serve THIS map file at whatever slot --map selects, "
                         "instead of the file content/maps.toml pairs with that "
                         "slot. Splits the map SLOT from the map GEOMETRY, which "
                         "content pairs by design. Added 2026-08-15 for the "
                         "minimap C2 arm: the compass ground image is cropped from "
                         "the AREA ROW (a property of the slot) while the ground "
                         "you walk on comes from the FILE, and no other flag can "
                         "hold one still while moving the other. The spawn stays "
                         "the slot's, so a file whose rect does not contain it "
                         "will not spawn -- predict that before the run.")
    ap.add_argument("--outpost", action="store_true",
                    help="The COUNTERPART of --explorable: force the 0x0199 map-type "
                         "byte to 0 (MISSION_MAP_OUTPOST) even on a map "
                         "content/maps.toml marks explorable. Added 2026-08-14 for "
                         "the minimap ladder's C3 arm, which needs BOTH values of "
                         "that byte on one map id — and --explorable can only force "
                         "it ON, so on an explorable map the toggle had no off "
                         "position. The byte selects which of the area row's two "
                         "footprint rectangles the compass crops with (0 -> +0x48, "
                         "1 -> +0x58, studies/minimap/FINDINGS.md §3.3), so on a row "
                         "where those differ this is a real lever on the picture. "
                         "Refused together with --explorable: they contradict.")
    ap.add_argument("--no-fog-init", action="store_true",
                    help="Do NOT send the exploration-init pair (0x008B+0x008A) "
                         "at map load. The pair is on by default since "
                         "2026-08-24 because without it the world map is "
                         "unopenable -- M kills the client on GmMapView.cpp"
                         "(1731) (studies/minimap/FINDINGS.md 6f.2, RUNBOOK "
                         "failure table). Pass this to restore the no-init "
                         "baseline: experiments around 0x008C need it, because "
                         "that opcode is INERT without the pair and ACTIVE "
                         "with it, so a default-on server silently inverts any "
                         "pre-2026-08-24 comparison.")
    ap.add_argument("--fog-reveal", action="store_true",
                    help="Send the init pair with an all-REVEALED stream "
                         "instead of all-fogged, so the world map shows the "
                         "whole continent picture. Carries fogrle.py's "
                         "CONTESTED colour-start: if a run with this flag "
                         "opens a fully FOGGED map, the static reading of the "
                         "expander was right after all -- flip "
                         "fogrle.FIRST_COLOUR and tell "
                         "studies/minimap/FINDINGS.md 6i.")
    ap.add_argument("--henchman", default=None, metavar="NPC_KEY",
                    help="Add one henchman row to the party roster: send "
                         "GAME_SMSG 0x01BF inside the party build window "
                         "carrying NPC_KEY's enc_name, and raise "
                         "PLAYER_PARTY_SIZE to 2. NO world body is created — "
                         "this isolates the roster question from the agent "
                         "question. Omit for the control arm (one roster row). "
                         "The 2026-08-12 sweep scored this opcode SILENT, but "
                         "with an all-zero payload whose party_id=0 resolved a "
                         "NULL party; the server has since learned to build "
                         "one, which is the condition that changed. "
                         "studies/heroes/FINDINGS.md §7.1")
    ap.add_argument("--henchman-body", action="store_true",
                    help="With --henchman, also create the henchman's world "
                         "body at the SAME agent id its roster row names, "
                         "~150 units from spawn. Arm two of the staged demo: "
                         "arm one measured that the row draws with no body at "
                         "all, but with no name and 'Lvl 255'. This asks "
                         "whether the row's CONTENT is what needs the agent.")
    ap.add_argument("--hero", default=None, metavar="INDEX[,INDEX...]",
                    help="Add a HERO row to the party roster: send 0x01C2 "
                         "inside the party build window for s_heroClientData "
                         "index INDEX (1..39; 0 is HERO_UNUSED and 40 is the "
                         "bound). Omit for the control arm. Unlike a "
                         "henchman, a hero carries NO name on the wire — the "
                         "client resolves its identity through the static "
                         "table. studies/heroes/FINDINGS.md §7.2")
    ap.add_argument("--hero-body", action="store_true",
                    help="Also create the hero's world body at agent "
                         "200 (deliberately outside the 1..39 hero-index "
                         "range, so the word-order arm is readable). "
                         "GmHeroCommander:120/121 demand a non-zero agentId.")
    ap.add_argument("--hero-body-npc", default="hatcher", metavar="NPC_KEY",
                    help="Content row to borrow a body from: s_heroClientData "
                         "carries NO model_id, so a hero's model cannot come "
                         "from the hero table and must be a placeholder.")
    ap.add_argument("--hero-swap", action="store_true",
                    help="Exchange 0x01C2's two identity words, i.e. send "
                         "the H1 order (agent id at msg+8), which rendered "
                         "nothing. Both words are settled: msg+8 owner "
                         "player number (heroes FINDINGS 21), msg+0xc agent "
                         "id (11.1). This flag is the control arm.")
    ap.add_argument("--hero-activate", "--hero-diagnostic", action="store_true",
                    dest="hero_activate",
                    help="Send 0x0072 HeroActivate last. Its four fields are "
                         "the client's own format string (hero, agent, "
                         "inventoryId, aiMode). WITHOUT it the roster row is "
                         "labelled from the BODY's agent; WITH it the client "
                         "resolves the hero's own name from s_heroClientData "
                         "and enables its commander-slot flag. Opened this arc "
                         "as a refutable diagnostic and turned out to be the "
                         "activation itself.")
    ap.add_argument("--hero-activate-first", action="store_true",
                    dest="hero_activate_first",
                    help="Send 0x0072 HeroActivate BEFORE the party build "
                         "instead of last. THE ORDERING ARM: case 93 runs "
                         "synchronously inside 0x01C2's worker and asks the "
                         "agent-keyed activation array who the hero is; that "
                         "array's only writer is 0x0072, so sent last it does "
                         "not exist yet and GmCtlSkListContext:574 asserts "
                         "(studies/heroes 37). Needs --hero-activate; the "
                         "order is INVENTED -- retail sends 0x0072 zero "
                         "times.")
    ap.add_argument("--hero-pipeline-first", action="store_true",
                    dest="hero_pipeline_first",
                    help="Send the WHOLE hero pipeline (info, body, "
                         "attributes, skill bar, char, activate) BEFORE the "
                         "party build, relative order untouched, instead of "
                         "after it. THE FIX --hero-activate-first pointed at: "
                         "moving 0x0072 alone satisfies case 93's lookup but "
                         "puts it ahead of the hero's attribute state and the "
                         "client asserts `attribState`; moving everything "
                         "satisfies both (studies/heroes 37.1). The resulting "
                         "order is OURS -- retail sends 0x0072 zero times.")
    ap.add_argument("--no-hero-info", action="store_true",
                    help="Drop the leading 0x0074. The route sends it first on "
                         "the hypothesis that it creates the data-cache "
                         "record; this asks whether it was needed.")
    ap.add_argument("--no-hero-skillbar", action="store_true",
                    help="Omit the hero's 0x00DA skill bar. 0x00DA is "
                         "agent-keyed with an eight-slot array and is the same "
                         "message the player's bar rides -- section 4's 'no "
                         "skill-bar field anywhere' was a scoping error.")
    ap.add_argument("--no-hero-attribs", action="store_true",
                    help="Omit the hero's attribute state (0x0037 -> 0x00B7 -> "
                         "0x003A). That trio is what completes the hero "
                         "record; without it the row still draws but is "
                         "labelled from the BODY's agent instead of resolving "
                         "the hero's own name from s_heroClientData. The "
                         "control arm for section 14.")
    ap.add_argument("--player-number", type=int, default=None, metavar="N",
                    help="The in-instance player number, normally 1 -- which is "
                         "also PLAYER_AGENT_ID, and that coincidence is what "
                         "makes 0x01C2's msg+8 undecidable. Set it to something "
                         "else and the two namespaces separate.")
    ap.add_argument("--hero-msg14", type=int, default=0, metavar="N",
                    help="0x01C2's second trailing u8 (msg+0x14 -> entry+0x14), "
                         "never varied. Its sibling msg+0x10 is inert on every "
                         "observable, so this asks rather than assumes.")
    ap.add_argument("--hero-info-name", default=None, metavar="NPC_KEY",
                    help="Put a real EncString on 0x0074's name field, which "
                         "every run so far has sent EMPTY. The hero row takes "
                         "its name from s_heroClientData; this asks whether "
                         "0x0074's own name overrides that.")
    ap.add_argument("--party-mine-late", type=float, default=None,
                    metavar="SECONDS",
                    help="Re-send 0x01B2 PARTY_SET_MINE once, SECONDS after "
                         "INSTANCE_LOAD_FINISH, leaving everything else where "
                         "it is. THE TIMING EXPERIMENT of "
                         "studies/pvpui/FINDINGS.md 19, and it is a different "
                         "one from --hero-late: that defers the hero PIPELINE, "
                         "this re-fires the RAISE. Run 6 timestamped our raise "
                         "of 0x10000114 at +0.000s and GmView's subscribe to "
                         "that same event at +0.053s -- 0x10000114 is the only "
                         "event whose GmView case calls the commander-model "
                         "rebuild, so it is raised into a map that does not yet "
                         "hold GmView and is never raised again. 0x01B2's "
                         "handler raises it on both branches, so a second send "
                         "is a second raise. Try 2.0. Predicted: the rebuild "
                         "runs, 0x00524C40 runs for the first time in this "
                         "project, and commanderpeek reports a non-zero "
                         "commander count. 19.2 names the three refutations.")
    ap.add_argument("--hero-late", type=float, default=None, metavar="SECONDS",
                    help="Hold the ENTIRE party/roster sequence (build window, "
                         "henchman and hero rows, 0x0074s) until SECONDS after "
                         "INSTANCE_LOAD_FINISH instead of sending it inside the "
                         "load. THE TIMING EXPERIMENT of "
                         "studies/heroes/FINDINGS.md 34.4: the commander event "
                         "is raised while the subscriber map holds nothing for "
                         "it, and eight events were measured changing "
                         "subscriber state mid-session -- so our 0x01C2 may "
                         "simply arrive before the commander UI subscribes. "
                         "UI_OVERLAY_FLAGS in this same handler is already sent "
                         "late for exactly that reason.")
    ap.add_argument("--hero-bust-cache", action="store_true",
                    help="Open a second party build right before 0x01C2 so the "
                         "party-manager cache holds a DIFFERENT party and the "
                         "hero-add takes the slow lookup. The only arm that "
                         "actually exercises the conditional raise.")
    ap.add_argument("--hero-post-commit", action="store_true",
                    help="Send 0x01C2 after 0x01B2 rather than inside the "
                         "build window. Tests whether the party-cache hit at "
                         "0x008590AF is what suppresses the commander event.")
    ap.add_argument("--hero-owner", type=int, default=None, metavar="N",
                    help="Override 0x01C2's msg+8 only (normally the player "
                         "number). With --player-number, this is the arm that "
                         "says whether the field is the owner's PLAYER NUMBER "
                         "or the owner's AGENT ID.")
    ap.add_argument("--hero-activate-id", type=int, default=None, metavar="N",
                    help="Override 0x0072's hero id only, leaving 0x0074 on "
                         "--hero's value. Splits the last confound: which of "
                         "the two data-cache messages supplies the identity.")
    ap.add_argument("--hero-roster-id", type=int, default=None, metavar="N",
                    help="Override 0x01C2's msg+0x10 only, leaving 0x0074 and "
                         "0x0072 on --hero's value. Three fields normally "
                         "carry the same hero id, so nothing can say which one "
                         "the client reads the identity from; this splits them.")
    ap.add_argument("--hero-inventory", type=lambda x: int(x,0), default=0,
                    metavar="N",
                    help="HeroActivate's inventoryId (field 3). Statically "
                         "traced 2026-08-18: stored at activation-record +8, "
                         "read back by the party window's equip walk, looked "
                         "up in inventoryTable -- ItCliApi:488 asserts when "
                         "it names no inventory, and 0 names none. Pair a "
                         "non-zero key with --hero-bags, which declares it.")
    ap.add_argument("--hero-bags", action="store_true",
                    help="Declare --hero-inventory's key to the item client: "
                         "0x0144 [key, 0] plus the equipped-items bag 0x013F, "
                         "sent in the REQUEST_ITEMS burst beside the player's "
                         "own. Refused for keys 0 and 1 -- 0 declares nothing "
                         "and 1 is the player's key, which 0x0144's handler "
                         "asserts against re-declaring (ItCliApi:2010).")
    ap.add_argument("--hero-char", action="store_true",
                    help="Register each hero agent id in the char client's "
                         "char-by-id table (0x009A, one per hero slot). The "
                         "floor after ItCliApi:488: the commander panel's "
                         "paperdoll indexes that table by agent id and "
                         "Array:587s on an unregistered one. Registration "
                         "alone suffices -- a NULL slot falls back cleanly.")
    ap.add_argument("--hero-appearance", default=None, metavar="D1[,D2]",
                    help="0x0074's two u32s at msg +0x14/+0x18 -- the hero's "
                         "appearance composite file reference, fed by the "
                         "commander paperdoll to CpsPlayer/CpsMonster. Zeros "
                         "(the default) assert `fileId` File.cpp:367 on the "
                         "hero-button click once --hero-char clears the char "
                         "table. The floor after Array:587.")
    ap.add_argument("--hero-level", type=int, default=None, metavar="N",
                    help="Send int property 36 (the agent's displayed level, "
                         "0x009F) for each hero agent, before any body. The "
                         "commander panel title's 'Lvl 255' is the no-entry "
                         "sentinel for this exact property -- the cheap arm "
                         "pvpui 28.3 stages; --hero-body is the heavy one.")
    ap.add_argument("--hero-body-offset", default=None, metavar="DX[,DY]",
                    help="Where --hero-body stands, offset from the player's "
                         "spawn (default -150,120 -- 150u to the side, fanned "
                         "by slot). DY is per-slot. A large DX is the "
                         "out-of-compass-range arm for the greyed party row.")
    ap.add_argument("--hero-vitals", default=None, metavar="H[,E]",
                    help="Send int properties 42 (health MAX) and 41 (energy "
                         "MAX) for each hero agent. pvpui 28.4: the panel's "
                         "vitals bars render 1/0 with neither sent; this arm "
                         "asks whether they display current or max.")
    ap.add_argument("--hero-ai-mode", type=int, default=0, metavar="N",
                    help="HeroActivate's aiMode (field 4): 0/1/2 = the three "
                         "CHAR_AI_MODES stances Fight/Guard/Avoid Combat.")
    ap.add_argument("--hero-chunk", default=None, metavar="LIST|N",
                    help="0x0074's ten trailing dwords: one int fills all "
                         "ten, or a comma list of up to ten. The client "
                         "copies them as TWO 5-dword groups to record +0x4c "
                         "and +0x60, and 5 dwords is exactly one "
                         "attribState->attrib entry — which is the hypothesis "
                         "this flag exists to TEST, and to let fail.")
    ap.add_argument("--hero-flag", type=lambda s: int(s, 0), default=0,
                    metavar="N",
                    help="The u32 before the chunk. Non-zero makes the client "
                         "take its CONDITIONAL third copy of the second group "
                         "to record+0x74, so this is the only way to exercise "
                         "that branch at all.")
    ap.add_argument("--hero-bytes", default=None, metavar="A,B,C",
                    help="0x0074's three leading u8s (record +8/+0xc/+0x10). "
                         "Upstream guesses level/primary/secondary; unnamed "
                         "here because no consumer was traced to a bound.")
    ap.add_argument("--henchman-wire-name", default=None, metavar="NPC_KEY",
                    help="Put a DIFFERENT row's enc_name on 0x01BF than the "
                         "one the body's 0x0056 carries. With --henchman-body "
                         "the two otherwise agree, so the rendered row cannot "
                         "say which it read.")
    ap.add_argument("--henchman-wire-prof", type=int, default=None,
                    metavar="N", help="Override 0x01BF's first trailing byte "
                                      "only (upstream calls it profession).")
    ap.add_argument("--henchman-wire-level", type=int, default=None,
                    metavar="N", help="Override 0x01BF's second trailing byte "
                                      "only (upstream calls it level).")
    ap.add_argument("--player-flags", type=lambda s: int(s, 0), default=None,
                    metavar="VALUE",
                    help="Send GAME_SMSG 0x003C (player number, VALUE, mask 7) "
                         "immediately before WORLD_CREATE_AGENT, which is retail's "
                         "own position for it: 423 sends over 12 of 12 live "
                         "connections, all inside the instance load, and this "
                         "server has never sent it. A lone player is VALUE 4 in "
                         "every single-connection capture. Omit for the control "
                         "arm — sending it LATE was already measured as a clean "
                         "null (RESKIN.md 18.8), so what this asks is whether a "
                         "LOAD-time write behaves differently.")
    ap.add_argument("--allow-any-session", action="store_true",
                    help="Accept a login with no matching session record. A debugging "
                         "escape hatch so a stale sessions.json cannot be mistaken for a "
                         "wire bug. Never the default: the rejection path has to stay exercised.")
    return ap
