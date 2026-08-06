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

### Why GWW 403s — and the wrong answer that looked right

**The edge fingerprints the HTTP/TLS client.** Not the IP, not the User-Agent,
not the headers.

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

What is left is the part of the request no header can forge: the **TLS
handshake fingerprint (JA3/JA4) and the HTTP version**. Every client available
on this machine is HTTP/1.1 over Schannel or OpenSSL; Chrome is HTTP/2 over
BoringSSL. That is the classic signature AWS WAF Bot Control keys on.

**UNVERIFIED, and honestly so:** this could not be confirmed directly, because
no HTTP/2-capable client is installed — every `curl` here is Schannel without
nghttp2, and there is no `pwsh`. It is the only hypothesis left standing after
the table above, not a demonstrated mechanism. To confirm it you would need a
client that speaks HTTP/2 with a browser-shaped ClientHello.

The practical consequence is not in doubt either way: **`gwwiki.py` cannot
reach GWW over the network from this machine, and no amount of header or UA
work will change that.**

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

Do **not** try to defeat the fingerprinting. Beyond the honesty problem, it
does not work from here — no installed client speaks HTTP/2, and matching a
browser ClientHello is not something the standard library does.

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
