from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from dev_up import main as _main

    return _main()


if __name__ == "__main__":
    raise SystemExit(main())
