"""One-shot bootstrap: create the schema, ingest the corpus, print stats.

    python -m scripts.seed
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.corpus.ingest import ingest_corpus  # noqa: E402
from app.db.models import Character, Passage, Source, Theme  # noqa: E402
from app.db.session import init_db, session_scope  # noqa: E402
from app.security import ensure_admin_user  # noqa: E402


def main() -> int:
    init_db()
    report = ingest_corpus()
    with session_scope() as db:
        ensure_admin_user(db)
        stats = {
            "ingest": report.as_dict(),
            "passages": db.query(Passage).count(),
            "sources": db.query(Source).count(),
            "themes": db.query(Theme).count(),
            "characters": db.query(Character).count(),
        }
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
