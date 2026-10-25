---
type: Playbook
title: Toolkit usage
description: How an app repository consumes phosh-toolkit for host setup, agent rules and Flatpak CI.
resource: https://github.com/suitably/phosh-toolkit
tags: [toolkit, setup, agents, ci]
generated: { by: claude-code/2.1.310, at: 2026-10-24T22:30:00Z }
---

# Layout

The toolkit and every app repository are checked out side by side:

```
workspace/
  phosh-toolkit/        # this repository
  my-app/               # one repository per app
```

App repositories refer to the toolkit with the relative path
`../phosh-toolkit`. See the decisions on a
[central toolkit](decisions/central-toolkit.md) and
[one repository per app](decisions/one-repo-per-app.md).

# 1. Host setup

`setup.sh` installs the build stack on Ubuntu 24.04 and adds the Flathub
remote. It is idempotent and does not depend on any agent product.

In a cloud agent environment, put this in the environment setup script,
which runs in the directory above the repositories:

```sh
[ -d phosh-toolkit ] || git clone https://github.com/suitably/phosh-toolkit.git
bash phosh-toolkit/setup.sh
```

On a laptop or VM, run the same two lines in the workspace directory.
`SKIP_FLATHUB=1` skips adding the Flathub remote; `SETUP_PROFILE=ci`
installs only the validation tools (see [host setup](host-setup.md)).

# 2. Agent rules

Each app repository has:

- `CLAUDE.md` containing only `@AGENTS.md`.
- `AGENTS.md` starting with the toolkit import, followed by app-specific
  rules:

  ```markdown
  @../phosh-toolkit/AGENTS.md

  # My App

  App-specific rules go here. The shared rules in
  ../phosh-toolkit/AGENTS.md apply as well.
  ```

Claude Code resolves the `@` import recursively; other agents read the
path in the prose. See the [AGENTS.md decision](decisions/agents-md.md).

# 3. Flatpak CI

`.github/workflows/flatpak.yml` in the app repository:

```yaml
name: Flatpak
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
jobs:
  flatpak:
    uses: suitably/phosh-toolkit/.github/workflows/flatpak.yml@main
    with:
      manifest: de.nexumia.MyApp.yml
```

Inputs: `manifest` (required), `bundle` (file name without extension,
defaults to the app id), `retention-days` (default 14),
`dependencies-doc` (licence inventory, default `docs/dependencies.md`,
see [licensing](licensing.md)), `release`
(attach the bundles to the rolling release `latest` on push) and
`publish-repo` (repository to notify afterwards; needs the secret
`PUBLISH_TOKEN`). Details in the [Flatpak workflow](flatpak-workflow.md);
publishing to the phone through GNOME Software is described in
[shared app repository](app-repository.md).

For a fork of a third-party app, trigger the workflow on the `phosh`
branch instead of `main`.

# 3b. Updates and licences

- `.github/workflows/update-check.yml` calling
  `suitably/phosh-toolkit/.github/workflows/update-check.yml@main`
  weekly, and `.github/dependabot.yml` for GitHub Actions. Setup steps:
  [dependency updates](dependency-updates.md).
- `REUSE.toml` and `LICENSES/`, `docs/dependencies.md`, and licence
  installs for every manifest module: [licensing](licensing.md).

# 4. Screenshots

From the app repository:

```sh
../phosh-toolkit/scripts/screenshot.sh -o shot.png -- <command>
```

See [screenshot testing](screenshot-testing.md).

# 5. Knowledge

Each app repository keeps its own OKF bundle in `docs/` with the same
conventions as this one (see the [OKF decision](decisions/okf-docs.md)).
Toolkit-wide knowledge goes into this bundle instead.
