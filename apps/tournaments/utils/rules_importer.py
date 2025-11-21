"""
Tournament Rules PDF Importer

Extracts text from tournament rules PDF files and converts them into HTML
for display in the frontend Rules tab.

Usage:
    from apps.tournaments.utils import import_rules_from_pdf
    
    html = import_rules_from_pdf(tournament, overwrite=True)
"""

import logging
import re
from typing import Optional
from html import escape

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__)


def import_rules_from_pdf(tournament, *, overwrite: bool = True) -> Optional[str]:
    """
    Extracts text from tournament.rules_pdf and converts it to HTML in rules_text.
    
    Args:
        tournament: Tournament model instance
        overwrite: If False, skip if rules_text already has content
        
    Returns:
        Generated HTML string, or None if no import was performed
        
    Raises:
        ImportError: If PyPDF2 is not installed
        FileNotFoundError: If PDF file doesn't exist
        Exception: For other PDF reading errors
    """
    
    # Check if PyPDF2 is available
    if not PYPDF2_AVAILABLE:
        raise ImportError(
            "PyPDF2 is required for PDF import. "
            "Install it with: pip install PyPDF2"
        )
    
    # Check if tournament has a PDF
    if not tournament.rules_pdf or not tournament.rules_pdf.name:
        logger.info(f"Tournament {tournament.id} has no rules_pdf attached")
        return None
    
    # Check if we should skip due to existing content
    if not overwrite and tournament.rules_text and tournament.rules_text.strip():
        logger.info(
            f"Tournament {tournament.id} already has rules_text, "
            f"skipping (overwrite=False)"
        )
        return None
    
    try:
        # Open and read the PDF file
        logger.info(f"Reading PDF from {tournament.rules_pdf.path}")
        
        with open(tournament.rules_pdf.path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            num_pages = len(reader.pages)
            
            logger.info(f"PDF has {num_pages} page(s)")
            
            # Extract text from all pages
            text_content = []
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(page_text)
                        logger.debug(f"Extracted {len(page_text)} chars from page {i+1}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {i+1}: {e}")
                    continue
            
            if not text_content:
                logger.error(f"No text could be extracted from PDF")
                return None
            
            # Join all pages
            full_text = "\n\n".join(text_content)
            
            # Convert to HTML
            html = _convert_text_to_html(full_text)
            
            # Save to tournament
            tournament.rules_text = html
            tournament.save(update_fields=['rules_text'])
            
            logger.info(
                f"Successfully imported {len(full_text)} chars "
                f"({len(html)} HTML chars) to tournament {tournament.id}"
            )
            
            return html
            
    except FileNotFoundError:
        logger.error(f"PDF file not found: {tournament.rules_pdf.path}")
        raise
    except Exception as e:
        logger.error(f"Failed to import rules from PDF: {e}", exc_info=True)
        raise


def _convert_text_to_html(text: str) -> str:
    """
    Converts plain text to HTML with better formatting preservation.
    
    Enhanced process:
    1. Normalize whitespace and line endings
    2. Detect and preserve indentation levels
    3. Identify headings, bullet points, and numbered lists
    4. Create structured HTML with proper spacing
    5. Add CSS classes for styling
    
    Args:
        text: Plain text content from PDF
        
    Returns:
        HTML string with preserved formatting
    """
    
    if not text or not text.strip():
        return ""
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines
    lines = text.split('\n')
    
    html_parts = []
    current_paragraph = []
    current_indent = 0
    
    for line in lines:
        stripped = line.rstrip()
        if not stripped:  # Empty line
            # End current paragraph if we have content
            if current_paragraph:
                html_parts.append(_format_paragraph(current_paragraph, current_indent))
                current_paragraph = []
            continue
        
        # Detect indentation level
        indent = len(line) - len(line.lstrip())
        
        # Check for special elements
        if _is_heading(stripped):
            # End current paragraph first
            if current_paragraph:
                html_parts.append(_format_paragraph(current_paragraph, current_indent))
                current_paragraph = []
            
            # Add heading
            html_parts.append(_format_heading(stripped))
            continue
            
        elif _is_bullet_point(stripped):
            # End current paragraph first
            if current_paragraph:
                html_parts.append(_format_paragraph(current_paragraph, current_indent))
                current_paragraph = []
            
            # Add bullet point
            html_parts.append(_format_bullet_point(stripped))
            continue
            
        elif _is_numbered_item(stripped):
            # End current paragraph first
            if current_paragraph:
                html_parts.append(_format_paragraph(current_paragraph, current_indent))
                current_paragraph = []
            
            # Add numbered item
            html_parts.append(_format_numbered_item(stripped))
            continue
        
        # Regular text line
        # If indentation changed significantly, start new paragraph
        if abs(indent - current_indent) > 2 and current_paragraph:
            html_parts.append(_format_paragraph(current_paragraph, current_indent))
            current_paragraph = []
            current_indent = indent
        
        # Add line to current paragraph
        current_paragraph.append(stripped)
        current_indent = indent
    
    # Don't forget the last paragraph
    if current_paragraph:
        html_parts.append(_format_paragraph(current_paragraph, current_indent))
    
    return '\n'.join(html_parts)


def _is_heading(line: str) -> bool:
    """Check if line looks like a heading."""
    stripped = line.strip()
    
    # Short lines (likely headings)
    if len(stripped) > 100:
        return False
    
    # Mostly uppercase
    alpha_chars = [c for c in stripped if c.isalpha()]
    if not alpha_chars:
        return False
        
    uppercase_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    
    # At least 70% uppercase and doesn't end with period
    return uppercase_ratio >= 0.7 and not stripped.endswith('.')


def _is_bullet_point(line: str) -> bool:
    """Check if line starts with bullet point markers."""
    stripped = line.strip()
    return stripped.startswith(('•', '●', '○', '-', '·', '▪', '▫'))


def _is_numbered_item(line: str) -> bool:
    """Check if line starts with numbering."""
    stripped = line.strip()
    # Match patterns like "1.", "1)", "(1)", "a.", etc.
    return bool(re.match(r'^[\(\[]?\d+[\.\)\]]|\w+[\.\)\]]', stripped))


def _format_heading(text: str) -> str:
    """Format text as a heading."""
    escaped = escape(text.strip())
    return f'<h3 class="rules-heading">{escaped}</h3>'


def _format_bullet_point(text: str) -> str:
    """Format text as a bullet point."""
    # Remove the bullet marker
    content = re.sub(r'^[\s•●○\-·▪▫]+', '', text.strip())
    escaped = escape(content)
    return f'<div class="rules-bullet"><span class="rules-bullet-marker">•</span><span class="rules-bullet-text">{escaped}</span></div>'


def _format_numbered_item(text: str) -> str:
    """Format text as a numbered item."""
    # Extract number/label
    match = re.match(r'^([\(\[]?\d+[\.\)\]]|\w+[\.\)\]])', text.strip())
    if match:
        number = match.group(1)
        content = text.strip()[len(number):].strip()
    else:
        number = "•"
        content = text.strip()
    
    escaped = escape(content)
    return f'<div class="rules-numbered"><span class="rules-number-marker">{number}</span><span class="rules-numbered-text">{escaped}</span></div>'


def _format_paragraph(lines: list, indent: int) -> str:
    """Format lines as a paragraph with proper indentation."""
    if not lines:
        return ""
    
    # Join lines with line breaks
    content = '<br>'.join(escape(line) for line in lines)
    
    # Add indentation class based on indent level
    indent_class = ""
    if indent >= 4:
        indent_class = "rules-indented"
    elif indent >= 2:
        indent_class = "rules-indented-sm"
    
    css_class = f"rules-paragraph {indent_class}".strip()
    
    return f'<p class="{css_class}">{content}</p>'


def preview_pdf_text(tournament, max_chars: int = 1000) -> Optional[str]:
    """
    Preview the text that would be extracted from the PDF (for testing).
    
    Args:
        tournament: Tournament model instance
        max_chars: Maximum characters to return
        
    Returns:
        Preview of extracted text, or None if no PDF
    """
    
    if not PYPDF2_AVAILABLE:
        return "PyPDF2 not installed"
    
    if not tournament.rules_pdf or not tournament.rules_pdf.name:
        return None
    
    try:
        with open(tournament.rules_pdf.path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            first_page = reader.pages[0]
            text = first_page.extract_text()
            
            if len(text) > max_chars:
                return text[:max_chars] + "..."
            return text
            
    except Exception as e:
        return f"Error: {str(e)}"
