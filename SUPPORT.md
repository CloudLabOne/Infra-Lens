# Support Guide for Infra-Lens

## Getting Help

We're here to help you get the most out of Infra-Lens! Here are the best ways to get support:

### Support Channels

| Channel | Response Time | Best For |
|---------|---------------|----------|
| **GitHub Issues** | 24-48 hours | Bug reports, feature requests, general questions |
| **GitHub Discussions** | 12-24 hours | Community help, best practices, examples |
| **Documentation** | Instant | Setup guides, configuration, troubleshooting |

### Reporting Issues

When reporting an issue, please include:

1. **Action Version**: Check the latest release
2. **GitHub Actions Logs**: Full error output
3. **Infrastructure Diff File**: Sample of the diff causing issues
4. **Workflow Configuration**: Your action.yml setup
5. **Environment**: GitHub-hosted or self-hosted runner

**Issue Template:**
```markdown
## Bug Report

**Action Version:** [e.g., v1.0.0]
**GitHub Actions Runner:** [e.g., ubuntu-latest]
**Infrastructure Tool Version:** [e.g., CDK 2.0.0, Terraform 1.0.0]

### Expected Behavior
[What you expected to happen]

### Actual Behavior
[What actually happened]

### Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Error Logs
```
[Paste full error logs here]
```

### Configuration
```yaml
[Your workflow configuration]
```

### Infrastructure Diff Sample
```json
[Sample of your infrastructure diff file]
```
```

### Feature Requests

For feature requests, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** clearly
3. **Provide examples** of how you'd use the feature
4. **Consider alternatives** that might already exist

### Common Issues & Solutions

#### Issue: "AI API key is required"
**Solution:**
- Ensure `OPENAI_API_KEY` is set in GitHub Secrets
- Check that the secret name matches your workflow
- Verify the API key is valid and has credits

#### Issue: "Infrastructure diff file not found"
**Solution:**
- Verify the file path in `cdk-diff-file` input
- Ensure the file exists in your repository
- Check file permissions and format

#### Issue: "Action times out"
**Solution:**
- Reduce `max-tokens` parameter
- Simplify complex infrastructure diffs
- Check OpenAI API rate limits

#### Issue: "Summary not generated"
**Solution:**
- Check OpenAI API quota and billing
- Verify infrastructure diff file format is valid JSON
- Review action logs for specific errors

### Documentation

- **[Quick Start Guide](README.md#quick-start)**
- **[Configuration Options](README.md#inputs)**
- **[Output Formats](README.md#output-formats)**
- **[Advanced Usage](README.md#advanced-usage)**
- **[Troubleshooting](README.md#troubleshooting)**

### 🛠️ Self-Help Resources

#### Debug Mode
Enable debug logging by setting:
```yaml
env:
  DEBUG: "true"
```

#### Local Testing
Test the action locally using our test script:
```bash
cd test-cdk-project
./test-action.sh
```

#### Community Examples
Check our [examples directory](examples/) for:
- Basic workflow configurations
- Advanced use cases
- Integration patterns

### Contact Information

- **GitHub Issues**: [Create an issue](https://github.com/CloudLabOne/Infra-Lens/issues)
- **GitHub Discussions**: [Join the discussion](https://github.com/CloudLabOne/Infra-Lens/discussions)
- **Email**: support@yourdomain.com
- **Documentation**: [Full docs](https://github.com/CloudLabOne/Infra-Lens#readme)

### Response Times

- **Critical Issues**: 4-8 hours
- **Bug Reports**: 24-48 hours
- **Feature Requests**: 1-2 weeks
- **General Questions**: 12-24 hours

### 🤝 Contributing

Want to help improve the action?

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests**
5. **Submit a pull request**

See our [Contributing Guide](CONTRIBUTING.md) for details.

---

**Need immediate help?** Check our [FAQ](FAQ.md) or search existing [issues](https://github.com/CloudLabOne/Infra-Lens/issues). 