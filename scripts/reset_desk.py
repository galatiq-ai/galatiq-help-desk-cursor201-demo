#!/usr/bin/env python3
"""Restore the local desk to its starting queue (data/desk/tickets.seed.json -> tickets.json).

Works without git (for example when you downloaded the zip). With git you can also run:
    git checkout data/desk/tickets.json
"""

import shutil
import sys
from pathlib import Path

DESK = Path(__file__).resolve().parents[1] / "data" / "desk"


def main() -> int:
    seed = DESK / "tickets.seed.json"
    if not seed.is_file():
        print(f"Missing {seed}", file=sys.stderr)
        return 1
    shutil.copyfile(seed, DESK / "tickets.json")
    print("desk reset: data/desk/tickets.json restored (70 untriaged tickets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
