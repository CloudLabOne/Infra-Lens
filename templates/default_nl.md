## Infrastructuurwijzigingen

{% if changes.summary.total_changes > 0 %}
**{{ changes.summary.total_changes }}** wijzigingen verdeeld over **{{ statistics.total_stacks }}** stack{% if statistics.total_stacks != 1 %}s{% endif %} · **Risiconiveau:** {{ statistics.risk_level | format_risk_level }}

| Actie | Aantal |
|---|---:|
| Aanmaken | {{ changes.summary.creates }} |
| Bijwerken | {{ changes.summary.updates }} |
| Verwijderen | {{ changes.summary.deletes }} |
| Vervangen | {{ changes.summary.replaces }} |
{% else %}
Geen infrastructuurwijzigingen gedetecteerd.
{% endif %}

{% if changes.resources %}
### Resources

| Actie | Type | Logische ID | Stack |
|---|---|---|---|
{% for resource in changes.resources %}{% for action in resource.actions %}| {{ action | format_action }} | {{ resource.type | format_resource_type }} | `{{ resource.id }}` | `{{ resource.stack }}` |
{% endfor %}{% endfor %}
{% endif %}

{% set security_resources = changes.resources | selectattr('type', 'match', 'IAM|KMS|SecretsManager|SecurityGroup') | list %}
{% if security_resources %}
### Security-gevoelige resources

{% for resource in security_resources %}- `{{ resource.id }}` ({{ resource.type | format_resource_type }}) — {{ resource.actions | map('format_action') | join(', ') }}
{% endfor %}
{% endif %}

{% if statistics.total_changes > 20 %}
**Let op:** dit is een grote wijziging ({{ statistics.total_changes }} resources). Overweeg om dit op te splitsen.
{% endif %}
