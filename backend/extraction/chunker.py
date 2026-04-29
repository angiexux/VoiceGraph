"""Text chunking utilities for the extraction pipeline.

Splits text into overlapping chunks at sentence boundaries,
approximating token count by whitespace-delimited word count.
"""

from __future__ import annotations

import re
from typing import Any


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """Split *text* into overlapping chunks at sentence boundaries.

    Token count is approximated as word count (whitespace-split).

    Args:
        text: The full text to chunk.
        chunk_size: Target number of tokens (words) per chunk.
        overlap: Number of tokens to overlap between consecutive chunks.

    Returns:
        A list of text chunks.
    """
    if not text or not text.strip():
        return []

    # Split into sentences — handle ". ", "! ", "? " and newline boundaries
    sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        # If a single sentence exceeds chunk_size, add it as its own chunk
        if sentence_words > chunk_size:
            # Flush current buffer first
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                current_sentences = []
                current_word_count = 0
            chunks.append(sentence)
            continue

        # If adding this sentence would exceed the chunk size, flush
        if current_word_count + sentence_words > chunk_size and current_sentences:
            chunks.append(" ".join(current_sentences))

            # Build overlap: walk backwards through current_sentences
            # to collect ~overlap words
            overlap_sentences: list[str] = []
            overlap_count = 0
            for s in reversed(current_sentences):
                s_words = len(s.split())
                if overlap_count + s_words > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_count += s_words

            current_sentences = overlap_sentences
            current_word_count = overlap_count

        current_sentences.append(sentence)
        current_word_count += sentence_words

    # Flush remaining
    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


def chunk_text_hierarchical(
    text: str,
    parent_size: int = 1000,
    child_size: int = 200,
    parent_overlap: int = 100,
    child_overlap: int = 20,
) -> list[dict[str, Any]]:
    """Split text into parent-child chunk pairs for retrieval.

    Parent chunks (~1000 words) provide context for the LLM.
    Child chunks (~200 words) are used for precise retrieval matching.
    Retrieval finds the child chunk, returns the parent for LLM context.

    Returns:
        List of dicts: {"parent": str, "children": list[str], "parent_index": int}
    """
    from typing import Any  # already imported at module level in most cases

    parent_chunks = chunk_text(text, chunk_size=parent_size, overlap=parent_overlap)
    result: list[dict[str, Any]] = []

    for idx, parent in enumerate(parent_chunks):
        children = chunk_text(parent, chunk_size=child_size, overlap=child_overlap)
        result.append({
            "parent": parent,
            "children": children,
            "parent_index": idx,
        })

    return result
