#!/usr/bin/env python3
"""Release automation for app repositories (docs/releases.md).

Reads `release.toml` in the app repository root:

    metainfo = "data/de.nexumia.MyApp.metainfo.xml"
    version-files = ["meson.build", "myapp/__init__.py"]
    fragments = "changelog.d"          # default

    [screenshots]                      # optional
    env = { MYAPP_DEMO = "{root}/tests/data/demo" }
    expose = ["{root}/tests/data/demo"]
    delay = 3

    [[screenshots.shot]]
    name = "main"
    caption = "The main window"
    actions = ["win.show-thing"]

Commands:

    release.py check [--changed FILE]      validate changelog fragments; with
                                           the files a pull request changed,
                                           also require one
    release.py next-version                version the pending fragments ask for
    release.py prepare [--version V] [--repo OWNER/REPO]
                                           bump the version, add the metainfo
                                           <release>, list the screenshots of
                                           the release, delete the fragments
    release.py notes VERSION               release notes as Markdown
    release.py latest [--metainfo FILE]    newest stable release version
    release.py devel --suffix S            add a development <release> with the
                                           pending fragments (nightly builds)
    release.py screenshots --out DIR [--check-metainfo FILE] -- COMMAND...
                                           take every screenshot of every shot
    release.py flathub-manifest MANIFEST_JSON --url URL --tag TAG --commit SHA
                                           the manifest for a Flathub submission
                                           (needs no release.toml; exit code 3
                                           if the app module has no
                                           `type: dir` source)

Standard library only (Python 3.11+), so CI runs it without installing
anything.
"""
import argparse
import datetime
import fnmatch
import json
import os
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

# Fragment types in the order they are listed; a feature bumps the minor
# version, everything else the patch version.
TYPES = ("feature", "improvement", "fix")
FRAGMENT = re.compile(r"[a-z0-9][a-z0-9._-]*\.(%s)\.md" % "|".join(TYPES))
# Files in the fragment directory that are not fragments.
IGNORED = {"README.md", ".gitkeep"}
# A pull request that changes only these needs no fragment.
EXEMPT = ("docs/*", "tests/*", ".github/*", "*.md", "LICENSES/*",
          "REUSE.toml", ".gitignore", "release.toml")
# Every shot is taken at these sizes and colour schemes. Phone: the Phosh
# logical resolution at scale 2, like the phone's screen.
SIZES = {"phone": (360, 720, 2), "desktop": (1000, 700, 1)}
SCHEMES = ("light", "dark")
# Only these go into the metainfo: a store that ignores the screenshot
# environment would show every dark screenshot as a duplicate. The dark
# ones are still taken, for review and as release assets.
LISTED = (("phone", "light"), ("desktop", "light"))
SCREENSHOT_SH = Path(__file__).resolve().parent / "screenshot.sh"


class ReleaseError(Exception):
    pass


class NotApplicable(ReleaseError):
    """Nothing to do for this app (exit code 3)."""


class Config:
    def __init__(self, root):
        self.root = Path(root).resolve()
        path = self.root / "release.toml"
        if not path.is_file():
            raise ReleaseError(f"{path} is missing")
        with path.open("rb") as f:
            data = tomllib.load(f)
        self.metainfo = self.root / data["metainfo"]
        self.version_files = [self.root / p for p in data.get("version-files", [])]
        self.fragments = self.root / data.get("fragments", "changelog.d")
        screenshots = data.get("screenshots", {})
        self.shots = screenshots.get("shot", [])
        self.shot_env = {k: self.expand(v)
                         for k, v in screenshots.get("env", {}).items()}
        self.shot_expose = [self.expand(p) for p in screenshots.get("expose", [])]
        self.shot_delay = screenshots.get("delay", 3)
        for shot in self.shots:
            if not re.fullmatch(r"[a-z0-9-]+", shot.get("name", "")):
                raise ReleaseError(f"screenshot name {shot.get('name')!r}: "
                                   "use lower-case letters, digits and '-'")
            if not shot.get("caption"):
                raise ReleaseError(f"screenshot {shot['name']} has no caption")

    def expand(self, value):
        return str(value).replace("{root}", str(self.root))


# Changelog fragments

def fragments(config):
    """[(path, type, [entries])] in listing order; raises ReleaseError for
    files that are not valid fragments."""
    if not config.fragments.is_dir():
        return []
    found, errors = [], []
    for path in sorted(config.fragments.iterdir()):
        if path.name in IGNORED:
            continue
        match = FRAGMENT.fullmatch(path.name)
        if not match:
            errors.append(f"{path.name}: name it <slug>.<{'|'.join(TYPES)}>.md")
            continue
        # Paragraphs (separated by blank lines) are entries; lines of one
        # paragraph are joined.
        text = path.read_text(encoding="utf-8").strip()
        entries = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)
                   if p.strip()]
        if not entries:
            errors.append(f"{path.name}: empty")
            continue
        found.append((path, match[1], entries))
    if errors:
        raise ReleaseError("invalid changelog fragments in "
                           f"{config.fragments.name}/:\n  " + "\n  ".join(errors))
    return sorted(found, key=lambda f: (TYPES.index(f[1]), f[0].name))


def needs_fragment(changed, fragment_dir):
    """True if a pull request that changed these paths needs a fragment."""
    prefix = fragment_dir.rstrip("/") + "/"
    return any(not path.startswith(prefix)
               and not any(fnmatch.fnmatch(path, g) for g in EXEMPT)
               for path in changed)


def description(entries, indent, unit):
    """<description> lines for a <release>."""
    pad = indent + unit
    lines = [f"{indent}<description>", f"{pad}<ul>"]
    lines += [f"{pad}{unit}<li>{escape(e)}</li>" for e in entries]
    lines += [f"{pad}</ul>", f"{indent}</description>"]
    return lines


# Versions and the metainfo

def parse_version(version):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ReleaseError(f"version {version!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(n) for n in match.groups())


def latest_release(metainfo_text):
    """Newest stable release version (development releases skipped)."""
    root = ET.fromstring(metainfo_text)
    for release in root.findall("releases/release"):
        if release.get("type", "stable") == "stable":
            return release.get("version")
    raise ReleaseError("the metainfo has no stable <release>")


def next_version(current, found):
    major, minor, patch = parse_version(current)
    if any(kind == "feature" for _, kind, _ in found):
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _releases_line(text):
    match = re.search(r"^([ \t]*)<releases>[ \t]*\n", text, re.M)
    if not match:
        raise ReleaseError("the metainfo has no <releases> element")
    # Indentation unit: from the first <release>, else two spaces.
    unit = "  "
    nested = re.match(r"([ \t]*)<release\b", text[match.end():])
    if nested and len(nested[1]) > len(match[1]):
        unit = nested[1][len(match[1]):]
    return match, unit


def insert_release(text, version, date, entries, kind="stable"):
    match, unit = _releases_line(text)
    indent = match[1] + unit
    type_ = f' type="{kind}"' if kind != "stable" else ""
    lines = [f'{indent}<release version="{escape(version)}" date="{date}"{type_}>']
    if entries:
        lines += description(entries, indent + unit, unit)
    else:
        lines += [f"{indent}{unit}<description>",
                  f"{indent}{unit * 2}<p>No user-facing changes.</p>",
                  f"{indent}{unit}</description>"]
    lines.append(f"{indent}</release>")
    return text[:match.end()] + "\n".join(lines) + "\n" + text[match.end():]


def replace_screenshots(text, shots, base_url):
    """Replace the <screenshots> element (or add it before <releases>)."""
    text = re.sub(r"^[ \t]*<screenshots>.*?</screenshots>[ \t]*\n", "", text,
                  flags=re.M | re.S)
    if not shots:
        return text
    match, unit = _releases_line(text)
    indent = match[1]
    lines = [f"{indent}<screenshots>"]
    first = True
    for shot in shots:
        for size, scheme in LISTED:
            type_ = ' type="default"' if first else ""
            first = False
            lines += [f"{indent}{unit}<screenshot{type_}>",
                      f"{indent}{unit * 2}<caption>{escape(shot['caption'])}</caption>",
                      f"{indent}{unit * 2}<image>{escape(base_url)}"
                      f"{shot_file(shot, size, scheme)}</image>",
                      f"{indent}{unit}</screenshot>"]
    lines.append(f"{indent}</screenshots>")
    return text[:match.start()] + "\n".join(lines) + "\n" + text[match.start():]


def bump_version_file(path, old, new):
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"(['\"])%s\1" % re.escape(old))
    if len(pattern.findall(text)) != 1:
        raise ReleaseError(f"{path.name}: expected exactly one quoted '{old}'")
    path.write_text(pattern.sub(lambda m: m[1] + new + m[1], text),
                    encoding="utf-8")


def notes(metainfo_text, version):
    """The description of one release as Markdown."""
    root = ET.fromstring(metainfo_text)
    for release in root.findall("releases/release"):
        if release.get("version") == version:
            break
    else:
        raise ReleaseError(f"the metainfo has no <release version=\"{version}\">")
    blocks = []
    description_ = release.find("description")
    for element in [] if description_ is None else description_:
        def flat(e):
            return " ".join("".join(e.itertext()).split())
        if element.tag == "p":
            blocks.append(flat(element))
        elif element.tag in ("ul", "ol"):
            blocks.append("\n".join(f"- {flat(li)}" for li in element))
    return "\n\n".join(blocks) + "\n"


# Screenshots

def shot_file(shot, size, scheme):
    return f"{shot['name']}-{size}-{scheme}.png"


def take_screenshots(config, out, command):
    out.mkdir(parents=True, exist_ok=True)
    taken = []
    for shot in config.shots:
        for size, (width, height, scale) in SIZES.items():
            for scheme in SCHEMES:
                path = out / shot_file(shot, size, scheme)
                args = [str(SCREENSHOT_SH), "-o", str(path), "-W", str(width),
                        "-H", str(height), "-s", str(scale), "-c", scheme,
                        "-d", str(shot.get("delay", config.shot_delay))]
                for key, value in config.shot_env.items():
                    args += ["-e", f"{key}={value}"]
                for path_ in config.shot_expose:
                    args += ["-F", path_]
                for action in shot.get("actions", []):
                    args += ["-a", action]
                print(f"{path.name}: {shot['caption']}", flush=True)
                subprocess.run(args + ["--"] + command, check=True)
                taken.append(path)
    return taken


def check_listed(metainfo_text, out):
    """Every screenshot the metainfo lists must have been taken."""
    root = ET.fromstring(metainfo_text)
    missing = [url for url in (i.text.strip() for i in root.iterfind(
               "screenshots/screenshot/image")) if not (out / url.rsplit("/", 1)[-1]).is_file()]
    if missing:
        raise ReleaseError("the metainfo lists screenshots that were not taken "
                           "(update release.toml or the metainfo):\n  "
                           + "\n  ".join(missing))


# Flathub

def flathub_manifest(manifest, url, tag, commit):
    """The manifest Flathub builds (docs/flathub.md): the app's own
    module, the last one, built from the git tag instead of the local
    checkout (its `type: dir` sources). x-checker-data lets Flathub's
    update bot propose the next tag."""
    manifest = json.loads(json.dumps(manifest))
    app = manifest["modules"][-1]
    sources = app.get("sources", [])
    local = [s for s in sources if isinstance(s, dict) and s.get("type") == "dir"]
    if not local:
        raise NotApplicable("the app module builds from no `type: dir` source, "
                            "so there is no Flathub manifest to derive")
    git = {"type": "git", "url": url, "tag": tag, "commit": commit,
           "x-checker-data": {"type": "git", "tag-pattern": r"^v([\d.]+)$"}}
    # The first local source becomes the git source, further ones go.
    app["sources"] = [git if s is local[0] else s for s in sources
                      if not (isinstance(s, dict) and s.get("type") == "dir")
                      or s is local[0]]
    return manifest


# Commands

def cmd_check(config, args):
    found = fragments(config)
    if args.changed:
        changed = [line.strip() for line in
                   Path(args.changed).read_text().splitlines() if line.strip()]
        added = {str(p.relative_to(config.root)) for p, _, _ in found}
        rel = str(config.fragments.relative_to(config.root))
        if needs_fragment(changed, rel) and not added & set(changed):
            raise ReleaseError(
                f"add a changelog fragment {rel}/<slug>.<{'|'.join(TYPES)}>.md "
                "with one sentence for users, or the label no-changelog if "
                "nothing changes for them (docs/releases.md in phosh-toolkit)")
    for path, kind, entries in found:
        print(f"{path.name} ({kind}): {' | '.join(entries)}")


def cmd_next_version(config, args):
    found = fragments(config)
    if not found:
        raise ReleaseError("no changelog fragments")
    text = config.metainfo.read_text(encoding="utf-8")
    print(next_version(latest_release(text), found))


def cmd_prepare(config, args):
    found = fragments(config)
    if not found:
        print("No changelog fragments: nothing to release.", file=sys.stderr)
        return 3
    text = config.metainfo.read_text(encoding="utf-8")
    current = latest_release(text)
    version = args.version or next_version(current, found)
    if parse_version(version) <= parse_version(current):
        raise ReleaseError(f"version {version} is not newer than {current}")
    for path in config.version_files:
        bump_version_file(path, current, version)
    entries = [e for _, _, es in found for e in es]
    text = insert_release(text, version, args.date, entries)
    if config.shots:
        if not args.repo:
            raise ReleaseError("--repo is needed for the screenshot URLs")
        base = f"https://github.com/{args.repo}/releases/download/v{version}/"
        text = replace_screenshots(text, config.shots, base)
    ET.fromstring(text)
    config.metainfo.write_text(text, encoding="utf-8")
    for path, _, _ in found:
        path.unlink()
    print(version)
    return 0


def cmd_notes(config, args):
    print(notes(config.metainfo.read_text(encoding="utf-8"), args.version), end="")


def cmd_latest(config, args):
    path = Path(args.metainfo) if args.metainfo else config.metainfo
    print(latest_release(path.read_text(encoding="utf-8")))


def cmd_devel(config, args):
    text = config.metainfo.read_text(encoding="utf-8")
    found = fragments(config)
    current = latest_release(text)
    upcoming = next_version(current, found) if found else current
    version = f"{upcoming}~dev.{args.suffix}"
    text = insert_release(text, version, args.date,
                          [e for _, _, es in found for e in es], kind="development")
    ET.fromstring(text)
    config.metainfo.write_text(text, encoding="utf-8")
    print(version)


def cmd_screenshots(config, args):
    if not config.shots:
        print("release.toml lists no screenshots.", file=sys.stderr)
        return 0
    out = Path(args.out)
    take_screenshots(config, out, args.command)
    if args.check_metainfo:
        check_listed(Path(args.check_metainfo).read_text(encoding="utf-8"), out)
    return 0


def cmd_flathub_manifest(config, args):
    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        raise ReleaseError(f"--commit must be a full SHA, not {args.commit!r}")
    result = flathub_manifest(manifest, args.url, args.tag, args.commit)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# Commands that work without a release.toml.
NO_CONFIG = {"flathub-manifest"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=".",
                        help="app repository root (default: .)")
    sub = parser.add_subparsers(dest="command_name", required=True)
    p = sub.add_parser("check")
    p.add_argument("--changed", help="file with the changed paths, one per line")
    p.set_defaults(func=cmd_check)
    sub.add_parser("next-version").set_defaults(func=cmd_next_version)
    today = datetime.date.today().isoformat()
    p = sub.add_parser("prepare")
    p.add_argument("--version")
    p.add_argument("--date", default=today)
    p.add_argument("--repo", help="OWNER/REPO for the screenshot URLs")
    p.set_defaults(func=cmd_prepare)
    p = sub.add_parser("notes")
    p.add_argument("version")
    p.set_defaults(func=cmd_notes)
    p = sub.add_parser("latest")
    p.add_argument("--metainfo", help="read this file instead")
    p.set_defaults(func=cmd_latest)
    p = sub.add_parser("devel")
    p.add_argument("--suffix", required=True)
    p.add_argument("--date", default=today)
    p.set_defaults(func=cmd_devel)
    p = sub.add_parser("screenshots")
    p.add_argument("--out", required=True)
    p.add_argument("--check-metainfo")
    p.add_argument("command", nargs="+")
    p.set_defaults(func=cmd_screenshots)
    p = sub.add_parser("flathub-manifest")
    p.add_argument("manifest", help="JSON from flatpak-builder --show-manifest")
    p.add_argument("--url", required=True, help="git URL of the app repository")
    p.add_argument("--tag", required=True)
    p.add_argument("--commit", required=True)
    p.set_defaults(func=cmd_flathub_manifest)
    args = parser.parse_args(argv)
    try:
        config = None if args.command_name in NO_CONFIG else Config(args.root)
        return args.func(config, args) or 0
    except NotApplicable as error:
        print(f"not applicable: {error}", file=sys.stderr)
        return 3
    except (ReleaseError, subprocess.CalledProcessError) as error:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("::error::" + str(error).replace("\n", "%0A"), file=sys.stderr)
        else:
            print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
