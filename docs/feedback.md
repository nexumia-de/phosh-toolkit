---
type: Guideline
title: Report a problem from the app
description: How every app lets users report a problem or an idea as a GitHub issue without leaving the app - with their own token directly, otherwise through GitHub's issue form in the browser; wording, privacy and the phosh_toolkit.feedback module.
tags: [feedback, issues, github, about-dialog, keyring]
generated: { by: claude-code/2.1.310, at: 2026-11-22T22:30:00Z }
sources:
  - id: gh-issues-api
    resource: https://docs.github.com/en/rest/issues/issues#create-an-issue
    title: GitHub REST API, create an issue
  - id: gh-issue-url
    resource: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue#creating-an-issue-from-a-url-query
    title: GitHub Docs, creating an issue from a URL query
---

# Report a problem from the app

Reporting a problem should cost one menu tap and a few words, so the
owner hears about it while it is fresh. Every app with a UI therefore
has **Report a Problem…** in its main menu. Why this way:
[decision](decisions/in-app-issue-reports.md).

## What the user sees

The dialog asks for the kind (Problem or Idea), a title and the text.
Then one of two ways:

| The user has… | Send | Result |
|---|---|---|
| a GitHub token (typed once, kept in the keyring) | **Send** | The issue is created through the REST API[^gh-issues-api]; the dialog shows "Thank You" and **View Issue** |
| no token | **Open on GitHub** | The browser opens the repository's issue form with title, text, version and device filled in[^gh-issue-url]; the user signs in there and submits |

**Open on GitHub** is always there, also as the way out when sending
fails (wrong token, offline): the banner offers it and the text stays.

- The token is a fine-grained personal access token with
  **Issues: Read and write** on the app's repository ("Create a Token"
  opens GitHub's page). It is stored only after GitHub accepted it, and
  **Forget** removes it.
- A text too long for an address (GitHub serves about 8 KiB) is
  shortened in the form with a note; the full text is put on the
  clipboard to paste.

## What is sent

Only what the user typed, the app version and the kind of device
(`Phone (Phosh)` under Phosh, else `Desktop`). Never account data,
server addresses, file contents or logs; the dialog says so. Log lines
name the repository and the outcome, never title, text or token.

The issue follows the apps' issue forms in `.github/ISSUE_TEMPLATE/`:

| Kind | Form | Label | Fields filled |
|---|---|---|---|
| Problem | `bug.yml` | `bug` | `what`, `version`, `device` |
| Idea | `feature.yml` | `enhancement` | `problem` |

Through the API the body is the same `### Heading` sections GitHub
renders for a form, so both ways read alike. An app whose forms use
other field ids has to align them (or the toolkit grows a parameter
when a second such app exists).

## In the app

```python
from phosh_toolkit import feedback

feedback.install(app, repo="nexumia-de/<app>", app_name="<Visible Name>",
                 version=VERSION, keyring=KEYRING, client=CLIENT)
```

- `install()` adds the action `app.report-problem`; put
  `("Report a Problem…", "app.report-problem")` in the main menu next to
  About.
- `keyring` and `client` are optional: the app's own `Keyring` (the
  token is kind `feedback.GITHUB_TOKEN`) and `http.Client`; without them
  the module makes its own with the app id and the app's User-Agent.
- The About dialog's **Report an Issue** goes to the filled-in form:
  `Adw.AboutDialog(issue_url=feedback.issue_url(repo, VERSION), …)`.
- Tests and screenshots set `PHOSH_TOOLKIT_TEST_KEYRING=memory` (or use
  their own keyring's memory switch).

## Apps outside the GTK stack

Apps not written with `phosh_toolkit` (web apps, Super Productivity
plugins, the Rust fork Nuntius) offer the same two ways in their own
code, with the same wording, fields and privacy rules. QuestArc has no
in-app reporting (owner, 2026-11-22).
