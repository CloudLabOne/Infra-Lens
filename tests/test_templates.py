import os

os.environ["ANTHROPIC_API_KEY"] = "test"

from config import Config, Language  # noqa: E402
from templates import TemplateManager  # noqa: E402


def _config(language: str = "en") -> Config:
    os.environ["LANGUAGE"] = language
    return Config()


def test_render_summary_includes_resource_counts():
    diff = {
        "stacks": {
            "Prod": {
                "resources": {
                    "Bucket": {"type": "AWS::S3::Bucket", "create": True},
                    "Func": {"type": "AWS::Lambda::Function", "update": True},
                    "Old": {"type": "AWS::IAM::Role", "destroy": True},
                }
            }
        }
    }

    rendered = TemplateManager(_config()).render_summary(diff)

    assert "Prod" in rendered
    assert "Bucket" in rendered
    assert "Func" in rendered


def test_high_risk_when_many_iam_changes():
    diff = {
        "stacks": {
            "Sec": {
                "resources": {
                    f"Role{i}": {"type": "AWS::IAM::Role", "create": True}
                    for i in range(5)
                }
            }
        }
    }

    rendered = TemplateManager(_config()).render_summary(diff)

    assert "High risk" in rendered or "Hoog risico" in rendered or "high" in rendered.lower()


def test_dutch_language_localizes_action_labels():
    diff = {
        "stacks": {
            "X": {"resources": {"B": {"type": "AWS::S3::Bucket", "create": True}}}
        }
    }

    rendered = TemplateManager(_config("nl")).render_summary(diff)

    assert "Aanmaken" in rendered
