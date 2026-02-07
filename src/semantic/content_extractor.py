"""
Content extractor for deriving bounded excerpts from page payloads.

Supports dual-path extraction:
1. Wikitext path - Uses triple quote (''') as content start hook
2. HTML path - Uses mw-parser-output container and first meaningful <p>

Produces a bounded excerpt suitable for LLM classification.
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ContentFormat(str, Enum):
    """Detected content format."""
    WIKITEXT = "wikitext"
    HTML = "html"
    UNKNOWN = "unknown"


class ExtractionStrategy(str, Enum):
    """Strategy used to find content start."""
    TRIPLE_QUOTE = "triple_quote"
    FIRST_PARAGRAPH = "first_paragraph"
    MW_PARSER_OUTPUT = "mw_parser_output"
    FALLBACK = "fallback"


@dataclass
class ExtractionConfig:
    """Configuration for content extraction."""
    # Minimum target excerpt length in characters
    min_chars: int = 1000
    # Default maximum excerpt length (used if model context not known)
    default_max_chars: int = 8000
    # Maximum excerpt length (hard cap)
    hard_max_chars: int = 12000
    # Fraction of model context to use (if known)
    context_fraction: float = 0.35
    # Minimum paragraph length to be considered meaningful
    min_paragraph_chars: int = 200
    # Maximum lines to scan for content start
    max_scan_lines: int = 500


@dataclass
class ExtractionResult:
    """Result from content extraction."""
    # The extracted excerpt text
    excerpt: str
    # Detected content format
    content_format: ContentFormat
    # Strategy used to find content start
    strategy: ExtractionStrategy
    # Character offset where content starts in original
    content_start_offset: int
    # Length of the excerpt
    excerpt_length: int
    # Whether extraction was successful
    success: bool = True
    # Whether manual review is needed
    needs_review: bool = False
    # Error message if extraction failed
    error_message: Optional[str] = None
    # Extraction duration in milliseconds
    extraction_duration_ms: Optional[int] = None
    # SHA256 hash of the excerpt
    excerpt_hash: Optional[str] = None


class ContentExtractor:
    """
    Extracts bounded content excerpts from page payloads.
    
    Supports wikitext and HTML formats with format-specific hooks
    for finding the actual article content start.
    
    Example:
        >>> extractor = ContentExtractor()
        >>> result = extractor.extract(payload)
        >>> result.excerpt
        "Luke Skywalker was a human male who..."
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        
        # Compile regex patterns
        # Wikitext patterns
        self._triple_quote_pattern = re.compile(r"'''([^']+)'''")
        self._wikitext_heading_pattern = re.compile(r'^==+\s*[^=]+\s*==+', re.MULTILINE)
        self._ref_tag_pattern = re.compile(r'<ref[^>]*>.*?</ref>|<ref[^/>]*/>', re.DOTALL | re.IGNORECASE)
        self._wikilink_pattern = re.compile(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]')
        self._template_pattern = re.compile(r'\{\{[^{}]*\}\}')
        
        # HTML patterns
        self._mw_parser_output_pattern = re.compile(
            r'<div[^>]*class="[^"]*mw-parser-output[^"]*"[^>]*>(.*?)</div>',
            re.DOTALL | re.IGNORECASE
        )
        self._paragraph_pattern = re.compile(
            r'<p[^>]*>(.*?)</p>',
            re.DOTALL | re.IGNORECASE
        )
        self._html_tag_pattern = re.compile(r'<[^>]+>')
        self._infobox_pattern = re.compile(
            r'<(?:table|div)[^>]*class="[^"]*infobox[^"]*"[^>]*>.*?</(?:table|div)>',
            re.DOTALL | re.IGNORECASE
        )
        self._nav_pattern = re.compile(
            r'<(?:div|table)[^>]*class="[^"]*(?:navbox|toc|mw-jump-link)[^"]*"[^>]*>.*?</(?:div|table)>',
            re.DOTALL | re.IGNORECASE
        )
        
        # Format detection patterns
        self._wikitext_markers = [
            "'''",  # Bold
            "[[",   # Wiki link
            "{{",   # Template
            "==",   # Heading
        ]
        self._html_markers = [
            "<div",
            "<table",
            "<p>",
            "mw-parser-output",
            "class=",
        ]
    
    def extract(
        self,
        payload: Any,
        content_type_hint: Optional[str] = None,
        model_context_size: Optional[int] = None,
    ) -> ExtractionResult:
        """
        Extract a bounded excerpt from the payload.
        
        Args:
            payload: The page payload (string, dict, or other)
            content_type_hint: Optional hint about content type
            model_context_size: Optional model context size for bounding
            
        Returns:
            ExtractionResult with the excerpt and metadata
        """
        start_time = time.time()
        
        # Get raw text content
        text_content = self._get_text_content(payload)
        if not text_content or len(text_content.strip()) < 10:
            return ExtractionResult(
                excerpt="",
                content_format=ContentFormat.UNKNOWN,
                strategy=ExtractionStrategy.FALLBACK,
                content_start_offset=0,
                excerpt_length=0,
                success=False,
                needs_review=True,
                error_message="No text content found in payload",
            )
        
        # Detect content format
        content_format = self._detect_format(text_content, content_type_hint)
        
        # Calculate max chars based on model context
        max_chars = self._calculate_max_chars(model_context_size)
        
        # Extract based on format
        if content_format == ContentFormat.WIKITEXT:
            excerpt, strategy, offset = self._extract_wikitext(text_content, max_chars)
        elif content_format == ContentFormat.HTML:
            excerpt, strategy, offset = self._extract_html(text_content, max_chars)
        else:
            excerpt, strategy, offset = self._extract_fallback(text_content, max_chars)
        
        # Calculate extraction time
        extraction_time_ms = int((time.time() - start_time) * 1000)
        
        # Check if we got enough content
        needs_review = len(excerpt) < self.config.min_chars
        
        # Calculate hash
        excerpt_hash = None
        if excerpt:
            excerpt_hash = hashlib.sha256(excerpt.encode('utf-8')).hexdigest()
        
        return ExtractionResult(
            excerpt=excerpt,
            content_format=content_format,
            strategy=strategy,
            content_start_offset=offset,
            excerpt_length=len(excerpt),
            success=len(excerpt) > 0,
            needs_review=needs_review,
            extraction_duration_ms=extraction_time_ms,
            excerpt_hash=excerpt_hash,
        )
    
    def _get_text_content(self, payload: Any) -> Optional[str]:
        """Extract text content from payload."""
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
                if isinstance(parse, dict):
                    if "wikitext" in parse:
                        wikitext = parse["wikitext"]
                        if isinstance(wikitext, dict) and "*" in wikitext:
                            return wikitext["*"]
                        return wikitext if isinstance(wikitext, str) else None
                    if "text" in parse:
                        text = parse["text"]
                        if isinstance(text, dict) and "*" in text:
                            return text["*"]
                        return text if isinstance(text, str) else None
            
            # Try query format
            if "query" in payload and "pages" in payload.get("query", {}):
                pages = payload["query"]["pages"]
                if isinstance(pages, dict):
                    for page_id, page_data in pages.items():
                        if "revisions" in page_data:
                            revisions = page_data["revisions"]
                            if revisions and len(revisions) > 0:
                                rev = revisions[0]
                                if "*" in rev:
                                    return rev["*"]
                                if "content" in rev:
                                    return rev["content"]
        
        return None
    
    def _detect_format(
        self,
        text: str,
        content_type_hint: Optional[str] = None,
    ) -> ContentFormat:
        """Detect whether content is wikitext or HTML."""
        # Use hint if provided
        if content_type_hint:
            hint_lower = content_type_hint.lower()
            if "wiki" in hint_lower or "text/x-wiki" in hint_lower:
                return ContentFormat.WIKITEXT
            if "html" in hint_lower:
                return ContentFormat.HTML
        
        # Check first chunk of content
        sample = text[:5000]
        
        # Count markers
        wikitext_score = 0
        html_score = 0
        
        for marker in self._wikitext_markers:
            if marker in sample:
                wikitext_score += sample.count(marker)
        
        for marker in self._html_markers:
            if marker.lower() in sample.lower():
                html_score += sample.lower().count(marker.lower())
        
        # Additional heuristics
        # Strong wikitext indicators
        if "{{Top" in sample or "{{Infobox" in sample:
            wikitext_score += 10
        if sample.strip().startswith("{{"):
            wikitext_score += 5
        
        # Strong HTML indicators
        if "mw-parser-output" in sample:
            html_score += 10
        if sample.strip().startswith("<!DOCTYPE") or sample.strip().startswith("<html"):
            html_score += 20
        
        # Check for revisions marker (API response with wikitext)
        if '"revisions"' in sample and '"contentformat"' in sample:
            if "text/x-wiki" in sample:
                wikitext_score += 20
        
        if wikitext_score > html_score:
            return ContentFormat.WIKITEXT
        elif html_score > wikitext_score:
            return ContentFormat.HTML
        else:
            # Default to wikitext if ambiguous (more common in our pipeline)
            return ContentFormat.WIKITEXT if "'''" in sample else ContentFormat.UNKNOWN
    
    def _calculate_max_chars(self, model_context_size: Optional[int]) -> int:
        """Calculate maximum excerpt size based on model context."""
        if model_context_size:
            # Rough estimate: 1 token ~ 4 characters
            model_context_chars = model_context_size * 4
            calculated_max = int(model_context_chars * self.config.context_fraction)
            return min(calculated_max, self.config.hard_max_chars)
        return self.config.default_max_chars
    
    def _extract_wikitext(
        self,
        text: str,
        max_chars: int,
    ) -> Tuple[str, ExtractionStrategy, int]:
        """
        Extract excerpt from wikitext content.
        
        Uses triple quote (''') as the hook for content start.
        """
        # Find the first occurrence of ''' (bold subject line)
        triple_quote_match = self._triple_quote_pattern.search(text)
        
        if triple_quote_match:
            # Find the start of the line containing the triple quote
            start_pos = triple_quote_match.start()
            # Go back to find line start
            line_start = text.rfind('\n', 0, start_pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            
            content_start = line_start
            strategy = ExtractionStrategy.TRIPLE_QUOTE
        else:
            # Fallback: skip templates at the start and find first real content
            content_start = self._find_wikitext_content_start(text)
            strategy = ExtractionStrategy.FALLBACK
        
        # Extract from content start to first heading or max chars
        excerpt_text = text[content_start:]
        
        # Find the first heading to delimit the lead section
        heading_match = self._wikitext_heading_pattern.search(excerpt_text)
        if heading_match:
            lead_end = heading_match.start()
            lead_text = excerpt_text[:lead_end].strip()
            
            # If lead is too short, extend into next section (but stop BEFORE heading)
            if len(lead_text) < self.config.min_chars:
                # Find the line after this heading
                heading_line_end = excerpt_text.find('\n', heading_match.end())
                if heading_line_end == -1:
                    heading_line_end = heading_match.end()
                else:
                    heading_line_end += 1
                
                # Find next heading after this one
                next_heading = self._wikitext_heading_pattern.search(
                    excerpt_text, heading_line_end
                )
                if next_heading:
                    # Take content up to (but not including) the next heading
                    lead_text = excerpt_text[:next_heading.start()].strip()
                else:
                    # No more headings, take up to max_chars
                    lead_text = excerpt_text[:max_chars]
        else:
            lead_text = excerpt_text[:max_chars]
        
        # Clean up wikitext
        clean_text = self._clean_wikitext(lead_text)
        
        # Ensure we don't exceed max
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars]
            # Try to end at a sentence boundary
            last_period = clean_text.rfind('.')
            if last_period > max_chars * 0.8:
                clean_text = clean_text[:last_period + 1]
        
        return clean_text.strip(), strategy, content_start
    
    def _find_wikitext_content_start(self, text: str) -> int:
        """Find the start of actual content in wikitext, skipping templates."""
        lines = text.split('\n')
        in_template = 0
        offset = 0
        
        for i, line in enumerate(lines[:self.config.max_scan_lines]):
            # Track template depth
            in_template += line.count('{{') - line.count('}}')
            
            if in_template > 0:
                offset += len(line) + 1
                continue
            
            stripped = line.strip()
            
            # Skip empty lines and category links
            if not stripped or stripped.startswith('[[Category:'):
                offset += len(line) + 1
                continue
            
            # Skip __NOTOC__ and similar magic words
            if stripped.startswith('__') and stripped.endswith('__'):
                offset += len(line) + 1
                continue
            
            # Found content
            return offset
            
            offset += len(line) + 1
        
        return 0
    
    def _clean_wikitext(self, text: str) -> str:
        """Clean wikitext markup from text."""
        # Remove <ref>...</ref> and <ref .../> tags
        text = self._ref_tag_pattern.sub('', text)
        
        # Convert [[Link|Display]] to Display, [[Link]] to Link
        text = self._wikilink_pattern.sub(r'\1', text)
        
        # Remove templates (best-effort, handles non-nested)
        # Apply multiple times for nested templates
        for _ in range(3):
            new_text = self._template_pattern.sub('', text)
            if new_text == text:
                break
            text = new_text
        
        # Remove remaining HTML-style tags
        text = self._html_tag_pattern.sub('', text)
        
        # Remove bold/italic markers
        text = re.sub(r"'{2,5}", '', text)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _extract_html(
        self,
        text: str,
        max_chars: int,
    ) -> Tuple[str, ExtractionStrategy, int]:
        """
        Extract excerpt from HTML content.
        
        Looks for mw-parser-output container and meaningful paragraphs.
        """
        # Try to find mw-parser-output container
        content_text = text
        content_start = 0
        strategy = ExtractionStrategy.FIRST_PARAGRAPH
        
        mw_output_match = self._mw_parser_output_pattern.search(text)
        if mw_output_match:
            content_text = mw_output_match.group(1)
            content_start = mw_output_match.start()
            strategy = ExtractionStrategy.MW_PARSER_OUTPUT
        
        # Remove infoboxes and navboxes from the start
        content_text = self._infobox_pattern.sub('', content_text)
        content_text = self._nav_pattern.sub('', content_text)
        
        # Find paragraphs with sufficient text
        paragraphs = []
        for p_match in self._paragraph_pattern.finditer(content_text):
            p_content = p_match.group(1)
            # Strip HTML tags to get text
            p_text = self._html_tag_pattern.sub('', p_content)
            p_text = p_text.strip()
            
            # Skip very short paragraphs
            if len(p_text) >= self.config.min_paragraph_chars:
                paragraphs.append(p_text)
            elif len(p_text) >= 50 and paragraphs:
                # Include shorter paragraphs after we've found the first real one
                paragraphs.append(p_text)
        
        if not paragraphs:
            # Fallback: just strip all HTML and take content
            clean_text = self._html_tag_pattern.sub(' ', content_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            return clean_text[:max_chars], ExtractionStrategy.FALLBACK, 0
        
        # Combine paragraphs up to max_chars
        excerpt = ""
        for p in paragraphs:
            if len(excerpt) + len(p) + 1 > max_chars:
                if len(excerpt) >= self.config.min_chars:
                    break
                # Add partial to meet minimum
                remaining = max_chars - len(excerpt) - 1
                excerpt += " " + p[:remaining]
                break
            excerpt += " " + p if excerpt else p
        
        return excerpt.strip(), strategy, content_start
    
    def _extract_fallback(
        self,
        text: str,
        max_chars: int,
    ) -> Tuple[str, ExtractionStrategy, int]:
        """Fallback extraction for unknown formats."""
        # Strip any obvious HTML
        clean = self._html_tag_pattern.sub(' ', text)
        # Clean wikitext artifacts
        clean = self._clean_wikitext(clean)
        # Clean whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        return clean[:max_chars], ExtractionStrategy.FALLBACK, 0
