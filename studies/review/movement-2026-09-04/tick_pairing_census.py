"""Read-only census over the LIVE corpus: does a 0x001E precede every 0x0029,
is that specific to movement or a property of every flush, what do >=490 ms
ticks carry, and does the delta sum track wall clock. Prints only."""
import sys, statistics, collections
sys.path.insert(0, r"C:/gd/Rurik/toolkit/authsrv"); sys.path.insert(0, r"C:/gd/Rurik/toolkit")
sys.path.insert(0, r"C:/gd/Rurik/toolkit/clientscan")
import livewire

OP_TICK = 0x1E
OP_GRANT = 0x29
MOVE_OPS = {0x29, 0x2B, 0x25, 0x2C, 0x28, 0x2A, 0x2E, 0x27}
n_conn = n_ok = 0
deltas = []
grant_dt = []          # (dt_ms, msgs_between, same_t)
grant_total = 0
any_dt_le3 = 0; any_total = 0
big_ticks = 0; big_ticks_with_move = 0; big_ticks_bare = 0
tick_followers = collections.Counter()
bare_tick_deltas = []
per_conn = []
sum_err = []
for capdir, gf in livewire.live_connections():
    conn, merged, ok = livewire.decode_conn(capdir, gf)
    n_conn += 1
    if not ok:
        continue
    n_ok += 1
    s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
    if not s2c:
        continue
    last_tick = None   # (index, t)
    ticks_idx = [i for i, (t, op, v) in enumerate(s2c) if op == OP_TICK]
    nt = len(ticks_idx)
    span = s2c[-1][0] - s2c[0][0]
    per_conn.append((capdir.split("\\")[-1].split("/")[-1], gf[:24], nt, span, nt / span if span else 0))
    # delta sum vs wall
    tk = [(t, v[1]) for t, op, v in s2c if op == OP_TICK]
    if len(tk) > 2:
        s = sum(dv for _t, dv in tk[1:])
        w = (tk[-1][0] - tk[0][0]) * 1000.0
        sum_err.append((s - w) / w * 100.0 if w else 0.0)
    for i, (t, op, v) in enumerate(s2c):
        if op == OP_TICK:
            deltas.append(v[1])
            last_tick = (i, t)
            continue
        any_total += 1
        if last_tick is not None and (t - last_tick[1]) * 1000.0 <= 3.0:
            any_dt_le3 += 1
        if op == OP_GRANT:
            grant_total += 1
            if last_tick is None:
                grant_dt.append((None, None, False))
            else:
                dt = (t - last_tick[1]) * 1000.0
                grant_dt.append((dt, i - last_tick[0] - 1, t == last_tick[1]))
    # what follows each tick before the next tick
    for k, ti in enumerate(ticks_idx):
        nxt = ticks_idx[k + 1] if k + 1 < nt else len(s2c)
        follow = s2c[ti + 1:nxt]
        tick_followers[len(follow)] += 1
        dv = s2c[ti][2][1]
        if dv >= 490:
            big_ticks += 1
            if any(op in MOVE_OPS for _t, op, _v in follow):
                big_ticks_with_move += 1
            if not follow:
                big_ticks_bare += 1
        if not follow:
            bare_tick_deltas.append(dv)

print(f"connections {n_conn}, byte-closed {n_ok}")
print(f"0x001E n {len(deltas)} min {min(deltas)} max {max(deltas)} p50 {sorted(deltas)[len(deltas)//2]}")
c = collections.Counter(deltas)
print("top deltas:", c.most_common(12))
print(f"delta-sum vs wall error % per conn: min {min(sum_err):.3f} max {max(sum_err):.3f} median {statistics.median(sum_err):.3f}")
le3 = sum(1 for dt, _b, _s in grant_dt if dt is not None and dt <= 3.0)
same = sum(1 for dt, _b, s in grant_dt if s)
zero_between = sum(1 for dt, b, _s in grant_dt if b == 0)
print(f"0x0029 n {grant_total}: tick <=3 ms before {le3} ({100*le3/grant_total:.2f}%); same-segment-timestamp {same}; tick IMMEDIATELY before (0 s2c msgs between) {zero_between}")
between = collections.Counter(b for _dt, b, _s in grant_dt if b is not None)
print("s2c msgs between preceding tick and 0x0029:", sorted(between.items())[:12])
far = sorted((dt for dt, _b, _s in grant_dt if dt is not None and dt > 3.0), reverse=True)[:10]
print("worst dt (ms) for 0x0029:", [round(x, 1) for x in far])
print(f"CONTROL: ALL non-tick s2c msgs n {any_total}: tick <=3 ms before {any_dt_le3} ({100*any_dt_le3/any_total:.2f}%)")
print(f"ticks with delta>=490: {big_ticks}; of which carry a movement op before next tick {big_ticks_with_move} ({100*big_ticks_with_move/big_ticks:.1f}%); bare (nothing follows) {big_ticks_bare}")
print("followers-per-tick histogram (n msgs after tick before next tick):", sorted(tick_followers.items())[:15])
bc = collections.Counter(bare_tick_deltas)
print(f"bare ticks n {len(bare_tick_deltas)}; their delta top:", bc.most_common(8))
print("per-connection tick rate (ticks/s):", [round(r[4], 2) for r in per_conn])
