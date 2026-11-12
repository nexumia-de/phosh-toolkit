"""Text for log lines without the media proxy's secret and queries. No
GTK, no libsoup."""
import re


def redact(value, secret):
    """`value` for a log line: `secret` (the media proxy's) and every
    query replaced by "…"; other values unchanged."""
    if not isinstance(value, str):
        return value
    text = value.replace(secret, "…") if secret else value
    return re.sub(r"\?\S*", "?…", text)
