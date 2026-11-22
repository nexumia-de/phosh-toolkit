"""What a report says, as a GitHub issue body or as an address of GitHub's
new-issue form. Follows the apps' issue forms (`.github/ISSUE_TEMPLATE/`
`bug.yml` and `feature.yml`), so a report reads the same whichever way
it was sent. No GTK."""
import os
from dataclasses import dataclass
from urllib.parse import urlencode

PROBLEM = "problem"
IDEA = "idea"

PHONE = "Phone (Phosh)"
DESKTOP = "Desktop"

# GitHub serves addresses up to about 8 KiB; stay well below.
MAX_URL = 7000
_CUT = "\n\n[…shortened, please paste the rest]"


@dataclass(frozen=True)
class Kind:
    template: str
    label: str
    # Form field id that takes the user's text, and its heading in the
    # rendered issue (the field's label in the form).
    field: str
    heading: str
    # Whether the form has the `version` and `device` fields.
    details: bool


KINDS = {
    PROBLEM: Kind("bug.yml", "bug", "what", "What happened", True),
    IDEA: Kind("feature.yml", "enhancement", "problem",
               "What do you want to do", False),
}


@dataclass(frozen=True)
class Report:
    kind: str
    title: str
    text: str
    version: str
    device: str


def device(environ=None):
    """PHONE under Phosh, else DESKTOP: the options of the form's
    `device` field."""
    environ = os.environ if environ is None else environ
    desktops = environ.get("XDG_CURRENT_DESKTOP", "").lower().split(":")
    return PHONE if "phosh" in desktops else DESKTOP


def body(report):
    """Markdown like GitHub renders the issue form: one `###` section per
    field. Only what the user typed, the version and the device."""
    kind = KINDS[report.kind]
    sections = [(kind.heading, report.text.strip())]
    if kind.details:
        sections += [("Version", report.version), ("Device", report.device)]
    return "\n\n".join(f"### {heading}\n\n{value or '_No response_'}"
                       for heading, value in sections)


def labels(report):
    return [KINDS[report.kind].label]


def form_url(repo, report):
    """Address of the repository's issue form for the report's kind,
    filled in. Text that would make the address too long is shortened
    with a note; the dialog keeps the full text to paste."""
    kind = KINDS[report.kind]
    text = report.text.strip()
    while True:
        fields = {"template": kind.template, "title": report.title.strip(),
                  kind.field: text}
        if kind.details:
            fields.update(version=report.version, device=report.device)
        url = f"https://github.com/{repo}/issues/new?{urlencode(fields)}"
        if len(url) <= MAX_URL or not text:
            return url
        keep = max(0, len(text) - (len(url) - MAX_URL) // 3 - len(_CUT))
        text = text[:keep].rstrip() + _CUT if keep else ""
