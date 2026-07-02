from pathlib import Path

import fitz
import pytesseract
from PIL import Image

OCR_DPI = 200


def extract_data_from_transform(file_path: str) -> dict:
    with fitz.open(file_path) as doc:
        text = '\n'.join(page.get_text() for page in doc).strip()
        page_count = doc.page_count

    if not text:
        raise ValueError('No embedded text found in document')

    return {
        'text': text,
        'method': 'transform',
        'page_count': page_count,
    }


# !IMPORTANT: need system level dep: tesseract
def extract_data_from_ocr(file_path: str) -> dict:
    path = Path(file_path)

    if path.suffix.lower() == '.pdf':
        page_texts = []

        with fitz.open(file_path) as doc:
            page_count = doc.page_count

            for page in doc:
                pix = page.get_pixmap(dpi=OCR_DPI)

                image = Image.frombytes(
                    'RGB', [pix.width, pix.height], pix.samples)
                page_texts.append(pytesseract.image_to_string(image))

        text = '\n\n'.join(t.strip() for t in page_texts if t.strip()).strip()
    else:
        page_count = 1

        with Image.open(file_path) as image:
            text = pytesseract.image_to_string(image).strip()

    if not text:
        raise ValueError('OCR produced no text')

    return {
        'text': text,
        'method': 'ocr',
        'page_count': page_count,
    }
