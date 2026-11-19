"""Text chunking service for RAG pipeline."""
import re
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def chunk_pages(
    pages: list[dict],
    document_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    """
    Split page-level text into overlapping chunks.
    Each chunk retains its source page number and document ID.

    Returns list of dicts with keys:
        chunk_id, document_id, chunk_index, content, page_number,
        page_range_start, page_range_end, char_start, char_end
    """
    chunks = []
    chunk_index = 0

    for page in pages:
        if page.get('is_empty') or not page.get('text', '').strip():
            continue

        page_num = page['page_number']
        text = page['text']

        # Split into sentences for smarter chunking
        sentences = _split_into_sentences(text)
        page_chunks = _sentences_to_chunks(sentences, chunk_size, chunk_overlap)

        for chunk_text, char_start, char_end in page_chunks:
            chunk_text = chunk_text.strip()
            if len(chunk_text) < 30:  # skip very short chunks
                continue
            chunks.append({
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_index': chunk_index,
                'content': chunk_text,
                'page_number': page_num,
                'page_range_start': page_num,
                'page_range_end': page_num,
                'char_start': char_start,
                'char_end': char_end,
            })
            chunk_index += 1

    # Deduplicate adjacent very similar chunks
    chunks = _deduplicate_chunks(chunks)
    return chunks


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using simple regex."""
    # Split on sentence-ending punctuation followed by whitespace
    sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    sentences = sentence_endings.split(text)
    # Also split on newlines that separate paragraphs
    result = []
    for sent in sentences:
        sub = sent.split('\n\n')
        result.extend(sub)
    return [s.strip() for s in result if s.strip()]


def _sentences_to_chunks(
    sentences: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[tuple[str, int, int]]:
    """
    Combine sentences into chunks of approximately chunk_size characters.
    Returns list of (chunk_text, char_start, char_end) tuples.
    Overlap is implemented by re-including trailing sentences in the next chunk.
    """
    chunks = []
    current_chunk = []
    current_len = 0
    char_pos = 0

    i = 0
    while i < len(sentences):
        sent = sentences[i]
        sent_len = len(sent)

        if current_len + sent_len > chunk_size and current_chunk:
            # Emit current chunk
            chunk_text = ' '.join(current_chunk)
            chunks.append((chunk_text, char_pos, char_pos + len(chunk_text)))

            # Calculate overlap: go back some sentences
            overlap_text = ''
            overlap_sents = []
            for prev_sent in reversed(current_chunk):
                if len(overlap_text) + len(prev_sent) <= chunk_overlap:
                    overlap_sents.insert(0, prev_sent)
                    overlap_text = ' '.join(overlap_sents)
                else:
                    break

            char_pos += len(chunk_text) + 1
            current_chunk = overlap_sents
            current_len = len(' '.join(current_chunk))

        current_chunk.append(sent)
        current_len += sent_len + 1
        i += 1

    # Emit last chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append((chunk_text, char_pos, char_pos + len(chunk_text)))

    return chunks


def _deduplicate_chunks(chunks: list[dict]) -> list[dict]:
    """Remove duplicate consecutive chunks on the same page."""
    if not chunks:
        return chunks
    result = [chunks[0]]
    for chunk in chunks[1:]:
        prev = result[-1]
        # Only deduplicate if on the same page and identical content
        if prev['page_number'] == chunk['page_number'] and prev['content'].strip() == chunk['content'].strip():
            continue
        result.append(chunk)
    return result

