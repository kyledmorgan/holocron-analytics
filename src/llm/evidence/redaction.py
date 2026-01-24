"""
Redaction hooks for evidence content.

Provides a minimal redaction layer for Phase 2. This is a placeholder
for future Phase 7 hardening with more sophisticated PII detection.

The design allows redaction to be toggled on/off via policy and records
all redactions in evidence metadata for auditability.
"""

import re
import logging
from typing import Tuple, Dict, Any, List

logger = logging.getLogger(__name__)


class RedactionRule:
    """Base class for redaction rules."""
    
    def __init__(self, name: str, pattern: str, replacement: str = "[REDACTED]"):
        """
        Initialize redaction rule.
        
        Args:
            name: Name of the rule (for logging)
            pattern: Regex pattern to match
            replacement: Replacement text
        """
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.replacement = replacement
    
    def apply(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply redaction rule to text.
        
        Args:
            text: Text to redact
            
        Returns:
            Tuple of (redacted_text, redaction_records)
        """
        matches = list(self.pattern.finditer(text))
        if not matches:
            return text, []
        
        redacted_text = self.pattern.sub(self.replacement, text)
        
        records = [
            {
                "rule": self.name,
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
                "replacement": self.replacement,
            }
            for match in matches
        ]
        
        return redacted_text, records


# Default redaction rules (minimal, pattern-based)
DEFAULT_RULES = [
    # Email addresses
    RedactionRule(
        name="email",
        pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        replacement="[EMAIL_REDACTED]"
    ),
    
    # Phone numbers (simple pattern)
    RedactionRule(
        name="phone",
        pattern=r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        replacement="[PHONE_REDACTED]"
    ),
    
    # Social Security Numbers (US format)
    RedactionRule(
        name="ssn",
        pattern=r'\b\d{3}-\d{2}-\d{4}\b',
        replacement="[SSN_REDACTED]"
    ),
    
    # Credit card patterns (basic 4-4-4-4 format)
    RedactionRule(
        name="credit_card",
        pattern=r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        replacement="[CC_REDACTED]"
    ),
    
    # Common secret markers
    RedactionRule(
        name="secret_marker",
        pattern=r'(password|api[_-]?key|secret|token)["\s:=]+[A-Za-z0-9+/=]{8,}',
        replacement="[SECRET_REDACTED]"
    ),
]


def redact(text: str, enable_redaction: bool = False, rules: List[RedactionRule] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Apply redaction rules to text.
    
    Args:
        text: Text to redact
        enable_redaction: Whether to apply redaction (defaults to False)
        rules: List of redaction rules (defaults to DEFAULT_RULES)
        
    Returns:
        Tuple of (redacted_text, redaction_metadata)
    """
    if not enable_redaction:
        return text, {
            "enabled": False,
            "redactions": []
        }
    
    if rules is None:
        rules = DEFAULT_RULES
    
    redacted_text = text
    all_redactions = []
    
    for rule in rules:
        redacted_text, redactions = rule.apply(redacted_text)
        all_redactions.extend(redactions)
    
    if all_redactions:
        logger.info(f"Applied {len(all_redactions)} redactions across {len(rules)} rules")
    
    metadata = {
        "enabled": True,
        "rules_applied": [rule.name for rule in rules],
        "redactions": all_redactions,
        "redaction_count": len(all_redactions),
    }
    
    return redacted_text, metadata


def create_custom_rule(name: str, pattern: str, replacement: str = "[REDACTED]") -> RedactionRule:
    """
    Create a custom redaction rule.
    
    Args:
        name: Name of the rule
        pattern: Regex pattern
        replacement: Replacement text
        
    Returns:
        RedactionRule instance
    """
    return RedactionRule(name, pattern, replacement)
