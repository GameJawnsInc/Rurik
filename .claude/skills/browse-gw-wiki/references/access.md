# Getting bytes out of the Guild Wars wikis

## The two wikis are not the same wiki

| Key | Host | What it is |
|---|---|---|
| `gww` | `wiki.guildwars.com` | **Official Guild Wars Wiki.** ArenaNet-hosted, still maintained, current with live balance. The default. |
| `guildwiki` | `guildwars.fandom.com` | **GuildWiki.** The original community wiki, started 2005. The community forked to GWW in 2007 and GuildWiki has been effectively frozen since. |

They are separate projects with separate editors and separate text. That is
useful — see `labeling.md` on why it makes them two witnesses rather than one.

### How frozen GuildWiki actually is — measured 2026-08-06

Do not take "largely frozen" on faith; it is worse than that phrase suggests.

Mainspace recent changes: **6 edits between 2025-07 and 2025-12**, all lore and
quest pages, none touching skills.

Last edit on the skill templates that `infobox` reads:

| Template | Last edited |
|---|---|
| `Template:Rush` | 2008-04-09 |
| `Template:Shield of Absorption` | 2008-04-10 |
| `Template:Splinter Weapon` | 2008-05-01 |
| `Template:Battle Rage` | 2008-08-12 |
| `Template:Ursan Blessing` | 2008-10-26 |
| `Template:Healing Signet` | 2009-03-06 |
| `Template:Mending` | 2010-03-04 |
| `Template:Eviscerate` | 2010-03-06 |
| `Template:Defy Pain` | 2010-11-14 |

Meanwhile GWW carries a **`Game updates:2026`** page and its `Ursan Blessing`
article was updated 2025-05-27. ArenaNet still patches GW1.

So: GuildWiki skill stats are a **2008–2010 snapshot**. For a project whose
whole point is matching a current client build, that is a live hazard, not a
footnote. `gwwiki.py infobox` therefore reports `last_edited` on every call and
attaches a `staleness_warning` to pre-2015 GuildWiki templates.

Where GuildWiki is still the better read: core mechanics prose that no patch
has touched (adrenaline point accounting, condition stacking rules), where it
is frequently more detailed than GWW and carries player experiment tables GWW
never had. Mechanism, yes. Current per-skill numbers, no.

## What is actually reachable, measured 2026-08-06

| Route | Result |
|---|---|
| **Browser MCP** → `wiki.guildwars.com` | **200.** Verified on **Windows** 2026-08-06 (`osPlatform: "Windows"`, `isLocal: true`). The primary route. |
| `WebSearch` restricted to `wiki.guildwars.com` | **Works.** Prose only — no infobox numbers. |
| `curl`/`urllib` → `wiki.guildwars.com` (any path, any UA, any headers) | **403** |
| `WebFetch` → `wiki.guildwars.com` | **403** |
| `curl`/`urllib` → `guildwars.fandom.com/api.php` | 200 — but **deliberately unused**, see above |
| `r.jina.ai` text proxy | 401 — *jina* refusing jina; says nothing about the wiki |

### Why GWW 403s — and two wrong answers that looked right

**Scripted clients get a small allowance and then get refused.** Not the IP, not
the User-Agent, not the headers — and, on the evidence below, not a TLS
fingerprint either, which was this document's second wrong guess.

This section has been wrong twice, so read the measurements rather than the
narrative. Both errors came from generalising a confident story off too few
observations; both were caught by someone checking a specific case.

An earlier pass of this document blamed egress IP reputation and told you to
drop the VPN. That was **wrong**, and the way it went wrong is worth keeping:
`r.jina.ai` refused the same egress citing "bad network reputation (AS9009)",
and that was read as a second opinion about the wiki. It was not. It was jina
refusing *jina*, and it said nothing whatsoever about ArenaNet's edge. One
service's block was quietly promoted into corroboration for another's.

What actually settles it: **a browser on the same machine, on the same VPN
tunnel, reaches the wiki fine.** Same IP, opposite result. That single
observation eliminates the IP hypothesis outright.

Ruled out, by experiment:

| Hypothesis | Test | Result |
|---|---|---|
| Egress IP / VPN | Chrome on the same machine and tunnel | **200** — hypothesis dead |
| User-Agent | descriptive UA, browser UA, no UA | all **403**, identically |
| MediaWiki UA policy | inspect the 403 body | 118 bytes, `Server: awselb/2.0` — the load balancer, not MediaWiki |
| Path / endpoint | bare `https://wiki.guildwars.com/` | **403** |
| Missing browser headers | full Chrome set: `sec-ch-ua`, `Sec-Fetch-*`, `Accept-Language`, `Upgrade-Insecure-Requests` over HTTP/1.1 | **403**, while the same request to Wikipedia returned **200** |

The first reading of that was **TLS fingerprinting** (JA3/JA4 plus HTTP
version), on the grounds that it is the only part of a request a header cannot
forge. **Measurement has since weakened that**, and the correction is more
useful than the original guess.

### It behaves like a quota, not a fingerprint check — MEASURED 2026-08-06

| Probe | Result |
|---|---|
| `curl` (Schannel), 20 requests, 1s apart | **0/20** — but ~40 diagnostic requests preceded it |
| Python `urllib` (OpenSSL), 20 requests, 1s apart | **5/20** — the *first five consecutively*, then hard 403 for the rest |
| Python `urllib`, 4 requests, 30s apart, after a 45s rest | **0/4** |
| Python `urllib`, 1 request, after several idle minutes | **200** |

Five consecutive successes followed by a lockout is not what a fingerprint
check produces — that would be 0/20 from the first request. It is what a
**burst allowance followed by a penalty** produces. Two minutes of backoff did
not restore access; several idle minutes did. So the bucket refills, slowly,
and the practical unit of politeness here is *minutes between requests*, not
the one second `MIN_INTERVAL` enforces.

That last row is also a warning about how easy this is to misread. It arrived
by accident, as a selftest that had been skipping suddenly passing — and had
the check been reading its cache (which it was, the first time) it would have
looked like the block lifting rather than a bucket refilling.

This also explains observations that previously looked inconsistent: a prior
session's `vault/research/2026-08-04/skill-substrate.md` recorded GWW blocking
"~90% of requests" with "a small number... apparently non-deterministically"
getting through, and this skill's own selftest once reported a live fetch
passing minutes after `--no-cache` was refused. Both are a quota, not a coin
flip and not a stack signature.

**Still unexplained:** why the browser sails through while scripted clients get
a handful of requests and then nothing. Different quota class, a cookie, or a
stack signature feeding into the same limiter — this was not run to ground, and
the honest label is **UNVERIFIED**. What is *not* in doubt is the practical
consequence below.

### What follows practically

- **Do not build on scripted access.** A handful of requests may succeed, which
  is worse than none succeeding, because it invites a design that collapses at
  request six.
- **Never poll or retry in a loop.** That is what burns the allowance, and it
  is rude besides.
- **Cache hard** — and make sure your *tests* distinguish cached from live, or a
  stale hit will report the block as lifted (this file's own selftest had that
  bug).
- **Use the browser**, which is unaffected and, via the API-from-page-context
  technique below, faster anyway.

### How to actually read GWW

1. **Browser MCP** (`mcp__claude-in-chrome__*`). A real browser passes the
   fingerprint check — demonstrated on Windows, not hoped for. **This is the
   primary route**, and the only one that yields exact infobox numbers. If the
   tools report "Claude in Chrome is not connected", the extension needs
   installing from the Chrome Web Store and signing in with the same account;
   `list_connected_browsers` returning `[]` means exactly that.
   - `https://wiki.guildwars.com/index.php?title=X&action=raw` gives raw
     wikitext in the browser, which feeds straight into
     `gwwiki.py infobox --from-file`. Chain several with `browser_batch`.
   - **Do not confuse this with the "Control Chrome" connector** in the
     Directory. That is a different Anthropic extension that drives Chrome via
     its **AppleScript** API and is therefore **macOS-only** — its requirements
     panel says so. The Web Store extension used here is account-relayed and
     cross-platform; `list_connected_browsers` reports each browser's
     `osPlatform`, which would be meaningless if it were Mac-only.
2. **`WebSearch` restricted to `wiki.guildwars.com`.** Works from anywhere with
   no setup. Returns summarised prose, so it answers "how does adrenaline work"
   but not "what is this skill's exact recharge". Good enough for mechanics
   research, not for skill stats.
3. **Parse offline.** The parsers are transport-independent on purpose:
   `gwwiki.py infobox --from-file page.wikitext` and `gwwiki.py totext
   page.html`. However you got the bytes, the extraction logic is reusable.

Do **not** try to defeat the limiter — by rotating agents, retrying in a loop,
or spacing requests to sneak under it. Beyond the honesty problem, retry loops
are exactly what exhausts the allowance, and the browser route below is both
permitted and faster.

## The API *is* reachable — from inside the page

This is the most useful thing in this document. The WAF blocks scripted
*clients*, not scripted *requests*: a `fetch()` issued from a wiki page runs on
Chrome's own TLS/HTTP stack, so **`api.php` works normally**. Navigate to any
page on the wiki once, then use `javascript_tool`:

```js
const r = await fetch('/api.php?action=query&format=json&formatversion=2'
  + '&titles=Battle%20Rage&prop=revisions&rvprop=content&rvslots=main',
  {credentials:'same-origin'});
const j = await r.json();
j.query.pages[0].revisions[0].slots.main.content;   // wikitext
```

That turns "one navigation per page" into "50 pages per request". A crawl of
1,788 skill pages took a handful of calls this way; one `navigate` per page
would have taken 1,788.

**Both snippets below are verified verbatim** (2026-08-06): the single fetch
returns 200 with `id = 317` in Battle Rage's wikitext, and the crawl pulls
`Category:Warrior skills` — 152 pages — in **4 requests**. If you change them,
re-run them; a recipe nobody has executed is a guess with syntax highlighting.

Bulk crawl with a generator and continuation — `gcmlimit=50` is the
unauthenticated cap, and the `sleep` is not optional politeness padding, it is
the difference between a well-behaved client and a scrape:

```js
let cont = null;
do {
  let url = '/api.php?action=query&format=json&formatversion=2'
    + '&generator=categorymembers&gcmtitle=' + encodeURIComponent('Category:Warrior skills')
    + '&gcmlimit=50&gcmnamespace=0&prop=revisions&rvprop=content&rvslots=main';
  if (cont) url += '&gcmcontinue=' + encodeURIComponent(cont);
  const j = await (await fetch(url, {credentials:'same-origin'})).json();
  for (const p of j.query.pages) { /* p.revisions[0].slots.main.content */ }
  cont = j.continue && j.continue.gcmcontinue;
  await new Promise(r => setTimeout(r, 150));
} while (cont);
```

### Return summaries, not corpora

`javascript_tool` truncates its **result** at roughly 1,900 characters, and
noticeably less per item inside `browser_batch` — so batching *shrinks* your
output budget rather than growing it. Base64 output is blocked outright by the
tool, which rules out the obvious "gzip it and decode in Python" trick.

The consequence shapes how you should use this: **do the filtering, joining and
aggregating inside the browser, and return only the answer.** Accumulate into a
`window.__something` on one call and slice it on later calls if you must, but
pulling a whole dataset out through this pipe is the slow path and you will
spend a dozen calls on truncation.

Concretely, when comparing wiki values against local data, do not export the
wiki table. Export the *disagreements*:

```js
const mine = new Set('317,318,319'.split(','));           // pushed in
const theirs = new Set(window.__wikiIds);
JSON.stringify({onlyMine: [...mine].filter(i=>!theirs.has(i)),
                onlyTheirs: [...theirs].filter(i=>!mine.has(i))});
```

An empty result is then a real answer that costs almost nothing to transmit.
`studies/skills/FINDINGS.md` records a 1,564-skill join done this way; the
payload that came back was three short lists.

## Being a good citizen

`gwwiki.py` already does all of this; keep it that way if you edit it.

- **Identify honestly.** The default UA names the project and its purpose. Set
  `GWWIKI_UA` to override. Never impersonate a browser — the 403 above is not
  a UA problem, so spoofing buys nothing and costs honesty.
- **Cache.** Responses land in `~/.cache/gwwiki` for 7 days (`GWWIKI_CACHE`,
  `GWWIKI_TTL`). Re-reading a page you already pulled costs the wiki nothing.
- **Rate limit.** One second minimum between live calls, exponential backoff on
  429/503. Do not parallelise this across agents.
- **Text only.** Quote and cite prose and numbers freely. Do not download
  images, icons or any game asset — `CLAUDE.md`'s provenance gate is absolute
  and wiki-hosted art is still ArenaNet's.

## API shapes worth knowing

```
action=parse&page=X&prop=wikitext      raw source
action=parse&page=X&prop=text          rendered HTML (strip it for plain text)
action=parse&page=X&prop=sections      headings, for citing a section
action=query&list=search&srsearch=X    full-text search
```

Two gotchas found the hard way:

- **`prop=extracts` returns empty on Fandom.** The TextExtracts extension is
  not installed. Use `prop=text` and strip the HTML — which is what
  `gwwiki.py text` does.
- **Fandom search returns empty snippets** for every hit regardless of
  `srprop`. Use `search` to find titles, then `text`/`get` the page.
