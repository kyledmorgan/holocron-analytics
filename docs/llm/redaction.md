# Redaction Hooks - Phase 2

## Overview

The Phase 2 evidence system includes a **minimal redaction layer** to remove sensitive information from evidence content before it reaches the LLM. This is a foundational hook system designed for Phase 7 hardening, not a comprehensive PII protection solution.

## Design Philosophy

**Phase 2 Approach:**
- **Minimal but present** - Basic pattern-based redaction
- **Toggle on/off** - Disabled by default
- **Auditable** - All redactions recorded in metadata
- **Extensible** - Easy to add custom rules

**Future (Phase 7):**
- Advanced PII detection (NER, ML-based)
- Context-aware redaction
- Compliance with privacy regulations
- Redaction review workflows

## Enable/Disable Redaction

Redaction is controlled by the `enable_redaction` flag in the evidence policy:

```python
from llm.contracts.evidence_contracts import EvidencePolicy

# Disabled (default)
policy = EvidencePolicy(enable_redaction=False)

# Enabled
policy = EvidencePolicy(enable_redaction=True)
```

When disabled, no redaction is applied and metadata reflects this:
```json
{
  "redactions": {
    "enabled": false,
    "redactions": []
  }
}
```

## Default Redaction Rules

Phase 2 includes basic pattern-based rules:

### Email Addresses
Pattern: `user@example.com`  
Replacement: `[EMAIL_REDACTED]`

### Phone Numbers
Pattern: `555-123-4567` or `5551234567`  
Replacement: `[PHONE_REDACTED]`

### Social Security Numbers (US)
Pattern: `123-45-6789`  
Replacement: `[SSN_REDACTED]`

### Credit Card Numbers
Pattern: `1234-5678-9012-3456` or `1234 5678 9012 3456`  
Replacement: `[CC_REDACTED]`

### Secret Markers
Pattern: `password="value"`, `api_key="value"`, `token="value"`  
Replacement: `[SECRET_REDACTED]`

## Redaction Process

1. **Evidence loaded** from source
2. **Redaction applied** (if enabled) - Pattern matching replaces sensitive data
3. **Metadata recorded** - All redactions logged
4. **Bounding applied** - After redaction
5. **Final content** ready for LLM

## Redaction Metadata

Each evidence item includes redaction metadata:

```json
{
  "evidence_id": "inline:0",
  "content": "Contact [EMAIL_REDACTED] for help",
  "metadata": {
    "redactions": {
      "enabled": true,
      "rules_applied": ["email", "phone", "ssn", "credit_card", "secret_marker"],
      "redaction_count": 1,
      "redactions": [
        {
          "rule": "email",
          "match": "user@example.com",
          "start": 8,
          "end": 24,
          "replacement": "[EMAIL_REDACTED]"
        }
      ]
    }
  }
}
```

**Fields:**
- `enabled` - Whether redaction was on
- `rules_applied` - List of rule names applied
- `redaction_count` - Total number of redactions
- `redactions` - Array of individual redaction records

Each redaction record includes:
- `rule` - Which rule matched
- `match` - Original matched text
- `start`, `end` - Position in original text
- `replacement` - What it was replaced with

## Custom Redaction Rules

You can define custom rules:

```python
from llm.evidence.redaction import create_custom_rule, redact

# Create custom rule
custom_rule = create_custom_rule(
    name="employee_id",
    pattern=r"EMP-\d{6}",
    replacement="[EMP_ID_REDACTED]"
)

# Apply redaction with custom rules
text = "Employee EMP-123456 submitted the report"
redacted, meta = redact(text, enable_redaction=True, rules=[custom_rule])

# Result: "Employee [EMP_ID_REDACTED] submitted the report"
```

## Usage in Evidence Builder

Redaction is automatically applied by source adapters when `enable_redaction=True`:

```python
from llm.evidence.builder import build_evidence_bundle
from llm.contracts.evidence_contracts import EvidencePolicy

policy = EvidencePolicy(enable_redaction=True)

job_input = {
    "extra_params": {
        "evidence": [
            {"text": "Contact user@example.com or call 555-1234"}
        ]
    }
}

bundle = build_evidence_bundle(job_input, None, policy)

# Evidence will have redacted content
print(bundle.items[0].content)
# Output: "Contact [EMAIL_REDACTED] or call [PHONE_REDACTED]"
```

## Audit Trail

All redaction decisions are preserved:

1. **In evidence item metadata** - Per-item redaction records
2. **In evidence bundle** - Summary of redactions across bundle
3. **In SQL Server** (via evidence_bundle table) - Auditable via policy_json

This enables:
- Debugging why certain information was removed
- Auditing compliance with redaction policies
- Reviewing false positives (over-redaction)

## Limitations

**Phase 2 limitations:**
- Pattern-based only (no semantic understanding)
- May miss context-specific PII
- May have false positives (e.g., "call 555-1212" in fictional text)
- No handling of encoded/obfuscated data
- No support for non-English text patterns

**NOT a replacement for:**
- Comprehensive PII detection systems
- Legal compliance reviews
- Data loss prevention (DLP) tools
- Manual review of sensitive data

## Best Practices

1. **Test with real data** - Verify rules catch what you expect
2. **Review false positives** - Check that legitimate content isn't over-redacted
3. **Document decisions** - Note why certain rules are enabled/disabled
4. **Prefer source-level filtering** - Don't ingest sensitive data if possible
5. **Enable only when needed** - Default is off to avoid false positives
6. **Monitor metadata** - Track redaction counts to detect unexpected patterns

## Configuration Example

```python
from llm.contracts.evidence_contracts import EvidencePolicy

# Strict policy with redaction
strict_policy = EvidencePolicy(
    enable_redaction=True,
    max_item_bytes=5000,  # Smaller items for closer review
)

# Permissive policy (no redaction)
permissive_policy = EvidencePolicy(
    enable_redaction=False,
    max_item_bytes=10000,
)

# Use strict policy for public-facing interrogations
# Use permissive policy for internal analysis with vetted data
```

## Redaction Rule Class

For advanced use cases, you can work directly with the `RedactionRule` class:

```python
from llm.evidence.redaction import RedactionRule

# Create rule
rule = RedactionRule(
    name="account_number",
    pattern=r"Account #\d{8}",
    replacement="[ACCOUNT_REDACTED]"
)

# Apply to text
text = "Account #12345678 was charged"
redacted, records = rule.apply(text)

print(redacted)  # "Account [ACCOUNT_REDACTED] was charged"
print(records)   # List of redaction records
```

## Future Enhancements (Phase 7+)

Planned improvements for production hardening:

1. **ML-based PII detection** - Use NER models for semantic understanding
2. **Context-aware redaction** - Distinguish between fictional and real PII
3. **Multi-language support** - Patterns for non-English text
4. **Redaction review UI** - Human-in-the-loop for edge cases
5. **Compliance presets** - GDPR, HIPAA, CCPA rule sets
6. **Anonymization vs redaction** - Replace with fake but plausible data
7. **Differential privacy** - Statistical guarantees on data leakage

## See Also

- [Evidence Bundles](evidence.md) - Overall evidence system
- [SQL Evidence](sql-evidence.md) - SQL-specific evidence handling
- [Phase 1 Runner](phase1-runner.md) - How evidence is consumed
- [Governance](governance.md) - Broader data governance considerations
