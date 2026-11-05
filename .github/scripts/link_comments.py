"""Links citations in the comments of the website (runs in the public site repository).

Started by .github/workflows/link-comments.yml when a comment is written or edited (only that
comment), or by hand (all comments). Citations of provisions that exist on the site become
Markdown links; see citations.py. Standard library only.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import citations  # noqa: E402

SITE = os.environ.get("SITE_URL", "https://pmierzwi.github.io/AnnotateEPC-site/")
INDEX = json.loads((HERE.parent / "link-index.json").read_text(encoding="utf-8"))
OLD_WORKS = ("epc1973/", "ir1973/", "rfees1973/")
FAILED: list[str] = []

ALL = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    discussions(first: 20, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { title comments(first: 100) { nodes { id body replies(first: 100) {
        nodes { id body } } } } }
    }
  }
}"""
UPDATE = """
mutation($id: ID!, $body: String!) {
  updateDiscussionComment(input: {commentId: $id, body: $body}) { comment { id } }
}"""


def graphql(query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json", "User-Agent": "annotate-epc-site"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.load(resp)
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]


def relink(comment_id: str, body: str, title: str) -> int:
    """Adds links to one comment; returns the number of citations linked."""
    page = title.rsplit(" · ", 1)[-1].strip()
    new, n = citations.link_markdown(body, INDEX, SITE, default_1973=page.startswith(OLD_WORKS))
    if n and new != body:
        try:
            graphql(UPDATE, {"id": comment_id, "body": new})
        except RuntimeError as e:
            print(f"{comment_id}: could not update: {e}")
            FAILED.append(comment_id)
            return 0
        print(f"{comment_id}: {n} citation(s) linked")
    return n


def main() -> None:
    who = graphql("query { viewer { login } }", {})["viewer"]["login"]
    print(f"acting as {who}")  # the owner if COMMENT_LINKER_TOKEN is set, else the Actions bot
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event == "discussion_comment":
        payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        c = payload["comment"]
        relink(c["node_id"], c["body"], payload["discussion"]["title"])
        sys.exit(1 if FAILED else 0)
    owner, name = os.environ["GITHUB_REPOSITORY"].split("/")
    after, total = None, 0
    while True:
        data = graphql(ALL, {"owner": owner, "name": name, "after": after})
        ds = data["repository"]["discussions"]
        for d in ds["nodes"]:
            for c in d["comments"]["nodes"]:
                total += relink(c["id"], c["body"], d["title"])
                for r in c["replies"]["nodes"]:
                    total += relink(r["id"], r["body"], d["title"])
        if not ds["pageInfo"]["hasNextPage"]:
            break
        after = ds["pageInfo"]["endCursor"]
    print(f"linked {total} citation(s), failed: {len(FAILED)}")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
