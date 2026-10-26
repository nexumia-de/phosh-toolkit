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
  - id: gh-hardening
    resource: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-third-party-actions
    title: GitHub Docs, security hardening for GitHub Actions (pin actions to a full-length commit SHA)
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
| GitHub Actions, pinned to the commit of an exact release (`actions/checkout@3d3c42e… # v7.0.1`) | Dependabot, `.github/dependabot.yml` in every repository, weekly; it updates the SHA and the version comment together | one grouped pull request |
| Playwright for screenshots (`scripts/package.json` in phosh-toolkit) | Dependabot (`npm`, directory `/scripts`), weekly | a pull request |
| The toolkit's reusable workflows (`@main`) | not pinned; toolkit changes must stay backward compatible ([central toolkit](decisions/central-toolkit.md)) | – |
| Check-only tools: the flatpak-external-data-checker image (`:latest`) and Flathub's linter (`org.flatpak.Builder`, branch `stable`) | not pinned, see below | – |

A tag like `@v7` can be moved to other code by whoever controls the
action; a commit SHA cannot, so a compromised or rewritten tag does not
reach the CI (GitHub's hardening guide recommends full-length SHAs[^gh-hardening]).
The version comment tells readers and Dependabot which release the SHA
is; keep it when editing a `uses:` line.

The two check-only tools float on purpose: they produce no shipped
artifact, Flathub updates them for new runtime and metadata rules, and
no bot can propose updates for a `docker://` digest or a Flathub app
commit, so a pin would silently go stale. If a new linter rule fails CI,
fix the finding or add a documented exception (see the
[Flatpak workflow](flatpak-workflow.md#flathub-linter)).

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

# Binary wheel from PyPI, one source per arch. Flathub does not accept
# compiled wheels (docs/flathub.md); prefer the sdist with type pypi. The checker's own "pypi"
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
[^gh-hardening]: GitHub Docs, security hardening for GitHub Actions
