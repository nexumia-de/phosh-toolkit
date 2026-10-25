# Decision records

* [Flatpak as distribution format](flatpak-distribution.md) - Apps ship as Flatpak bundles built for x86_64 and aarch64.
* [Own Flatpak repository](own-flatpak-repo.md) - All apps are published as one signed Flatpak repository on GitHub Pages.
* [Domain-based names](domain-names.md) - App ids are de.nexumia.* and the repository is served at flatpak.nexumia.de, independent of the code host.
* [Release channels from main and tags](release-channels.md) - main feeds the nightly app <app id>.Devel, tags v<version> feed the stable app; no long-lived nightly branch.
* [Release automation](release-automation.md) - Changelog fragments per pull request, a release pull request writes the metainfo <release>, merging tags; screenshots from the built Flatpak as release assets.
* [Planning in GitHub issues](planning-issues.md) - Issues, milestones and labels instead of roadmap checklists; an organisation Project is an optional view.
* [One repository per app](one-repo-per-app.md) - Every app lives in its own repository.
* [Central toolkit](central-toolkit.md) - Shared setup, rules, scripts and CI live in phosh-toolkit.
* [Code reuse between apps](code-reuse.md) - Rule of three; shared code moves into phosh-toolkit and apps pin it to a tag.
* [Pinned dependencies with automated updates](pinned-dependencies.md) - Exact pins; bots open update pull requests and issues; licences checked in the same CI gate.
* [Support platforms](support-platforms.md) - Liberapay now, Open Collective once hosted; one support link per app, no prompts in the main UI.
* [OKF for documentation](okf-docs.md) - Knowledge is kept as an Open Knowledge Format bundle in docs/.
* [AGENTS.md for vendor neutrality](agents-md.md) - Agent rules live in AGENTS.md; CLAUDE.md only imports it.
