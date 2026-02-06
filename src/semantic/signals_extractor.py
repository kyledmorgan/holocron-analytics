"""
Signals extractor for page classification (Stage 1).

Extracts minimal signals from page content without processing the full payload.
This includes lead sentence, infobox type, categories, and boolean flags.
"""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .models import PageSignals, SourcePage

logger = logging.getLogger(__name__)


@dataclass
class SignalsExtractorConfig:
    """Configuration for the signals extractor."""
    # Maximum length of lead sentence to extract
    max_lead_sentence_length: int = 1000
    # Maximum number of categories to extract
    max_categories: int = 20
    # Whether to extract section headers
    extract_section_headers: bool = True
    # Maximum number of section headers to extract
    max_section_headers: int = 10


class SignalsExtractor:
    """
    Extracts signals from page content for classification.
    
    This is a minimal peek into the payload to extract:
    - Lead sentence (first paragraph/sentence)
    - Infobox type (if present)
    - Categories (if available)
    - Boolean flags (is_list_page, is_disambiguation, etc.)
    
    The extractor is designed to work with various content formats:
    - Wikitext/MediaWiki markup
    - HTML (rendered)
    - JSON API responses
    
    Example usage:
        >>> extractor = SignalsExtractor()
        >>> signals = extractor.extract(source_page, payload)
        >>> signals.lead_sentence
        "Anakin Skywalker was a human male who..."
    """
    
    def __init__(self, config: Optional[SignalsExtractorConfig] = None):
        self.config = config or SignalsExtractorConfig()
        
        # Compile regex patterns
        self._infobox_pattern = re.compile(
            r'\{\{(?:Infobox|Infobox_)?([^|}\n]+)',
            re.IGNORECASE
        )
        self._category_pattern = re.compile(
            r'\[\[Category:([^\]|]+)',
            re.IGNORECASE
        )
        self._disambiguation_pattern = re.compile(
            r'\{\{(?:Disambig|Disambiguation|Disamb)',
            re.IGNORECASE
        )
        self._section_header_pattern = re.compile(
            r'^={2,}\s*([^=]+?)\s*={2,}$',
            re.MULTILINE
        )
        # HTML infobox detection
        self._html_infobox_pattern = re.compile(
            r'class="[^"]*infobox[^"]*"',
            re.IGNORECASE
        )
        # HTML category detection
        self._html_category_pattern = re.compile(
            r'<a[^>]*href="[^"]*Category:([^"]+)"[^>]*>',
            re.IGNORECASE
        )
    
    def extract(
        self,
        source_page: SourcePage,
        payload: Any,
        content_type: Optional[str] = None,
    ) -> PageSignals:
        """
        Extract signals from page payload.
        
        Args:
            source_page: The source page being processed
            payload: The page payload (dict, string, or other)
            content_type: Optional content type hint (wikitext, html, json)
            
        Returns:
            PageSignals with extracted data
        """
        start_time = time.time()
        
        # Determine content type if not provided
        if content_type is None:
            content_type = self._detect_content_type(payload)
        
        # Extract text content from payload
        text_content = self._get_text_content(payload, content_type)
        
        # Calculate content hash
        content_hash = None
        if text_content:
            content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
        
        # Initialize signals
        signals = PageSignals(
            source_page_id=source_page.source_page_id,
            content_hash_sha256=content_hash,
            extraction_method=content_type,
        )
        
        if not text_content:
            logger.warning(f"No text content extracted for {source_page.resource_id}")
            return signals
        
        # Extract lead sentence
        signals.lead_sentence = self._extract_lead_sentence(
            text_content, content_type
        )
        
        # Extract infobox type
        signals.infobox_type = self._extract_infobox_type(
            text_content, content_type
        )
        signals.has_infobox = signals.infobox_type is not None
        
        # Extract categories
        categories = self._extract_categories(text_content, content_type)
        if categories:
            signals.categories_json = json.dumps(categories[:self.config.max_categories])
        
        # Detect boolean flags
        signals.is_list_page = self._detect_list_page(
            source_page.resource_id, text_content
        )
        signals.is_disambiguation = self._detect_disambiguation(text_content)
        signals.has_timeline_markers = self._detect_timeline_markers(text_content)
        
        # Extract additional signals
        additional_signals = {}
        
        if self.config.extract_section_headers:
            headers = self._extract_section_headers(text_content)
            if headers:
                additional_signals["section_headers"] = headers[:self.config.max_section_headers]
        
        if additional_signals:
            signals.signals_json = json.dumps(additional_signals)
        
        # Calculate extraction time
        signals.extraction_duration_ms = int((time.time() - start_time) * 1000)
        
        return signals
    
    def _detect_content_type(self, payload: Any) -> str:
        """Detect the content type from the payload structure."""
        if isinstance(payload, dict):
            # Check for common API response structures
            if "wikitext" in payload or "parse" in payload:
                return "wikitext"
            if "html" in payload or "text" in payload:
                return "html"
            return "json"
        
        if isinstance(payload, str):
            # Check for HTML markers
            if payload.strip().startswith("<") or "<html" in payload.lower():
                return "html"
            # Check for wikitext markers
            if "{{" in payload or "[[" in payload:
                return "wikitext"
            return "text"
        
        return "unknown"
    
    def _get_text_content(self, payload: Any, content_type: str) -> Optional[str]:
        """Extract text content from payload based on content type."""
        if isinstance(payload, str):
            return payload
        
        if isinstance(payload, dict):
            # Try common API response keys
            for key in ["wikitext", "content", "text", "html", "*"]:
                if key in payload:
                    value = payload[key]
                    if isinstance(value, str):
                        return value
                    if isinstance(value, dict) and "*" in value:
                        return value["*"]
            
            # Try nested structures (MediaWiki API format)
            if "parse" in payload:
                parse = payload["parse"]
                if "wikitext" in parse:
                    wikitext = parse["wikitext"]
                    if isinstance(wikitext, dict) and "*" in wikitext:
                        return wikitext["*"]
                    return wikitext if isinstance(wikitext, str) else None
            
            # Return stringified JSON for other dicts
            return json.dumps(payload)
        
        return None
    
    def _extract_lead_sentence(
        self, text: str, content_type: str
    ) -> Optional[str]:
        """Extract the lead sentence from content."""
        if content_type == "html":
            return self._extract_lead_from_html(text)
        elif content_type in ("wikitext", "text"):
            return self._extract_lead_from_wikitext(text)
        else:
            # Generic extraction
            return self._extract_lead_generic(text)
    
    def _extract_lead_from_wikitext(self, text: str) -> Optional[str]:
        """Extract lead sentence from wikitext."""
        # Skip any templates/infoboxes at the start
        lines = text.split('\n')
        in_template = 0
        lead_lines = []
        
        for line in lines:
            # Track template depth
            in_template += line.count('{{') - line.count('}}')
            
            # Skip lines that are just templates
            if in_template > 0:
                continue
            
            # Skip empty lines and headers
            stripped = line.strip()
            if not stripped or stripped.startswith('='):
                if lead_lines:
                    break
                continue
            
            # Skip category links
            if stripped.startswith('[[Category:'):
                continue
            
            # Found content
            lead_lines.append(stripped)
            
            # Stop after first paragraph
            if len(lead_lines) >= 3:
                break
        
        if not lead_lines:
            return None
        
        lead = ' '.join(lead_lines)
        
        # Clean up wikitext markup
        lead = self._clean_wikitext(lead)
        
        # Truncate if needed
        if len(lead) > self.config.max_lead_sentence_length:
            lead = lead[:self.config.max_lead_sentence_length] + "..."
        
        return lead if lead.strip() else None
    
    def _extract_lead_from_html(self, text: str) -> Optional[str]:
        """Extract lead sentence from HTML."""
        # Simple approach: find first <p> tag content
        p_match = re.search(r'<p[^>]*>(.+?)</p>', text, re.DOTALL | re.IGNORECASE)
        if p_match:
            lead = p_match.group(1)
            # Strip HTML tags
            lead = re.sub(r'<[^>]+>', '', lead)
            lead = lead.strip()
            
            if len(lead) > self.config.max_lead_sentence_length:
                lead = lead[:self.config.max_lead_sentence_length] + "..."
            
            return lead if lead else None
        
        return None
    
    def _extract_lead_generic(self, text: str) -> Optional[str]:
        """Generic lead sentence extraction."""
        # Take first non-empty line
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped and len(stripped) > 20:
                if len(stripped) > self.config.max_lead_sentence_length:
                    return stripped[:self.config.max_lead_sentence_length] + "..."
                return stripped
        return None
    
    def _clean_wikitext(self, text: str) -> str:
        """Clean wikitext markup from text."""
        # Remove [[...]] links, keeping display text
        text = re.sub(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]', r'\1', text)
        # Remove {{...}} templates
        text = re.sub(r'\{\{[^}]+\}\}', '', text)
        # Remove ''...'' (italic) and '''...''' (bold)
        text = re.sub(r"'''?", '', text)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_infobox_type(
        self, text: str, content_type: str
    ) -> Optional[str]:
        """Extract infobox type from content."""
        if content_type == "html":
            # Check for infobox class in HTML
            if self._html_infobox_pattern.search(text):
                return "html_infobox"
            return None
        
        # Wikitext infobox detection
        match = self._infobox_pattern.search(text)
        if match:
            infobox_type = match.group(1).strip()
            # Normalize common variations
            infobox_type = infobox_type.replace('_', ' ').title()
            return infobox_type
        
        return None
    
    def _extract_categories(
        self, text: str, content_type: str
    ) -> List[str]:
        """Extract categories from content."""
        categories = []
        
        if content_type == "html":
            matches = self._html_category_pattern.findall(text)
            categories = [m.replace('_', ' ').strip() for m in matches]
        else:
            matches = self._category_pattern.findall(text)
            categories = [m.strip() for m in matches]
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for cat in categories:
            if cat not in seen:
                seen.add(cat)
                unique.append(cat)
        
        return unique
    
    def _detect_list_page(self, title: str, text: str) -> bool:
        """Detect if page is a list page."""
        if title.lower().startswith("list of"):
            return True
        
        # Check for many bullet points
        bullet_count = text.count('\n*') + text.count('\n#')
        if bullet_count > 20:
            return True
        
        return False
    
    def _detect_disambiguation(self, text: str) -> bool:
        """Detect if page is a disambiguation page."""
        return bool(self._disambiguation_pattern.search(text))
    
    def _detect_timeline_markers(self, text: str) -> bool:
        """Detect if page has timeline markers (BBY/ABY)."""
        # Look for year references
        timeline_pattern = re.compile(r'\b\d+\s*(?:BBY|ABY)\b', re.IGNORECASE)
        matches = timeline_pattern.findall(text)
        return len(matches) >= 3  # Multiple timeline references
    
    def _extract_section_headers(self, text: str) -> List[str]:
        """Extract section headers from wikitext."""
        matches = self._section_header_pattern.findall(text)
        return [h.strip() for h in matches if h.strip()]
