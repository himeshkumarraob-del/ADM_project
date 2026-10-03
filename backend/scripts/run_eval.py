"""Run the evaluation suite.

    python -m scripts.run_eval [--dataset default] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import init_db  # noqa: E402
from app.eval.runner import run_evaluation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="default")
    parser.add_argument("--json", action="store_true", help="print full results")
    args = parser.parse_args()

    init_db()
    results = run_evaluation(dataset=args.dataset)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(results["metrics"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
