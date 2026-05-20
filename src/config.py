"""Configuration for Infra-Lens."""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class OutputFormat(Enum):
    """How the summary is rendered."""

    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class Language(Enum):
    """Supported summary languages."""

    EN = "en"
    NL = "nl"


@dataclass
class AIConfig:
    """LLM provider configuration. Anthropic-only for now."""

    api_key: str = ""
    model: str = "claude-opus-4-7"
    max_tokens: int = 1024
    temperature: float = 0.2
    max_retries: int = 3
    timeout: int = 60


@dataclass
class GitHubConfig:
    """GitHub posting configuration."""

    token: str
    repository: str
    event_path: str
    output_path: str = field(default_factory=lambda: os.getenv("GITHUB_OUTPUT", ""))
    post_comment: bool = True
    create_issue: bool = False
    fail_on_destructive: bool = False


@dataclass
class TemplateConfig:
    template_path: Optional[str] = None
    language: Language = Language.EN
    custom_variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class CacheConfig:
    enabled: bool = True
    cache_dir: str = ".infra-lens-cache"
    ttl_hours: int = 24
    max_cache_size_mb: int = 100


@dataclass
class Config:
    """Top-level configuration, populated from environment variables."""

    cdk_diff_file: str = "cdk-diff.json"
    output_format: OutputFormat = OutputFormat.MARKDOWN
    working_directory: str = "."

    ai: AIConfig = field(default_factory=AIConfig)
    github: Optional[GitHubConfig] = None
    template: TemplateConfig = field(default_factory=TemplateConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

    log_level: str = "INFO"
    dry_run: bool = False

    def __post_init__(self):
        self._load_from_environment()
        self._validate()

    def _load_from_environment(self):
        self.ai.api_key = os.getenv("ANTHROPIC_API_KEY", self.ai.api_key)
        self.ai.model = os.getenv("AI_MODEL", self.ai.model)
        self.ai.max_tokens = int(os.getenv("AI_MAX_TOKENS", self.ai.max_tokens))
        self.ai.temperature = float(os.getenv("AI_TEMPERATURE", self.ai.temperature))
        self.ai.max_retries = int(os.getenv("AI_MAX_RETRIES", self.ai.max_retries))
        self.ai.timeout = int(os.getenv("AI_TIMEOUT", self.ai.timeout))

        self.cdk_diff_file = os.getenv("CDK_DIFF_FILE", self.cdk_diff_file)
        self.output_format = OutputFormat(
            os.getenv("OUTPUT_FORMAT", self.output_format.value).lower()
        )
        self.working_directory = os.getenv("WORKING_DIRECTORY", self.working_directory)

        github_token = os.getenv("GITHUB_TOKEN")
        github_repo = os.getenv("GITHUB_REPOSITORY")
        github_event_path = os.getenv("GITHUB_EVENT_PATH")

        if github_token and github_repo:
            self.github = GitHubConfig(
                token=github_token,
                repository=github_repo,
                event_path=github_event_path or "",
                post_comment=_envbool("POST_COMMENT", True),
                create_issue=_envbool("CREATE_ISSUE", False),
                fail_on_destructive=_envbool("FAIL_ON_DESTRUCTIVE", False),
            )

        template_path = os.getenv("TEMPLATE_PATH")
        if template_path:
            self.template.template_path = template_path

        try:
            self.template.language = Language(os.getenv("LANGUAGE", "en").lower())
        except ValueError:
            self.template.language = Language.EN

        self.cache.enabled = _envbool("CACHE_ENABLED", True)
        self.cache.cache_dir = os.getenv("CACHE_DIR", self.cache.cache_dir)
        self.cache.ttl_hours = int(os.getenv("CACHE_TTL_HOURS", self.cache.ttl_hours))
        self.cache.max_cache_size_mb = int(
            os.getenv("CACHE_MAX_SIZE_MB", self.cache.max_cache_size_mb)
        )

        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.dry_run = _envbool("DRY_RUN", False)

    def _validate(self):
        if not self.ai.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. Pass it via the `anthropic-api-key` action input."
            )
        if self.ai.max_tokens <= 0:
            raise ValueError("AI max_tokens must be positive")
        if not 0 <= self.ai.temperature <= 2:
            raise ValueError("AI temperature must be between 0 and 2")
        if self.ai.max_retries < 0:
            raise ValueError("AI max_retries must be non-negative")
        if self.cache.ttl_hours <= 0:
            raise ValueError("Cache TTL must be positive")
        if self.cache.max_cache_size_mb <= 0:
            raise ValueError("Cache max size must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cdk_diff_file": self.cdk_diff_file,
            "output_format": self.output_format.value,
            "working_directory": self.working_directory,
            "ai": {
                "model": self.ai.model,
                "max_tokens": self.ai.max_tokens,
                "temperature": self.ai.temperature,
                "max_retries": self.ai.max_retries,
                "timeout": self.ai.timeout,
            },
            "github": {
                "repository": self.github.repository if self.github else None,
                "post_comment": self.github.post_comment if self.github else False,
                "create_issue": self.github.create_issue if self.github else False,
                "fail_on_destructive": (
                    self.github.fail_on_destructive if self.github else False
                ),
            },
            "template": {
                "template_path": self.template.template_path,
                "language": self.template.language.value,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "cache_dir": self.cache.cache_dir,
                "ttl_hours": self.cache.ttl_hours,
                "max_cache_size_mb": self.cache.max_cache_size_mb,
            },
        }


def _envbool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
