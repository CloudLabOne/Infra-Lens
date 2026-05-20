## Infrastructure changes

{% if changes.summary.total_changes > 0 %}
**{{ changes.summary.total_changes }}** changes across **{{ statistics.total_stacks }}** stack{% if statistics.total_stacks != 1 %}s{% endif %} · **Risk:** {{ statistics.risk_level | format_risk_level }}

| Action | Count |
|---|---:|
| Create | {{ changes.summary.creates }} |
| Update | {{ changes.summary.updates }} |
| Delete | {{ changes.summary.deletes }} |
| Replace | {{ changes.summary.replaces }} |
{% else %}
No infrastructure changes detected.
{% endif %}

{% if changes.resources %}
### Resources

| Action | Type | Logical ID | Stack |
|---|---|---|---|
{% for resource in changes.resources %}{% for action in resource.actions %}| {{ action | format_action }} | {{ resource.type | format_resource_type }} | `{{ resource.id }}` | `{{ resource.stack }}` |
{% endfor %}{% endfor %}
{% endif %}

{% set security_resources = changes.resources | selectattr('type', 'match', 'IAM|KMS|SecretsManager|SecurityGroup') | list %}
{% if security_resources %}
### Security-relevant resources

{% for resource in security_resources %}- `{{ resource.id }}` ({{ resource.type | format_resource_type }}) — {{ resource.actions | map('format_action') | join(', ') }}
{% endfor %}
{% endif %}

{% if statistics.total_changes > 20 %}
**Note:** this is a large change set ({{ statistics.total_changes }} resources). Consider splitting into smaller deployments.
{% endif %}
