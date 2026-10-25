---
type: Playbook
title: Dependency updates
description: How every pinned version (Flatpak modules, GNOME runtime, GitHub Actions) is kept current through automated pull requests and issues.
tags: [dependencies, updates, flatpak, ci, dependabot]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:00:00Z }
sources:
  - id: fedc
    resource: https://github.com/flathub-infra/flatpak-external-data-checker
    title: flatpak-external-data-checker README
  - id: dependabot
    resource: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
    title: Dependabot options reference
---

# Principle

Versions are **pinned exactly** (Flatpak sources need a checksum anyway)
and **updated by bots through pull requests**, which CI builds before
anyone merges them. Nothing floats on "latest": a build is reproducible,
and an update is one reviewable change. Why:
[decision](decisions/pinned-dependencies.md).

# What updates what

| Pinned thing | Tool | Result |
|---|---|---|
| Flatpak module sources (tarballs, wheels, files) | flatpak-external-data-checker in the reusable [update-check workflow](../.github/workflows/update-check.yml), weekly | one pull request with new URLs and checksums |
| `runtime-version` (GNOME runtime) | same workflow, job `runtime` | an issue "GNOME runtime N is available" |
| GitHub Actions (`actions/checkout@v7`, …) | Dependabot, `.github/dependabot.yml` in every repository, weekly | one grouped pull request |
| The toolkit's reusable workflows (`@main`) | not pinned; toolkit changes must stay backward compatible ([central toolkit](decisions/central-toolkit.md)) | – |

# x-checker-data per source type

The checker reads `x-checker-data` on each source.[^fedc] Patterns used
in the apps:

```yaml
# GNOME tarball (download.gnome.org)
x-checker-data:
  type: gnome
  name: libshumate
  stable-only: true

# GitHub release asset
x-checker-data:
  type: json
  url: https://api.github.com/repos/protobuf-c/protobuf-c/releases/latest
  version-query: .tag_name | sub("^v"; "")
  url-query: .assets[] | select(.name == "protobuf-c-" + $version + ".tar.gz") | .browser_download_url

# Binary wheel from PyPI, one source per arch. The checker's own "pypi"
# type only handles noarch wheels, so query PyPI's JSON API instead.
x-checker-data:
  type: json
  url: https://pypi.org/pypi/numpy/json
  version-query: .info.version
  url-query: '[.urls[] | select(.packagetype == "bdist_wheel" and (.filename | test("-cp314-cp314-manylinux[^-]*_x86_64\\.whl$")))] | first | .url'
```

The wheel tag (`cp314`) is the runtime's Python. When a runtime update
changes Python, update the tags together with `runtime-version`.

Sources that only make sense together with another one (for example a
licence file for a library a wheel bundles) get no checker; note in a
comment which source they follow.

# Setting up an app

1. `.github/workflows/update-check.yml` calling the toolkit workflow
   (usage block at the top of the
   [workflow](../.github/workflows/update-check.yml)).
2. `.github/dependabot.yml` with the `github-actions` ecosystem.
3. `x-checker-data` on every source of the manifest.
4. Repository settings → Actions → General → *Allow GitHub Actions to
   create and approve pull requests*, otherwise the checker cannot open
   pull requests.
5. Optional but recommended: a fine-grained token as secret
   `UPDATE_TOKEN` (repository access: the app; permissions: contents,
   pull requests and workflows read/write). Pull requests opened with the
   default `GITHUB_TOKEN` do not trigger CI, so without the token start
   the build by hand (*Run workflow* on the Flatpak workflow for the
   update branch).

Run the checker locally (read-only) to test new `x-checker-data`:

```sh
flatpak run --filesystem="$PWD" org.flathub.flatpak-external-data-checker "$PWD/de.nexumia.MyApp.yml"
```

# Reviewing an update pull request

- CI green (build on both arches, licence checks).
- New major versions: read the upstream changelog.
- A licence change shows up in CI only if the licence files disappear;
  compare the module's licence with the app's `docs/dependencies.md` and
  update the entry (see [licensing](licensing.md)).

[^fedc]: flatpak-external-data-checker README
[^dependabot]: Dependabot options reference
