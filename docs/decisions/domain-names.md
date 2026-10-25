---
type: Decision Record
title: Domain-based app ids and repository URL
description: App ids use de.nexumia.* and the Flatpak repository is served at flatpak.nexumia.de, so neither depends on the code host.
tags: [decision, flatpak, app-id, domain, distribution]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:00:00Z }
sources:
  - id: flathub-verification
    resource: https://docs.flathub.org/docs/for-app-authors/verification
    title: Flathub documentation, app verification
  - id: pages-custom-domain
    resource: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site
    title: GitHub documentation, custom domains for GitHub Pages
  - id: codeberg-tou
    resource: https://codeberg.org/codeberg/org/src/branch/main/TermsOfUse.md
    title: Codeberg Terms of Use, § 2 (1) 7
---

# Status

Accepted (2026-10-25) by the owner.

# Context

App ids were `io.github.suitably.*` and the shared repository was served
at `https://suitably.github.io/phosh-apps/`. Both tie the apps to one
personal GitHub account: moving the repositories to an organization or
off GitHub would change the app id (users must reinstall; an app id
cannot be renamed without an `end-of-life-rebase` kept for a long time)
and the remote URL (GitHub Pages does not redirect after a transfer, so
installed remotes break). Flathub accepts `io.github.<owner>` ids only
from whoever controls that owner, and verifies other ids through the
domain.[^flathub-verification]

Moving only phosh-apps to Codeberg was considered and rejected: since
July 2026 its terms forbid projects that mostly consist of code written
by generative AI tools,[^codeberg-tou] which covers phosh-apps as well
as the apps.

No app had been released when this was decided, so the rename cost
nothing for users.

# Decision

- The owner's domain `nexumia.de` is the namespace: app ids are
  `de.nexumia.<AppName>`, the AppStream developer id is `de.nexumia`.
- The shared Flatpak repository is served at
  `https://flatpak.nexumia.de/` (GitHub Pages custom
  domain[^pages-custom-domain]); the remote is named `nexumia`
  (`nexumia.flatpakrepo`).
- Code stays on GitHub for now; repository URLs (`homepage`,
  `bugtracker`, the `User-Agent`, `uses:` of the reusable workflow) still
  name the GitHub owner and are updated whenever the code moves.

# Consequences

- Moving the code (to a GitHub organization or another host) only
  changes repository URLs and the DNS record of `flatpak`; app ids, the
  remote URL and the signing key stay, so installed apps keep updating.
- The domain must stay registered; losing it breaks the remote and
  Flathub verification.
- Flathub verification, if wanted later, needs
  `https://nexumia.de/.well-known/org.flathub.VerifiedApps.txt`.
- The DNS record and the Pages custom domain are manual one-time steps
  (phosh-apps README).

[^flathub-verification]: Flathub documentation, app verification
[^pages-custom-domain]: GitHub documentation, custom domains for GitHub Pages
[^codeberg-tou]: Codeberg Terms of Use, § 2 (1) 7
