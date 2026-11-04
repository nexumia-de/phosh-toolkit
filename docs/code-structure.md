---
type: Concept
title: Code structure
description: One job per file, the project's own module layout, and when to split a file; applies to apps, forks and phosh_toolkit.
tags: [code, structure, review]
generated: { by: claude-code/2.1.317, at: 2026-11-04T19:00:00Z }
---

# Code structure

## Rule

- **One job per file.** A file does one thing that can be named in a
  few words: "the D-Bus connector", "the stored endpoints", "the album
  page". When describing a file needs "and", it holds several jobs and
  is split.
- **A feature with several jobs is a folder module**: Python
  `feature/__init__.py` plus one module per job; Rust `feature/mod.rs`
  plus one file per job. `__init__.py`/`mod.rs` holds only what ties
  the jobs together (the public entry points, wiring) and a short
  overview of the files.
- **Follow the project's layout.** Use the folder structure, naming and
  file sizes the project already has. In a fork, follow upstream's
  layout (for Fractal: folder modules like `session/notifications/`
  with `mod.rs` and one file per part) and keep new code in new files,
  so upstream merges stay easy.
- **Size is a signal, not the rule.** A file that grows past about 300
  lines is checked for mixed jobs; a long file with one job (a large
  page, a generated table) may stay. A file with several jobs is split
  at any size.
- Split **before the pull request**, not as a later clean-up: the
  first version that goes into review already has the structure.

## Check before committing

For every new or grown file:

1. Name its job in one phrase without "and".
2. Compare its size and place with the files around it.
3. For a feature that is not finished (more steps planned), choose the
   folder module now, so later steps add files instead of growing one.

## Why

The owner found a 530-line `src/unifiedpush.rs` in Nuntius that mixed
four jobs (D-Bus connector, distributor calls, pusher, endpoint store)
although its size was normal for Fractal (nexumia-de/nuntius#9). Split
files are easier to review and to change one at a time, and they match
how the upstream projects are organised.
