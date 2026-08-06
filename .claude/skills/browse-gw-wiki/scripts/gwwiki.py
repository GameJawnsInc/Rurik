#!/usr/bin/env python3
"""Read the official Guild Wars Wiki (wiki.guildwars.com) through its API.

Python 3 standard library only, per the Rurik house rules.

GWW is the only source this talks to, deliberately. The old Fandom GuildWiki
(guildwars.fandom.com) is reachable when GWW is not, which makes it a standing
temptation -- but its skill templates were last edited 2008-2010 while ArenaNet
still ships GW1 balance updates, so it answers "what did this cost in 2008"
while looking like it answered "what does this cost". A stale value that
happens to match the client is a false corroboration, which is worse for this
project than no value at all. It was evaluated and dropped; see
references/access.md before reintroducing it.

GWW's AWS edge gives scripted clients a small burst allowance and then refuses
them for a long while -- MEASURED: 5 consecutive successes out of 20, then hard
403s, with a 2-minute backoff failing to restore access. No User-Agent, header
set or VPN toggle changes this, and retrying in a loop is precisely what
exhausts the allowance. A browser is unaffected; see references/access.md.

So: fetch with the Chrome browser MCP, then parse here with --from-file. The
parsers are transport-independent for exactly that reason.

Commands
  get      <page>    raw wikitext
  text     <page>    rendered page as plain text
  search   <query>   full-text search
  infobox  <skill>   parsed skill-box fields as JSON
  sections <page>    section headings, to find what to quote

Responses are cached on disk so repeated reads cost the wiki nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

HOST = "wiki.guildwars.com"

# MediaWiki's User-Agent policy asks for a real, identifying agent. Say who we
# are and how to complain; a generic or absent UA is what gets tools banned.
DEFAULT_UA = (
    "Rurik-Research/1.0 (private Guild Wars 1 server-emulator study; "
    "single-user, cached, low-rate; contact via repo owner)"
)
USER_AGENT = os.environ.get("GWWIKI_UA", DEFAULT_UA)

CACHE_DIR = Path(os.environ.get("GWWIKI_CACHE", Path.home() / ".cache" / "gwwiki"))
CACHE_TTL = int(os.environ.get("GWWIKI_TTL", 7 * 24 * 3600))

_last_call = [0.0]
MIN_INTERVAL = 1.0  # seconds between live requests; be a good citizen

BLOCKED_HELP = (
    f"{HOST} returned 403 before MediaWiki saw the request.\n"
    "Scripted clients get a small burst allowance and are then refused for a\n"
    "long while. MEASURED: 5 consecutive successes out of 20, then hard 403s;\n"
    "a 2-minute backoff did not restore access.\n"
    "\n"
    "DO NOT RETRY IN A LOOP. Retrying is what exhausts the allowance, and it\n"
    "is rude to a wiki that owes us nothing. Ruled out by experiment: egress\n"
    "IP (a browser on the same machine and tunnel succeeds), User-Agent, and\n"
    "headers (a full Chrome header set still 403s while the same request to\n"
    "Wikipedia returns 200). No UA or VPN change fixes this.\n"
    "\n"
    "Use instead:\n"
    "  * the Chrome browser MCP tools -- unaffected, and via fetch('/api.php')\n"
    "    from a wiki page it is faster than this script ever was\n"
    "  * WebSearch restricted to wiki.guildwars.com -- prose, not infobox\n"
    "    numbers\n"
    "Then feed what you retrieved back through the parsers here with\n"
    "--from-file, which is transport-independent.\n"
    "\n"
    "Do NOT substitute guildwars.fandom.com; its skill data is frozen at\n"
    "2008-2010. See references/access.md."
)


class WikiBlocked(RuntimeError):
    """The wiki's edge refused us before MediaWiki saw the request."""


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def _cache_path(params: dict) -> Path:
    key = HOST + "?" + urllib.parse.urlencode(sorted(params.items()))
    return CACHE_DIR / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")


def api(params: dict, *, use_cache: bool = True) -> dict:
    """Call the MediaWiki API, going through the on-disk cache first."""
    params = dict(params)
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")

    cp = _cache_path(params)
    if use_cache and cp.exists() and (time.time() - cp.stat().st_mtime) < CACHE_TTL:
        return json.loads(cp.read_text(encoding="utf-8"))

    gap = time.time() - _last_call[0]
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)

    url = f"https://{HOST}/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })

    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as fh:
                data = json.loads(fh.read().decode("utf-8"))
            _last_call[0] = time.time()
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cp.write_text(json.dumps(data), encoding="utf-8")
            return data
        except urllib.error.HTTPError as e:
            _last_call[0] = time.time()
            if e.code == 403:
                raise WikiBlocked(BLOCKED_HELP) from None
            last_err = e
            if e.code in (429, 503) and attempt < 2:
                time.sleep(2 ** attempt * 2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt * 2)
                continue
    raise RuntimeError(f"{HOST}: {last_err}")


# --------------------------------------------------------------------------
# page content
# --------------------------------------------------------------------------

def get_wikitext(page: str) -> str:
    d = api({"action": "parse", "page": page, "prop": "wikitext"})
    if "error" in d:
        raise KeyError(f"{page}: {d['error'].get('info', d['error'])}")
    return d["parse"]["wikitext"]


def last_edited(page: str) -> str | None:
    """Timestamp of the page's most recent revision, or None."""
    d = api({"action": "query", "prop": "revisions", "titles": page,
             "rvprop": "timestamp"})
    for p in d.get("query", {}).get("pages", []):
        for rv in p.get("revisions") or []:
            return rv.get("timestamp")
    return None


class _Stripper(HTMLParser):
    SKIP = {"script", "style", "sup"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("p", "div", "tr", "li", "h1", "h2", "h3", "h4", "br"):
            self.out.append("\n")
        elif tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)

    def text(self) -> str:
        t = html.unescape("".join(self.out))
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
        return "\n".join(ln.rstrip() for ln in t.splitlines()).strip()


def html_to_text(markup: str) -> str:
    """Rendered HTML to readable plain text. Transport-independent."""
    s = _Stripper()
    s.feed(markup)
    return s.text()


def get_plaintext(page: str) -> str:
    """Plain text of the rendered page, tables included."""
    d = api({"action": "parse", "page": page, "prop": "text"})
    if "error" in d:
        raise KeyError(f"{page}: {d['error'].get('info', d['error'])}")
    return html_to_text(d["parse"]["text"])


def get_sections(page: str) -> list:
    d = api({"action": "parse", "page": page, "prop": "sections"})
    if "error" in d:
        raise KeyError(f"{page}: {d['error'].get('info', d['error'])}")
    return [
        {"index": s.get("index"), "level": s.get("level"), "line": s.get("line")}
        for s in d["parse"]["sections"]
    ]


def search(query: str, limit: int = 10) -> list:
    d = api({"action": "query", "list": "search", "srsearch": query,
             "srlimit": str(limit), "srprop": "snippet|wordcount"})
    out = []
    for hit in d.get("query", {}).get("search", []):
        snippet = re.sub(r"<[^>]+>", "", hit.get("snippet", "") or "")
        out.append({
            "title": hit["title"],
            "snippet": html.unescape(snippet).strip(),
            "wordcount": hit.get("wordcount"),
        })
    return out


# --------------------------------------------------------------------------
# skill infobox
# --------------------------------------------------------------------------

def _split_template_fields(body: str) -> dict:
    """Split `| key = value` pairs at brace/bracket depth zero.

    Values routinely contain [[links]], {{templates}} and '''markup''', so a
    naive split on '|' corrupts them.
    """
    parts, depth, buf = [], 0, []
    i = 0
    while i < len(body):
        nxt = body[i:i + 2]
        if nxt in ("{{", "[["):
            depth += 1
            buf.append(nxt)
            i += 2
            continue
        if nxt in ("}}", "]]"):
            depth = max(0, depth - 1)
            buf.append(nxt)
            i += 2
            continue
        if body[i] == "|" and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(body[i])
        i += 1
    parts.append("".join(buf))

    fields = {}
    for part in parts[1:]:  # parts[0] is the template name
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        # GWW writes `concise description` / `var1 at0`; the old GuildWiki wrote
        # `concise_description`. Normalise so callers see one spelling.
        k = "_".join(k.strip().lower().split())
        if k:
            fields[k] = v.strip()
    return fields


def _iter_templates(text: str):
    """Yield (name, body) for every top-level {{...}} template.

    Scanning all of them beats string-matching a prefix: `{{skill icon|...}}`
    in a "Related skills" list otherwise masquerades as the skill box.
    """
    i = 0
    while i < len(text):
        if text[i:i + 2] != "{{":
            i += 1
            continue
        depth, j = 0, i
        while j < len(text):
            if text[j:j + 2] == "{{":
                depth += 1
                j += 2
                continue
            if text[j:j + 2] == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    inner = text[i + 2:j - 2]
                    yield re.split(r"[|\n}]", inner, maxsplit=1)[0].strip(), inner
                    break
                continue
            j += 1
        else:
            break
        i = j


# Fields this project cares about, in a stable order. `id` leads because GWW
# carries ArenaNet's own skill id, which is the join key between a wiki page and
# a row in the client's skill table -- by far the most useful field here.
INFOBOX_KEYS = [
    "id", "name", "campaign", "profession", "attribute", "type", "elite",
    "energy", "adrenaline", "activation", "recharge", "upkeep", "sacrifice",
    "description", "concise_description",
]


def infobox_from_wikitext(wikitext: str, skill: str = "", source: str = "") -> dict:
    """Parse skill-box fields out of wikitext. Transport-independent.

    Use this on text pulled by the browser MCP when the API is unreachable.
    """
    fields = _find_skill_box(wikitext)
    if not fields:
        raise KeyError(f"no skill box in supplied wikitext for {skill!r}")
    ordered = {k: fields[k] for k in INFOBOX_KEYS if k in fields}

    # Attribute scaling lives in a sibling {{Skill progression}} template on
    # GWW, not inside the infobox -- look for it separately or it comes back
    # empty and silently looks like "this skill does not scale".
    progression = {k: v for k, v in fields.items() if k.startswith("progression")}
    for name, body in _iter_templates(wikitext):
        if name.lower().startswith("skill progression"):
            progression.update(_split_template_fields(body))
            break

    return {
        "skill": skill or fields.get("name", ""),
        "wiki": HOST,
        "source_page": source or "<supplied>",
        "fields": ordered,
        "other": {k: v for k, v in fields.items()
                  if k not in ordered and not k.startswith("progression")},
        "progression": progression,
    }


def _find_skill_box(wikitext: str) -> dict | None:
    """First template in the text that carries skill-box content."""
    for name, body in _iter_templates(wikitext):
        cand = _split_template_fields(body)
        if not cand:
            continue
        # GWW names its box differently from the old GuildWiki, so match on
        # shape rather than on a template name: a description plus at least
        # one stat field is a skill box and a nav template never is.
        looks_right = "description" in cand and any(
            k in cand for k in ("energy", "adrenaline", "activation",
                                "recharge", "upkeep", "sacrifice",
                                "profession", "attribute")
        )
        if looks_right or name.lower().startswith("skill box"):
            return cand
    return None


def get_infobox(skill: str) -> dict:
    """Parsed skill-box fields.

    Tries the article, then `Template:<skill>` -- some skill boxes are
    transcluded rather than written inline.
    """
    tried = []
    for page in (skill, f"Template:{skill}"):
        try:
            wt = get_wikitext(page)
        except KeyError as e:
            tried.append(str(e))
            continue
        if _find_skill_box(wt):
            out = infobox_from_wikitext(wt, skill, page)
            out["last_edited"] = last_edited(page)
            return out
        tried.append(f"{page}: no skill box")

    raise KeyError(f"no skill box found for {skill!r}: {'; '.join(tried)}")


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name in ("get", "text", "sections"):
        s = sub.add_parser(name)
        s.add_argument("page")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s = sub.add_parser("infobox")
    s.add_argument("skill")
    s.add_argument("--from-file", metavar="PATH",
                   help="parse wikitext from a file instead of fetching -- use "
                        "when the API is blocked and you pulled the page with "
                        "the browser MCP")
    s = sub.add_parser("totext", help="HTML file to plain text (browser output)")
    s.add_argument("path")

    a = p.parse_args(argv)
    if a.no_cache:
        global CACHE_TTL
        CACHE_TTL = 0

    try:
        if a.cmd == "get":
            out = get_wikitext(a.page)
            print(json.dumps({"page": a.page, "wikitext": out}) if a.json else out)
        elif a.cmd == "text":
            out = get_plaintext(a.page)
            print(json.dumps({"page": a.page, "text": out}) if a.json else out)
        elif a.cmd == "sections":
            out = get_sections(a.page)
            if a.json:
                print(json.dumps(out, indent=2))
            else:
                for s_ in out:
                    print(f"{'  ' * (int(s_['level']) - 1)}{s_['index']}. {s_['line']}")
        elif a.cmd == "search":
            out = search(a.query, a.limit)
            if a.json:
                print(json.dumps(out, indent=2))
            else:
                for hit in out:
                    wc = hit.get("wordcount")
                    print(f"* {hit['title']}" + (f"  ({wc} words)" if wc else ""))
                    if hit["snippet"]:
                        print(f"    {hit['snippet']}")
        elif a.cmd == "infobox":
            if getattr(a, "from_file", None):
                wt = Path(a.from_file).read_text(encoding="utf-8")
                out = infobox_from_wikitext(wt, a.skill, a.from_file)
            else:
                out = get_infobox(a.skill)
            print(json.dumps(out, indent=2))
        elif a.cmd == "totext":
            print(html_to_text(Path(a.path).read_text(encoding="utf-8")))
    except WikiBlocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 3
    except KeyError as e:
        print(f"NOT FOUND: {e}", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
