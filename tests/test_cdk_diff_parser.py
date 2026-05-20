from cdk_diff_to_json import parse


def test_parses_create_update_destroy_and_replace():
    diff_text = """
Stack DummyStack
Resources
[+] AWS::S3::Bucket MyBucket MyBucket1234
[~] AWS::Lambda::Function MyFunc MyFunc5678 may be replaced
[-] AWS::EC2::Instance MyInst MyInst9012
[~] AWS::IAM::Role MyRole MyRole3456
""".strip()

    result = parse(diff_text)
    resources = result["stacks"]["DummyStack"]["resources"]

    assert resources["MyBucket"] == {"type": "AWS::S3::Bucket", "create": True}
    assert resources["MyFunc"] == {"type": "AWS::Lambda::Function", "replace": True}
    assert resources["MyInst"] == {"type": "AWS::EC2::Instance", "destroy": True}
    assert resources["MyRole"] == {"type": "AWS::IAM::Role", "update": True}


def test_handles_multiple_stacks():
    diff_text = """
Stack AlphaStack
Resources
[+] AWS::S3::Bucket Bucket BucketA
Stack BetaStack
Resources
[+] AWS::SNS::Topic Topic TopicB
""".strip()

    result = parse(diff_text)

    assert "AlphaStack" in result["stacks"]
    assert "BetaStack" in result["stacks"]
    assert "Bucket" in result["stacks"]["AlphaStack"]["resources"]
    assert "Topic" in result["stacks"]["BetaStack"]["resources"]


def test_ignores_non_resource_lines():
    diff_text = """
Stack DummyStack
IAM Statement Changes
+-----+------------+--------+
|     | Resource   | Effect |
|  +  | *          | Allow  |
+-----+------------+--------+
Resources
[+] AWS::S3::Bucket OnlyOne OnlyOne1
""".strip()

    result = parse(diff_text)
    resources = result["stacks"]["DummyStack"]["resources"]

    assert list(resources.keys()) == ["OnlyOne"]


def test_empty_input_returns_empty_stacks():
    assert parse("") == {"stacks": {}}


def test_custom_resource_type_parses():
    diff_text = """
Stack X
Resources
[+] Custom::S3AutoDeleteObjects MyBucket/Cleanup CleanupABC
""".strip()

    result = parse(diff_text)
    resources = result["stacks"]["X"]["resources"]

    assert "MyBucket/Cleanup" in resources
    assert resources["MyBucket/Cleanup"]["type"] == "Custom::S3AutoDeleteObjects"
