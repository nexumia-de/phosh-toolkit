---
type: Playbook
title: Shared app repository
description: How all apps are published as one signed Flatpak repository on GitHub Pages (suitably/phosh-apps) so GNOME Software on the phone installs and updates them.
resource: https://github.com/suitably/phosh-apps
tags: [flatpak, distribution, repository, gnome-software, pages, ci]
generated: { by: claude-code/2.1.310, at: 2026-10-25T16:00:00Z }
sources:
  - id: flatpak-hosting
    resource: https://docs.flatpak.org/en/latest/hosting-a-repository.html
    title: Flatpak documentation, hosting a repository
  - id: flatpak-repo-files
    resource: https://docs.flatpak.org/en/latest/repositories.html
    title: Flatpak documentation, repositories (.flatpakrepo and .flatpakref)
---

# Goal

Every app stays in its own repository
([one repository per app](decisions/one-repo-per-app.md)), but the phone
adds **one** Flatpak remote and then installs and updates all apps from
GNOME Software. Why not Flathub: [decision](decisions/own-flatpak-repo.md).

# Pieces

```
app repo (tag v*, push to main)            suitably/phosh-apps
  flatpak.yml (toolkit, release + nightly)   apps.txt
   ├─ build x86_64 + aarch64 bundles         publish.yml (dispatch / daily / manual)
   ├─ release v<version>, "nightly" ◄── gh release download ── scripts/build-site.sh
   └─ repository_dispatch "app-updated" ──►     import + sign + build-update-repo
                                               ─► GitHub Pages
                                                  https://flatpak.nexumia.de/
```

1. **App repository**: the reusable [Flatpak workflow](flatpak-workflow.md)
   attaches `<bundle>-<arch>.flatpak` and the source bundle
   `<bundle>-sources-<arch>.flatpak` to GitHub Releases (release assets
   do not expire, unlike workflow artifacts), one per
   [release channel](flatpak-workflow.md#release-channels): with
   `release: true` a tag `v<version>` gets its own release (stable app),
   with `nightly: true` every push to `main` replaces the assets of the
   pre-release `nightly` (app `<app id>.Devel`). Assets the nightly build
   no longer produces (e.g. after an app id rename) are deleted, so the
   old app does not stay in the shared repository. With `publish-repo` and a `PUBLISH_TOKEN`
   secret it then sends `repository_dispatch` `app-updated`.
2. **phosh-apps**: `scripts/build-site.sh` downloads, for every
   repository in `apps.txt`, the bundles of its newest non-pre-release
   release (stable; missing one fails the run) and of the pre-release
   `nightly` if it exists, creates a fresh ostree repository,
   `flatpak build-import-bundle --gpg-sign` for each bundle (the source
   bundles become `runtime/<app id>.Sources` refs, published like on
   Flathub; see [licensing](licensing.md)), and
   `flatpak build-update-repo --gpg-sign` (summary and AppStream
   branches with icons, which GNOME Software reads).[^flatpak-hosting]
   It writes `nexumia.flatpakrepo`, one `<app-id>.flatpakref` per app
   (with `RuntimeRepo` = Flathub, so the GNOME runtime comes from there)
   and an `index.html`.[^flatpak-repo-files] The workflow deploys the
   result to Pages. It fails if a listed app has no bundle, so an app
   never silently vanishes.
3. **Address**: Pages serves the site under the custom domain
   `flatpak.nexumia.de` (DNS `CNAME` to the owner's `github.io`), so the
   remote URL survives moving the code
   ([decision](decisions/domain-names.md)). The workflow reads the URL
   from `actions/configure-pages`, which returns the custom domain once
   it is set in the Pages settings.
4. **Signing**: one GPG key, secret `FLATPAK_GPG_KEY` in phosh-apps; the
   public key is embedded in the `.flatpakrepo`/`.flatpakref` files.

# Facts verified (2026-10-24, locally, flatpak 1.14 on Ubuntu 24.04)

- `build-import-bundle` keeps the bundle's commit id, so rebuilding the
  repository from scratch with an unchanged bundle is not an update on
  the client (`flatpak update` → "Nothing to do").
- `build-update-repo` creates `appstream/<arch>` and `appstream2/<arch>`
  with 64 and 128 px icons from the app's SVG; it needs the gdk-pixbuf
  SVG loader (`librsvg2-common`) like `appstreamcli compose`.
- An ed25519 signing key works for `remote-add` with `GPGKey=` and for
  `flatpak install --from <url>.flatpakref`.
- `build-import-bundle` prints GLib/OSTree `CRITICAL` warnings about a
  missing remote name but exits 0 and imports correctly.

# Add an app

1. App workflow:

   ```yaml
   jobs:
     flatpak:
       permissions:
         contents: write
       uses: suitably/phosh-toolkit/.github/workflows/flatpak.yml@main
       with:
         manifest: de.nexumia.MyApp.yml
         release: true
         nightly: true
         publish-repo: suitably/phosh-apps
       secrets:
         PUBLISH_TOKEN: ${{ secrets.PUBLISH_TOKEN }}
   ```

   Trigger it on `push` to `main` and on tags `v*` (see the
   [Flatpak workflow](flatpak-workflow.md#release-channels)); with
   `nightly: true` the app's meson needs the options `profile` and
   `build_label`.
2. Push the first tag `v<version>`, then add `owner/repo` to `apps.txt`
   in phosh-apps (an app without a stable release fails the publish run).

# On the phone

Open the Pages site and tap an app (GNOME Software handles the
`.flatpakref`), or add the remote once:

```sh
flatpak remote-add --user --if-not-exists nexumia https://flatpak.nexumia.de/nexumia.flatpakrepo
```

GNOME Software lists the stable app ("Cirro") and the nightly app
("Cirro (Nightly)") separately; they install side by side. Single
bundles from CI still work for testing a pull request; see the
[Flatpak workflow](flatpak-workflow.md).

[^flatpak-hosting]: Flatpak documentation, hosting a repository
[^flatpak-repo-files]: Flatpak documentation, repositories
