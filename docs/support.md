---
type: Guideline
title: Support for development
description: How the apps ask for voluntary support (Liberapay first, Open Collective later), where the link goes, wording, donor privacy and fee transparency.
tags: [support, donation, liberapay, metainfo, about-dialog]
resource: https://liberapay.com/suitably
generated: { by: claude-code/2.1.310, at: 2026-10-25T18:30:00Z }
sources:
  - id: lp-public
    resource: https://liberapay.com/suitably/public.json
    title: Liberapay public profile data of suitably (fetched 2026-10-25)
  - id: lp-wiki
    resource: https://en.wikipedia.org/wiki/Liberapay
    title: Liberapay (Wikipedia)
  - id: lp-stripe
    resource: https://blog.techlore.tech/stripe-liberapay
    title: Is Stripe Killing Liberapay? (Techlore)
  - id: oc-host
    resource: https://docs.opencollective.com/help/collectives/add-fiscal-host
    title: Open Collective docs, add a fiscal host
  - id: oc-europe
    resource: https://docs.opencollective.com/oceurope/faq/fiscal-hosting-faqs
    title: Open Collective Europe, fiscal hosting FAQs
---

# Support for development

All apps are free for everyone. Users can support development
voluntarily; the money pays for the AI subscription that builds the
apps first, then for new projects. Why this setup:
[decision](decisions/support-platforms.md). Planning and open points:
issue `nexumia-de/phosh-toolkit#11`.

# Platforms

| Platform | Status | URL |
|---|---|---|
| Liberapay | **Active** | `https://liberapay.com/suitably` |
| Open Collective | Collective `nexumia` created, no fiscal host yet, cannot receive money | `https://opencollective.com/nexumia` |

Liberapay account `suitably` (individual) with Stripe connected as
processor, verified live through its public JSON[^lp-public]:

- Stripe business type "Privatperson (Einzelunternehmen) / Freiberufler".
- Statement descriptor `LIBERAPAY.COM` (the Liberapay default): card
  statements show the platform, not the owner's name.
- Stripe Radar **Lite** (no cost). Standard costs €0.05 per payment,
  too much for small support payments; upgrade only if fraud or
  chargebacks appear.
- Liberapay takes no platform fee; only the processor's fee applies
  (on average about 3 % with Stripe, 5 % with PayPal)[^lp-wiki].
  Stripe has closed accounts linked to Liberapay before[^lp-stripe],
  so a second platform is planned.

Open Collective is the intended main platform once a fiscal host has
accepted it: it covers projects outside the Phosh apps, publishes a
full ledger and its host fee goes to a non-profit. Hosts are applied
to under Settings → Fiscal Host[^oc-host]. Open Source Collective once
required 100 GitHub stars; Open Collective Europe pays out in EUR
(host fees 5–10 %, unverified)[^oc-europe]. When it is live, it goes
first in every list below and Liberapay second.

# Where the link goes

Every app repository has:

1. Metainfo: `<url type="donation">` with the support URL. GNOME
   Software shows it as a donate button.
2. About dialog: `dialog.add_link("Support Development", SUPPORT_URL)`.
   libadwaita shows it on the Details page; nothing in the main UI.
3. README: a short "Support" section.
4. `.github/FUNDING.yml` with every active platform, e.g.
   `liberapay: suitably`.

The shared repository page (`flatpak.nexumia.de`, built by
phosh-apps) links it too.

# Rules

- **No nagging**: no pop-ups, banners or prompts in the main UI.
- **Wording**: "Support" / "Support Development". German texts avoid
  "Spende": it implies a tax-deductible gift to a charity, which
  support for a private person is not.
- **Donor privacy**: offer every privacy level a platform has (on
  Liberapay secret, private, public). Thank people by name only if
  they chose public; never name private supporters in public.
- **Fees**: name each platform's fee and who receives it. Platforms
  whose fees go to non-profit or open-source projects come first.
- **Transparency**: income is shown publicly on the platforms
  (Liberapay `receiving` in `public.json`, Open Collective's ledger).
  No manually written ledger is promised. A scheduled job in
  phosh-apps that collects the totals through the platforms' APIs is
  a possible later step.

# Not legal advice

Support payments to a private person are taxable income. Whether a
business registration, the Kleinunternehmerregelung or an Impressum
is needed is for the owner and a tax advisor to decide.

[^lp-public]: Liberapay public profile data of suitably (fetched 2026-10-25)
[^lp-wiki]: Liberapay (Wikipedia)
[^lp-stripe]: Is Stripe Killing Liberapay? (Techlore)
[^oc-host]: Open Collective docs, add a fiscal host
[^oc-europe]: Open Collective Europe, fiscal hosting FAQs
