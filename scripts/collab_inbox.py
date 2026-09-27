"""List messages waiting for a reply, or print a new message's filename.

    uv run python scripts/collab_inbox.py --me <github-username>
    uv run python scripts/collab_inbox.py --new --me <you> --to <them> --slug "t2-results"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from labbs2026.collab import MESSAGE_DIR, load_all, message_filename, open_for


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--me", required=True, help="your GitHub username")
    parser.add_argument("--new", action="store_true", help="print a path for a new message")
    parser.add_argument("--to", help="recipient GitHub username, or 'all'")
    parser.add_argument("--slug", help="short subject for the filename")
    args = parser.parse_args()
    root = args.root.resolve()

    if args.new:
        if not args.to or not args.slug:
            raise SystemExit("--new needs --to and --slug")
        print((MESSAGE_DIR / message_filename(args.me, args.to, args.slug)).as_posix())
        return

    waiting = open_for(root, args.me)
    total = len(load_all(root))
    print(f"{len(waiting)} message(s) waiting for {args.me} ({total} in collab/messages/)")
    for message in waiting:
        print(f"  [{message.type}] {message.path.relative_to(root).as_posix()}  from {message.sender}: {message.subject}")


if __name__ == "__main__":
    main()
