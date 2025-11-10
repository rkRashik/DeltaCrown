# DeltaCrown Certificate Fonts

## Noto Sans Bengali

**License:** SIL Open Font License (OFL)  
**Source:** Google Fonts / Noto Fonts Project

### Installation

Download the Noto Sans Bengali Regular font from one of these sources:

1. **Google Fonts** (recommended):
   - Visit: https://fonts.google.com/noto/specimen/Noto+Sans+Bengali
   - Download the font family
   - Extract `NotoSansBengali-Regular.ttf` to this directory

2. **GitHub Repository**:
   - Visit: https://github.com/notofonts/bengali
   - Navigate to: `fonts/NotoSansBengali/unhinted/ttf/`
   - Download `NotoSansBengali-Regular.ttf`

3. **Direct Download** (PowerShell):
   ```powershell
   # From project root
   $url = "https://github.com/notofonts/bengali/raw/main/fonts/NotoSansBengali/unhinted/ttf/NotoSansBengali-Regular.ttf"
   Invoke-WebRequest -Uri $url -OutFile "static/fonts/NotoSansBengali-Regular.ttf"
   ```

### Required Files

Place the following font files in this directory:

- `NotoSansBengali-Regular.ttf` (Required for Bengali certificate text)

### Usage in CertificateService

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Bengali font
font_path = settings.STATIC_ROOT / 'fonts' / 'NotoSansBengali-Regular.ttf'
pdfmetrics.registerFont(TTFont('NotoSansBengali', font_path))
```

### Fallback

If Bengali font is not available, the service will:
1. Log a warning
2. Fall back to standard Helvetica font
3. Bengali text may not render correctly

### Testing

Verify font installation:

```python
python manage.py shell
>>> from reportlab.pdfbase import pdfmetrics
>>> from reportlab.pdfbase.ttfonts import TTFont
>>> from pathlib import Path
>>> font_path = Path('static/fonts/NotoSansBengali-Regular.ttf')
>>> pdfmetrics.registerFont(TTFont('NotoSansBengali', str(font_path)))
>>> print("Font registered successfully!")
```
