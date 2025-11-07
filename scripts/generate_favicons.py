"""
Generate favicon files from the new logo SVG.

Run this script to create all favicon sizes from static/img/deltaCrown_logos/logo.svg

NOTE: This script requires manual conversion first!
Since SVG to PNG conversion requires external tools on Windows,
please follow these steps:

1. Open static/img/deltaCrown_logos/logo.svg in a browser or image editor
2. Export/Save as PNG at 512x512 pixels to static/img/favicon/logo-source.png
3. Run this script to generate all favicon sizes from that PNG

Or use an online tool like https://realfavicongenerator.net/
"""
from pathlib import Path
from PIL import Image

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_PNG = BASE_DIR / "static" / "img" / "deltaCrown_logos" / "logo.png"
FAVICON_DIR = BASE_DIR / "static" / "img" / "favicon"

# Sizes to generate
SIZES = [16, 32, 48, 64, 180, 192, 512]


def png_to_resized_png(source_path, output_path, size):
    """Resize PNG to specified size."""
    img = Image.open(source_path)
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    img.save(output_path, "PNG")
    print(f"✓ Generated {output_path.name}")


def create_ico(png_path_16, png_path_32, png_path_48, output_path):
    """Create .ico file from PNG files."""
    img_16 = Image.open(png_path_16)
    img_32 = Image.open(png_path_32)
    img_48 = Image.open(png_path_48)
    
    img_16.save(
        output_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[img_32, img_48]
    )
    print(f"✓ Generated {output_path.name}")


def main():
    print("Generating favicon files from new logo...")
    print(f"Source: {SOURCE_PNG}")
    print(f"Output: {FAVICON_DIR}\n")
    
    if not SOURCE_PNG.exists():
        print(f"❌ Error: Source PNG not found at {SOURCE_PNG}")
        print("\nPlease ensure the PNG logo exists at the specified path.")
        return
    
    # Ensure favicon directory exists
    FAVICON_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate PNG files for each size
    png_files = {}
    for size in SIZES:
        output_path = FAVICON_DIR / f"favicon-{size}x{size}.png"
        png_to_resized_png(SOURCE_PNG, output_path, size)
        png_files[size] = output_path
    
    # Create favicon.ico from 16x16, 32x32, and 48x48
    ico_path = FAVICON_DIR / "favicon.ico"
    create_ico(png_files[16], png_files[32], png_files[48], ico_path)
    
    print("\n✅ All favicon files generated successfully!")
    print(f"\nFiles created in: {FAVICON_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
