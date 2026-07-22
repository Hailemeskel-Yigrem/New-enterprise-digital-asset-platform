"""Full-text search document indexing helpers."""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from vaultforge.core.logging import get_logger

log = get_logger(__name__)

WHITESPACE_RE = re.compile(r"\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
NON_ALNUM_RE = re.compile(r"[^\w\s]", re.UNICODE)


class IndexField(StrEnum):
    TITLE = "title"
    BODY = "body"
    FILENAME = "filename"
    TAGS = "tags"
    METADATA = "metadata"
    AUTHOR = "author"
    FOLDER_PATH = "folder_path"


class IndexAnalyzer(StrEnum):
    STANDARD = "standard"
    KEYWORD = "keyword"
    NGRAM = "ngram"
    EDGE_NGRAM = "edge_ngram"


@dataclass(slots=True)
class IndexDocument:
    """Normalized document payload for search indexing."""

    organization_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    title: str
    body: str = ""
    filename: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    author_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    folder_path: str = ""
    mime_type: str = ""
    language: str = "en"
    version: int = 1
    updated_at: datetime | None = None

    def content_hash(self) -> str:
        payload = "|".join(
            [
                self.title,
                self.body,
                self.filename,
                ",".join(sorted(self.tags)),
                str(sorted(self.metadata.items())),
                str(self.version),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class IndexToken:
    field: IndexField
    term: str
    position: int
    weight: float = 1.0


@dataclass(slots=True)
class IndexResult:
    document_id: uuid.UUID
    tokens: list[IndexToken]
    content_hash: str
    indexed_fields: list[IndexField]
    token_count: int
    skipped: bool = False
    reason: str | None = None


@dataclass(slots=True)
class BatchIndexResult:
    total: int
    indexed: int
    skipped: int
    errors: int
    results: list[IndexResult] = field(default_factory=list)


class TextNormalizer:
    """Normalize text for consistent tokenization."""

    def __init__(self, *, lowercase: bool = True, strip_html: bool = True) -> None:
        self.lowercase = lowercase
        self.strip_html = strip_html

    def normalize(self, text: str) -> str:
        if self.strip_html:
            text = HTML_TAG_RE.sub(" ", text)
        text = NON_ALNUM_RE.sub(" ", text)
        text = WHITESPACE_RE.sub(" ", text).strip()
        if self.lowercase:
            text = text.lower()
        return text


class Tokenizer:
    """Split normalized text into weighted tokens."""

    def __init__(
        self,
        *,
        min_token_length: int = 2,
        max_token_length: int = 64,
        stop_words: frozenset[str] | None = None,
    ) -> None:
        self.min_token_length = min_token_length
        self.max_token_length = max_token_length
        self.stop_words = stop_words or _DEFAULT_STOP_WORDS

    def tokenize(
        self, text: str, field: IndexField, *, base_weight: float = 1.0
    ) -> list[IndexToken]:
        normalized = TextNormalizer().normalize(text)
        if not normalized:
            return []
        tokens: list[IndexToken] = []
        for position, raw in enumerate(normalized.split()):
            if len(raw) < self.min_token_length or len(raw) > self.max_token_length:
                continue
            if raw in self.stop_words:
                continue
            weight = base_weight * _field_weight(field)
            tokens.append(IndexToken(field=field, term=raw, position=position, weight=weight))
        return tokens


_FIELD_WEIGHTS: dict[IndexField, float] = {
    IndexField.TITLE: 3.0,
    IndexField.FILENAME: 2.5,
    IndexField.TAGS: 2.0,
    IndexField.BODY: 1.0,
    IndexField.METADATA: 0.8,
    IndexField.AUTHOR: 0.5,
    IndexField.FOLDER_PATH: 1.2,
}

_DEFAULT_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "that",
        "the",
        "to",
        "was",
        "were",
        "will",
        "with",
        "this",
        "but",
        "they",
        "have",
        "had",
        "what",
        "when",
        "where",
        "who",
        "which",
        "why",
        "how",
    }
)


def _field_weight(field: IndexField) -> float:
    return _FIELD_WEIGHTS.get(field, 1.0)


@dataclass(slots=True)
class NgramGenerator:
    min_n: int = 3
    max_n: int = 5

    def generate(self, term: str) -> list[str]:
        if len(term) < self.min_n:
            return [term]
        ngrams: list[str] = []
        for n in range(self.min_n, min(self.max_n, len(term)) + 1):
            for i in range(len(term) - n + 1):
                ngrams.append(term[i : i + n])
        return ngrams


@dataclass(slots=True)
class DocumentIndexer:
    """Build searchable token streams from domain documents."""

    tokenizer: Tokenizer = field(default_factory=Tokenizer)
    include_ngrams: bool = False
    ngram_generator: NgramGenerator = field(default_factory=NgramGenerator)
    max_body_tokens: int = 10000

    def index_document(self, document: IndexDocument) -> IndexResult:
        content_hash = document.content_hash()
        if not document.title.strip() and not document.body.strip():
            return IndexResult(
                document_id=document.resource_id,
                tokens=[],
                content_hash=content_hash,
                indexed_fields=[],
                token_count=0,
                skipped=True,
                reason="empty content",
            )

        all_tokens: list[IndexToken] = []
        indexed_fields: list[IndexField] = []

        if document.title.strip():
            tokens = self.tokenizer.tokenize(document.title, IndexField.TITLE)
            all_tokens.extend(tokens)
            indexed_fields.append(IndexField.TITLE)

        if document.filename.strip():
            tokens = self.tokenizer.tokenize(document.filename, IndexField.FILENAME)
            all_tokens.extend(tokens)
            indexed_fields.append(IndexField.FILENAME)

        if document.body.strip():
            body_tokens = self.tokenizer.tokenize(document.body, IndexField.BODY)
            if len(body_tokens) > self.max_body_tokens:
                body_tokens = body_tokens[: self.max_body_tokens]
            all_tokens.extend(body_tokens)
            indexed_fields.append(IndexField.BODY)

        for tag in document.tags:
            tag_tokens = self.tokenizer.tokenize(tag, IndexField.TAGS, base_weight=1.5)
            all_tokens.extend(tag_tokens)
        if document.tags:
            indexed_fields.append(IndexField.TAGS)

        for key, value in document.metadata.items():
            meta_text = f"{key} {value}"
            meta_tokens = self.tokenizer.tokenize(meta_text, IndexField.METADATA, base_weight=0.7)
            all_tokens.extend(meta_tokens)
        if document.metadata:
            indexed_fields.append(IndexField.METADATA)

        if document.folder_path.strip():
            path_tokens = self.tokenizer.tokenize(document.folder_path, IndexField.FOLDER_PATH)
            all_tokens.extend(path_tokens)
            indexed_fields.append(IndexField.FOLDER_PATH)

        if self.include_ngrams:
            all_tokens = self._expand_ngrams(all_tokens)

        deduped = self._dedupe_tokens(all_tokens)
        log.debug(
            "document_indexed",
            resource_id=str(document.resource_id),
            token_count=len(deduped),
            fields=[f.value for f in indexed_fields],
        )
        return IndexResult(
            document_id=document.resource_id,
            tokens=deduped,
            content_hash=content_hash,
            indexed_fields=indexed_fields,
            token_count=len(deduped),
        )

    def index_batch(self, documents: Sequence[IndexDocument]) -> BatchIndexResult:
        results: list[IndexResult] = []
        indexed = skipped = errors = 0
        for document in documents:
            try:
                result = self.index_document(document)
                results.append(result)
                if result.skipped:
                    skipped += 1
                else:
                    indexed += 1
            except Exception as exc:
                errors += 1
                log.warning(
                    "index_document_failed", resource_id=str(document.resource_id), error=str(exc)
                )
                results.append(
                    IndexResult(
                        document_id=document.resource_id,
                        tokens=[],
                        content_hash="",
                        indexed_fields=[],
                        token_count=0,
                        skipped=True,
                        reason=str(exc),
                    )
                )
        return BatchIndexResult(
            total=len(documents),
            indexed=indexed,
            skipped=skipped,
            errors=errors,
            results=results,
        )

    def build_inverted_index(
        self, results: Iterable[IndexResult]
    ) -> dict[str, list[tuple[uuid.UUID, float, IndexField]]]:
        inverted: dict[str, list[tuple[uuid.UUID, float, IndexField]]] = {}
        for result in results:
            if result.skipped:
                continue
            for token in result.tokens:
                inverted.setdefault(token.term, []).append(
                    (result.document_id, token.weight, token.field)
                )
        return inverted

    def extract_snippet(
        self,
        body: str,
        query_terms: list[str],
        *,
        context_words: int = 12,
        max_snippets: int = 3,
    ) -> list[str]:
        normalized_body = TextNormalizer(strip_html=True).normalize(body)
        words = normalized_body.split()
        if not words:
            return []
        term_set = {t.lower() for t in query_terms}
        snippets: list[str] = []
        for i, word in enumerate(words):
            if word not in term_set:
                continue
            start = max(0, i - context_words)
            end = min(len(words), i + context_words + 1)
            snippet = " ".join(words[start:end])
            if snippet not in snippets:
                snippets.append(snippet)
            if len(snippets) >= max_snippets:
                break
        return snippets

    def _expand_ngrams(self, tokens: list[IndexToken]) -> list[IndexToken]:
        expanded = list(tokens)
        for token in tokens:
            for ngram in self.ngram_generator.generate(token.term):
                if ngram != token.term:
                    expanded.append(
                        IndexToken(
                            field=token.field,
                            term=ngram,
                            position=token.position,
                            weight=token.weight * 0.5,
                        )
                    )
        return expanded

    def _dedupe_tokens(self, tokens: list[IndexToken]) -> list[IndexToken]:
        seen: set[tuple[str, IndexField, int]] = set()
        deduped: list[IndexToken] = []
        for token in tokens:
            key = (token.term, token.field, token.position)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(token)
        return deduped


def document_from_record(
    *,
    organization_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    title: str,
    body: str = "",
    filename: str = "",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    author_id: uuid.UUID | None = None,
    folder_id: uuid.UUID | None = None,
    folder_path: str = "",
    mime_type: str = "",
    version: int = 1,
    updated_at: datetime | None = None,
) -> IndexDocument:
    """Factory helper for building IndexDocument from persistence records."""
    return IndexDocument(
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        title=title,
        body=body,
        filename=filename,
        tags=tags or [],
        metadata=metadata or {},
        author_id=author_id,
        folder_id=folder_id,
        folder_path=folder_path,
        mime_type=mime_type,
        version=version,
        updated_at=updated_at,
    )
