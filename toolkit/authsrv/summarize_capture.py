"""Summarise what a client actually said during an AuthSrv session.

After a run, the question is always the same: which messages did the client send,
and which of them do we still owe an answer to? This reads the decrypted frames
out of the capture and reports the headers it saw.

A caveat worth stating rather than hiding: a TCP read is not a message boundary.
A frame here may contain several messages back to back, or the tail of one. Until
we can size messages properly -- which needs the client's own packet-template
table (PLAN.md §1.2) -- only the FIRST header in each frame is trustworthy, and
that is all this reports. Counting every u16 in the buffer would produce
confident-looking nonsense.
"""

import argparse
import binascii
import glob
import json
import os
import struct
from collections import Counter


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", default=r"C:\gd\Rurik\vault\captures\authsrv")
    ap.add_argument("--session", help="one .jsonl file; default = all of them")
    a = ap.parse_args()

    files = [a.session] if a.session else sorted(glob.glob(os.path.join(a.vault, "*.jsonl")))
    if not files:
        raise SystemExit(f"no captures in {a.vault} — run a session first")

    headers = Counter()
    total_frames = total_bytes = 0
    sessions = 0

    for path in files:
        sessions += 1
        build = key = None
        frames = []
        for line in open(path, encoding="utf-8"):
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("kind") == "version":
                build = e.get("build")
            elif e.get("kind") == "key_exchange_ok":
                key = e.get("arc4_key", "")[:16]
            elif e.get("kind") == "frame" and e.get("direction") == "c2s":
                plain = binascii.unhexlify(e.get("plain", ""))
                frames.append((e.get("n", 0), plain))

        print(f"\n{os.path.basename(path)}")
        print(f"  build {build}   arc4 {key}…   {len(frames)} client frames")
        for n, plain in frames:
            total_frames += 1
            total_bytes += n
            if len(plain) >= 2:
                h = struct.unpack("<H", plain[:2])[0]
                headers[h] += 1
                preview = plain[2:34]
                printable = "".join(chr(b) if 32 <= b < 127 else "." for b in preview)
                print(f"    0x{h:04x}  {n:5d}B  {binascii.hexlify(preview).decode()[:48]:<48} |{printable}|")

    print(f"\n{sessions} session(s), {total_frames} client frames, {total_bytes} bytes")
    if headers:
        print("\nfirst-header histogram (these are what we owe answers to):")
        for h, c in headers.most_common():
            print(f"  0x{h:04x}  x{c}")
    else:
        print("\nno decrypted client frames — did the key exchange complete?")


if __name__ == "__main__":
    main()
