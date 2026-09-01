"""Check that the YOR visual contract is present in the shipped surfaces."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKENS_PATH = ROOT / "design" / "yor-tokens.json"
APP_PATH = ROOT / "app.py"
README_PATH = ROOT / "README.md"


def main() -> int:
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    app_text = APP_PATH.read_text(encoding="utf-8")
    readme_text = README_PATH.read_text(encoding="utf-8")

    required_colors = set(tokens["palette"].values()) | set(tokens["gradient"])
    missing_colors = sorted(color for color in required_colors if color not in app_text.lower() and color not in readme_text.lower())
    if missing_colors:
        raise SystemExit(f"Missing YOR colors: {', '.join(missing_colors)}")

    for state in tokens["surfaces"].values():
        if state not in app_text and state not in readme_text:
            raise SystemExit(f"Missing evidence state: {state}")

    if "Routes are root-level" not in readme_text or "| `GET` | `/health`" not in readme_text:
        raise SystemExit("README must describe the current root-level route contract")

    print("YOR design contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
