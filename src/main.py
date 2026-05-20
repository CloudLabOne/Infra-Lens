#!/usr/bin/env python3
"""Entry point for the Infra-Lens GitHub Action."""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config  # noqa: E402
from summarizer import run_summarizer  # noqa: E402


def main() -> int:
    try:
        config = Config()
    except ValueError as e:
        print(f"::error::Configuration error: {e}")
        return 1

    try:
        result = run_summarizer(config)
    except FileNotFoundError as e:
        print(f"::error::File not found: {e}")
        return 1
    except Exception as e:
        print(f"::error::Unexpected error: {e}")
        print(f"::debug::{traceback.format_exc()}")
        return 1

    if result.get("success"):
        return 0

    print(f"::error::{result.get('error', 'unknown error')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
