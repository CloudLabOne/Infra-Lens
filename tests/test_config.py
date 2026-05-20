import os

import pytest


def _fresh_config():
    from importlib import reload

    import config

    reload(config)
    return config


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = _fresh_config()
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        cfg.Config()


def test_post_comment_env_var_parses(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_EVENT_PATH", "/tmp/event.json")
    monkeypatch.setenv("POST_COMMENT", "false")
    monkeypatch.setenv("CREATE_ISSUE", "true")

    cfg = _fresh_config().Config()

    assert cfg.github is not None
    assert cfg.github.post_comment is False
    assert cfg.github.create_issue is True


def test_output_format_loads_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("OUTPUT_FORMAT", "json")

    cfg_module = _fresh_config()
    cfg = cfg_module.Config()

    assert cfg.output_format == cfg_module.OutputFormat.JSON
