"""REALFIX sec.0.7 cell 2's lever: the trigger, the cells, the locks.

--pc-spoof exists because the parked+pc-flip cell could not be staged by
geography (the plane seam is a bridge too narrow to strafe, owner's run
2026-08-25 ~23:17). Its whole output is ONE rewritten wire field on the
first fired grant after a park -- nothing here can assert the client's
half (that the flip kills the 100u veto and that no gate fires on a
parked copy; that is the owner run's job, and its prediction is
registered in REALFIX.md sec.0.7 and on the startup banner). What this
file CAN refuse to let rot: the pure trigger's truth table (the park gap
is the whole cell -- a spoof that fires on ordinary leg cadence would
expose every leg and the census could attribute nothing), the
composition cells that keep the run unconfoundable, and the source locks
on the rebind site -- the 2026-08-25 review's lesson that an unpinned
rebind survives every test.

What this file deliberately does NOT claim: that the flip produces (or
does not produce) a snap. Both outcomes are informative and neither is
this file's to assert.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import authsrv     # noqa: E402
import checks      # noqa: E402

# MEASURED from the real green run on 2026-08-26: 23 checks, no fixture, no
# vault, no client. Set AT the run per the house rule -- zero headroom, so
# unhooking any single check reddens here. (History: the first draft
# declared 21 from a count in the author's head before running; the run
# said 23. The rule working, again -- same as test_familyrate's header.)
# 2026-09-10: 23 -> 25. The send lock became two (the seeding line and the
# send itself, after MOVECODE-1z-cl split the words into their own names) and
# the d1-lead composition cell was added -- see its comment for why that one
# is load-bearing rather than decorative.
LEDGER = checks.Ledger("the REALFIX-0.7 pc-spoof lever", floor=25)
check = checks.adopt(LEDGER)


def main():
    # ---------------------------------------------------------------- 1
    print("1. the pure trigger: pc_spoof_field4's whole truth table")
    f = authsrv.pc_spoof_field4
    check(f(None, None, 7) == (7, False),
          "flag off, first grant: carry passes through untouched",
          "the helper runs on EVERY fired grant; off must be a no-op or "
          "the shipped default just grew a policy")
    check(f(None, 100.0, 7) == (7, False),
          "flag off, any gap: still a pure pass-through",
          "same ground: None is the shipped state")
    check(f(26, None, 0) == (26, True),
          "since_last None (first grant of a connection) SPOOFS",
          "the copy spawned parked -- a first press is the cell's own "
          "shape, and the A1 tape's first grant fired with since_last "
          "null")
    check(f(26, authsrv.PC_SPOOF_GAP, 0) == (26, True),
          "gap exactly PC_SPOOF_GAP spoofs (>= boundary, not >)",
          "an off-by-one here silently halves the exposed reps at the "
          "recipe's own cadence")
    check(f(26, authsrv.PC_SPOOF_GAP - 0.1, 0) == (0, False),
          "gap just under the threshold carries -- leg cadence is safe",
          "A1's fired-grant gaps top out at 3.054s during continuous "
          "play; a spoof below the gap would expose every leg and the "
          "census could attribute nothing")
    check(f(26, 3.054, 0) == (0, False),
          "the A1 tape's own maximum leg-cadence gap (3.054s) does NOT "
          "spoof",
          "the constant is sized off that measurement; this row is the "
          "measurement holding the constant honest")
    check(f("26", None, 0) == (26, True) and
          isinstance(f("26", None, 0)[0], int),
          "the spoof value is coerced to int on the way out",
          "argparse delivers int, but the helper is pure and callable "
          "from anywhere -- a str riding into a struct.pack would raise "
          "mid-connection")
    check(f(0, None, 26) == (0, True),
          "spoofing plane 0 itself works (0 is falsy but not None)",
          "an `if spoof:` truthiness bug would make the one plane id "
          "every map uses unspoofable, silently")
    check(authsrv.PC_SPOOF_GAP == 4.0,
          "PC_SPOOF_GAP is 4.0 -- above A1's 3.054s leg-cadence max, "
          "below the recipe's 6s parks",
          "both distances matter: the margin is the cell's identity")
    check(authsrv.PC_SPOOF is None,
          "PC_SPOOF ships None (off)",
          "a diagnostic that defaults on is a policy")

    # ---------------------------------------------------------------- 2
    print("2. composition cells: the lattice refuses what would confound")
    comp = authsrv.zero_lead_composition
    r, _ = comp(zero_lead=False, pc_spoof=26)
    check(r is not None and "--pc-spoof requires --zero-lead" in r,
          "pc-spoof without zero-lead is REFUSED naming the dependency",
          "no send site and no gap clock without the zero-lead arm: the "
          "inert-flag defect --plane-carry's refusal documents")
    r, _ = comp(zero_lead=True, pc_spoof=-1)
    check(r is not None and "not a plane" in r,
          "a negative spoof is REFUSED as not-a-plane",
          "plane words are non-negative dwords in every decoded report; "
          "the client would stamp the garbage raw at +0x80")
    r, _ = comp(zero_lead=True, pc_spoof=26, cancel_answer="suppress")
    check(r is not None and "--pc-spoof and --cancel-answer" in r,
          "pc-spoof with cancel-answer is REFUSED as a pair",
          "the lead arms ride the SAME 0x0029 send site whose field 4 "
          "the spoof rewrites -- a two-variable instant in a "
          "one-variable cell")
    r, _ = comp(zero_lead=False, pc_spoof=26, cancel_answer="suppress")
    check(r is not None and "--pc-spoof and --cancel-answer" in r,
          "with BOTH violations pending, the pairwise cell outranks the "
          "requires cell",
          "the family-rate precedent (test_familyrate sec.5): 'you "
          "passed two levers' is the more useful refusal, and ordering "
          "is a property mutations flip silently")
    r, notes = comp(zero_lead=True, pc_spoof=26)
    check(r is None,
          "the registered cell itself -- zero-lead + pc-spoof -- is "
          "ALLOWED",
          "the whole lever exists to run")
    check(any("--pc-spoof 26" in n for n in notes),
          "and its startup note names the armed value",
          "the gamesrv jsonl header carries no argv (REALFIX-Q8); the "
          "note plus the verdict rows are how a later session attributes "
          "the run")
    check(any("void" in n for n in notes if "--pc-spoof" in n),
          "the note warns that spoofing your own ground plane is VOID",
          "plane_differs false on every rep is a run that measured "
          "nothing wearing a run's clothes")
    # THE CELL THAT KEEPS THE LEVER FROM BEING SILENTLY ANNIHILATED, and it
    # was NOT covered here until 2026-09-10 -- found by tracing why the send
    # lock above went red. Under --d1-lead the very next statement after the
    # spoof is `a2_matched_field4(plane, zl_plane_cur)`, whose whole contract
    # is that "the carry's value is OVERRIDDEN to match whenever it differs"
    # -- and a deliberately DIFFERENT field 4 is exactly what the spoof
    # produces. So with both flags on, the spoof would be erased one line
    # after it fired and every run would measure nothing while looking armed.
    # The refusal is what makes that unreachable; it is load-bearing for this
    # lever and now has a check of its own.
    r, _ = comp(zero_lead=True, pc_spoof=26, d1_lead=True)
    check(r is not None and "--d1-lead and --pc-spoof" in r,
          "d1-lead with pc-spoof is REFUSED -- the cell that keeps "
          "a2_matched_field4 from erasing the spoof it just wrote",
          "field 4 MATCHES field 3 under A2, and the spoof's entire output "
          "is a field 4 that does not match. Without this refusal the lever "
          "is inert with both flags on, which is the failure mode the send "
          "lock above names in prose and could not see")
    r, _ = comp(zero_lead=True, pc_spoof=26, family_rate_probe=True)
    check(r is None,
          "pc-spoof beside family-rate-probe is allowed (different wire "
          "fields), the note carrying the one-probe-per-run advice",
          "orthogonal fields are not a hard conflict; the advice lives "
          "in the note so the pair stays runnable if a question ever "
          "needs both")

    # ---------------------------------------------------------------- 3
    print("3. source locks: the rebind site cannot drift or unhook")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    rebind = "zl_plane_cur, pcs_fired = pc_spoof_field4("
    check(src.count(rebind) == 1,
          "exactly ONE rebind site rewrites zl_plane_cur through the "
          "helper",
          "a second site would spoof grants outside the zero-lead "
          "verdict -- the two-arms-one-clock defect from the other side")
    i_carry = src.index('zl_carry = "arrival-carry"')
    i_rebind = src.index(rebind)
    # The verdict anchor's FIRST file-wide occurrence is prose inside the
    # composition matrix (line ~5299), not the send path -- search from the
    # rebind forward so the lock measures the region it claims to.
    i_verdict = src.index('rec.event("grant_verdict"', i_rebind)
    check(i_carry < i_rebind < i_verdict,
          "and it sits AFTER both carry policies, BEFORE the verdict "
          "row -- the spoof outranks the carry and the row records what "
          "was sent",
          "moved above the carries, plane-carry would silently overwrite "
          "the spoof and every exposed rep would be void; moved below "
          "the verdict, the row would log the carry value while the "
          "wire carried the spoof -- the unattributable-capture defect")
    check("pc_spoofed=(pcs_fired" in src,
          "the verdict row carries pc_spoofed",
          "the census key: without it, exposure is reconstructed from a "
          "policy someone assumes was running (REALFIX-Q8's lesson)")
    check('+ (" PC-SPOOF" if pcs_fired' in src,
          "the wire label appends PC-SPOOF on an exposed grant",
          "a human reading the gamesrv log finds the exposed sends "
          "without joining the verdict rows")
    # RE-AIMED 2026-09-10. This asserted the send read `plane, zl_plane_cur],`
    # VERBATIM, and MOVECODE-1z-cl refactored the site to carry the two plane
    # words in their own names -- so the literal went stale and this lock went
    # red without the lever having moved. The SUBJECT was never the spelling:
    # it is that the name the spoof rebinds still reaches the wire. That is now
    # two links, and both are pinned, so a break in either still reddens:
    #   1. `lead_f3, lead_f4 = plane, zl_plane_cur` -- the spoofed word enters
    #      the pair the send actually reads, and it happens BEFORE the D1_LEAD
    #      block that may rebind them;
    #   2. the 0x0029 send reads that pair.
    check(src.count("lead_f3, lead_f4 = plane, zl_plane_cur") == 1,
          "the spoofed zl_plane_cur is what seeds the send's own field-4 name",
          "the spoof works by REBINDING zl_plane_cur -- if this seeding line "
          "grows its own field-4 expression the lever goes inert while this "
          "suite stays green")
    check("lead_f3, lead_f4]," in src,
          "and the one 0x0029 send reads that pair",
          "the second link: a send that computed its own words would ignore "
          "the seed above however faithfully it was set")

    return LEDGER.verdict()


# `sys.exit(main())`, not a bare `main()`, and `main` RETURNS the verdict:
# both halves were missing until 2026-08-31, so this file printed its FAIL
# banner and exited 0. run_suite.py catches that as SUSPECT (exit 0 with no
# ALL CHECKS PASSED line), which is the backstop working -- but a developer
# running the file directly saw a clean exit code on a red run, and
# CLAUDE.md's rule is that a test exits non-zero.
if __name__ == "__main__":
    sys.exit(main())
