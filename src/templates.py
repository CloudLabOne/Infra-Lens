"""Jinja2 template rendering for Infra-Lens."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, Template

from config import Config


_HIGH_RISK_PREFIXES = ("AWS::IAM::", "AWS::KMS::", "AWS::SecretsManager::")
_MEDIUM_RISK_PREFIXES = ("AWS::EC2::", "AWS::RDS::", "AWS::Lambda::")

_SECURITY_PATTERN = re.compile(r"IAM|KMS|SecretsManager|SecurityGroup")

_ACTION_LABELS = {
    "en": {
        "create": "Create",
        "update": "Update",
        "destroy": "Delete",
        "replace": "Replace",
    },
    "nl": {
        "create": "Aanmaken",
        "update": "Bijwerken",
        "destroy": "Verwijderen",
        "replace": "Vervangen",
    },
}

_RISK_LABELS = {
    "en": {"low": "Low risk", "medium": "Medium risk", "high": "High risk"},
    "nl": {"low": "Laag risico", "medium": "Gemiddeld risico", "high": "Hoog risico"},
}

_UI_TEXT = {
    "en": {
        "executive_summary": "Executive Summary",
        "resource_changes": "Resource Changes",
        "security_considerations": "Security Considerations",
        "risk_assessment": "Risk Assessment",
        "deployment_notes": "Deployment Notes",
        "no_changes": "No infrastructure changes detected",
    },
    "nl": {
        "executive_summary": "Samenvatting",
        "resource_changes": "Resource wijzigingen",
        "security_considerations": "Beveiligingsoverwegingen",
        "risk_assessment": "Risicobeoordeling",
        "deployment_notes": "Deployment notities",
        "no_changes": "Geen infrastructuurwijzigingen gedetecteerd",
    },
}


class TemplateManager:
    """Loads templates and renders them with diff data."""

    def __init__(self, config: Config):
        self.config = config
        self.env = self._build_env()
        self.templates = self._load_templates()

    def _build_env(self) -> Environment:
        search_paths: List[str] = []
        if self.config.template.template_path:
            search_paths.append(self.config.template.template_path)
        builtin = Path(__file__).parent.parent / "templates"
        if builtin.exists():
            search_paths.append(str(builtin))
        search_paths.append(self.config.working_directory)

        env = Environment(
            loader=FileSystemLoader(search_paths),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_resource_type"] = self._format_resource_type
        env.filters["format_action"] = self._format_action
        env.filters["format_risk_level"] = self._format_risk_level
        env.globals["t"] = self._text
        env.tests["match"] = lambda value, pattern: re.search(pattern, value or "") is not None
        return env

    def _load_templates(self) -> Dict[str, Template]:
        templates: Dict[str, Template] = {}
        builtin = Path(__file__).parent.parent / "templates"
        if builtin.exists():
            for file in builtin.glob("*.md"):
                try:
                    templates[file.stem] = self.env.get_template(file.name)
                except Exception as e:
                    print(f"::warning::Failed to load template {file.name}: {e}")
        return templates

    def render_summary(self, diff_data: Dict[str, Any]) -> str:
        name = self._pick_template()
        template = self.templates.get(name) or self.templates.get("default")
        if template is None:
            raise ValueError("No templates available")
        return template.render(**self._context(diff_data))

    def _pick_template(self) -> str:
        language_suffix = self.config.template.language.value
        candidates = [f"default_{language_suffix}", "default"]
        for candidate in candidates:
            if candidate in self.templates:
                return candidate
        return "default"

    def _context(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        changes = self._extract_changes(diff_data)
        statistics = self._statistics(changes)
        return {
            "changes": changes,
            "statistics": statistics,
            "language": self.config.template.language.value,
            "metadata": {
                "generator": "Infra-Lens",
                "model": self.config.ai.model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _extract_changes(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        stacks: List[Dict[str, Any]] = []
        resources: List[Dict[str, Any]] = []
        counts = {"creates": 0, "updates": 0, "deletes": 0, "replaces": 0}

        for stack_name, stack_data in diff_data.get("stacks", {}).items():
            stack_entry: Dict[str, Any] = {
                "name": stack_name,
                "actions": [],
                "resources": [],
            }

            for action, counter in (
                ("create", "creates"),
                ("update", "updates"),
                ("destroy", "deletes"),
            ):
                if stack_data.get(action):
                    stack_entry["actions"].append(action)
                    counts[counter] += 1

            for resource_id, resource_data in stack_data.get("resources", {}).items():
                resource_entry: Dict[str, Any] = {
                    "id": resource_id,
                    "type": resource_data.get("type", "Unknown"),
                    "stack": stack_name,
                    "actions": [],
                }
                for action, counter in (
                    ("create", "creates"),
                    ("update", "updates"),
                    ("destroy", "deletes"),
                    ("replace", "replaces"),
                ):
                    if resource_data.get(action):
                        resource_entry["actions"].append(action)
                        counts[counter] += 1

                if resource_entry["actions"]:
                    stack_entry["resources"].append(resource_entry)
                    resources.append(resource_entry)

            if stack_entry["actions"] or stack_entry["resources"]:
                stacks.append(stack_entry)

        total = sum(counts.values())
        return {
            "stacks": stacks,
            "resources": resources,
            "summary": {**counts, "total_changes": total},
        }

    def _statistics(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        types: Dict[str, int] = {}
        risk_score = 0
        for resource in changes["resources"]:
            rtype = resource["type"]
            types[rtype] = types.get(rtype, 0) + 1
            if any(rtype.startswith(p) for p in _HIGH_RISK_PREFIXES):
                risk_score += 3
            elif any(rtype.startswith(p) for p in _MEDIUM_RISK_PREFIXES):
                risk_score += 2
            else:
                risk_score += 1

        if risk_score > 10:
            risk_level = "high"
        elif risk_score > 5:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "total_stacks": len(changes["stacks"]),
            "total_resources": len(changes["resources"]),
            "total_changes": changes["summary"]["total_changes"],
            "resource_types": types,
            "risk_level": risk_level,
            "risk_score": risk_score,
        }

    @staticmethod
    def _format_resource_type(resource_type: str) -> str:
        if resource_type.startswith("AWS::"):
            return resource_type[5:].replace("::", " ")
        return resource_type

    def _format_action(self, action: str) -> str:
        lang = self.config.template.language.value
        return _ACTION_LABELS.get(lang, _ACTION_LABELS["en"]).get(action, action.title())

    def _format_risk_level(self, level: str) -> str:
        lang = self.config.template.language.value
        return _RISK_LABELS.get(lang, _RISK_LABELS["en"]).get(level, level.title())

    def _text(self, key: str) -> str:
        lang = self.config.template.language.value
        return _UI_TEXT.get(lang, _UI_TEXT["en"]).get(key, key)


def is_security_resource(resource_type: str) -> bool:
    return bool(_SECURITY_PATTERN.search(resource_type or ""))
