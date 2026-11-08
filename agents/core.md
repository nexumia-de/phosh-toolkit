# Core agent rules (all nexumia-de repositories)

Imported by every repository with `@../phosh-toolkit/agents/core.md`.
GTK app repositories also import [gtk-app.md](gtk-app.md). Paths in
these files are relative to the phosh-toolkit checkout; from another
repository prefix them with `../phosh-toolkit/`. Why the rules are
split and kept short: [decision](../docs/decisions/lean-agent-rules.md).

## Language

- Everything in the repositories is English: code, comments, docs,
  commits, pull requests, issues.
- The owner may write German or English; reply in English.
- Commands for the owner: one command per code block, no comments
  inside the block, explanations around it.

## Token budget

Every request re-sends the whole session, and every rule file is loaded
on every turn. Spend tokens on the task, not on context.

- One task per session. Write findings to `docs/` as you go, so a new
  session can continue instead of a long one growing.
- Read only what the task needs: `grep`/`rg` first, then the relevant
  lines (`sed -n 'a,bp'`), not whole files or all docs up front.
- Keep command output short: send builds and test runs to a log file and
  show `tail -40` or the `grep` of errors; never print whole logs, lock
  files or generated files.
- Run the narrowest check while working (one test file, one target) and
  the full check once before committing.
- Subagents and workflows only for independent work that really runs in
  parallel or for wide searches; give them a small model and a narrow
  brief. Never fan out for a lookup you can do in a few commands.
- Never poll (CI, builds, servers) in a loop: subscribe to pull request
  activity or run one blocking wait.
- Screenshots only when the UI changed; for your own check use scale 1.
- Do not attach or clone repositories the task does not need.
- Answers to the owner: short, no restating, no closing summary.

## Network access

- When a host is blocked (proxy `403`, DNS, TLS, tool error), tell the
  owner at once which hosts are needed and why. List only hosts you
  tested (`curl -sS -m 15 -o /dev/null https://<host>/`), in one fenced
  block, one host per line, no comments; explain them outside it.
- Continue with what does not need them; never invent blocked data.
- Record needed hosts in the repository's `docs/`.

## Dependencies

- Pin every dependency exactly; updates come as bot pull requests.
  GitHub Actions are pinned to a commit SHA with the release as comment
  (`@<sha> # v7.0.1`). Details: [dependency updates](../docs/dependency-updates.md).
- Before adding a dependency, read its licence from its files, check
  compatibility and list it in the repository's `docs/dependencies.md`.

## Repositories and branches

- Protected default branches: [branch protection](../docs/branch-protection.md).
  When a CI job is renamed, update the required check names in the same
  pull request and tell the owner to re-import the ruleset.
- Forks of third-party projects: the upstream branch stays identical to
  upstream; fork work goes to `phosh`.

## Code structure

- One job per file; a feature with several jobs is a folder module.
  Past about 300 lines, check for mixed jobs and split before the pull
  request. In forks follow upstream's layout and put new code in new
  files. Details: [code structure](../docs/code-structure.md).

## Planning

- Where a repository plans with GitHub milestones: work items are issues
  in milestones `M<n> – <goal>` with `area: …` labels; work on the lowest
  open milestone and do not start a later one without asking.
  `docs/roadmap.md` holds goals only. A pull request that finishes an
  issue says `Closes #<n>`. Future work found on the way becomes an
  issue, not a line in a doc. Details: [planning](../docs/planning.md).

## Knowledge

- Each repository keeps its knowledge in its own OKF v0.2 bundle
  (`docs/`, entry `docs/index.md`); shared knowledge is in
  phosh-toolkit's `docs/`. Open the index and read only the concepts the
  task touches.
- Update `docs/` in the same commit as the change: the concept file,
  `docs/index.md` for added or removed concepts, an entry in
  `docs/log.md`. Never leave findings only in chat.
- One concept per file with YAML frontmatter (`type`, `title`,
  `description`, `tags`, `generated: { by, at }`, `sources` with `[^id]`
  footnotes). Agents use `<tool>/<version>` as actor; never write a
  `human:` actor in `verified` unless that person confirmed it.
- Decisions go into `docs/decisions/` as `type: Decision Record`.
  Cross-references are relative markdown links.

## Before committing

1. Build and run the tests of the touched project.
2. No code duplicated from another repository; every new or grown file
   has one job.
3. `docs/` updated in the same commit; commit message and texts in
   English.

## After the task: pull request and CI

Standing instruction unless a repository says otherwise.

1. When the task is pushed, open a pull request from the working branch
   into the default branch in every repository the task changed, unless
   one is open. The body says what changed, why and how it was verified,
   names closed issues and links the related pull requests.
2. Subscribe to each pull request's activity instead of polling. On a
   red check: find the cause, fix, validate locally, push. Never skip or
   disable a check.
3. A failure not caused by the pull request (red on the default branch
   too, blocked host, missing secret): say so in a pull request comment
   and tell the owner what is needed.
4. Report to the owner when all pull requests are green, or what blocks
   them, with links.
5. Do not merge; merging stays with the owner.
