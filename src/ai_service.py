"""Anthropic-powered summary generation for Infra-Lens."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import anthropic

from config import Config


_SYSTEM_PROMPT = """You are an AWS infrastructure reviewer. You read AWS CDK \
diffs and explain them in a way that's useful to engineers shipping the change \
AND non-technical stakeholders who need to understand what's about to happen \
in production.

Always produce output that is:
- Direct and concrete. Skip filler ("In this PR you will see…").
- Structured. Use markdown headings, short paragraphs, and tables where they help.
- Honest about risk. Call out destructive changes (deletes, replaces), IAM/secrets \
changes, and anything that could cause downtime. Don't manufacture risk that \
isn't there.
- Focused on what changed. If a section has nothing to report, omit it instead of \
filling space.

Your output is posted as a GitHub PR comment, so optimize for scannability."""


_USER_TEMPLATE = """Here is the CDK diff for this pull request.

**Resources affected:**
{change_lines}

**Pre-rendered structural summary** (from a deterministic template; use it as \
ground truth for counts and resource types, but rewrite the prose in your own \
voice):

{template_summary}

Write the PR comment now. Use these sections, in this order, and skip any that \
have nothing meaningful to report:

1. **TL;DR** — 1-2 sentences, what is changing and why it matters.
2. **What's changing** — table of action / resource type / logical ID / stack.
3. **Risk & blast radius** — what could go wrong, what is destructive, what is \
hard to roll back. Be specific; "review carefully" is not an answer.
4. **Security** — IAM, KMS, secrets, security groups, public exposure.
5. **Before you merge** — concrete checks the reviewer should do."""


class AIService:
    """Calls Claude to turn a CDK diff into a PR-ready summary."""

    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.Anthropic(
            api_key=config.ai.api_key,
            timeout=config.ai.timeout,
            max_retries=config.ai.max_retries,
        )

    def generate_summary(
        self,
        diff_data: Dict[str, Any],
        template_summary: Optional[str] = None,
    ) -> str:
        change_lines = self._render_change_lines(diff_data)
        if not change_lines:
            return (
                "## No infrastructure changes detected\n\n"
                "The diff was parsed but no create / update / destroy / replace "
                "actions were found. Double-check the `cdk diff` step in your "
                "workflow logs."
            )

        user_message = _USER_TEMPLATE.format(
            change_lines=change_lines,
            template_summary=(template_summary or "").strip()
            or "(no template summary)",
        )

        try:
            response = self.client.messages.create(
                model=self.config.ai.model,
                max_tokens=self.config.ai.max_tokens,
                thinking={"type": "adaptive"},
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.AuthenticationError:
            return self._error_summary(
                "Authentication failed — check that `anthropic-api-key` is set "
                "to a valid Anthropic API key."
            )
        except anthropic.RateLimitError:
            return self._error_summary(
                "Anthropic API rate limit exceeded. The SDK already retried — "
                "try again in a few minutes."
            )
        except anthropic.APIStatusError as e:
            return self._error_summary(f"Anthropic API error ({e.status_code}): {e.message}")
        except anthropic.APIConnectionError as e:
            return self._error_summary(f"Could not reach Anthropic API: {e}")

        text = next(
            (block.text for block in response.content if block.type == "text"),
            "",
        )
        if not text:
            return self._error_summary(
                "Anthropic returned no text content. "
                f"stop_reason={response.stop_reason}"
            )
        return text

    @staticmethod
    def _render_change_lines(diff_data: Dict[str, Any]) -> str:
        lines = []
        for stack_name, stack_data in diff_data.get("stacks", {}).items():
            for action in ("create", "update", "destroy"):
                if stack_data.get(action):
                    lines.append(f"- Stack `{stack_name}`: {action}")
            for rid, rdata in stack_data.get("resources", {}).items():
                rtype = rdata.get("type", "Unknown")
                for action in ("create", "update", "destroy", "replace"):
                    if rdata.get(action):
                        lines.append(
                            f"- `{stack_name}` / `{rid}` ({rtype}): {action}"
                        )
        return "\n".join(lines)

    @staticmethod
    def _error_summary(message: str) -> str:
        return (
            "## Infra-Lens couldn't generate a summary\n\n"
            f"{message}\n\n"
            "The CDK diff itself was parsed successfully — only the AI "
            "summarization step failed."
        )
