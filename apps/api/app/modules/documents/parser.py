from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from docx import Document
from pypdf import PdfReader

MAX_PASSAGE_CHARS = 1500


class DocumentExtractionError(Exception):
    """A safe message suitable for the lawyer-facing document status."""


@dataclass(frozen=True)
class ExtractedPassage:
    sequence_number: int
    page_number: int | None
    passage_label: str
    content: str


def _normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _chunks(text: str) -> list[str]:
    text = _normalize(text)
    if not text:
        return []
    chunks: list[str] = []
    remaining = text
    while len(remaining) > MAX_PASSAGE_CHARS:
        split_at = remaining.rfind(" ", 0, MAX_PASSAGE_CHARS + 1)
        if split_at <= 0:
            split_at = MAX_PASSAGE_CHARS
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _blocks(text: str) -> list[str]:
    return [block for raw in re.split(r"\n\s*\n+", text) for block in _chunks(raw)]


def extract_pdf(data: bytes) -> list[ExtractedPassage]:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:  # parser library exceptions are deliberately hidden
        raise DocumentExtractionError("The PDF could not be read.") from exc
    result: list[ExtractedPassage] = []
    sequence = 1
    try:
        for page_number, page in enumerate(reader.pages, start=1):
            page_blocks = _blocks(page.extract_text() or "")
            for page_passage, content in enumerate(page_blocks, start=1):
                result.append(
                    ExtractedPassage(sequence, page_number, f"Page {page_number}, Passage {page_passage}", content)
                )
                sequence += 1
    except Exception as exc:
        raise DocumentExtractionError("The PDF text could not be extracted.") from exc
    return result


def extract_docx(data: bytes) -> list[ExtractedPassage]:
    try:
        document = Document(BytesIO(data))
    except Exception as exc:
        raise DocumentExtractionError("The DOCX file could not be read.") from exc
    result: list[ExtractedPassage] = []
    sequence = 1
    paragraph_number = 0
    for paragraph in document.paragraphs:
        chunks = _chunks(paragraph.text)
        if not chunks:
            continue
        paragraph_number += 1
        for part, content in enumerate(chunks, start=1):
            label = f"Paragraph {paragraph_number}"
            if len(chunks) > 1:
                label += f", Part {part}"
            result.append(ExtractedPassage(sequence, None, label, content))
            sequence += 1
    return result


def extract_txt(data: bytes) -> list[ExtractedPassage]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("The text file must use UTF-8 encoding.") from exc
    result: list[ExtractedPassage] = []
    for sequence, content in enumerate(_blocks(text), start=1):
        result.append(ExtractedPassage(sequence, None, f"Passage {sequence}", content))
    return result


def extract_passages(data: bytes, content_type: str) -> list[ExtractedPassage]:
    if content_type == "application/pdf":
        passages = extract_pdf(data)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        passages = extract_docx(data)
    elif content_type == "text/plain":
        passages = extract_txt(data)
    else:
        raise DocumentExtractionError("This document type is not supported.")
    if not passages:
        raise DocumentExtractionError("No readable text was found. OCR is not available for scanned documents.")
    return passages
