"""Orchestrates Infra-Lens: read diff → render template → ask Claude → post."""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ai_service import AIService
from cache import DiffCache
from config import Config
from github_service import GitHubService, OutputFormatter
from templates import TemplateManager


_DESTRUCTIVE_ACTIONS = {"destroy", "replace"}


class InfraLensRunner:
    """Top-level runner."""

    def __init__(self, config: Config):
        self.config = config
        self.template_manager = TemplateManager(config)
        self.ai_service = AIService(config)
        self.github_service = GitHubService(config) if config.github else None
        self.cache = DiffCache(config.cache) if config.cache.enabled else None

    def run(self) -> Dict[str, Any]:
        try:
            print("::notice::Infra-Lens starting")
            diff_data = self._read_cdk_diff()

            if not self._has_changes(diff_data):
                print("::notice::No changes detected")
                return self._handle_no_changes()

            destructive = self._has_destructive_changes(diff_data)

            summary_result = self._generate_summary(diff_data)
            rendered = OutputFormatter.format_output(
                summary_result["summary"],
                self.config.output_format,
                summary_result["metadata"],
            )

            issue_number = None
            if self.github_service:
                issue_number = self.github_service.post_summary(rendered)

            self._set_outputs(rendered, summary_result["metadata"], issue_number)

            if destructive and self.config.github and self.config.github.fail_on_destructive:
                print(
                    "::error::Destructive changes detected and "
                    "fail-on-destructive is enabled"
                )
                return {
                    "success": False,
                    "error": "Destructive changes detected",
                    "summary": rendered,
                    "metadata": summary_result["metadata"],
                }

            return {
                "success": True,
                "summary": rendered,
                "issue_number": issue_number,
                "metadata": summary_result["metadata"],
            }

        except Exception as e:
            print(f"::error::Infra-Lens failed: {e}")
            self._set_error_outputs(str(e))
            return {"success": False, "error": str(e)}

    def _read_cdk_diff(self) -> Dict[str, Any]:
        diff_file = Path(self.config.cdk_diff_file)

        if not diff_file.exists():
            print(f"::warning::CDK diff file not found: {diff_file}")
            return {"stacks": {}}

        content = diff_file.read_text().strip()
        if not content:
            print(f"::warning::CDK diff file is empty: {diff_file}")
            return {"stacks": {}}

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"::error::Failed to parse CDK diff file: {e}")
            return {"stacks": {}}

    def _has_changes(self, diff_data: Dict[str, Any]) -> bool:
        for stack_data in diff_data.get("stacks", {}).values():
            if any(stack_data.get(a) for a in ("create", "update", "destroy")):
                return True
            for resource_data in stack_data.get("resources", {}).values():
                if any(
                    resource_data.get(a)
                    for a in ("create", "update", "destroy", "replace")
                ):
                    return True
        return False

    def _has_destructive_changes(self, diff_data: Dict[str, Any]) -> bool:
        for stack_data in diff_data.get("stacks", {}).values():
            if stack_data.get("destroy"):
                return True
            for resource_data in stack_data.get("resources", {}).values():
                if any(resource_data.get(a) for a in _DESTRUCTIVE_ACTIONS):
                    return True
        return False

    def _handle_no_changes(self) -> Dict[str, Any]:
        message = (
            "## No infrastructure changes detected\n\n"
            "The CDK diff is empty. Either nothing changed, or the diff "
            "command didn't produce output. Verify the diff step in your "
            "workflow logs."
        )
        metadata = self._make_metadata("none")
        rendered = OutputFormatter.format_output(
            message, self.config.output_format, metadata
        )
        self._set_outputs(rendered, metadata, None)
        return {
            "success": True,
            "summary": rendered,
            "issue_number": None,
            "metadata": metadata,
        }

    def _generate_summary(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.cache:
            diff_hash = self.cache.create_diff_hash(diff_data)
            cached = self.cache.get_diff_summary(diff_hash)
            if cached:
                print("::notice::Using cached summary")
                return {"summary": cached, "metadata": self._make_metadata("cached")}

        template_summary = self.template_manager.render_summary(diff_data)
        ai_summary = self.ai_service.generate_summary(diff_data, template_summary)

        if self.cache:
            self.cache.set_diff_summary(
                self.cache.create_diff_hash(diff_data), ai_summary
            )

        return {"summary": ai_summary, "metadata": self._make_metadata(self.config.ai.model)}

    def _make_metadata(self, model: str) -> Dict[str, str]:
        return {
            "generator": "Infra-Lens",
            "model": model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repository": os.getenv("GITHUB_REPOSITORY", ""),
            "commit_sha": os.getenv("GITHUB_SHA", ""),
            "run_id": os.getenv("GITHUB_RUN_ID", ""),
        }

    def _set_outputs(
        self,
        summary: str,
        metadata: Dict[str, str],
        issue_number: Optional[int],
    ):
        if not self.github_service:
            return
        self.github_service.set_output("summary", summary)
        self.github_service.set_output("success", "true")
        self.github_service.set_output("metadata", json.dumps(metadata))
        if issue_number is not None:
            self.github_service.set_output("issue-number", str(issue_number))

    def _set_error_outputs(self, error_message: str):
        if not self.github_service:
            return
        self.github_service.set_output("success", "false")
        self.github_service.set_output("error", error_message)


def run_summarizer(config: Config) -> Dict[str, Any]:
    return InfraLensRunner(config).run()
