# Labelling wiki evidence in Rurik

`studies/character/FINDINGS.md` defines the house vocabulary:

| Label | Meaning |
|---|---|
| **OBSERVED** | We saw it ourselves, against the real client, in our own logs. |
| **UPSTREAM** | OpenTyria's code says this, and a verifier confirmed the line. Not a fact about ArenaNet's server. |
| **RECONSTRUCTION** | The source itself signals it is guessing. |
| **CORROBORATED** | Genuinely independent lineages agree; each use names which ones. |
| **CONTESTED** | Sources disagree. Both sides recorded; nobody picks a winner. |
| **UNVERIFIED** | Claimed somewhere, the verifier could not confirm it. |
| **NOT FOUND** | We looked, recorded where, and there is no answer in our sources. |

`MEASURED` and `CLIENT-DATA` also appear in practice for numbers read off a
running client or out of client data files.

## The wiki does not fit any of these

**UPSTREAM** is the closest and it is wrong. UPSTREAM means *a reimplementation's
source code says so* — someone else's guess at ArenaNet's server, carrying that
guess's error bars. The wiki is a different kind of thing: **twenty years of
players observing the retail game and writing down what they saw.** It is not
code and it is not anyone's reimplementation.

Use a distinct label:

> **WIKI** — community documentation of observed retail behaviour, from
> `wiki.guildwars.com` (GWW). Strength depends entirely on whether the claim is
> player-visible; see below.

(The old Fandom GuildWiki is not a source here — its skill data is frozen at
2008–2010. If you are citing it for a historical value, say so explicitly and
give the revision date, because a 2008 number that happens to match the client
is a false corroboration, not a confirmation.)

## Its strength is not uniform, and this is the whole point

**Strong for DISPLAYED values.** A skill's shown adrenaline cost, recharge,
activation, description text, attribute — thousands of players read these off
their own screens for two decades and corrected each other. For "what number
does the client put on this skill", the wiki is *better evidence than any
reimplementation's source*, because a reimplementation is one author's reading
while the wiki is a mass observation of the retail client. Rank it near
OBSERVED for this class of claim.

**Weak for INTERNAL mechanics.** Byte layouts, field offsets, wire encodings,
internal units, server-side formulas. Players inferred these from the outside,
sometimes wrongly, and the wiki is *not* a primary source about the client's
data structures. Rank it near UNVERIFIED here and never build on it alone.

The dividing question: **could a player have seen this from the game window?**
If yes, the wiki is strong. If it takes a debugger or a packet capture, it is
weak.

**Middle ground — inferred-but-testable.** "A strike is 20–25 points depending
on the skill" is not on screen, but it comes from a documented player
experiment with a results table. Treat it as a strong hypothesis with a stated
method, and say so: it is evidence you can *test against client data*, which is
exactly how it earns its keep.

## It is a separate lineage, so it can corroborate

`vault/mirrors/` holds code-derived sources. The ldufr/GWCA cluster shares an
author and must be counted as **one** witness no matter how many repos it
spans. `schema/messages.json` was imported from OpenTyria, so the codec
agreeing with OpenTyria is one witness counted twice.

The wiki shares no author, no code and no ancestry with any of them. It was
built by a different population, from a different method (playing the game
rather than reading disassembly). So **wiki + a code lineage agreeing is
genuine CORROBORATION** and may be written as such, naming both.

## Carry the revision date

GWW tracks live balance, so it needs no vintage hedge the way a frozen wiki
would. Quote the revision date anyway — it is what makes the citation
checkable, and GW1 is still being patched, so "current" has a date attached.

```
WIKI (GWW, "Adrenaline" §Gaining adrenaline, rev. 2025-05-27): 25 per hit.
```

Two asymmetries worth internalising, whatever the source's age:

- The wiki **agreeing** with the client is corroboration of a displayed value,
  not proof of an internal one. It says the number on screen matches; it says
  nothing about the byte that produced it.
- The wiki **disagreeing** with the client is not automatically a wiki error.
  On anything patchable it is most likely a balance change on one side or the
  other, and belongs in the writeup as CONTESTED with both values and dates
  recorded — not silently resolved in favour of whichever you prefer.

The client's own skill record outranks the wiki on internals, always.

## Cite like everything else in this repo

Page title and section, plus which wiki. The section matters — these pages are
long and a bare page name is not checkable.

```
WIKI (GuildWiki, "Adrenaline" §Gaining adrenaline): 25 adrenaline points per
successful hit; +1 point per 1% of maximum health lost.
```

For a value pulled from a skill box, cite the template, since that is the page
the value actually lives on:

```
WIKI (GuildWiki, Template:Battle Rage): adrenaline = 4.
```

When the wiki contradicts itself — and it does — record both sides as
CONTESTED and let client data break the tie. A worked instance of exactly that
is in `SKILL.md`.
