"""
Markdown Processing Service - Render and sanitize markdown content (Task 7 Phase 2)

Handles markdown rendering with HTML sanitization for security.
"""
import re
import markdown
import bleach
from typing import List, Optional
from django.utils.safestring import mark_safe


class MarkdownProcessor:
    """
    Process markdown content with HTML sanitization.
    """
    
    # Allowed HTML tags after markdown conversion
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 's', 'del', 'ins',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'code', 'pre',
        'ul', 'ol', 'li',
        'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr',
        'span', 'div',
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'rel', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'code': ['class'],
        'pre': ['class'],
        'span': ['class'],
        'div': ['class'],
    }
    
    # Allowed URL schemes
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']
    
    # Markdown extensions to use
    MARKDOWN_EXTENSIONS = [
        'markdown.extensions.extra',      # Tables, fenced code, etc.
        'markdown.extensions.codehilite',  # Code syntax highlighting
        'markdown.extensions.nl2br',       # Newline to <br>
        'markdown.extensions.sane_lists',  # Better list handling
        'markdown.extensions.smarty',      # Smart quotes and dashes
    ]
    
    @classmethod
    def render_markdown(cls, text: str) -> str:
        """
        Convert markdown to safe HTML.
        
        Args:
            text: Markdown text
            
        Returns:
            Safe HTML string
        """
        if not text:
            return ''
        
        # Convert markdown to HTML
        html = markdown.markdown(
            text,
            extensions=cls.MARKDOWN_EXTENSIONS,
            output_format='html5'
        )
        
        # Sanitize HTML
        clean_html = cls.sanitize_html(html)
        
        return mark_safe(clean_html)
    
    @classmethod
    def sanitize_html(cls, html: str) -> str:
        """
        Sanitize HTML to prevent XSS attacks.
        
        Args:
            html: HTML string
            
        Returns:
            Sanitized HTML string
        """
        if not html:
            return ''
        
        # Clean HTML with bleach
        clean = bleach.clean(
            html,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            protocols=cls.ALLOWED_PROTOCOLS,
            strip=True
        )
        
        # Add target="_blank" to external links
        clean = cls._add_external_link_attrs(clean)
        
        return clean
    
    @staticmethod
    def _add_external_link_attrs(html: str) -> str:
        """
        Add target="_blank" and rel="noopener noreferrer" to external links.
        
        Args:
            html: HTML string
            
        Returns:
            Modified HTML string
        """
        # Find all <a> tags without target attribute
        pattern = r'<a href="(https?://[^"]+)"([^>]*)>'
        
        def replace_link(match):
            url = match.group(1)
            attrs = match.group(2)
            
            # Add target and rel if not present
            if 'target=' not in attrs:
                attrs += ' target="_blank"'
            if 'rel=' not in attrs:
                attrs += ' rel="noopener noreferrer"'
            
            return f'<a href="{url}"{attrs}>'
        
        return re.sub(pattern, replace_link, html)
    
    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """
        Extract @mentions from text.
        
        Args:
            text: Text content
            
        Returns:
            List of mentioned usernames
        """
        # Match @username or @"username with spaces"
        pattern = r'@(?:"([^"]+)"|(\w+))'
        matches = re.finditer(pattern, text)
        
        mentions = []
        for match in matches:
            username = match.group(1) or match.group(2)
            if username not in mentions:
                mentions.append(username)
        
        return mentions
    
    @staticmethod
    def extract_links(text: str) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: Text content
            
        Returns:
            List of URLs
        """
        # Match URLs
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        matches = re.finditer(pattern, text)
        
        links = []
        for match in matches:
            url = match.group(0)
            if url not in links:
                links.append(url)
        
        return links
    
    @staticmethod
    def truncate_html(html: str, max_length: int = 200, suffix: str = '...') -> str:
        """
        Truncate HTML content preserving tags.
        
        Args:
            html: HTML string
            max_length: Maximum character length
            suffix: Suffix to add if truncated
            
        Returns:
            Truncated HTML
        """
        # Strip HTML tags for length calculation
        text = bleach.clean(html, tags=[], strip=True)
        
        if len(text) <= max_length:
            return html
        
        # Truncate text
        truncated_text = text[:max_length].rsplit(' ', 1)[0] + suffix
        
        return truncated_text
    
    @staticmethod
    def strip_markdown(text: str) -> str:
        """
        Strip markdown formatting from text.
        
        Args:
            text: Markdown text
            
        Returns:
            Plain text
        """
        if not text:
            return ''
        
        # Convert to HTML then strip tags
        html = markdown.markdown(text)
        plain = bleach.clean(html, tags=[], strip=True)
        
        return plain
    
    @classmethod
    def preview_text(cls, text: str, max_length: int = 200) -> str:
        """
        Generate a plain text preview from markdown.
        
        Args:
            text: Markdown text
            max_length: Maximum preview length
            
        Returns:
            Plain text preview
        """
        # Strip markdown
        plain = cls.strip_markdown(text)
        
        # Truncate
        if len(plain) <= max_length:
            return plain
        
        return plain[:max_length].rsplit(' ', 1)[0] + '...'
    
    @staticmethod
    def highlight_code(code: str, language: str = 'python') -> str:
        """
        Highlight code with syntax highlighting.
        
        Args:
            code: Code string
            language: Programming language
            
        Returns:
            HTML with syntax highlighting
        """
        # Use markdown code block
        markdown_code = f'```{language}\n{code}\n```'
        
        html = markdown.markdown(
            markdown_code,
            extensions=['markdown.extensions.codehilite']
        )
        
        return mark_safe(html)
    
    @staticmethod
    def create_table_of_contents(markdown_text: str) -> List[dict]:
        """
        Extract table of contents from markdown headers.
        
        Args:
            markdown_text: Markdown text
            
        Returns:
            List of dicts with 'level', 'title', 'anchor'
        """
        toc = []
        
        # Match markdown headers
        pattern = r'^(#{1,6})\s+(.+)$'
        matches = re.finditer(pattern, markdown_text, re.MULTILINE)
        
        for match in matches:
            level = len(match.group(1))  # Count # symbols
            title = match.group(2).strip()
            anchor = re.sub(r'[^\w\s-]', '', title.lower()).replace(' ', '-')
            
            toc.append({
                'level': level,
                'title': title,
                'anchor': anchor
            })
        
        return toc
    
    @staticmethod
    def embed_media(text: str) -> str:
        """
        Convert media URLs to embed HTML.
        
        Supports:
        - YouTube videos
        - Twitch streams/videos
        - Twitter/X posts
        - Discord invites
        
        Args:
            text: Text with URLs
            
        Returns:
            Text with embedded media HTML
        """
        # YouTube embeds
        youtube_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
        text = re.sub(
            youtube_pattern,
            r'<div class="video-embed youtube"><iframe src="https://www.youtube.com/embed/\1" frameborder="0" allowfullscreen></iframe></div>',
            text
        )
        
        # Twitch embeds (streams)
        twitch_stream_pattern = r'https?://(?:www\.)?twitch\.tv/([a-zA-Z0-9_]+)(?:\?|$)'
        text = re.sub(
            twitch_stream_pattern,
            r'<div class="video-embed twitch"><iframe src="https://player.twitch.tv/?channel=\1&parent=deltacrown.gg" frameborder="0" allowfullscreen></iframe></div>',
            text
        )
        
        # Twitch embeds (videos)
        twitch_video_pattern = r'https?://(?:www\.)?twitch\.tv/videos/([0-9]+)'
        text = re.sub(
            twitch_video_pattern,
            r'<div class="video-embed twitch"><iframe src="https://player.twitch.tv/?video=\1&parent=deltacrown.gg" frameborder="0" allowfullscreen></iframe></div>',
            text
        )
        
        # Discord invites
        discord_pattern = r'https?://discord\.gg/([a-zA-Z0-9]+)'
        text = re.sub(
            discord_pattern,
            r'<div class="discord-invite"><a href="https://discord.gg/\1" target="_blank" rel="noopener noreferrer">🎮 Join Discord: discord.gg/\1</a></div>',
            text
        )
        
        return text
    
    @classmethod
    def render_with_embeds(cls, markdown_text: str) -> str:
        """
        Render markdown with embedded media.
        
        Args:
            markdown_text: Markdown text
            
        Returns:
            Safe HTML with embedded media
        """
        # First, embed media URLs
        text_with_embeds = cls.embed_media(markdown_text)
        
        # Then render markdown
        html = cls.render_markdown(text_with_embeds)
        
        return html
    
    @staticmethod
    def validate_markdown(text: str) -> tuple[bool, Optional[str]]:
        """
        Validate markdown text.
        
        Args:
            text: Markdown text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text or not text.strip():
            return False, "Content cannot be empty"
        
        if len(text) > 50000:
            return False, "Content exceeds maximum length (50,000 characters)"
        
        # Check for suspicious content
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'onerror=',
            r'onclick=',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "Content contains potentially malicious code"
        
        return True, None
    
    @staticmethod
    def count_words(markdown_text: str) -> int:
        """
        Count words in markdown text.
        
        Args:
            markdown_text: Markdown text
            
        Returns:
            Word count
        """
        # Strip markdown formatting
        plain = bleach.clean(
            markdown.markdown(markdown_text),
            tags=[],
            strip=True
        )
        
        # Count words
        words = plain.split()
        return len(words)
    
    @staticmethod
    def estimate_reading_time(markdown_text: str, words_per_minute: int = 200) -> int:
        """
        Estimate reading time in minutes.
        
        Args:
            markdown_text: Markdown text
            words_per_minute: Average reading speed
            
        Returns:
            Estimated reading time in minutes
        """
        word_count = MarkdownProcessor.count_words(markdown_text)
        minutes = max(1, round(word_count / words_per_minute))
        return minutes
