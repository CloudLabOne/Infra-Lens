<p align="center">
  <img src="assets/logo.svg" width="120" alt="Infra-Lens" />
</p>

<h1 align="center">Infra-Lens</h1>

<p align="center">
  <strong><code>cdk diff</code>, in plain English, on every PR.</strong>
</p>

<p align="center">
  So your reviewers stop scrolling past 400 lines of CloudFormation logical IDs<br/>
  and your product manager stops asking what's about to break in production.
</p>

<p align="center">
  <a href="https://github.com/marketplace/actions/infra-lens"><img alt="Marketplace" src="https://img.shields.io/badge/marketplace-Infra--Lens-purple"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="#"><img alt="Powered by Claude" src="https://img.shields.io/badge/powered_by-Claude-d97757"></a>
</p>

---

## What it does

Infra-Lens is a GitHub Action. It reads your CDK diff, asks [Claude](https://www.anthropic.com) to explain it, and posts the explanation as a PR comment.

That's the whole product. There's nothing to host, nothing to configure beyond an API key, and the summary lives where your team already reviews code.

```yaml
- uses: CloudLabOne/Infra-Lens@v2
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

The PR comment looks roughly like this:

> **TL;DR** — adds a public S3 bucket and a Lambda function. The Lambda gets full read/write on the new bucket via a service role.
>
> **Risk & blast radius** — bucket is created from scratch, so the only blast radius is forgetting to set a retention policy before it gets real traffic. No destructive changes.
>
> **Security** — the Lambda's `DefaultPolicy` grants `s3:*` on the new bucket. That's broader than it needs to be — if the Lambda only writes objects, narrow this to `s3:PutObject`.
>
> **Before you merge** — confirm the bucket name is the one production expects, and decide on lifecycle / retention before the first write.

---

## Why this exists

Three things kept happening:

1. **`cdk diff` is dense.** A meaningful change can be 20 lines or 2,000 lines of CloudFormation deltas. Reviewers skim and miss things.
2. **Non-technical stakeholders are locked out.** A PM, a designer, an oncall lead who isn't deep in CDK can't tell whether a PR is a no-op or a load-bearing rewrite.
3. **The "important" changes get buried.** A 5-line IAM policy change matters more than 200 lines of CDK metadata churn. Tools that show all changes equally hide the ones that need attention.

Infra-Lens isn't trying to replace `cdk diff`. It sits next to it: the diff is still in your CI logs, and the summary is in the PR thread.

---

## Quick start

### 1. Get an Anthropic API key

[console.anthropic.com](https://console.anthropic.com) → API keys. Add the key as a repository secret named `ANTHROPIC_API_KEY`.

### 2. Add the workflow

Create `.github/workflows/infra-lens.yml`:

```yaml
name: Infra-Lens
on:
  pull_request:

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  summary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm ci
      - run: npm install -g aws-cdk

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Generate CDK diff
        run: |
          cdk diff 2>&1 | python3 ${{ github.action_path || '.' }}/scripts/cdk_diff_to_json.py > cdk-diff.json
        continue-on-error: true

      - uses: CloudLabOne/Infra-Lens@v2
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

### 3. Open a PR

You should see the summary as a comment within ~10 seconds of the workflow finishing.

---

## Input format

Infra-Lens expects a JSON file describing the diff. The structure is:

```json
{
  "stacks": {
    "MyStack": {
      "create": true,
      "resources": {
        "MyBucket": { "type": "AWS::S3::Bucket", "create": true },
        "MyFunc":   { "type": "AWS::Lambda::Function", "update": true }
      }
    }
  }
}
```

`cdk diff` doesn't produce this shape out of the box — there's no `--json` flag. The bundled `scripts/cdk_diff_to_json.py` parses `cdk diff` text output into this format and is what the quick-start workflow uses. If you already produce CDK diff JSON another way (e.g. with [cdk-diff-action](https://github.com/corymhall/cdk-diff-action) or a custom synth script), point `cdk-diff-file` at it directly.

---

## Configuration

| Input | Default | Description |
|---|---|---|
| `anthropic-api-key` | *(required)* | Your Anthropic API key. |
| `cdk-diff-file` | `cdk-diff.json` | Path to the diff JSON. |
| `model` | `claude-opus-4-7` | Claude model ID. Sonnet 4.6 (`claude-sonnet-4-6`) is a good cheaper default. |
| `max-tokens` | `1024` | Summary length cap. |
| `output-format` | `markdown` | `markdown`, `json`, or `html`. |
| `language` | `en` | `en` or `nl`. |
| `post-comment` | `true` | Post as a PR comment. |
| `create-issue` | `false` | Fall back to creating an issue when there's no PR. |
| `fail-on-destructive` | `false` | Fail the workflow if any resource is being destroyed or replaced. |

### Outputs

| Output | Description |
|---|---|
| `summary` | The generated summary text. |
| `success` | `true` / `false`. |
| `issue-number` | PR or issue number the comment was posted to. |

---

## Cost

Infra-Lens uses [prompt caching](https://docs.claude.com/docs/build-with-claude/prompt-caching) for the system prompt, so when CI re-runs on the same PR within ~5 minutes (push, rerun, retry), most of the request cost is pennies.

A typical PR comment, on `claude-opus-4-7` with default settings, lands at **~$0.02–$0.05** in API spend. Switch `model` to `claude-sonnet-4-6` to drop that by roughly 5×.

---

## Compared to…

| | Infra-Lens | Raw `cdk diff` in CI logs | Custom Slack bot |
|---|---|---|---|
| Where it lives | PR comment | CI log tab | Slack channel |
| Audience | Anyone on the PR | Whoever opens the log | Whoever's in the channel |
| Explains *why* it matters | Yes | No | Depends on what you wrote |
| Highlights destructive changes | Yes | Buried in `[-]` lines | Maybe |
| Time to set up | One workflow file | Already there | A weekend |

We don't think Infra-Lens replaces reading the actual diff. It replaces *triaging* whether the diff needs reading.

---

## What it doesn't do (yet)

We'd rather tell you up front than have you find out by trying.

- **Doesn't run `cdk diff` for you.** You bring the diff (text → the bundled parser, or JSON from another tool). Adding a "we run CDK ourselves" mode is on the roadmap.
- **Doesn't analyze property-level changes.** It sees actions (`create`/`update`/`destroy`/`replace`) and resource types — not which property changed inside an `update`. That's a known limitation of the bundled parser, not the model.
- **Doesn't gate the PR.** `fail-on-destructive` is a blunt instrument. Fine-grained policy (allow IAM changes from this team, never allow S3 deletions, etc.) is not a thing yet.
- **No Terraform support.** This is CDK-only by design — Terraform diffs already have decent tooling.

---

## Roadmap

- Native CDK runner — let the action run `cdk diff` itself with your AWS credentials.
- Property-level diffs — read CFN template deltas, not just resource actions.
- Policy gates — "fail if any IAM policy widens", "fail if any resource is destroyed", etc.
- Per-team prompts — let teams override the system prompt for domain-specific framing.

If one of these matters to you, [open an issue](https://github.com/CloudLabOne/Infra-Lens/issues) — it bumps priority.

---

## Local development

```bash
git clone https://github.com/CloudLabOne/Infra-Lens
cd Infra-Lens

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest

pytest                      # run the test suite

ANTHROPIC_API_KEY=sk-...    \
CDK_DIFF_FILE=examples/cdk-diff.json \
python3 src/main.py         # try it on the sample diff
```

---

## Contributing

PRs welcome. The codebase is small (~700 lines of Python), the tests run in under a second, and the architecture is just `read JSON → render template → ask Claude → post comment`.

Things that are especially welcome:

- More language packs (currently `en` and `nl`).
- A better CDK diff parser — the bundled one is best-effort.
- Real-world diff samples we can use as test fixtures.

---

## License

MIT. See [LICENSE](LICENSE).

Infra-Lens is built and maintained by [CloudLabOne](https://github.com/CloudLabOne).
