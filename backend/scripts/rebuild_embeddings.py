"""Rebuild every embedding for the active provider.

    python -m scripts.rebuild_embeddings
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.corpus.ingest import rebuild_embeddings  # noqa: E402
from app.db.session import init_db, session_scope  # noqa: E402


def main() -> int:
    init_db()
    with session_scope() as db:
        built = rebuild_embeddings(db)
    print(json.dumps({"rebuilt": built}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
