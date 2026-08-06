# Test fixtures

Wikitext captured from the official Guild Wars Wiki (`wiki.guildwars.com`) on
2026-08-06 via `index.php?title=<page>&action=raw`.

These exist so `scripts/selftest.py` can verify the infobox parser against the
real thing. GWW 403s scripted clients, so a test that needed the live API would
skip forever and prove nothing — and every bug the parser has actually had was
a GWW-specific spelling the old Fandom format did not exhibit (`concise
description` with a space, progression in a sibling template, the `id` field).
Synthetic fixtures would have reproduced none of them.

**Provenance.** This is community-written wiki *text* — prose and template
fields — quoted for testing and cited in `studies/skills/FINDINGS.md`. It is not
game data: no `Gw.dat` bytes, no extracted assets, no images. Guild Wars Wiki
content is published by its contributors under the wiki's own licence; these
excerpts are here as citations, not as a redistributed corpus.

Refresh by re-fetching the same `action=raw` URLs. If a fixture changes, that
is a signal worth reading rather than a test to silence — GW1 still ships
balance updates, and a moved number is exactly what this project needs to know.
