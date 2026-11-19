"""PDF processing service using PyMuPDF."""
import os
import hashlib
import re
import logging
from typing import Optional

try:
    import pymupdf as fitz
except ImportError:
    import fitz

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def validate_pdf(file_path: str) -> dict:
    """Validate that a file is a valid PDF."""
    try:
        doc = fitz.open(file_path)
        if doc.page_count == 0:
            doc.close()
            return {'valid': False, 'error': 'PDF has no pages'}
        if doc.needs_pass:
            doc.close()
            return {'valid': False, 'error': 'PDF is encrypted/password-protected'}
        doc.close()
        return {'valid': True, 'error': None}
    except Exception as e:
        return {'valid': False, 'error': f'Invalid PDF file: {str(e)[:200]}'}


def extract_pdf_metadata(file_path: str) -> dict:
    """Extract metadata from a PDF file."""
    metadata = {
        'title': None,
        'authors': None,
        'publication_year': None,
        'total_pages': 0,
        'is_scanned': False,
        'abstract': None,
    }
    try:
        doc = fitz.open(file_path)
        metadata['total_pages'] = doc.page_count
        raw_meta = doc.metadata or {}

        title = (raw_meta.get('title') or '').strip()
        if title and len(title) > 2:
            metadata['title'] = title[:500]

        author = (raw_meta.get('author') or '').strip()
        if author:
            metadata['authors'] = author[:500]

        creation_date = raw_meta.get('creationDate', '')
        if creation_date:
            year_match = re.search(r'(\d{4})', creation_date)
            if year_match:
                yr = int(year_match.group(1))
                if 1900 <= yr <= 2100:
                    metadata['publication_year'] = yr

        # Detect scanned PDFs
        total_text_len = 0
        sample_pages = min(5, doc.page_count)
        for i in range(sample_pages):
            page = doc[i]
            try:
                total_text_len += len(page.get_text().strip())
            except Exception:
                pass

        avg_text = total_text_len / sample_pages if sample_pages > 0 else 0
        metadata['is_scanned'] = avg_text < 50

        # Extract abstract and title from first pages
        if not metadata['is_scanned']:
            first_text = ''
            for i in range(min(3, doc.page_count)):
                try:
                    first_text += doc[i].get_text()
                except Exception:
                    pass

            abstract = _extract_abstract(first_text)
            if abstract:
                metadata['abstract'] = abstract[:2000]

            if not metadata['title'] and doc.page_count > 0:
                try:
                    first_page = doc[0].get_text()
                    guessed = _guess_title_from_text(first_page)
                    if guessed:
                        metadata['title'] = guessed
                except Exception:
                    pass

        doc.close()
    except Exception as e:
        logger.warning(f'Error extracting PDF metadata: {e}')
    return metadata


def _extract_abstract(text: str) -> Optional[str]:
    patterns = [
        r'(?i)abstract[:\s\u2014\u2013-]*\n(.*?)(?:\n\s*(?:1\.|introduction|keywords?|index terms))',
        r'(?i)abstract[:\s\u2014\u2013-]*((?:.|\n){100,1500}?)(?:\n\s*\n|\n(?:1\s|introduction))',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            abstract = re.sub(r'\s+', ' ', abstract)
            if len(abstract) > 50:
                return abstract
    return None


def _guess_title_from_text(text: str) -> Optional[str]:
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:10]:
        if 20 < len(line) < 300 and not any(
            line.lower().startswith(kw)
            for kw in ('abstract', 'introduction', 'keywords', '©', 'doi:', 'arxiv')
        ):
            return line
    return None


def extract_text_by_page(file_path: str) -> list:
    """
    Extract text from each page. Returns list of page dicts (1-indexed).
    """
    pages = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(doc.page_count):
            page = doc[page_num]
            try:
                text = page.get_text()
            except Exception:
                text = ''

            text = _normalize_text(text)
            word_count = len(text.split()) if text else 0

            pages.append({
                'page_number': page_num + 1,
                'text': text,
                'word_count': word_count,
                'is_empty': word_count < 5,
            })
        doc.close()
    except Exception as e:
        logger.error(f'Error extracting text: {e}')
        raise
    return pages


def _normalize_text(text: str) -> str:
    if not text:
        return ''
    text = text.replace('\f', '\n').replace('\r', '\n').replace('\x00', '')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def attempt_ocr(file_path: str) -> list:
    """Attempt OCR on scanned PDFs (requires Tesseract)."""
    pages = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = ''
            try:
                # PyMuPDF OCR support
                tp = page.get_textpage_ocr(flags=0, language='eng')
                text = page.get_text(textpage=tp)
            except Exception:
                try:
                    text = page.get_text()
                except Exception:
                    text = ''

            text = _normalize_text(text)
            word_count = len(text.split()) if text else 0
            pages.append({
                'page_number': page_num + 1,
                'text': text,
                'word_count': word_count,
                'is_empty': word_count < 5,
            })
        doc.close()
    except Exception as e:
        logger.error(f'OCR failed: {e}')
        raise
    return pages
