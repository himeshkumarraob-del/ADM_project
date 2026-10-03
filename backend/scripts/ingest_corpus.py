"""Ingest (or re-ingest) the structured corpus.

    python -m scripts.ingest_corpus [--rebuild] [--path PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.corpus.ingest import ingest_corpus  # noqa: E402
from app.db.session import init_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true",
                        help="drop and rebuild all embeddings")
    parser.add_argument("--path", default=None, help="corpus file or directory")
    args = parser.parse_args()

    init_db()
    report = ingest_corpus(
        Path(args.path) if args.path else None, rebuild=args.rebuild
    )
    print(json.dumps(report.as_dict(), indent=2))
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
