---
type: Decision Record
title: In-app issue reports
description: Users report problems as GitHub issues from inside the apps - directly with their own token, otherwise through the prefilled issue form in the browser; no relay server, no device flow yet.
tags: [decision, feedback, issues, github]
generated: { by: claude-code/2.1.310, at: 2026-11-22T22:30:00Z }
---

# Status

Accepted (owner, 2026-11-22): "in all my repositories and apps, users
can create GitHub issues directly, so friction is low", both ways, not
in QuestArc. How it works: [feedback](../feedback.md).

# Context

GitHub only takes an issue from a signed-in account. The options:

1. **Prefilled issue form in the browser.** No secret and no request
   from the app; anyone with a GitHub account can submit; one step in
   the browser.
2. **The user's own token in the app.** The issue is created without
   leaving the app. Needs a token once; LocalGameGalaxy already works
   this way (`src/lib/github.ts`).
3. **GitHub's OAuth device flow.** Like 2, but signing in by code
   instead of pasting a token. Needs an OAuth app registered by the
   owner and its client id in every app.
4. **A relay server with a bot token.** Reports without a GitHub
   account, but a server to run, a secret to guard and spam to handle.

# Decision

Options 1 and 2 together: the dialog sends directly when a token is
there and otherwise opens the filled-in form. Option 4 is not built (a
service of our own, against "no third-party services"). Option 3 can
replace pasting a token later without changing the dialog's two ways;
it waits for the owner to register an OAuth app.

QuestArc is left out by the owner's choice; its plugin also makes no
network requests by rule.

# Consequences

- `phosh_toolkit.feedback` holds the dialog for the GTK apps; apps on
  other stacks write their own along [feedback](../feedback.md).
- Every app's issue forms keep the field ids the module fills.
