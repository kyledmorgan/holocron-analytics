"""
Unit tests for the page classification prompts module.

Tests system prompt structure, user message building, and message formatting.
"""

import json
import pytest

from llm.prompts.page_classification import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_messages,
    build_user_message,
)


class TestPromptVersion:
    """Tests for prompt version tracking."""
    
    def test_prompt_version_is_v3_contract(self):
        """Prompt version should be v3_contract."""
        assert PROMPT_VERSION == "v3_contract"
    
    def test_prompt_version_is_string(self):
        """Prompt version should be a string."""
        assert isinstance(PROMPT_VERSION, str)


class TestSystemPrompt:
    """Tests for the system prompt structure."""
    
    def test_system_prompt_not_empty(self):
        """System prompt should not be empty."""
        assert SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 100
    
    def test_system_prompt_includes_role_definition(self):
        """System prompt should include role definition."""
        assert "Wikipedia-style page classifier" in SYSTEM_PROMPT
    
    def test_system_prompt_includes_json_only_rule(self):
        """System prompt should enforce JSON-only output."""
        assert "ONLY valid JSON" in SYSTEM_PROMPT
    
    def test_system_prompt_includes_descriptor_sentence_rules(self):
        """System prompt should include descriptor sentence rules."""
        assert "50 words" in SYSTEM_PROMPT
        assert "one sentence" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_includes_confidence_calibration(self):
        """System prompt should include confidence calibration guidance."""
        assert "0.90" in SYSTEM_PROMPT or "0.90-1.00" in SYSTEM_PROMPT
        assert "needs_review" in SYSTEM_PROMPT
    
    def test_system_prompt_includes_primary_type_guidance(self):
        """System prompt should include primary_type guidance."""
        assert "primary_type" in SYSTEM_PROMPT
        assert "Other" in SYSTEM_PROMPT
    
    def test_system_prompt_includes_notes_guidance(self):
        """System prompt should include structured notes guidance."""
        assert "likely_subtype" in SYSTEM_PROMPT
        assert "new_type_suggestions" in SYSTEM_PROMPT
    
    def test_system_prompt_includes_noise_handling(self):
        """System prompt should include noise handling rules."""
        assert "noise" in SYSTEM_PROMPT.lower()
        assert "ignored_noise" in SYSTEM_PROMPT


class TestBuildUserMessage:
    """Tests for user message building."""
    
    def test_builds_valid_json(self):
        """User message should be valid JSON."""
        result = build_user_message(
            title="Luke Skywalker",
            namespace="Main",
            continuity_hint="Canon",
            excerpt_text="Luke was a Jedi Master.",
        )
        
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
    
    def test_includes_required_fields(self):
        """User message should include required fields."""
        result = build_user_message(
            title="Darth Vader",
            namespace="Main",
            continuity_hint="Canon",
            excerpt_text="Vader was a Sith Lord.",
        )
        
        parsed = json.loads(result)
        assert parsed["title"] == "Darth Vader"
        assert parsed["namespace"] == "Main"
        assert parsed["continuity_hint"] == "Canon"
        assert parsed["excerpt_text"] == "Vader was a Sith Lord."
    
    def test_includes_optional_source_system(self):
        """User message should include source_system when provided."""
        result = build_user_message(
            title="Tatooine",
            namespace="Main",
            continuity_hint="Canon",
            excerpt_text="A desert planet.",
            source_system="wookieepedia",
        )
        
        parsed = json.loads(result)
        assert parsed["source_system"] == "wookieepedia"
    
    def test_includes_optional_resource_id(self):
        """User message should include resource_id when provided."""
        result = build_user_message(
            title="Millennium Falcon",
            namespace="Main",
            continuity_hint="Canon",
            excerpt_text="A famous starship.",
            resource_id="Millennium_Falcon",
        )
        
        parsed = json.loads(result)
        assert parsed["resource_id"] == "Millennium_Falcon"
    
    def test_omits_optional_fields_when_not_provided(self):
        """User message should omit optional fields when not provided."""
        result = build_user_message(
            title="Yoda",
            namespace="Main",
            continuity_hint="Canon",
            excerpt_text="A Jedi Master.",
        )
        
        parsed = json.loads(result)
        assert "source_system" not in parsed
        assert "resource_id" not in parsed
    
    def test_handles_unicode_in_title(self):
        """User message should handle unicode characters."""
        result = build_user_message(
            title="Anakin Skywalker/Légendes",
            namespace="Main",
            continuity_hint="Legends",
            excerpt_text="Content with émoji 🚀",
        )
        
        parsed = json.loads(result)
        assert "Légendes" in parsed["title"]
        assert "🚀" in parsed["excerpt_text"]


class TestBuildMessages:
    """Tests for building the complete messages list."""
    
    def test_returns_list_of_two_messages(self):
        """Should return a list with system and user messages."""
        messages = build_messages(
            title="Test",
            namespace="Main",
            continuity_hint="Unknown",
            excerpt_text="Test content.",
        )
        
        assert isinstance(messages, list)
        assert len(messages) == 2
    
    def test_first_message_is_system(self):
        """First message should be system message."""
        messages = build_messages(
            title="Test",
            namespace="Main",
            continuity_hint="Unknown",
            excerpt_text="Test content.",
        )
        
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT
    
    def test_second_message_is_user(self):
        """Second message should be user message."""
        messages = build_messages(
            title="Test Page",
            namespace="Main",
            continuity_hint="Canon",
            excerpt_text="Test excerpt.",
        )
        
        assert messages[1]["role"] == "user"
        
        parsed = json.loads(messages[1]["content"])
        assert parsed["title"] == "Test Page"
    
    def test_passes_optional_params_to_user_message(self):
        """Should pass optional params to user message."""
        messages = build_messages(
            title="Test",
            namespace="Main",
            continuity_hint="Unknown",
            excerpt_text="Content.",
            source_system="mediawiki",
            resource_id="Test_Page",
        )
        
        parsed = json.loads(messages[1]["content"])
        assert parsed["source_system"] == "mediawiki"
        assert parsed["resource_id"] == "Test_Page"


class TestNamespaceValues:
    """Tests for valid namespace values."""
    
    @pytest.mark.parametrize("namespace", [
        "Main", "Module", "Forum", "UserTalk", "Wookieepedia", "Other"
    ])
    def test_valid_namespace_values(self, namespace):
        """Should accept all valid namespace values."""
        result = build_user_message(
            title="Test",
            namespace=namespace,
            continuity_hint="Unknown",
            excerpt_text="Content.",
        )
        
        parsed = json.loads(result)
        assert parsed["namespace"] == namespace


class TestContinuityValues:
    """Tests for valid continuity hint values."""
    
    @pytest.mark.parametrize("continuity", ["Canon", "Legends", "Unknown"])
    def test_valid_continuity_values(self, continuity):
        """Should accept all valid continuity values."""
        result = build_user_message(
            title="Test",
            namespace="Main",
            continuity_hint=continuity,
            excerpt_text="Content.",
        )
        
        parsed = json.loads(result)
        assert parsed["continuity_hint"] == continuity
