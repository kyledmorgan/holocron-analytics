"""
Unit tests for evidence redaction functionality.

Tests for:
- Redaction rules application
- Redaction metadata recording
- Enable/disable toggle
- Pattern-based redaction
"""

import pytest

from llm.evidence.redaction import (
    redact,
    RedactionRule,
    create_custom_rule,
    DEFAULT_RULES,
)


class TestRedactionRule:
    """Tests for RedactionRule class."""
    
    def test_rule_creation(self):
        """Test basic rule creation."""
        rule = RedactionRule("test", r"\d{3}", "[REDACTED]")
        
        assert rule.name == "test"
        assert rule.replacement == "[REDACTED]"
    
    def test_rule_apply_no_match(self):
        """Test rule with no matches."""
        rule = RedactionRule("email", r"email@example\.com")
        text = "No emails here"
        
        redacted, records = rule.apply(text)
        
        assert redacted == text
        assert records == []
    
    def test_rule_apply_single_match(self):
        """Test rule with single match."""
        rule = RedactionRule("email", r"test@example\.com", "[EMAIL]")
        text = "Contact test@example.com for info"
        
        redacted, records = rule.apply(text)
        
        assert "[EMAIL]" in redacted
        assert "test@example.com" not in redacted
        assert len(records) == 1
        assert records[0]["rule"] == "email"
        assert records[0]["match"] == "test@example.com"
    
    def test_rule_apply_multiple_matches(self):
        """Test rule with multiple matches."""
        rule = RedactionRule("phone", r"\d{3}-\d{4}", "[PHONE]")
        text = "Call 555-1234 or 555-5678"
        
        redacted, records = rule.apply(text)
        
        assert redacted == "Call [PHONE] or [PHONE]"
        assert len(records) == 2


class TestRedact:
    """Tests for main redact function."""
    
    def test_redaction_disabled(self):
        """Test with redaction disabled."""
        text = "Email: test@example.com"
        redacted, meta = redact(text, enable_redaction=False)
        
        assert redacted == text
        assert meta["enabled"] is False
        assert meta["redactions"] == []
    
    def test_redaction_enabled_no_matches(self):
        """Test with redaction enabled but no matches."""
        text = "Clean text with no sensitive data"
        redacted, meta = redact(text, enable_redaction=True, rules=[])
        
        assert redacted == text
        assert meta["enabled"] is True
        assert len(meta["redactions"]) == 0
    
    def test_email_redaction(self):
        """Test email address redaction."""
        text = "Contact user@example.com for help"
        email_rule = RedactionRule("email", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL]")
        
        redacted, meta = redact(text, enable_redaction=True, rules=[email_rule])
        
        assert "[EMAIL]" in redacted
        assert "user@example.com" not in redacted
        assert len(meta["redactions"]) == 1
    
    def test_phone_redaction(self):
        """Test phone number redaction."""
        text = "Call 555-123-4567"
        phone_rule = RedactionRule("phone", r'\d{3}-\d{3}-\d{4}', "[PHONE]")
        
        redacted, meta = redact(text, enable_redaction=True, rules=[phone_rule])
        
        assert "[PHONE]" in redacted
        assert "555-123-4567" not in redacted
    
    def test_multiple_rules(self):
        """Test applying multiple rules."""
        text = "Email: test@example.com, Phone: 555-1234"
        email_rule = RedactionRule("email", r'\S+@\S+', "[EMAIL]")
        phone_rule = RedactionRule("phone", r'\d{3}-\d{4}', "[PHONE]")
        
        redacted, meta = redact(text, enable_redaction=True, rules=[email_rule, phone_rule])
        
        assert "[EMAIL]" in redacted
        assert "[PHONE]" in redacted
        assert len(meta["redactions"]) == 2
    
    def test_redaction_count(self):
        """Test redaction count in metadata."""
        text = "Email1: a@b.com, Email2: c@d.com"
        email_rule = RedactionRule("email", r'\S+@\S+\.\S+', "[EMAIL]")
        
        redacted, meta = redact(text, enable_redaction=True, rules=[email_rule])
        
        assert meta["redaction_count"] == 2
    
    def test_default_rules(self):
        """Test using default rules."""
        text = "Email: test@example.com, Phone: 555-123-4567"
        redacted, meta = redact(text, enable_redaction=True)
        
        # Should redact both email and phone with default rules
        assert "test@example.com" not in redacted
        assert "555-123-4567" not in redacted
        assert meta["redaction_count"] >= 1


class TestCreateCustomRule:
    """Tests for creating custom rules."""
    
    def test_create_custom_rule(self):
        """Test custom rule creation."""
        rule = create_custom_rule("ssn", r"\d{3}-\d{2}-\d{4}", "[SSN]")
        
        assert rule.name == "ssn"
        assert rule.replacement == "[SSN]"
    
    def test_custom_rule_apply(self):
        """Test applying custom rule."""
        rule = create_custom_rule("id", r"ID-\d+", "[ID]")
        text = "User ID-12345"
        
        redacted, records = rule.apply(text)
        
        assert redacted == "User [ID]"
        assert len(records) == 1


class TestDefaultRules:
    """Tests for default redaction rules."""
    
    def test_default_rules_exist(self):
        """Test that default rules are defined."""
        assert len(DEFAULT_RULES) > 0
    
    def test_email_rule_exists(self):
        """Test email redaction rule exists."""
        rule_names = [r.name for r in DEFAULT_RULES]
        assert "email" in rule_names
    
    def test_phone_rule_exists(self):
        """Test phone redaction rule exists."""
        rule_names = [r.name for r in DEFAULT_RULES]
        assert "phone" in rule_names
    
    def test_secret_marker_rule(self):
        """Test secret marker redaction."""
        text = 'password="supersecret123"'
        redacted, meta = redact(text, enable_redaction=True)
        
        # Should redact password value
        assert "supersecret123" not in redacted or "SECRET_REDACTED" in redacted
