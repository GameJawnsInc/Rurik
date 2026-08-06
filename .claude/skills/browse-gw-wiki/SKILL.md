---
name: browse-gw-wiki
description: >-
  Read the official Guild Wars 1 wiki (wiki.guildwars.com) for game-mechanics
  research — skill costs, recharge, activation, attributes, campaigns, and how
  systems like adrenaline, energy, conditions, armor or aggro actually work.
  Use this whenever a question touches Guild Wars 1 rules, numbers, or skill
  data, including when checking a value read out of the client against what the
  game displays to players. Reach for it before trying WebFetch on
  wiki.guildwars.com — that host returns 403 to scripted fetchers and this
  skill knows why and what to do about it. Also use it when writing up findings
  that cite the wiki, since it defines how wiki evidence is labelled and cited
  in this repo.
---

# Browsing the Guild Wars wiki

One source: **GWW**, `wiki.guildwars.com`. Official, ArenaNet-hosted, current
with live balance — it carries a `Game updates:2026` page.

**The old Fandom GuildWiki (`guildwars.fandom.com`) is deliberately not used
here.** It is reachable when GWW is not, which makes it a standing temptation,
but its skill templates were last edited 2008–2010 (measured; table in
`references/access.md`) while ArenaNet kept patching. It answers *"what did
this cost in 2008"* while looking like it answered *"what does this cost"*. For
a project whose whole purpose is matching a current client build, a stale value
that happens to agree with the client is a **false corroboration** — worse than
no value. If you find yourself reaching for it because GWW is down, read
`access.md` first; that decision has already been made and recorded.

## Scripted HTTP cannot reach GWW — use a browser

GWW's AWS edge **403s scripted clients on every path**. Ruled out by
experiment: it is not the IP (a browser on the same machine and VPN tunnel
succeeds), not the User-Agent, and not the headers (a full Chrome header set
over HTTP/1.1 still 403s while the identical request to Wikipedia returns 200).
What is left is the TLS/HTTP-stack fingerprint, which headers cannot forge.

**Do not spend time on UA strings, header sets or VPN toggles. They do not
work.** `references/access.md` has the full table, including a wrong diagnosis
this skill previously shipped and why it was wrong.

Routes, in order:

1. **Browser MCP** (`mcp__claude-in-chrome__*`) — a real browser passes.
   **Confirmed working on Windows** (2026-08-06). This is the primary route and
   the only one that yields exact infobox numbers. The loop:

   ```
   navigate      https://wiki.guildwars.com/index.php?title=Battle_Rage&action=raw
   get_page_text → raw wikitext, no HTML to strip
   save to a file, then:
   python scripts/gwwiki.py infobox "Battle Rage" --from-file page.wikitext
   ```

   `action=raw` is worth the habit — it returns wikitext directly, so the
   infobox arrives already structured. Use `browser_batch` to chain
   navigate/get_page_text pairs across several skills in one round trip.

   If the tools say "not connected", the extension needs installing and signing
   in. Note this is **not** the "Control Chrome" connector in the Directory —
   that one uses Chrome's AppleScript API and is macOS-only.
2. **`WebSearch` restricted to `wiki.guildwars.com`** — no setup, works
   anywhere, returns summarised prose rather than infobox tables. Fine for
   mechanics questions, not for a skill's exact recharge.
3. **`scripts/gwwiki.py` over the network** — only if the WAF behaviour changes
   or you are on a client that passes. Expect exit 3 otherwise.

## The tool

`scripts/gwwiki.py` — Python 3 standard library only, per the house rules.
Caches to `~/.cache/gwwiki` for 7 days, rate-limits to one live request per
second, and identifies honestly.

Network commands — these need a client the WAF accepts, so expect exit 3
(`BLOCKED`) from an ordinary agent host:

```bash
python scripts/gwwiki.py search "adrenaline strike"      # find page titles
python scripts/gwwiki.py sections Adrenaline             # headings, to cite
python scripts/gwwiki.py text Adrenaline                 # rendered plain text
python scripts/gwwiki.py get Adrenaline                  # raw wikitext
python scripts/gwwiki.py infobox "Battle Rage"           # skill box as JSON
```

Offline commands — these always work, and are the point of the script when the
API is blocked. Pull the page with the browser MCP, save it, parse it here:

```bash
python scripts/gwwiki.py infobox "Battle Rage" --from-file page.wikitext
python scripts/gwwiki.py totext page.html
```

Exit 3 is `BLOCKED` (with the working routes printed), exit 4 is `NOT FOUND`.
`scripts/selftest.py` exercises the lot; it exits 2 with a clear message when
GWW is unreachable rather than passing vacuously or silently changing source.

**Which output to ask for.** `text` for reading prose and tables — readable,
markup gone. `get` when you need template calls, footnote markers or exact
table source. `infobox` for skill stats, always — do not eyeball them out of
prose.

**Verified against real GWW wikitext** (2026-08-06, via the browser). `fixtures/`
holds captured pages and `selftest.py` parses them, so the extraction stays
regression-tested without needing the API. Three GWW-specific shapes it handles,
each of which silently broke an earlier version:

- **`id`** — GWW carries ArenaNet's own skill id (`Battle Rage` 317, `Defy Pain`
  318, `Rush` 319; they run consecutively). This is the join key between a wiki
  page and a row in the client's skill table, and is probably the single most
  useful field here for this project.
- **`concise description`** is spelled with a space, not an underscore. Field
  keys are normalised (spaces → underscores) so callers see one spelling.
- **Attribute scaling is a sibling `{{Skill progression}}` template**, not
  infobox fields. Parsed separately — otherwise `progression` comes back empty
  and looks like "this skill does not scale".

## Worked example 1 — a skill page

Some skill boxes are written inline on the article, some are transcluded from
`Template:<Skill>`. `infobox` tries the article, then the template, and skips
decoy templates like `{{skill icon|...}}` in "Related skills" lists.

```bash
python scripts/gwwiki.py infobox "Battle Rage"
```

```json
{
  "skill": "Battle Rage",
  "source_page": "Battle Rage",
  "last_edited": "2025-XX-XXTXX:XX:XXZ",
  "fields": {
    "name": "Battle Rage", "campaign": "Core",
    "profession": "Warrior", "attribute": "Strength",
    "type": "Stance", "elite": "yes", "adrenaline": "4",
    "description": "For 5...17 seconds, you move 33% faster and gain double adrenaline from attacks. ..."
  },
  "progression": { "progression_0_effect": "Duration", ... }
}
```

`fields` holds the high-value stats — cost (`energy`/`adrenaline`/`sacrifice`/
`upkeep`), `activation`, `recharge`, `attribute`, `campaign`, `type`, `elite`.
A skill only carries the cost keys that apply to it: `Battle Rage` has
`adrenaline` and no `energy`; `Healing Signet` has `activation` and `recharge`
and neither. `progression` is the attribute-scaling table (rank 0 and rank 15
endpoints).

`last_edited` comes back on every call. On GWW that is a currency signal rather
than a warning, but quote it anyway — it is what makes the citation checkable.

## Worked example 2 — a mechanics page, and a real result

The question from live work: the client's 164-byte skill record holds a raw
adrenaline field at `+0x38`. Measured against what the client displayed —
Battle Rage raw `80` → shown `4`, Rush raw `80` → shown `4`, Defy Pain raw
`120` → shown `5`. The widely repeated "25 internal units per displayed strike"
fits none of them (80/25 = 3.2, 120/25 = 4.8). Both `ceil(raw/25)` and
`floor(raw/25)+1` fit all three, and three points cannot separate them.

The wiki supplies the **mechanism**, which is what breaks the tie:

> WIKI (GWW, "Adrenaline"): "You gain 25 units of adrenaline (=one strike) each
> time you successfully hit an opponent with a weapon", plus 1 unit per 1% of
> maximum health lost. And: skills "don't always require exactly a multiple of
> 25 points... some skills may require 3.2 adrenaline strikes or 5.2 strikes."

Gain is a flat 25 per hit, so a skill's displayed cost is simply **how many
hits it takes**:

```
displayed = ceil(raw / 25)
```

The individual skill pages settle it outright. Both `Battle Rage` and `Rush`
carry this note verbatim:

> WIKI (GWW, "Battle Rage" §Notes, and "Rush" §Notes): "This skill exactly
> requires **80 units** of adrenaline to be fully charged, so 3 strikes and 5
> units."

80 units is exactly the client's raw `+0x38`, from the current official wiki —
so the raw field *is* adrenaline units, not some scaled encoding. "3 strikes
and 5 units" is why the display reads 4: three full strikes leave 5 units
owing, and the fourth hit covers them. `ceil(80/25) = 4`. `floor(raw/25)+1`
predicts 5 for a 100-unit skill and 9 for a 200-unit one, so any cost that is
an exact multiple of 25 refutes it.

**Where to look for more raw values:** the per-skill `§Notes`, not a central
table. GWW's `Adrenaline` page has no points→strikes table (it has a
time-to-charge table instead), and `List of adrenal skills` is a server-rendered
`{{Skill table}}` whose raw wikitext contains no data at all. Fetch the skill
page and read its Notes.

This is the shape to aim for: the wiki supplies the **mechanism** and the
**extra data points** that discriminate between hypotheses the client's own
handful of observations cannot separate.

### Why the stale-source rule earned itself

An earlier pass of this work used the Fandom GuildWiki, which listed Defy Pain
at 130 points / 6 strikes. GWW gives `adrenaline = 5`, matching CLIENT-DATA raw
120 and `ceil(120/25)`. The Fandom number was simply out of date. A second
instance from the same pair: Fandom says all adrenaline is lost after **20
seconds** out of combat; GWW says **25**.

Neither page flags itself as uncertain. That is the point — a frozen wiki does
not produce obvious garbage, it produces plausible, specific, confidently
wrong numbers that survive a casual cross-check and then read as corroboration
of whatever they happen to match.

## Labelling what you find

Full guidance in `references/labeling.md`; read it before writing into
`studies/`. The short version:

The repo's vocabulary has no slot for the wiki, and **UPSTREAM is the wrong
one** — that means "a reimplementation's source says so". The wiki is twenty
years of players observing retail. Use **WIKI**, and note that its strength is
not uniform:

- **Strong for player-visible values** — displayed cost, recharge, activation,
  description text. For "what does the client show", mass observation of the
  retail game beats any single reimplementation's source code.
- **Weak for internals** — byte layouts, offsets, wire formats, server
  formulas. Players inferred these from outside; it is not a primary source
  about client data structures. Never build on it alone.
- The test: **could a player have seen this from the game window?**

Because the wiki shares no author, code or ancestry with the mirrors in
`vault/`, wiki + a code lineage agreeing is real **CORROBORATION** — unlike the
ldufr/GWCA cluster, which is one witness wearing several hats.

Cite page title, section, and revision date:
`WIKI (GWW, "Adrenaline" §Gaining adrenaline, rev. 2025-05-27): 25 per hit.`

## Staying welcome

The script identifies honestly, caches, and rate-limits; leave that intact if
you edit it. Override the agent with `GWWIKI_UA` to name a different contact.
Do not spoof a browser — the 403 is not a UA problem, so it buys nothing and
costs honesty.

**Text only.** Quote and cite prose and numbers freely. Never download images,
icons, or any game asset: `CLAUDE.md`'s provenance gate is absolute, and
wiki-hosted art is still ArenaNet's.
