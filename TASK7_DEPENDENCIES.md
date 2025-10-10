# Task 7 - Required Python Packages

## New Dependencies for Social & Community Integration

### Markdown Processing
```bash
pip install markdown==3.4.4
```
**Purpose:** Convert markdown text to HTML for discussion posts and chat messages.

**Features Used:**
- `markdown.extensions.extra` - Tables, fenced code blocks
- `markdown.extensions.codehilite` - Syntax highlighting
- `markdown.extensions.nl2br` - Newline to `<br>`
- `markdown.extensions.sane_lists` - Better list handling
- `markdown.extensions.smarty` - Smart quotes and dashes

### HTML Sanitization
```bash
pip install bleach==6.0.0
```
**Purpose:** Sanitize HTML to prevent XSS attacks while preserving safe markdown-generated HTML.

**Features Used:**
- Tag whitelist filtering
- Attribute whitelist filtering
- Protocol filtering (http, https, mailto)
- XSS prevention

### Real-time Features (Optional - for Phase 3)
```bash
pip install channels==4.0.0
pip install channels-redis==4.1.0
pip install daphne==4.0.0
```
**Purpose:** WebSocket support for real-time chat and typing indicators.

**Note:** These are for Phase 3 implementation. Not required for Phase 2.

---

## Installation Commands

### Phase 2 (Current - Required Now)
```powershell
# Install markdown and bleach for Phase 2
pip install markdown==3.4.4 bleach==6.0.0
```

### Phase 3 (Future - Real-time Features)
```powershell
# Install Django Channels for real-time WebSocket support
pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0
```

---

## Verification

After installation, verify imports:
```python
python -c "import markdown; import bleach; print('✅ Phase 2 dependencies installed')"
```

---

## Update requirements.txt

Add to your `requirements.txt`:
```
# Task 7 - Social & Community Integration (Phase 2)
markdown==3.4.4
bleach==6.0.0

# Task 7 - Real-time Features (Phase 3 - Optional)
# channels==4.0.0
# channels-redis==4.1.0
# daphne==4.0.0
```

---

## Package Details

### markdown 3.4.4
- **License:** BSD
- **Size:** ~350KB
- **Dependencies:** None
- **Documentation:** https://python-markdown.github.io/

### bleach 6.0.0
- **License:** Apache 2.0
- **Size:** ~120KB
- **Dependencies:** `webencodings`
- **Documentation:** https://bleach.readthedocs.io/

### channels 4.0.0 (Phase 3)
- **License:** BSD
- **Size:** ~600KB
- **Dependencies:** `asgiref`, `django`
- **Documentation:** https://channels.readthedocs.io/

### channels-redis 4.1.0 (Phase 3)
- **License:** BSD
- **Size:** ~40KB
- **Dependencies:** `channels`, `redis`, `msgpack`
- **Documentation:** https://github.com/django/channels_redis

### daphne 4.0.0 (Phase 3)
- **License:** BSD
- **Size:** ~50KB
- **Dependencies:** `twisted`, `autobahn`
- **Documentation:** https://github.com/django/daphne

---

## Security Notes

**bleach Configuration:**
- Whitelist-based HTML filtering (secure by default)
- Prevents `<script>` injection
- Prevents inline JavaScript (`onclick`, `onerror`, etc.)
- Prevents `javascript:` URLs
- Only allows safe protocols (http, https, mailto)

**markdown Configuration:**
- No raw HTML passthrough
- Output format: HTML5
- Safe extensions only (no code execution)
- Combined with bleach for double sanitization

---

## Optional: System-wide Installation

If you want to install for all Python projects:
```powershell
# Global installation (not recommended)
pip install --user markdown==3.4.4 bleach==6.0.0
```

Recommended: Use virtual environment instead.

