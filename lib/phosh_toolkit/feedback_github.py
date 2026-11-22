"""Create a GitHub issue with the user's own token (REST API). Blocking:
call from a worker (tasks.run). No GTK."""
import json

from phosh_toolkit import http

API = "https://api.github.com"

# Why sending failed, for the dialog's message.
NO_ACCESS = "no-access"      # token rejected, or it may not write issues
OFFLINE = "offline"          # no connection to GitHub
FAILED = "failed"            # anything else


class SendError(Exception):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def create_issue(client, token, repo, title, body, labels, api=API):
    """Open an issue in `repo` ("owner/name"); returns its web address.
    GitHub ignores the labels when the token's user may not set them."""
    payload = json.dumps({"title": title, "body": body,
                          "labels": list(labels)}).encode()
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    try:
        response = client.request("POST", f"{api}/repos/{repo}/issues",
                                  headers=headers, body=payload)
    except http.HttpError as e:
        if e.kind == http.AUTH or e.status in (403, 404):
            raise SendError(NO_ACCESS, str(e)) from None
        if e.kind in (http.NETWORK, http.TLS):
            raise SendError(OFFLINE, str(e)) from None
        raise SendError(FAILED, str(e)) from None
    try:
        return json.loads(response.body)["html_url"]
    except (ValueError, KeyError, TypeError):
        raise SendError(FAILED, "Unexpected answer from GitHub") from None
