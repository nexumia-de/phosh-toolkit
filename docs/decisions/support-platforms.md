---
type: Decision Record
title: Support platforms
description: Voluntary support through Liberapay now and Open Collective once hosted; one link per app in metainfo, About dialog, README and FUNDING.yml.
tags: [decision, support, donation, liberapay, open-collective]
generated: { by: claude-code/2.1.310, at: 2026-10-25T18:30:00Z }
---

# Status

Accepted (2026-10-25) by the owner.

# Context

The apps are free for everyone. The owner wants to accept voluntary
support to pay for the AI subscription that builds the apps and to
fund more projects, and wants this to be transparent: what came in,
which fees each platform takes and who receives them. Fees are
acceptable, but fees that fund open source are preferred. Supporters
should be able to choose among several platforms.

Options considered: GitHub Sponsors (no fee, but the owner does not
want to depend on GitHub for this), Ko-fi, Buy Me a Coffee, Patreon
(proprietary, 5–10 % on recurring support), Polar (open source, fee
to a company), Liberapay (non-profit, open source, no own fee) and
Open Collective (open source, public ledger, host fee to a
non-profit fiscal host).

# Decision

Start with **Liberapay** (`suitably`); add **Open Collective**
(`nexumia`) as the main platform once a fiscal host accepts it, since
it also covers the owner's projects outside the Phosh apps. Other
platforms may be added later, ordered so that open-source and
non-profit platforms come first.

Each app links the support page in its metainfo (`url type="donation"`),
its About dialog, its README and `.github/FUNDING.yml`; there are no
prompts in the main UI. Details: [support](../support.md).

# Consequences

- One URL per app to change when Open Collective goes live.
- Liberapay depends on Stripe accepting it as a processor; a second
  platform reduces that risk.
- Income is visible on the platforms themselves; a combined ledger
  page is a later, optional step.
