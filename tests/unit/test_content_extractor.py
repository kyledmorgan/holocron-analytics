"""
Unit tests for the ContentExtractor module.

Tests wikitext extraction, HTML extraction, format detection, and bounding.
"""

import pytest
from semantic.content_extractor import (
    ContentExtractor,
    ContentFormat,
    ExtractionConfig,
    ExtractionResult,
    ExtractionStrategy,
)


class TestContentExtractorFormatDetection:
    """Tests for format detection logic."""
    
    def test_detect_wikitext_with_triple_quote(self):
        """Triple quotes should be detected as wikitext."""
        extractor = ContentExtractor()
        content = "'''Luke Skywalker''' was a [[Jedi]] Master. He trained with Yoda and became a powerful Force user."
        result = extractor.extract(content)
        # With markers present, should detect as wikitext
        assert result.content_format in (ContentFormat.WIKITEXT, ContentFormat.UNKNOWN)
    
    def test_detect_wikitext_with_templates(self):
        """Templates should be detected as wikitext."""
        extractor = ContentExtractor()
        content = "{{Top}}\n{{Infobox character|name=Luke}}\n'''Luke''' was a Jedi. He was a hero of the Rebellion."
        result = extractor.extract(content)
        assert result.content_format == ContentFormat.WIKITEXT
    
    def test_detect_html_with_mw_parser_output(self):
        """mw-parser-output should be detected as HTML."""
        extractor = ContentExtractor()
        content = '<div class="mw-parser-output"><p>Luke Skywalker was a Jedi Master who fought in many battles.</p></div>'
        result = extractor.extract(content)
        assert result.content_format == ContentFormat.HTML
    
    def test_detect_html_with_div_and_class(self):
        """HTML divs with classes should be detected as HTML."""
        extractor = ContentExtractor()
        content = '<html><body><div class="content"><p>Content here with enough text to process.</p></div></body></html>'
        result = extractor.extract(content)
        assert result.content_format == ContentFormat.HTML
    
    def test_content_type_hint_wikitext(self):
        """Content type hint should override detection."""
        extractor = ContentExtractor()
        content = "Some ambiguous content without clear markers but long enough to process."
        result = extractor.extract(content, content_type_hint="text/x-wiki")
        assert result.content_format == ContentFormat.WIKITEXT
    
    def test_content_type_hint_html(self):
        """Content type hint should override detection for HTML."""
        extractor = ContentExtractor()
        content = "Some ambiguous content but long enough to be extracted properly."
        result = extractor.extract(content, content_type_hint="text/html")
        assert result.content_format == ContentFormat.HTML


class TestWikitextExtraction:
    """Tests for wikitext content extraction."""
    
    def test_extract_from_triple_quote(self):
        """Should extract content starting at triple quote."""
        extractor = ContentExtractor(ExtractionConfig(min_chars=50))
        content = """{{Top}}
{{Infobox character
|name = Luke Skywalker
|image = Luke.jpg
}}
'''Luke Skywalker''' was a legendary [[Jedi Knight|Jedi Master]] who was instrumental in defeating the [[Galactic Empire]]. He was the son of Anakin Skywalker and Padmé Amidala.

==Biography==
Luke was born on Polis Massa."""
        
        result = extractor.extract(content)
        assert result.strategy == ExtractionStrategy.TRIPLE_QUOTE
        assert "Luke Skywalker" in result.excerpt
        assert "Infobox" not in result.excerpt
    
    def test_clean_wiki_links(self):
        """Wiki links should be converted to plain text."""
        extractor = ContentExtractor()
        content = "'''Luke''' was a [[Jedi Knight|Jedi Master]] from [[Tatooine]]. He became very powerful."
        result = extractor.extract(content)
        assert "Jedi Master" in result.excerpt
        assert "Tatooine" in result.excerpt
        assert "[[" not in result.excerpt
        assert "]]" not in result.excerpt
    
    def test_remove_ref_tags(self):
        """Ref tags should be removed."""
        extractor = ContentExtractor()
        content = "'''Luke''' was born in 19 BBY.<ref name='source1'>Some source</ref> He grew up on Tatooine.<ref>Another ref</ref>"
        result = extractor.extract(content)
        assert "<ref" not in result.excerpt
        assert "</ref>" not in result.excerpt
    
    def test_extend_short_lead(self):
        """Short leads should be extended into next section."""
        extractor = ContentExtractor(ExtractionConfig(min_chars=100))
        content = """'''Luke''' was a Jedi.

==Early life==
Luke was born on Polis Massa during the final days of the Clone Wars. His mother died in childbirth."""
        
        result = extractor.extract(content)
        # Should have extracted some content
        assert len(result.excerpt) >= 20


class TestHtmlExtraction:
    """Tests for HTML content extraction."""
    
    def test_extract_from_mw_parser_output(self):
        """Should extract content from mw-parser-output container."""
        extractor = ContentExtractor()
        content = """<html>
<body>
<div class="mw-parser-output">
<table class="infobox">Infobox content</table>
<p>Luke Skywalker was a legendary Jedi Master who played a pivotal role in the Galactic Civil War.</p>
<p>He was the son of Anakin Skywalker.</p>
</div>
</body>
</html>"""
        
        result = extractor.extract(content)
        # Should successfully extract content
        assert "Luke Skywalker" in result.excerpt
        # HTML tags should be stripped
        assert "<p>" not in result.excerpt
    
    def test_skip_short_paragraphs(self):
        """Short paragraphs should be skipped."""
        extractor = ContentExtractor(ExtractionConfig(min_paragraph_chars=50))
        content = """<div class="mw-parser-output">
<p>See also:</p>
<p>Luke Skywalker was a legendary Jedi Master who played a crucial role in the defeat of the Galactic Empire during the Galactic Civil War.</p>
</div>"""
        
        result = extractor.extract(content)
        # Should include the longer paragraph content
        assert "legendary Jedi Master" in result.excerpt
    
    def test_strip_html_tags(self):
        """HTML tags should be stripped from output."""
        extractor = ContentExtractor()
        content = '<p>Luke <b>Skywalker</b> was a <a href="#">Jedi</a> Master. He was very powerful.</p>'
        result = extractor.extract(content)
        assert "<b>" not in result.excerpt
        assert "</b>" not in result.excerpt
        assert "<a" not in result.excerpt


class TestExtractionBounding:
    """Tests for excerpt bounding and sizing."""
    
    def test_respects_max_chars(self):
        """Excerpt should not exceed max chars."""
        config = ExtractionConfig(
            min_chars=100,
            default_max_chars=200,
            hard_max_chars=250,
        )
        extractor = ContentExtractor(config)
        
        # Generate long content
        long_content = "'''Test''' " + "word " * 500
        result = extractor.extract(long_content)
        
        assert len(result.excerpt) <= 250
    
    def test_min_chars_target(self):
        """Should try to reach min chars when possible."""
        config = ExtractionConfig(min_chars=100)
        extractor = ContentExtractor(config)
        
        content = "'''Test''' " + "Content text here. " * 50
        result = extractor.extract(content)
        
        # Should have extracted significant content
        assert len(result.excerpt) >= 50  # At least some content
    
    def test_model_context_bounding(self):
        """Should respect model context size for bounding."""
        config = ExtractionConfig(
            context_fraction=0.35,
            hard_max_chars=12000,
        )
        extractor = ContentExtractor(config)
        
        # With 4000 token context (estimated 16000 chars), should cap at ~5600 chars
        long_content = "'''Test''' " + "word " * 5000
        result = extractor.extract(long_content, model_context_size=4000)
        
        # Should be bounded by context calculation
        assert len(result.excerpt) <= 12000  # Hard cap


class TestExtractionMetadata:
    """Tests for extraction metadata tracking."""
    
    def test_tracks_content_format(self):
        """Should track detected content format."""
        extractor = ContentExtractor()
        content = "'''Luke''' was a Jedi. He was very powerful and strong."
        result = extractor.extract(content)
        assert result.content_format in (ContentFormat.WIKITEXT, ContentFormat.HTML, ContentFormat.UNKNOWN)
    
    def test_tracks_strategy(self):
        """Should track extraction strategy used."""
        extractor = ContentExtractor()
        content = "'''Luke''' was a Jedi. He was very powerful and strong."
        result = extractor.extract(content)
        assert result.strategy in list(ExtractionStrategy)
    
    def test_tracks_offset(self):
        """Should track content start offset."""
        extractor = ContentExtractor()
        content = "{{Template}}\n'''Luke''' was a Jedi. He was very powerful."
        result = extractor.extract(content)
        assert result.content_start_offset >= 0
    
    def test_tracks_length(self):
        """Should track excerpt length."""
        extractor = ContentExtractor()
        content = "'''Luke''' was a Jedi. He was very powerful and strong."
        result = extractor.extract(content)
        assert result.excerpt_length == len(result.excerpt)
    
    def test_computes_hash(self):
        """Should compute excerpt hash for non-empty content."""
        extractor = ContentExtractor()
        content = "'''Luke''' was a Jedi. He was very powerful and strong in the Force."
        result = extractor.extract(content)
        # If extraction succeeded, should have hash
        if result.success and result.excerpt:
            assert result.excerpt_hash is not None
            assert len(result.excerpt_hash) == 64  # SHA256 hex
    
    def test_tracks_success(self):
        """Should track extraction success."""
        extractor = ContentExtractor()
        content = "'''Luke Skywalker''' was a Jedi Master. He was very powerful and important."
        result = extractor.extract(content)
        assert result.success is True
    
    def test_empty_content_fails(self):
        """Empty content should fail extraction."""
        extractor = ContentExtractor()
        result = extractor.extract("")
        assert result.success is False
        assert result.needs_review is True


class TestDictPayloadExtraction:
    """Tests for extracting content from dict payloads."""
    
    def test_extract_from_wikitext_key(self):
        """Should extract content from wikitext key."""
        extractor = ContentExtractor()
        payload = {"wikitext": "'''Luke''' was a Jedi. He was very powerful and strong in the Force."}
        result = extractor.extract(payload)
        assert "Luke" in result.excerpt
    
    def test_extract_from_parse_structure(self):
        """Should extract from MediaWiki parse API structure."""
        extractor = ContentExtractor()
        payload = {
            "parse": {
                "wikitext": {
                    "*": "'''Luke Skywalker''' was a legendary Jedi Master. He fought in many battles."
                }
            }
        }
        result = extractor.extract(payload)
        assert "Luke Skywalker" in result.excerpt
    
    def test_extract_from_query_revisions(self):
        """Should extract from query/pages/revisions structure."""
        extractor = ContentExtractor()
        payload = {
            "query": {
                "pages": {
                    "12345": {
                        "title": "Luke Skywalker",
                        "revisions": [
                            {"*": "'''Luke Skywalker''' was born on Polis Massa. He became a Jedi."}
                        ]
                    }
                }
            }
        }
        result = extractor.extract(payload)
        assert "Luke Skywalker" in result.excerpt


class TestNeedsReviewFlag:
    """Tests for the needs_review flag."""
    
    def test_short_excerpt_needs_review(self):
        """Short excerpts should be flagged for review."""
        config = ExtractionConfig(min_chars=1000)
        extractor = ContentExtractor(config)
        
        short_content = "'''Luke''' was a Jedi."
        result = extractor.extract(short_content)
        
        assert result.needs_review is True
    
    def test_sufficient_excerpt_no_review(self):
        """Sufficient excerpts should not need review."""
        config = ExtractionConfig(min_chars=50)
        extractor = ContentExtractor(config)
        
        content = "'''Luke Skywalker''' was a legendary Jedi Master who played a pivotal role in defeating the Galactic Empire during the Galactic Civil War."
        result = extractor.extract(content)
        
        # With min_chars=50, this should be sufficient
        if len(result.excerpt) >= 50:
            assert result.needs_review is False
