"""Bounded native media/certificate smoke test; missing native libraries fail.

Run in the isolated Linux/Python 3.12 production environment. This does not
configure Django, access storage, connect to providers or write user records.
"""

from io import BytesIO
import json
import platform


def main():
    import cairo
    import cairocffi
    import cairosvg
    from PIL import Image
    from pypdf import PdfReader
    from reportlab.graphics import renderPDF, renderPM
    from reportlab.pdfgen.canvas import Canvas
    from svglib.svglib import svg2rlg

    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="32"><rect width="64" height="32" fill="#E2B761"/></svg>'
    png = cairosvg.svg2png(bytestring=svg)
    with Image.open(BytesIO(png)) as image:
        assert image.size == (64, 32)
        assert image.convert("RGB").getpixel((2, 2)) == (226, 183, 97)
    assert len(PdfReader(BytesIO(cairosvg.svg2pdf(bytestring=svg))).pages) == 1
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 16, 16)
    context = cairo.Context(surface)
    context.set_source_rgb(1, 1, 1)
    context.paint()
    assert surface.get_width() == 16
    ffi_surface = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, 16, 16)
    assert ffi_surface.get_width() == 16
    drawing = svg2rlg(BytesIO(svg))
    assert drawing is not None
    assert len(PdfReader(BytesIO(renderPDF.drawToString(drawing))).pages) == 1
    # Real svglib -> ReportLab -> rlPyCairo raster rendering used by certificates.
    raster = renderPM.drawToString(drawing, fmt="PNG", backend="rlPyCairo")
    with Image.open(BytesIO(raster)) as image:
        assert image.size == (64, 32)
    output = BytesIO()
    canvas = Canvas(output)
    canvas.drawString(20, 800, "OwnLobby synthetic certificate QA")
    canvas.showPage()
    canvas.save()
    assert "OwnLobby" in PdfReader(BytesIO(output.getvalue())).pages[0].extract_text()
    print(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cairo": cairo.cairo_version_string(),
                "native_svg_pdf_certificate": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
