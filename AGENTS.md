@agents/core.md
@agents/gtk-app.md

# phosh-toolkit

Shared material for the nexumia-de Phosh apps: agent rules (`agents/`),
docs (`docs/`, entry [docs/index.md](docs/index.md)), the shared Python
package `lib/phosh_toolkit/`, scripts, the app skeleton in `examples/`
and reusable CI workflows.

- Agent rules for other repositories live in `agents/`: every
  repository imports [agents/core.md](agents/core.md); GTK apps also
  import [agents/gtk-app.md](agents/gtk-app.md). Keep both short: a rule
  belongs there only if agents get it wrong without it; details go into
  `docs/` and are linked
  ([decision](docs/decisions/lean-agent-rules.md)).
- One repository per app; material shared by apps lives here.
- `main` is protected by `.github/rulesets/main.json`.
