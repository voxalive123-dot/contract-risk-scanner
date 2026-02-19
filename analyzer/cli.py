# analyzer/cli.py

import sys
from analyzer.scorer import score_text


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m analyzer.cli \"<contract text>\"")
        return 2

    text = " ".join(sys.argv[1:])
    result = score_text(text)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
