"""Render PDF pages to PNG images for Vision AI extraction."""
import pypdfium2 as pdfium
from pathlib import Path


def render_pages(pdf_path: str, output_dir: str | None = None, dpi: int = 250) -> list[str]:
    """Render all PDF pages to PNG. Returns list of image paths."""
    pdf = pdfium.PdfDocument(pdf_path)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    paths = []
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=dpi / 72)
        pil_image = bitmap.to_pil()
        if output_dir:
            path = str(Path(output_dir) / f"page_{i+1:04d}.png")
        else:
            path = pdf_path.replace('.pdf', f'_page_{i+1:04d}.png')
        pil_image.save(path)
        paths.append(path)
    pdf.close()
    return paths
