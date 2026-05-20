#!/usr/bin/env python3
"""Convert `cdk diff` text output into the JSON shape Infra-Lens expects.

Usage:
    cdk diff 2>&1 | python scripts/cdk_diff_to_json.py > cdk-diff.json

The parser is best-effort: it handles the common `[+]/[~]/[-]` resource
lines and groups them by `Stack <name>` headers. Detail blocks (property
diffs, IAM statement changes, etc.) are not preserved — Infra-Lens only
needs the action + resource type to produce a useful summary.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Dict


_STACK_RE = re.compile(r"^Stack\s+(?P<name>\S+)\s*$")
_RESOURCE_RE = re.compile(
    r"^\[(?P<sign>[+~\-])\]\s+"
    r"(?P<rtype>AWS::[A-Za-z0-9:]+|Custom::[A-Za-z0-9:]+)\s+"
    r"(?P<rid>\S+)"
    r"(?:\s+(?P<extra>.+))?$"
)


def parse(text: str) -> Dict:
    stacks: Dict[str, Dict] = {}
    current_stack: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stack_match = _STACK_RE.match(line)
        if stack_match:
            current_stack = stack_match.group("name")
            stacks.setdefault(current_stack, {"resources": {}})
            continue

        if current_stack is None:
            continue

        resource_match = _RESOURCE_RE.match(line.strip())
        if not resource_match:
            continue

        sign = resource_match.group("sign")
        rtype = resource_match.group("rtype")
        rid = resource_match.group("rid")
        extra = (resource_match.group("extra") or "").lower()

        resources = stacks[current_stack]["resources"]
        entry = resources.setdefault(rid, {"type": rtype})

        if sign == "+":
            entry["create"] = True
        elif sign == "-":
            entry["destroy"] = True
        elif sign == "~":
            if "replace" in extra or "may be replaced" in extra:
                entry["replace"] = True
            else:
                entry["update"] = True

    return {"stacks": stacks}


def main() -> int:
    text = sys.stdin.read()
    json.dump(parse(text), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
