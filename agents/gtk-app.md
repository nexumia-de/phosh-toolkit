# Agent rules for Phosh GTK apps

Imported by GTK app repositories after [core.md](core.md). Paths are
relative to the phosh-toolkit checkout; from an app repository prefix
them with `../phosh-toolkit/`. "The app's `docs/`" is the `docs/` of the
repository you work in.

## Target platform

- Phosh on a phone: 360×720 logical px, touch, aarch64
  ([device](../docs/device.md), [Phosh](../docs/phosh.md)). Every app
  also works as a normal desktop window.

## UI

Full rules: [adaptive libadwaita](../docs/adaptive-libadwaita.md); read
the rule you touch.

- GTK4 + libadwaita: `AdwBreakpoint` for layout changes;
  `AdwNavigationSplitView` for sidebar/content with a single content
  page; with pushed pages, one `AdwNavigationView` plus a moving sidebar
  (rule 9).
- No horizontal scrolling at 360 px; minimum window 360×294.
- Touch first: no hover-only affordances, targets ≥ 44×44 px, forms
  scroll for the on-screen keyboard, no text field focused when a page
  opens.
- Thumb reach (rule 10): the most used actions in a bottom bar; header
  bar keeps title, back and menu; destructive actions out of easy reach.
- Undo, not confirm: destructive actions act at once with an `AdwToast`
  offering Undo; ask first only when undo is impossible.
- Swipe back everywhere (rule 9): every page opened from another is
  pushed onto an `AdwNavigationView` (or is a split view's content); one
  navigation view per window, never nested in a split view's content; no
  `GtkStack` page switching with own back buttons; `can-pop` stays true.
- Check every UI change at 360×720 and once at desktop size
  ([screenshot testing](../docs/screenshot-testing.md)):

  ```sh
  ../phosh-toolkit/scripts/screenshot.sh -o shot.png -- <command>
  ../phosh-toolkit/scripts/screenshot.sh -W 1000 -H 700 -o wide.png -- <command>
  ```

## Design

Full guideline and review checklist: [design](../docs/design.md).

- libadwaita look after the GNOME HIG: no own theme, no logos in the UI.
- Each app has its own accent colour, set only through
  `--accent-bg-color`/`--accent-fg-color` in its `style.css` and recorded
  in the app's `docs/design.md`
  ([decision](../docs/decisions/app-accent-colours.md)).
- Light/dark follow the system; preferences offer Follow System, Light
  and Dark and keep the choice.
- Style classes before CSS. Unavoidable CSS: colours only via `var(--…)`,
  one `style.css` per app, app-prefixed classes. No hard-coded colours or
  font sizes in chrome; fixed colours only for data and never as the
  only carrier of information.
- Symbolic icons; icon-only buttons get a tooltip and an accessible
  label. Empty/error/offline states: `AdwStatusPage`, `AdwToast`,
  `AdwBanner`. Header capitalisation for titles and buttons, sentence
  capitalisation for descriptions.

## Metadata

- App id `de.nexumia.<AppName>`, files named after it
  ([decision](../docs/decisions/domain-names.md)).
- Code name for repository and app id; the visible name says what the
  app does. For a new app or renaming, suggest names and let the owner
  choose ([decision](../docs/decisions/app-names.md)).
- `.desktop`: `X-Purism-FormFactor=Workstation;Mobile;` including the
  trailing `;` (Phosh hides the app otherwise;
  `desktop-file-validate` does not catch it, [Phosh](../docs/phosh.md)):

  ```sh
  grep -Eiq '^X-Purism-FormFactor=.*mobile;' path/to/*.desktop
  ```

- metainfo: `<recommends><display_length compare="ge">360</display_length></recommends>`
  and `<supports>` with `pointing`, `keyboard` and `touch` controls.
- Support link `https://liberapay.com/suitably`: metainfo
  `<url type="donation">`, About dialog `add_link("Support Development", …)`,
  README, `.github/FUNDING.yml`; no prompts in the main UI
  ([support](../docs/support.md)).
- Before committing metadata, fix every error and warning of:

  ```sh
  appstreamcli validate path/to/*.metainfo.xml
  desktop-file-validate path/to/*.desktop
  ```

## Releases and changelog

- A pull request users notice adds `changelog.d/<slug>.<feature|improvement|fix>.md`
  with one sentence for users; internal changes get the label
  `no-changelog`. Never edit `<release>` elements or versions by hand.
- A feature worth showing gets a `[[screenshots.shot]]` in
  `release.toml`, with recorded data, never live data
  ([releases](../docs/releases.md)).

## Distribution and licences

- Apps ship as Flatpak (GNOME runtime), built for x86_64 and aarch64
  with the reusable workflow `nexumia-de/phosh-toolkit/.github/workflows/flatpak.yml`
  ([Flatpak workflow](../docs/flatpak-workflow.md)). Host setup:
  `bash ../phosh-toolkit/setup.sh`.
- Every manifest source gets `x-checker-data`.
- Install each module's licence texts into
  `/app/share/licenses/<app id>/<module>/`; CI fails otherwise.
- REUSE compliant (`REUSE.toml`, `LICENSES/`); third-party files get
  their real holder and licence. Data sources: follow and record their
  attribution rules ([licensing](../docs/licensing.md)).

## Shared code

- No copy-paste between apps. Code moves into phosh-toolkit
  (`lib/phosh_toolkit/`) when a second app needs it, never in advance;
  apps pin it to a toolkit tag, never `main`
  ([shared code](../docs/shared-connection.md),
  [decision](../docs/decisions/code-reuse.md)).
- A bug whose cause is in `phosh_toolkit` is fixed there, not worked
  around in the app. The task ends only when every app using the module
  ([used by](../docs/shared-connection.md#used-by), keep it current) has
  adopted the fix in its own pull request or has an issue for it.
- Shared behaviour is on by default; opt-in switches only for behaviour
  some apps must not have. After a toolkit change apps need, ask the
  owner to tag a toolkit release.
- New apps start from `../phosh-toolkit/examples/`.

## Before committing (in addition to core)

- `appstreamcli validate` and `desktop-file-validate` if metadata changed.
- Screenshot at 360×720 and the design checklist if the UI changed.
- `reuse lint` passes; new modules are in `docs/dependencies.md`.
- A changelog fragment if users notice the change.
